(function () {
    const ACE_BASE_PATH = 'https://cdn.jsdelivr.net/npm/ace-builds@1.32.6/src-min-noconflict/';

    function onReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    }

    function looksLikeJson(text) {
        const trimmed = text.trim();
        if (!trimmed) {
            return false;
        }
        if (trimmed[0] !== '{' && trimmed[0] !== '[') {
            return false;
        }
        try {
            JSON.parse(trimmed);
            return true;
        } catch (error) {
            return false;
        }
    }

    function looksLikePython(text) {
        if (/^#!/.test(text)) {
            return false;
        }
        if (/\b(def|class)\s+\w+\s*\(/.test(text)) {
            return true;
        }
        if (/\b(async\s+)?def\s+\w+/.test(text)) {
            return true;
        }
        if (/\b(import|from)\s+[\w.]+/.test(text)) {
            return true;
        }
        if (/:\s*\n\s+return\b/.test(text)) {
            return true;
        }
        return false;
    }

    function looksLikeYaml(text) {
        if (text.includes('{') || text.includes('[')) {
            return false;
        }
        const lines = text.split(/\r?\n/).slice(0, 20);
        let structuredLines = 0;
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || /^#/.test(trimmed)) {
                continue;
            }
            if (/^-[\s\w'"[{]/.test(trimmed)) {
                structuredLines += 1;
                continue;
            }
            if (/^[\w"'][\w\s"'-.]*:\s+/.test(trimmed)) {
                structuredLines += 1;
            }
        }
        return structuredLines >= 2;
    }

    function looksLikeIni(text) {
        const lines = text.split(/\r?\n/);
        let sections = 0;
        let assignments = 0;
        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line || line.startsWith('#') || line.startsWith(';')) {
                continue;
            }
            if (/^\[[^\]]+\]$/.test(line)) {
                sections += 1;
                continue;
            }
            if (/^[^=]+=[^=]+$/.test(line)) {
                assignments += 1;
            }
        }
        return sections > 0 && assignments > 0;
    }

    function looksLikeHtml(text) {
        return /<\w+(\s|>)/.test(text) && /<\/\w+>/.test(text);
    }

    function looksLikeShell(text) {
        if (/^#!\/(bin|usr\/bin)\//.test(text.trim())) {
            return true;
        }
        const lines = text.split(/\r?\n/).slice(0, 5);
        return lines.some((line) => /\b(set -[eux]|fi|then|do|done)\b/.test(line));
    }

    function looksLikeSql(text) {
        const upper = text.trim().toUpperCase();
        return /^(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)\b/.test(upper);
    }

    function looksLikeCss(text) {
        return /\{[^}]*\}/.test(text) && /[.#]?[A-Za-z0-9_-]+\s*\{/.test(text);
    }

    function looksLikeJavascript(text) {
        if (/^#!/.test(text)) {
            return false;
        }
        if (/\b(function|const|let|class|import|export)\b/.test(text)) {
            return true;
        }
        if (/=>/.test(text)) {
            return true;
        }
        return false;
    }

    function detectLanguage(value, fallback) {
        if (typeof value !== 'string') {
            return fallback || 'text';
        }
        const text = value.trim();
        if (!text) {
            return fallback || 'text';
        }
        if (looksLikeJson(text)) {
            return 'json';
        }
        if (looksLikePython(text)) {
            return 'python';
        }
        if (looksLikeJavascript(text)) {
            return 'javascript';
        }
        if (looksLikeHtml(text)) {
            return 'html';
        }
        if (looksLikeCss(text)) {
            return 'css';
        }
        if (looksLikeYaml(text)) {
            return 'yaml';
        }
        if (looksLikeIni(text)) {
            return 'ini';
        }
        if (looksLikeShell(text)) {
            return 'sh';
        }
        if (looksLikeSql(text)) {
            return 'sql';
        }
        return fallback || 'text';
    }

    function isElementVisible(element) {
        if (!element || !element.isConnected) {
            return false;
        }
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden' || Number.parseFloat(style.opacity) === 0) {
            return false;
        }
        if (rect.width === 0 && rect.height === 0 && style.position !== 'fixed') {
            return false;
        }
        if (element.offsetParent === null && style.position !== 'fixed') {
            return false;
        }
        return true;
    }

    function watchVisibility(element, callback) {
        if (!element || typeof callback !== 'function') {
            return null;
        }
        let current = element.parentElement;
        if (!current) {
            return null;
        }
        const observer = new MutationObserver(() => {
            if (!isElementVisible(element)) {
                return;
            }
            observer.disconnect();
            callback();
        });
        while (current) {
            observer.observe(current, { attributes: true, attributeFilter: ['style', 'class'] });
            current = current.parentElement;
        }
        return observer;
    }

    function determineEditorHeight(textarea, container, minimum) {
        const minHeight = typeof minimum === 'number' && minimum > 0 ? minimum : 320;
        const textareaHeight = textarea
            ? Math.max(textarea.scrollHeight || 0, textarea.offsetHeight || 0)
            : 0;
        const containerHeight = container ? container.offsetHeight || 0 : 0;
        return Math.max(minHeight, textareaHeight, containerHeight);
    }

    function createEditor(container) {
        if (!container || container.__aceInitialised) {
            return null;
        }
        if (typeof window.ace === 'undefined') {
            return null;
        }

        const targetId = container.getAttribute('data-code-editor-for');
        if (!targetId) {
            return null;
        }

        const textarea = document.getElementById(targetId);
        if (!textarea) {
            return null;
        }

        container.__aceInitialised = true;

        const defaultLanguage = container.getAttribute('data-code-editor-language') || 'text';
        const detect = container.getAttribute('data-code-editor-detect-language') !== 'false';
        const minimumHeightAttr = container.getAttribute('data-code-editor-min-height');
        const minimumHeight = minimumHeightAttr ? Number.parseInt(minimumHeightAttr, 10) : null;

        if (typeof window.ace.config?.set === 'function') {
            window.ace.config.set('basePath', ACE_BASE_PATH);
            window.ace.config.set('modePath', ACE_BASE_PATH);
            window.ace.config.set('themePath', ACE_BASE_PATH);
        }

        const desiredHeight = determineEditorHeight(textarea, container, minimumHeight || undefined);

        const removedHiddenClass = container.classList.contains('d-none');
        if (removedHiddenClass) {
            container.classList.remove('d-none');
        }

        const previousVisibility = container.style.visibility;
        const previousPosition = container.style.position;
        const previousDisplay = container.style.display;

        container.style.visibility = 'hidden';
        container.style.position = 'absolute';
        container.style.display = 'block';
        container.style.height = `${desiredHeight}px`;

        let editor;
        try {
            editor = window.ace.edit(container);
        } catch (error) {
            console.error('Unable to initialise Ace editor', error);
            container.classList.add('d-none');
            textarea.classList.remove('d-none');
            return null;
        }

        let visibilityObserver = null;
        editor.session.setUseSoftTabs(true);
        editor.session.setTabSize(4);
        editor.session.setUseWrapMode(true);
        editor.setShowPrintMargin(false);
        editor.setHighlightActiveLine(true);
        editor.renderer.setScrollMargin(12, 12, 0, 0);
        editor.setOptions({
            fontSize: '0.95rem',
            highlightGutterLine: true,
        });

        if (typeof editor.setTheme === 'function') {
            editor.setTheme('ace/theme/github');
        }

        let suppress = false;

        function applyLanguage(value) {
            const mode = detect ? detectLanguage(value, defaultLanguage) : (defaultLanguage || 'text');
            const modeId = `ace/mode/${mode || 'text'}`;
            if (editor.session.getMode()?.$id === modeId) {
                return;
            }
            editor.session.setMode(modeId);
        }

        function syncEditorWithTextarea() {
            if (suppress) {
                return;
            }
            const value = textarea.value || '';
            if (editor.getValue() === value) {
                return;
            }
            suppress = true;
            const cursor = editor.getCursorPosition();
            editor.session.setValue(value);
            editor.moveCursorToPosition(cursor);
            editor.session.selection.clearSelection();
            applyLanguage(value);
            suppress = false;
        }

        editor.session.on('change', () => {
            if (suppress) {
                return;
            }
            const value = editor.getValue();
            if (textarea.value === value) {
                return;
            }
            suppress = true;
            textarea.value = value;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            applyLanguage(value);
            suppress = false;
        });

        textarea.addEventListener('input', syncEditorWithTextarea);

        editor.session.setValue(textarea.value || '');
        applyLanguage(textarea.value || '');
        editor.resize(true);

        function showEditor() {
            container.style.visibility = previousVisibility || '';
            container.style.position = previousPosition || '';
            container.style.display = previousDisplay || '';
            container.style.height = `${determineEditorHeight(textarea, container, minimumHeight || undefined)}px`;
            textarea.classList.add('d-none');
            textarea.setAttribute('aria-hidden', 'true');
        }

        function revertToTextarea() {
            if (visibilityObserver) {
                visibilityObserver.disconnect();
                visibilityObserver = null;
            }
            if (typeof editor.destroy === 'function') {
                editor.destroy();
            }
            textarea.removeEventListener('input', syncEditorWithTextarea);
            container.style.visibility = previousVisibility || '';
            container.style.position = previousPosition || '';
            container.style.display = previousDisplay || '';
            container.style.height = '';
            if (removedHiddenClass) {
                container.classList.add('d-none');
            }
            textarea.classList.remove('d-none');
            textarea.removeAttribute('aria-hidden');
            delete container.__aceInitialised;
            if (window.codeEditors && window.codeEditors[targetId]) {
                delete window.codeEditors[targetId];
            }
        }

        function ensureVisible(attempt) {
            const tries = typeof attempt === 'number' ? attempt : 0;
            const visibleHeight = container.getBoundingClientRect().height;
            if (visibleHeight >= 32 && isElementVisible(container)) {
                showEditor();
                return;
            }

            if (!isElementVisible(container)) {
                if (!visibilityObserver) {
                    visibilityObserver = watchVisibility(container, () => {
                        visibilityObserver = null;
                        const newHeight = determineEditorHeight(textarea, container, minimumHeight || undefined);
                        container.style.height = `${newHeight}px`;
                        editor.resize(true);
                        ensureVisible(0);
                    });
                }
                return;
            }

            if (tries < 5) {
                const newHeight = determineEditorHeight(textarea, container, minimumHeight || undefined);
                container.style.height = `${newHeight}px`;
                editor.resize(true);
                setTimeout(() => ensureVisible(tries + 1), 150);
                return;
            }

            console.error('Ace editor failed to render a visible height; reverting to textarea fallback.');
            revertToTextarea();
        }

        requestAnimationFrame(() => {
            ensureVisible(0);
        });

        window.addEventListener('resize', () => {
            const newHeight = determineEditorHeight(textarea, container, minimumHeight || undefined);
            container.style.height = `${newHeight}px`;
            editor.resize(true);
        });

        const controller = {
            getValue() {
                return editor.getValue();
            },
            setValue(value) {
                suppress = true;
                const text = typeof value === 'string' ? value : '';
                textarea.value = text;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                editor.session.setValue(text);
                editor.session.selection.clearSelection();
                applyLanguage(text);
                suppress = false;
            },
            focus() {
                editor.focus();
            },
            scrollIntoView() {
                container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            },
            setLanguage(mode) {
                const lang = mode || defaultLanguage || 'text';
                editor.session.setMode(`ace/mode/${lang}`);
            },
            getAceEditor() {
                return editor;
            },
            refreshLayout() {
                const newHeight = determineEditorHeight(textarea, container, minimumHeight || undefined);
                container.style.height = `${newHeight}px`;
                editor.resize(true);
                ensureVisible(0);
            },
        };

        if (!window.codeEditors) {
            window.codeEditors = {};
        }
        window.codeEditors[targetId] = controller;

        return controller;
    }

    function initialiseEditors() {
        if (typeof window.ace === 'undefined') {
            return;
        }
        const containers = document.querySelectorAll('[data-code-editor-for]');
        containers.forEach((container) => {
            if (!container.__aceInitialised) {
                createEditor(container);
            }
        });
    }

    onReady(() => {
        const triggerInitialisation = () => {
            initialiseEditors();
        };

        if (typeof window.ace !== 'undefined') {
            triggerInitialisation();
        } else {
            const aceScript = document.querySelector('script[src*="ace-builds"][src*="ace.js"]')
                || document.querySelector('script[src*="ace.js"]');
            if (aceScript && !aceScript.__viewerAceListenerAttached) {
                aceScript.__viewerAceListenerAttached = true;
                aceScript.addEventListener('load', triggerInitialisation, { once: true });
            }
        }

        if (typeof window.requestIdleCallback === 'function') {
            window.requestIdleCallback(() => initialiseEditors());
        } else {
            setTimeout(() => initialiseEditors(), 50);
        }
        window.initialiseCodeEditors = initialiseEditors;
    });
})();
