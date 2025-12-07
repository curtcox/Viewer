/**
 * URL Editor Application
 * 
 * Provides interactive editing of chained server URLs with live preview and validation.
 * @param {object} ace - Ace editor instance
 * @param {string} initialUrl - Initial URL to populate the editor
 */
(function(ace, initialUrl) {
    'use strict';

    let editor;
    
    // Try to initialize Ace editor, fall back to textarea if not available
    if (typeof ace !== 'undefined' && ace.edit) {
        try {
            editor = ace.edit("url-editor");
            editor.setTheme("ace/theme/textmate");
            editor.session.setMode("ace/mode/text");
            editor.setOptions({
                fontSize: "14px",
                showPrintMargin: false,
                highlightActiveLine: true,
                wrap: true
            });
            // Set initial content
            editor.setValue(initialUrl, -1);
        } catch (e) {
            console.error("Failed to initialize Ace editor:", e);
            editor = createFallbackEditor(initialUrl);
        }
    } else {
        console.warn("Ace editor not available, using fallback textarea");
        editor = createFallbackEditor(initialUrl);
    }
    
    /**
     * Create a fallback textarea-based editor when Ace is not available
     */
    function createFallbackEditor(content) {
        const editorDiv = document.getElementById("url-editor");
        editorDiv.innerHTML = '';
        editorDiv.style.backgroundColor = '#ffffff';
        editorDiv.style.display = 'block';
        
        const textarea = document.createElement('textarea');
        textarea.id = 'url-editor-textarea';
        textarea.className = 'url-editor-textarea';
        textarea.setAttribute('placeholder', 'Enter URL path elements (one per line or separated by /)');
        textarea.setAttribute('aria-label', 'URL Editor');
        
        // Aggressive inline styling to ensure visibility
        textarea.style.width = '100%';
        textarea.style.height = '100%';
        textarea.style.minHeight = '350px';
        textarea.style.padding = '12px';
        textarea.style.fontFamily = '"Courier New", Courier, monospace';
        textarea.style.fontSize = '16px';
        textarea.style.lineHeight = '1.6';
        textarea.style.border = '2px solid #ced4da';
        textarea.style.borderRadius = '4px';
        textarea.style.resize = 'none';
        textarea.style.backgroundColor = '#ffffff';
        textarea.style.color = '#212529';
        textarea.style.display = 'block';
        textarea.style.boxSizing = 'border-box';
        textarea.style.outline = 'none';
        textarea.value = content;
        
        editorDiv.appendChild(textarea);
        
        // Force focus to make it visible
        setTimeout(() => textarea.focus(), 100);
        
        // Create Ace-compatible wrapper
        return {
            getValue: () => textarea.value,
            setValue: (value) => { textarea.value = value; },
            session: {
                on: (event, callback) => {
                    if (event === 'change') {
                        textarea.addEventListener('input', callback);
                    }
                }
            }
        };
    }
    
    // URL Editor Core Logic
    class URLEditorApp {
        constructor() {
            this.editor = editor;
            this.currentUrl = "";
            this.setupEventListeners();
            this.updateFromEditor();
        }
        
        setupEventListeners() {
            // Update on editor change
            this.editor.session.on('change', () => {
                this.updateFromEditor();
            });
            
            // Copy URL button
            document.getElementById('copy-url-btn').addEventListener('click', () => {
                this.copyCurrentUrl();
            });
            
            // Open URL button
            document.getElementById('open-url-btn').addEventListener('click', () => {
                this.openCurrentUrl();
            });
            
            // Listen to hash changes
            window.addEventListener('hashchange', () => {
                this.loadFromHash();
            });
        }
        
        updateFromEditor() {
            const editorContent = this.editor.getValue();
            this.currentUrl = this.normalizeUrl(editorContent);
            this.updateHash();
            this.updateUI();
        }
        
        normalizeUrl(content) {
            // Handle CID literal conversion (lines starting with #)
            // Split into lines directly without redundant replacement
            const lines = content.split(/\r\n|\n|\r/);
            const segments = [];
            
            for (let line of lines) {
                line = line.trim();
                if (!line) continue;
                
                if (line.startsWith('#')) {
                    // Convert text to CID literal
                    // For now, just use the text as-is
                    // In production, this would convert to actual CID format
                    const cidText = line.substring(1).trim();
                    const cidPath = this.textToCidLiteral(cidText);
                    segments.push(cidPath);
                } else {
                    segments.push(line);
                }
            }
            
            // Build URL from segments
            const url = '/' + segments.join('/');
            
            // Clean up multiple slashes
            return url.replace(/\/+/g, '/');
        }
        
        textToCidLiteral(text) {
            // Convert text to CID literal format
            // This is a simplified version - actual implementation would use proper CID encoding
            const base64like = btoa(text).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
            return `AAAAAAA${base64like.substring(0, 20)}`;
        }
        
        updateHash() {
            // Update URL hash without triggering hashchange
            const newHash = '#' + this.currentUrl;
            if (window.location.hash !== newHash) {
                history.replaceState(null, null, newHash);
            }
        }
        
        loadFromHash() {
            const hash = window.location.hash;
            if (hash && hash.length > 1) {
                const url = hash.substring(1); // Remove #
                this.editor.setValue(url, -1);
            }
        }
        
        updateUI() {
            this.updateIndicators();
        }
        
        updateIndicators() {
            const lines = this.parseUrlLines();
            const indicatorsList = document.getElementById('indicators-list');
            
            if (lines.length === 0) {
                indicatorsList.innerHTML = '<div class="text-muted text-center">Edit URL to see indicators</div>';
                document.getElementById('final-output').textContent = '-';
                return;
            }
            
            let html = '';
            for (let i = 0; i < lines.length; i++) {
                html += this.renderIndicatorRow(lines[i], i);
            }
            indicatorsList.innerHTML = html;
            
            // Setup hover listeners for indicators
            this.setupHoverListeners();
            
            // Fetch preview data for each line asynchronously
            for (let i = 0; i < lines.length; i++) {
                this.fetchPreviewData(lines, i);
            }
            
            // Update final output with full URL
            this.fetchFinalOutput();
        }
        
        setupHoverListeners() {
            const indicators = document.querySelectorAll('.indicator');
            const sectionTitle = document.getElementById('section-title-text');
            const originalTitle = 'Line Indicators';
            
            indicators.forEach(indicator => {
                indicator.addEventListener('mouseenter', (e) => {
                    const detail = e.target.getAttribute('data-detail');
                    if (detail) {
                        sectionTitle.textContent = detail;
                    }
                });
                
                indicator.addEventListener('mouseleave', () => {
                    sectionTitle.textContent = originalTitle;
                });
            });
        }
        
        parseUrlLines() {
            const editorContent = this.editor.getValue();
            const lines = editorContent.split(/\r\n|\n|\r/).filter(l => l.trim());
            
            return lines.map(line => ({
                text: line.trim(),
                isValidSegment: this.isValidPathSegment(line.trim()),
                isServer: this.isKnownServer(line.trim()),
                isValidCid: this.isValidCid(line.trim()),
                supportsChaining: this.supportsChaining(line.trim()),
                language: this.getLanguage(line.trim())
            }));
        }
        
        isValidPathSegment(text) {
            // Simple validation - non-empty and URL-safe
            return text.length > 0 && !/[\s<>"]/.test(text);
        }
        
        isKnownServer(text) {
            // Placeholder - would check against known servers
            const knownServers = ['echo', 'markdown', 'shell', 'ai_stub', 'jinja', 'glom'];
            const cleaned = text.replace(/^#+/, '').replace(/^[/]+/, '');
            return knownServers.includes(cleaned);
        }
        
        isValidCid(text) {
            // Check if text starts with # or looks like a CID
            return text.startsWith('#') || /^AAAAAAA[A-Za-z0-9_-]+$/.test(text);
        }
        
        supportsChaining(text) {
            // Placeholder - would check server capabilities
            const cleaned = text.replace(/^#+/, '').replace(/^[/]+/, '');
            return this.isKnownServer(cleaned);
        }
        
        getLanguage(text) {
            // Placeholder - would detect language
            const cleaned = text.replace(/^#+/, '').replace(/^[/]+/, '');
            if (this.isKnownServer(cleaned)) {
                return 'python';
            }
            return '-';
        }
        
        escapeHtml(text) {
            // Escape HTML to prevent XSS
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        renderIndicatorRow(line, index) {
            const indicators = [
                { label: 'Valid', value: line.isValidSegment, detail: `Valid: ${line.isValidSegment ? 'Yes' : 'No'}` },
                { label: 'Server', value: line.isServer, detail: `Server: ${line.isServer ? 'Yes' : 'No'}` },
                { label: 'CID', value: line.isValidCid, detail: `CID: ${line.isValidCid ? 'Yes' : 'No'}` },
                { label: 'Chain', value: line.supportsChaining, detail: `Chain: ${line.supportsChaining ? 'Yes' : 'No'}` },
                { label: this.escapeHtml(line.language), value: line.language !== '-', detail: `Language: ${this.escapeHtml(line.language)}` }
            ];
            
            let html = '<div class="indicator-row" data-index="' + index + '">';
            
            // Render indicator icons without labels
            for (const ind of indicators) {
                const cssClass = ind.value === true ? 'valid' : (ind.value === false ? 'invalid' : 'unknown');
                const icon = ind.value === true ? '✓' : (ind.value === false ? '✗' : '-');
                html += `<div class="indicator ${this.escapeHtml(cssClass)}" data-detail="${this.escapeHtml(ind.detail)}">${icon}</div>`;
            }
            
            // Add Size, Type, View, Preview columns
            html += `<div class="indicator-info" id="size-${index}">-</div>`;
            html += `<div class="indicator-info" id="type-${index}">-</div>`;
            html += `<div class="indicator-link"><a href="#" class="btn btn-sm btn-link" id="link-${index}">View</a></div>`;
            html += `<div class="indicator-preview" id="preview-${index}">-</div>`;
            
            html += '</div>';
            return html;
        }
        
        async fetchPreviewData(lines, index) {
            try {
                // Build URL up to and including this line
                const urlSegments = lines.slice(0, index + 1).map(l => l.text);
                const url = '/' + urlSegments.join('/');
                
                // Make HEAD request to get size and content-type without downloading full content
                const response = await fetch(url, { method: 'HEAD' });
                const contentType = response.headers.get('content-type') || 'unknown';
                const contentLength = response.headers.get('content-length') || '?';
                
                // Now fetch a small portion to get preview text
                const previewResponse = await fetch(url);
                const text = await previewResponse.text();
                const preview = text.substring(0, 50);
                
                // Update Size column
                const sizeElement = document.getElementById(`size-${index}`);
                if (sizeElement) {
                    sizeElement.textContent = contentLength;
                    sizeElement.title = `Size: ${contentLength} bytes`;
                }
                
                // Update Type column
                const typeElement = document.getElementById(`type-${index}`);
                if (typeElement) {
                    const shortType = contentType.split(';')[0].split('/').pop();
                    typeElement.textContent = shortType;
                    typeElement.title = `Content-Type: ${contentType}`;
                }
                
                // Update Preview column
                const previewElement = document.getElementById(`preview-${index}`);
                if (previewElement) {
                    previewElement.textContent = preview + (text.length > 50 ? '...' : '');
                    previewElement.title = preview + (text.length > 50 ? '...' : '');
                }
                
                // Update the link to point to this URL
                const linkElement = document.getElementById(`link-${index}`);
                if (linkElement) {
                    linkElement.href = url;
                    linkElement.onclick = (e) => {
                        e.preventDefault();
                        window.open(url, '_blank');
                    };
                }
            } catch (error) {
                const sizeElement = document.getElementById(`size-${index}`);
                if (sizeElement) {
                    sizeElement.textContent = 'Error';
                    sizeElement.title = error.message;
                }
                const typeElement = document.getElementById(`type-${index}`);
                if (typeElement) {
                    typeElement.textContent = 'Error';
                }
                const previewElement = document.getElementById(`preview-${index}`);
                if (previewElement) {
                    previewElement.textContent = 'Error loading';
                    previewElement.title = error.message;
                }
            }
        }
        
        async fetchFinalOutput() {
            try {
                const url = this.currentUrl || '/';
                if (url === '/') {
                    document.getElementById('final-output').textContent = '-';
                    return;
                }
                
                const response = await fetch(url);
                const text = await response.text();
                const preview = text.substring(0, 100);
                
                document.getElementById('final-output').innerHTML = `
                    <code>${this.escapeHtml(preview)}${text.length > 100 ? '...' : ''}</code>
                    <div class="mt-2"><small class="text-muted">Full length: ${text.length} characters</small></div>
                `;
            } catch (error) {
                document.getElementById('final-output').innerHTML = `
                    <span class="text-danger">Error: ${this.escapeHtml(error.message)}</span>
                `;
            }
        }
        
        copyCurrentUrl() {
            const url = this.currentUrl || '/';
            navigator.clipboard.writeText(url).then(() => {
                alert('URL copied to clipboard!');
            });
        }
        
        openCurrentUrl() {
            const url = this.currentUrl || '/';
            window.open(url, '_blank');
        }
    }
    
    // Initialize the app
    const app = new URLEditorApp();
    
    // Load initial URL from hash if present
    if (window.location.hash) {
        app.loadFromHash();
    }
    
    // Export for testing
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { URLEditorApp };
    }
})(typeof ace !== 'undefined' ? ace : {}, typeof INITIAL_URL !== 'undefined' ? INITIAL_URL : '');
