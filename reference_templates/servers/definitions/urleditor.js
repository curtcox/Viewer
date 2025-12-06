/**
 * URL Editor Application
 * 
 * Provides interactive editing of chained server URLs with live preview and validation.
 * @param {object} ace - Ace editor instance
 * @param {string} initialUrl - Initial URL to populate the editor
 */
(function(ace, initialUrl) {
    'use strict';

    // Initialize Ace editor
    const editor = ace.edit("url-editor");
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
            this.updatePreviews();
        }
        
        updateIndicators() {
            const lines = this.parseUrlLines();
            const indicatorsList = document.getElementById('indicators-list');
            
            if (lines.length === 0) {
                indicatorsList.innerHTML = '<div class="text-muted text-center">Edit URL to see indicators</div>';
                return;
            }
            
            let html = '';
            for (const line of lines) {
                html += this.renderIndicatorRow(line);
            }
            indicatorsList.innerHTML = html;
        }
        
        async updatePreviews() {
            const lines = this.parseUrlLines();
            const previewList = document.getElementById('preview-list');
            
            if (lines.length === 0) {
                previewList.innerHTML = '<div class="text-muted text-center">Edit URL to see previews</div>';
                document.getElementById('final-output').textContent = '-';
                return;
            }
            
            // Build preview rows with async loading
            let html = '';
            for (let i = 0; i < lines.length; i++) {
                html += this.renderPreviewRow(lines[i], i);
            }
            previewList.innerHTML = html;
            
            // Fetch preview data for each line asynchronously
            for (let i = 0; i < lines.length; i++) {
                this.fetchPreviewData(lines, i);
            }
            
            // Update final output with full URL
            this.fetchFinalOutput();
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
        
        renderIndicatorRow(line) {
            const indicators = [
                { label: 'Valid', value: line.isValidSegment },
                { label: 'Server', value: line.isServer },
                { label: 'CID', value: line.isValidCid },
                { label: 'Chain', value: line.supportsChaining },
                { label: this.escapeHtml(line.language), value: line.language !== '-' }
            ];
            
            let html = '<div class="indicator-row">';
            for (const ind of indicators) {
                const cssClass = ind.value === true ? 'valid' : (ind.value === false ? 'invalid' : 'unknown');
                const icon = ind.value === true ? '✓' : (ind.value === false ? '✗' : '-');
                const escapedLabel = this.escapeHtml(ind.label);
                html += `<div class="indicator ${this.escapeHtml(cssClass)}" title="${escapedLabel}">${escapedLabel}: ${icon}</div>`;
            }
            html += '</div>';
            return html;
        }
        
        renderPreviewRow(line, index) {
            const escapedText = this.escapeHtml(line.text);
            return `
                <div class="preview-row" data-index="${index}">
                    <div><strong>${escapedText}</strong></div>
                    <div class="preview-output" id="preview-${index}">
                        <span class="text-muted">Loading...</span>
                    </div>
                    <a href="#" class="btn btn-sm btn-link preview-link" id="link-${index}">View</a>
                </div>
            `;
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
                const preview = text.substring(0, 20);
                
                // Update the preview element
                const previewElement = document.getElementById(`preview-${index}`);
                if (previewElement) {
                    previewElement.innerHTML = `
                        Size: ${contentLength} | Type: ${contentType} | 
                        Preview: <code>${this.escapeHtml(preview)}${text.length > 20 ? '...' : ''}</code>
                    `;
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
                const previewElement = document.getElementById(`preview-${index}`);
                if (previewElement) {
                    previewElement.innerHTML = `<span class="text-danger">Error: ${this.escapeHtml(error.message)}</span>`;
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
