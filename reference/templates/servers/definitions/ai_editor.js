(function () {
    function $(selector) {
        return document.querySelector(selector);
    }

    function setText(element, text) {
        if (!element) {
            return;
        }
        element.textContent = text;
    }

    function formatForEditor(value, fallback) {
        if (value === undefined || value === null) {
            return fallback;
        }
        if (typeof value === 'object') {
            try {
                return JSON.stringify(value, null, 2);
            } catch (error) {
                return fallback;
            }
        }
        return String(value);
    }

    function parseJsonField(text, fallback) {
        if (typeof text !== 'string') {
            return fallback;
        }
        var trimmed = text.trim();
        if (!trimmed) {
            return fallback;
        }
        try {
            return JSON.parse(trimmed);
        } catch (error) {
            throw new Error('Invalid JSON: ' + error.message);
        }
    }

    function buildPayload(fields) {
        return {
            request_text: fields.requestText.value || '',
            original_text: fields.originalText.value || '',
            target_label: fields.targetLabel.value || '',
            context_data: parseJsonField(fields.contextData.value, {}),
            form_summary: parseJsonField(fields.formSummary.value, {}),
        };
    }

    function renderResponse(target, data) {
        if (!target) {
            return;
        }
        target.innerHTML = '';
        var pre = document.createElement('pre');
        if (typeof data === 'string') {
            pre.textContent = data;
        } else {
            try {
                pre.textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                pre.textContent = String(data);
            }
        }
        target.appendChild(pre);
    }

    function setActiveEndpointIndicator(element, endpoint) {
        if (element) {
            element.textContent = 'Target: ' + (endpoint || '/ai');
        }
    }

    function initialiseTabs() {
        var firstTab = document.querySelector('#aiEditorTabs .nav-link');
        if (firstTab) {
            firstTab.classList.add('active');
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var config = window.AI_EDITOR_BOOTSTRAP || {};
        var payload = config.payload || {};
        var targetEndpoint = config.targetEndpoint || '/ai';

        var root = document.getElementById('ai-editor-root');
        if (root) {
            var rootPayload = root.getAttribute('data-initial-payload');
            if (!payload && rootPayload) {
                try {
                    payload = JSON.parse(rootPayload);
                } catch (error) {
                    payload = {};
                }
            }
            var rootTarget = root.getAttribute('data-target-endpoint');
            if (!targetEndpoint && rootTarget) {
                targetEndpoint = rootTarget;
            }
        }

        var fields = {
            requestText: document.querySelector('[data-ai-field="request_text"]'),
            originalText: document.querySelector('[data-ai-field="original_text"]'),
            targetLabel: document.querySelector('[data-ai-field="target_label"]'),
            contextData: document.querySelector('[data-ai-field="context_data"]'),
            formSummary: document.querySelector('[data-ai-field="form_summary"]'),
        };

        fields.requestText.value = formatForEditor(payload.request_text, '');
        fields.originalText.value = formatForEditor(payload.original_text, '');
        fields.targetLabel.value = formatForEditor(payload.target_label, '');
        fields.contextData.value = formatForEditor(payload.context_data, '{}');
        fields.formSummary.value = formatForEditor(payload.form_summary, '{}');

        var endpointInput = document.querySelector('[data-ai-target-endpoint]');
        if (endpointInput) {
            endpointInput.value = targetEndpoint || '/ai';
        }

        var responseTarget = document.querySelector('[data-ai-response]');
        var statusTarget = document.querySelector('[data-ai-status]');
        var spinner = document.querySelector('[data-ai-spinner]');
        var endpointIndicator = document.querySelector('[data-ai-endpoint-indicator]');

        setActiveEndpointIndicator(endpointIndicator, targetEndpoint);

        function updateStatus(message, isError) {
            if (!statusTarget) {
                return;
            }
            statusTarget.classList.toggle('text-danger', !!isError);
            statusTarget.classList.toggle('text-muted', !isError);
            setText(statusTarget, message);
        }

        function toggleLoading(isLoading) {
            if (spinner) {
                spinner.classList.toggle('d-none', !isLoading);
            }
        }

        function handleError(error) {
            toggleLoading(false);
            updateStatus(error.message || 'Unable to submit request', true);
        }

        function handleSuccess(data) {
            toggleLoading(false);
            updateStatus('Response received', false);
            renderResponse(responseTarget, data);
        }

        function submitRequest() {
            if (!endpointInput) {
                return;
            }
            var endpoint = endpointInput.value || '/ai';
            setActiveEndpointIndicator(endpointIndicator, endpoint);

            var payloadForRequest;
            try {
                payloadForRequest = buildPayload(fields);
            } catch (error) {
                handleError(error);
                return;
            }

            toggleLoading(true);
            updateStatus('Submitting...', false);

            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify(payloadForRequest)
            }).then(function (response) {
                if (!response.ok) {
                    return response.text().then(function (text) {
                        throw new Error(text || response.statusText);
                    });
                }
                return response.json().catch(function () {
                    return response.text();
                });
            }).then(function (data) {
                handleSuccess(data);
            }).catch(function (error) {
                handleError(error);
            });
        }

        var form = document.querySelector('[data-ai-editor-form]');
        if (form) {
            form.addEventListener('submit', function (event) {
                event.preventDefault();
                submitRequest();
            });
        }

        var aiButton = document.querySelector('[data-ai-editor-submit]');
        if (aiButton) {
            aiButton.addEventListener('click', function () {
                submitRequest();
            });
        }

        if (config.metaInspectorUrl) {
            var metaLink = document.querySelector('[data-meta-link]');
            if (metaLink) {
                metaLink.href = config.metaInspectorUrl;
            }
        }
        if (config.historySinceUrl) {
            var historyLink = document.querySelector('[data-history-link]');
            if (historyLink) {
                historyLink.href = config.historySinceUrl;
            }
        }
        if (config.serverEventsSinceUrl) {
            var serverEventsLink = document.querySelector('[data-server-events-link]');
            if (serverEventsLink) {
                serverEventsLink.href = config.serverEventsSinceUrl;
            }
        }

        initialiseTabs();
    });
})();
