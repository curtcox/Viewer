/**
 * CID Editor Controls
 *
 * Provides functionality for converting between CID references and their contents
 * in editor text fields.
 */

(function () {
    'use strict';

    const CID_CHECK_ENDPOINT = '/api/cid/check';
    const CID_GENERATE_ENDPOINT = '/api/cid/generate';

    /**
     * Debounce function to limit the rate of API calls.
     * @param {Function} func - The function to debounce.
     * @param {number} wait - The debounce delay in milliseconds.
     * @returns {Function} A debounced version of the function.
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    /**
     * Check if content is a CID and get its status.
     * @param {string} content - The content to check.
     * @returns {Promise<Object>} The CID check result.
     */
    async function checkCidStatus(content) {
        const response = await fetch(CID_CHECK_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content.trim() }),
        });
        return response.json();
    }

    /**
     * Generate a CID for the given content.
     * @param {string} content - The content to generate a CID for.
     * @param {boolean} store - Whether to store the content in the database.
     * @returns {Promise<Object>} The generated CID result.
     */
    async function generateCid(content, store = true) {
        const response = await fetch(CID_GENERATE_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, store }),
        });
        return response.json();
    }

    /**
     * Update the CID editor controls UI based on the current content.
     * @param {HTMLElement} container - The CID controls container element.
     * @param {Object} result - The CID check result.
     */
    function updateControls(container, result) {
        const expandButton = container.querySelector('[data-cid-expand]');
        const compressButton = container.querySelector('[data-cid-compress]');
        const cidPopup = container.querySelector('[data-cid-popup]');
        const statusMessage = container.querySelector('[data-cid-status]');

        // Hide all controls initially
        if (expandButton) expandButton.classList.add('d-none');
        if (compressButton) compressButton.classList.add('d-none');
        if (cidPopup) cidPopup.classList.add('d-none');
        if (statusMessage) statusMessage.classList.add('d-none');

        if (result.is_cid) {
            // Content is a CID
            if (cidPopup && result.cid_link_html) {
                cidPopup.innerHTML = result.cid_link_html;
                cidPopup.classList.remove('d-none');
            }

            if (result.has_content) {
                // CID has known contents - show expand button
                if (expandButton) {
                    expandButton.classList.remove('d-none');
                    expandButton.dataset.cidContent = result.content || '';
                }
            } else {
                // CID contents not found
                if (statusMessage) {
                    statusMessage.textContent = 'CID contents not found';
                    statusMessage.classList.remove('d-none');
                    statusMessage.classList.add('text-warning');
                    statusMessage.classList.remove('text-muted');
                }
            }
        } else {
            // Content is not a CID - show compress button
            if (compressButton) {
                compressButton.classList.remove('d-none');
            }
        }
    }

    /**
     * Initialize CID editor controls for a text field.
     * @param {HTMLElement} container - The CID controls container element.
     */
    function initCidControls(container) {
        const targetId = container.dataset.cidEditorFor;
        if (!targetId) return;

        const textarea = document.getElementById(targetId);
        if (!textarea) return;

        let abortController = null;

        const checkContent = debounce(async () => {
            // Cancel any pending request
            if (abortController) {
                abortController.abort();
            }
            abortController = new AbortController();

            const content = textarea.value || '';
            if (!content.trim()) {
                // Empty content - hide all controls
                updateControls(container, { is_cid: false });
                return;
            }

            try {
                const result = await checkCidStatus(content);
                updateControls(container, result);
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Error checking CID status:', error);
                }
            }
        }, 300);

        // Expand CID to its contents
        const expandButton = container.querySelector('[data-cid-expand]');
        if (expandButton) {
            expandButton.addEventListener('click', function () {
                const content = this.dataset.cidContent;
                if (typeof content === 'string') {
                    setValue(textarea, content);
                    checkContent();
                }
            });
        }

        // Compress content to CID
        const compressButton = container.querySelector('[data-cid-compress]');
        if (compressButton) {
            compressButton.addEventListener('click', async function () {
                const content = textarea.value || '';
                if (!content.trim()) return;

                try {
                    const result = await generateCid(content, true);
                    if (result.cid_value) {
                        setValue(textarea, result.cid_value);
                        checkContent();
                    }
                } catch (error) {
                    console.error('Error generating CID:', error);
                }
            });
        }

        // Listen for content changes
        textarea.addEventListener('input', checkContent);

        // Also handle Ace editor changes if present
        function watchEditor() {
            const editorController = window.codeEditors && window.codeEditors[targetId];
            if (editorController && typeof editorController.getAceEditor === 'function') {
                const aceEditor = editorController.getAceEditor();
                aceEditor.session.on('change', checkContent);
            }
        }

        // Try to attach to editor now and after a delay (editor may load later)
        watchEditor();
        setTimeout(watchEditor, 500);

        // Initial check
        checkContent();
    }

    /**
     * Set value in textarea and trigger input event.
     * @param {HTMLTextAreaElement} textarea - The textarea element.
     * @param {string} value - The value to set.
     */
    function setValue(textarea, value) {
        const targetId = textarea.id;
        const editorController = window.codeEditors && window.codeEditors[targetId];

        if (editorController && typeof editorController.setValue === 'function') {
            editorController.setValue(value);
        } else {
            textarea.value = value;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }

    /**
     * Initialize all CID editor controls on the page.
     */
    function initAllCidControls() {
        const containers = document.querySelectorAll('[data-cid-editor-for]');
        containers.forEach(initCidControls);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllCidControls);
    } else {
        initAllCidControls();
    }

    // Expose for external use
    window.cidEditorControls = {
        init: initAllCidControls,
        initContainer: initCidControls,
        checkCidStatus,
        generateCid,
    };
})();
