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
                // These will be updated asynchronously via fetchMetadata
                isServer: null,
                isValidCid: null,
                supportsChaining: null,
                language: null
            }));
        }
        
        isValidPathSegment(text) {
            // Simple validation - non-empty and URL-safe
            return text.length > 0 && !/[\s<>"]/.test(text);
        }
        
        async fetchMetadata(segment) {
            // Fetch metadata from /meta/{segment} endpoint
            try {
                const response = await fetch(`/meta/${encodeURIComponent(segment)}`);
                if (!response.ok) {
                    return null;
                }
                return await response.json();
            } catch (error) {
                console.error('Error fetching metadata for', segment, error);
                return null;
            }
        }
        
        escapeHtml(text) {
            // Escape HTML to prevent XSS
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        renderIndicatorRow(line, index) {
            const indicators = [
                { label: 'Valid', value: line.isValidSegment, detail: `Valid path segment: ${line.isValidSegment ? 'Yes - this is a valid URL path segment' : 'No - contains invalid characters'}`, id: `valid-${index}` },
                { label: 'Server', value: line.isServer, detail: `Server: Loading metadata...`, id: `server-${index}` },
                { label: 'CID', value: line.isValidCid, detail: `CID: Loading metadata...`, id: `cid-${index}` },
                { label: 'Chain', value: line.supportsChaining, detail: `Chaining: Loading metadata...`, id: `chain-${index}` },
                { label: line.language || '-', value: line.language !== '-' && line.language !== null, detail: `Language: Loading metadata...`, id: `lang-${index}` }
            ];
            
            let html = '<div class="indicator-row" data-index="' + index + '">';
            
            // Render indicator icons without labels
            for (const ind of indicators) {
                const cssClass = ind.value === true ? 'valid' : (ind.value === false ? 'invalid' : 'unknown');
                const icon = ind.value === true ? '✓' : (ind.value === false ? '✗' : '-');
                html += `<div class="indicator ${this.escapeHtml(cssClass)}" id="${ind.id}" data-detail="${this.escapeHtml(ind.detail)}">${icon}</div>`;
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
                // Fetch metadata for this segment first
                const segment = lines[index].text;
                const metadata = await this.fetchMetadata(segment);
                
                // Update indicators based on metadata
                await this.updateIndicatorsFromMetadata(index, segment, metadata, index === lines.length - 1);
                
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
                // Use a longer preview length to fill available space on the line
                const PREVIEW_LENGTH = 200;
                const preview = text.substring(0, PREVIEW_LENGTH);
                
                // Update Size column
                const sizeElement = document.getElementById(`size-${index}`);
                if (sizeElement) {
                    sizeElement.textContent = contentLength;
                    sizeElement.title = `Size: ${contentLength} bytes`;
                }
                
                // Update Type column
                const typeElement = document.getElementById(`type-${index}`);
                if (typeElement) {
                    // Safely extract the short type name from content-type
                    const typeParts = contentType.split(';')[0].split('/');
                    const shortType = typeParts.length > 1 ? typeParts.pop() : contentType;
                    typeElement.textContent = shortType;
                    typeElement.title = `Content-Type: ${contentType}`;
                }
                
                // Update Preview column
                const previewElement = document.getElementById(`preview-${index}`);
                if (previewElement) {
                    previewElement.textContent = preview + (text.length > PREVIEW_LENGTH ? '...' : '');
                    previewElement.title = preview + (text.length > PREVIEW_LENGTH ? '...' : '');
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
        
        async updateIndicatorsFromMetadata(index, segment, metadata, isLastSegment) {
            // Determine indicator states based on metadata
            let isServer = false;
            let isValidCid = false;
            let supportsChaining = false;
            let language = '-';
            
            if (metadata && metadata.resolution) {
                const res = metadata.resolution;
                
                // Check if it's a server
                if (res.type === 'server_execution' || res.type === 'server_function_execution') {
                    isServer = res.available === true;
                    supportsChaining = res.supports_chaining === true;
                    language = res.language || 'python';
                }
                
                // Check if it's a CID
                if (res.type === 'cid') {
                    isValidCid = true;
                    // If CID has server info, use it
                    if (res.server) {
                        language = res.server.language || 'python';
                        supportsChaining = res.server.supports_chaining === true;
                    }
                }
            }
            
            // Update Server indicator
            // Green if valid server, red if not a server (unless last segment = gray)
            const serverElement = document.getElementById(`server-${index}`);
            if (serverElement) {
                let cssClass, icon, detail;
                if (isServer) {
                    cssClass = 'valid';
                    icon = '✓';
                    detail = 'Server: Yes - this segment specifies a valid server that can execute code';
                } else if (isLastSegment) {
                    cssClass = 'unknown';
                    icon = '-';
                    detail = 'Server: Unknown - this is the last segment, server validation not required';
                } else {
                    cssClass = 'invalid';
                    icon = '✗';
                    detail = 'Server: No - this segment does not specify a valid server';
                }
                serverElement.className = `indicator ${cssClass}`;
                serverElement.textContent = icon;
                serverElement.setAttribute('data-detail', detail);
            }
            
            // Update CID indicator
            // Gray if not a CID, green if valid CID with content, red if invalid/unavailable
            const cidElement = document.getElementById(`cid-${index}`);
            if (cidElement) {
                let cssClass, icon, detail;
                if (isValidCid) {
                    cssClass = 'valid';
                    icon = '✓';
                    detail = 'CID: Yes - this is a valid Content Identifier with available content';
                } else if (/^AAAAAAA[A-Za-z0-9_-]+$/.test(segment) || segment.startsWith('#')) {
                    cssClass = 'invalid';
                    icon = '✗';
                    detail = 'CID: Invalid - this looks like a CID but the content is not available';
                } else {
                    cssClass = 'unknown';
                    icon = '-';
                    detail = 'CID: No - this segment is not a Content Identifier';
                }
                cidElement.className = `indicator ${cssClass}`;
                cidElement.textContent = icon;
                cidElement.setAttribute('data-detail', detail);
            }
            
            // Update Chain indicator
            // Green if supports chaining, gray if last segment, red otherwise
            const chainElement = document.getElementById(`chain-${index}`);
            if (chainElement) {
                let cssClass, icon, detail;
                if (supportsChaining) {
                    cssClass = 'valid';
                    icon = '✓';
                    detail = 'Chaining: Yes - this server can accept chained input from previous segments';
                } else if (isLastSegment) {
                    cssClass = 'unknown';
                    icon = '-';
                    detail = 'Chaining: N/A - this is the last segment, chaining capability not required';
                } else {
                    cssClass = 'invalid';
                    icon = '✗';
                    detail = 'Chaining: No - this segment cannot accept chained input';
                }
                chainElement.className = `indicator ${cssClass}`;
                chainElement.textContent = icon;
                chainElement.setAttribute('data-detail', detail);
            }
            
            // Update Language indicator
            const langElement = document.getElementById(`lang-${index}`);
            if (langElement) {
                let cssClass, icon, detail;
                if (language && language !== '-') {
                    cssClass = 'valid';
                    icon = language;
                    detail = `Language: ${language} - implementation language of this server`;
                } else {
                    cssClass = 'unknown';
                    icon = '-';
                    detail = 'Language: Unknown - language information not available';
                }
                langElement.className = `indicator ${cssClass}`;
                langElement.textContent = icon;
                langElement.setAttribute('data-detail', detail);
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
