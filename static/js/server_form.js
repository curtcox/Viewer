(function () {
    function onReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    }

    function escapeHtml(value) {
        if (typeof value !== 'string') {
            return '';
        }
        return value
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    onReady(() => {
        const definitionField = document.getElementById('definition');
        if (!definitionField) {
            return;
        }

        const validationInput = document.getElementById('server-definition-validate-url');
        const validationUrl = validationInput ? validationInput.value : null;
        const csrfTokenInput = document.querySelector('input[name="csrf_token"]');

        const errorContainer = document.getElementById('server-definition-errors');
        const testForm = document.getElementById('server-test-form');
        const mainSection = document.getElementById('server-test-main-section');
        const querySection = document.getElementById('server-test-query-section');
        const parametersContainer = document.getElementById('server-test-parameters');
        const noParametersMessage = document.getElementById('server-test-no-parameters');
        const aiWrapper = document.getElementById('server-test-ai-wrapper');
        const resultContainer = document.getElementById('server-test-result');

        const editorContainer = document.getElementById('server-definition-editor');
        const aceBasePath = 'https://cdn.jsdelivr.net/npm/ace-builds@1.32.6/src-min-noconflict/';

        let debounceHandle = null;
        let requestCounter = 0;
        let aceEditor = null;
        let suppressAceChange = false;

        function updateTextareaFromEditor() {
            if (!aceEditor || suppressAceChange) {
                return;
            }

            const value = aceEditor.getValue();
            if (definitionField.value === value) {
                return;
            }

            definitionField.value = value;
            definitionField.dispatchEvent(new Event('input', { bubbles: true }));
        }

        function syncEditorWithTextarea() {
            if (!aceEditor) {
                return;
            }

            const value = definitionField.value;
            if (aceEditor.getValue() === value) {
                return;
            }

            suppressAceChange = true;
            const cursorPosition = aceEditor.getCursorPosition();
            aceEditor.session.setValue(value);
            aceEditor.moveCursorToPosition(cursorPosition);
            aceEditor.session.selection.clearSelection();
            suppressAceChange = false;
        }

        function determineEditorHeight() {
            const textareaHeight = definitionField
                ? Math.max(definitionField.scrollHeight || 0, definitionField.offsetHeight || 0)
                : 0;
            const containerHeight = editorContainer ? editorContainer.offsetHeight || 0 : 0;
            const defaultHeight = 384; // 24rem assuming 16px base font size
            return Math.max(textareaHeight, containerHeight, defaultHeight);
        }

        function ensureAceEditor() {
            if (!editorContainer || typeof window.ace === 'undefined') {
                return null;
            }

            if (typeof editorContainer.classList?.remove === 'function') {
                editorContainer.classList.remove('d-none');
            }

            const desiredHeight = determineEditorHeight();
            if (editorContainer && typeof editorContainer.style !== 'undefined') {
                editorContainer.style.height = `${desiredHeight}px`;
            }

            try {
                if (typeof window.ace.config?.set === 'function') {
                    window.ace.config.set('basePath', aceBasePath);
                    window.ace.config.set('modePath', aceBasePath);
                    window.ace.config.set('themePath', aceBasePath);
                }

                const editor = window.ace.edit(editorContainer);
                editor.session.setMode('ace/mode/python');
                editor.session.setUseSoftTabs(true);
                editor.session.setTabSize(4);
                editor.session.setUseWrapMode(true);
                editor.session.setValue(definitionField.value || '');
                editor.setShowPrintMargin(false);
                editor.setHighlightActiveLine(true);
                editor.renderer.setScrollMargin(12, 12, 0, 0);
                editor.setOptions({
                    fontSize: '0.95rem',
                    highlightGutterLine: true,
                });

                editor.resize(true);

                if (typeof editor.setTheme === 'function') {
                    editor.setTheme('ace/theme/github');
                }

                editor.session.on('change', () => {
                    if (suppressAceChange) {
                        return;
                    }
                    updateTextareaFromEditor();
                });

                return editor;
            } catch (error) {
                if (typeof console !== 'undefined' && typeof console.error === 'function') {
                    console.error('Failed to initialise Ace editor for server definition', error);
                }
                if (typeof editorContainer.classList?.add === 'function') {
                    editorContainer.classList.add('d-none');
                }
                return null;
            }
        }

        aceEditor = ensureAceEditor();

        if (!aceEditor) {
            if (editorContainer) {
                editorContainer.classList.add('d-none');
                editorContainer.style.height = '';
            }
            definitionField.classList.remove('d-none');
        } else {
            requestAnimationFrame(() => {
                const visibleHeight = editorContainer?.getBoundingClientRect().height || 0;
                if (visibleHeight < 32) {
                    if (typeof console !== 'undefined' && typeof console.error === 'function') {
                        console.error('Ace editor failed to render with a visible height; falling back to textarea.');
                    }

                    if (typeof aceEditor.destroy === 'function') {
                        aceEditor.destroy();
                    }

                    aceEditor = null;

                    if (editorContainer) {
                        editorContainer.classList.add('d-none');
                        editorContainer.style.height = '';
                    }

                    definitionField.classList.remove('d-none');
                    return;
                }

                if (editorContainer) {
                    editorContainer.classList.remove('d-none');
                }
                definitionField.classList.add('d-none');
            });
        }

        window.addEventListener('resize', () => {
            if (!aceEditor) {
                return;
            }
            const updatedHeight = determineEditorHeight();
            if (editorContainer && typeof editorContainer.style !== 'undefined') {
                editorContainer.style.height = `${updatedHeight}px`;
            }
            aceEditor.resize(true);
        });

        const definitionController = {
            getValue() {
                return aceEditor ? aceEditor.getValue() : definitionField.value;
            },
            setValue(value) {
                definitionField.value = typeof value === 'string' ? value : '';
                definitionField.dispatchEvent(new Event('input', { bubbles: true }));
                syncEditorWithTextarea();
            },
            focus() {
                if (aceEditor) {
                    aceEditor.focus();
                } else {
                    definitionField.focus();
                }
            },
            scrollIntoView() {
                const target = editorContainer || definitionField;
                if (target && typeof target.scrollIntoView === 'function') {
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            },
        };

        window.serverDefinitionEditor = definitionController;

        syncEditorWithTextarea();

        function clearTestResult() {
            if (!resultContainer) {
                return;
            }
            resultContainer.classList.add('d-none');
            resultContainer.classList.remove('alert-danger', 'alert-success', 'alert-info', 'alert-warning');
            resultContainer.innerHTML = '';
        }

        window.clearServerTestResult = clearTestResult;

        function resetErrorContainer() {
            if (!errorContainer) {
                return;
            }
            errorContainer.classList.add('d-none');
            errorContainer.classList.remove('alert-danger', 'alert-warning');
            errorContainer.innerHTML = '';
        }

        function renderDefinitionErrors(result) {
            if (!errorContainer) {
                return;
            }

            const syntaxErrors = Array.isArray(result?.errors) ? result.errors : [];
            const autoMainErrors = result && result.has_main && Array.isArray(result.auto_main_errors)
                ? result.auto_main_errors
                : [];

            if (syntaxErrors.length === 0 && autoMainErrors.length === 0) {
                resetErrorContainer();
                return;
            }

            const messages = [];

            syntaxErrors.forEach((error) => {
                if (!error || typeof error !== 'object') {
                    return;
                }
                let message = error.message || 'Invalid server definition';
                if (typeof error.line === 'number') {
                    message += ` (line ${error.line}`;
                    if (typeof error.column === 'number') {
                        message += `, column ${error.column}`;
                    }
                    message += ')';
                }
                if (typeof error.text === 'string' && error.text.trim()) {
                    message += ` — ${error.text.trim()}`;
                }
                messages.push(message);
            });

            autoMainErrors.forEach((reason) => {
                if (typeof reason === 'string' && reason.trim()) {
                    messages.push(`main(): ${reason.trim()}`);
                }
            });

            const listItems = messages
                .map((msg) => `<li>${escapeHtml(msg)}</li>`)
                .join('');
            errorContainer.innerHTML = `
                <div class="fw-semibold mb-2">Server definition issues detected:</div>
                <ul class="mb-0 ps-3">${listItems}</ul>
            `;

            errorContainer.classList.remove('d-none', 'alert-danger', 'alert-warning');
            if (syntaxErrors.length > 0) {
                errorContainer.classList.add('alert-danger');
            } else {
                errorContainer.classList.add('alert-warning');
            }
        }

        function showValidationWarning(message) {
            if (!errorContainer) {
                return;
            }
            const text = message || 'Unable to validate server definition. Please try again.';
            errorContainer.classList.remove('d-none', 'alert-danger');
            errorContainer.classList.add('alert-warning');
            errorContainer.innerHTML = `<div class="mb-0">${escapeHtml(text)}</div>`;
        }

        function rebuildParameterInputs(parameters) {
            if (!parametersContainer) {
                return;
            }

            const existingValues = {};
            parametersContainer.querySelectorAll('input[name], textarea[name]').forEach((input) => {
                existingValues[input.name] = input.value;
            });

            parametersContainer.innerHTML = '';

            if (!Array.isArray(parameters) || parameters.length === 0) {
                return;
            }

            parameters.forEach((parameter, index) => {
                if (!parameter || typeof parameter !== 'object') {
                    return;
                }

                const fieldId = `server-test-param-${index}`;
                const column = document.createElement('div');
                column.className = 'col-md-6';

                const label = document.createElement('label');
                label.className = 'form-label';
                label.setAttribute('for', fieldId);
                label.appendChild(document.createTextNode(parameter.name || `Parameter ${index + 1}`));

                const badge = document.createElement('span');
                badge.className = `badge ms-2 ${parameter.required ? 'bg-danger' : 'bg-secondary'}`;
                badge.textContent = parameter.required ? 'Required' : 'Optional';
                label.appendChild(badge);

                const input = document.createElement('textarea');
                input.className = 'form-control';
                input.id = fieldId;
                input.name = parameter.name || `param_${index}`;
                input.placeholder = `Value for ${parameter.name || `param_${index}`}`;
                input.rows = 3;
                if (Object.prototype.hasOwnProperty.call(existingValues, input.name)) {
                    input.value = existingValues[input.name];
                }

                column.appendChild(label);
                column.appendChild(input);
                parametersContainer.appendChild(column);
            });
        }

        function updateTestCard(result) {
            if (!testForm) {
                return;
            }

            const isAutoMain = Boolean(result && result.is_valid && result.auto_main);
            const nextMode = result && typeof result.mode === 'string' ? result.mode : (isAutoMain ? 'main' : 'query');

            testForm.dataset.mode = nextMode;

            if (mainSection) {
                if (isAutoMain) {
                    mainSection.classList.remove('d-none');
                } else {
                    mainSection.classList.add('d-none');
                }
            }

            if (querySection) {
                if (isAutoMain) {
                    querySection.classList.add('d-none');
                } else {
                    querySection.classList.remove('d-none');
                }
            }

            if (aiWrapper) {
                if (isAutoMain) {
                    aiWrapper.classList.add('d-none');
                } else {
                    aiWrapper.classList.remove('d-none');
                }
            }

            if (isAutoMain) {
                rebuildParameterInputs(result ? result.parameters : []);
            } else if (parametersContainer) {
                parametersContainer.innerHTML = '';
            }

            if (noParametersMessage) {
                const hasParameters = isAutoMain && Array.isArray(result?.parameters) && result.parameters.length > 0;
                if (hasParameters) {
                    noParametersMessage.classList.add('d-none');
                } else if (isAutoMain) {
                    noParametersMessage.classList.remove('d-none');
                } else {
                    noParametersMessage.classList.add('d-none');
                }
            }
        }

        async function sendValidationRequest(value, requestId) {
            if (!validationUrl) {
                return;
            }

            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            };

            if (csrfTokenInput && csrfTokenInput.value) {
                headers['X-CSRFToken'] = csrfTokenInput.value;
            }

            try {
                const response = await fetch(validationUrl, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({ definition: value }),
                });

                if (!response.ok) {
                    throw new Error(`Validation failed with status ${response.status}`);
                }

                const data = await response.json();
                if (requestId !== requestCounter) {
                    return;
                }

                renderDefinitionErrors(data);
                updateTestCard(data);
            } catch (error) {
                if (requestId !== requestCounter) {
                    return;
                }
                showValidationWarning(error && error.message ? error.message : undefined);
            }
        }

        function scheduleValidation() {
            if (!validationUrl) {
                return;
            }
            const currentValue = definitionField.value;
            const requestId = ++requestCounter;
            sendValidationRequest(currentValue, requestId);
        }

        definitionField.addEventListener('input', () => {
            syncEditorWithTextarea();
            clearTestResult();

            if (!validationUrl) {
                return;
            }

            if (debounceHandle) {
                clearTimeout(debounceHandle);
            }

            debounceHandle = window.setTimeout(() => {
                scheduleValidation();
            }, 400);
        });

        if (validationUrl) {
            scheduleValidation();
        }

        if (aceEditor) {
            aceEditor.commands.addCommand({
                name: 'saveServerDefinition',
                bindKey: { win: 'Ctrl-S', mac: 'Command-S' },
                exec() {
                    const submitButton = document.querySelector('[data-primary-save="true"]');
                    if (submitButton && typeof submitButton.click === 'function') {
                        submitButton.click();
                    }
                },
            });
        }
    });
})();
