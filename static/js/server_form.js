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

        let debounceHandle = null;
        let requestCounter = 0;

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
            parametersContainer.querySelectorAll('input[name]').forEach((input) => {
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

                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control';
                input.id = fieldId;
                input.name = parameter.name || `param_${index}`;
                input.placeholder = `Value for ${parameter.name || `param_${index}`}`;
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
    });
})();
