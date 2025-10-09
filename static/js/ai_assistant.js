(function () {
    'use strict';

    function parseContext(root) {
        var contextAttribute = root.getAttribute('data-ai-context');
        if (!contextAttribute) {
            return null;
        }
        try {
            return JSON.parse(contextAttribute);
        } catch (error) {
            console.warn('Unable to parse AI context data:', error);
            return null;
        }
    }

    function normaliseButtonClasses(button) {
        if (!button.classList.contains('btn')) {
            button.classList.add('btn');
        }
        if (!button.classList.contains('btn-outline-primary') && !button.classList.contains('btn-primary')) {
            button.classList.add('btn-outline-primary');
        }
    }

    function summariseContext(context) {
        if (!context || typeof context !== 'object') {
            return null;
        }
        var keys = Object.keys(context);
        if (keys.length === 0) {
            return null;
        }
        return 'Context keys: ' + keys.join(', ');
    }

    function collectFormData(form) {
        if (!form) {
            return null;
        }
        try {
            var formData = new FormData(form);
            var summary = {};
            for (var pair of formData.entries()) {
                var key = pair[0];
                var value = pair[1];
                if (value instanceof File) {
                    summary[key] = value.name || 'file';
                } else {
                    summary[key] = value;
                }
            }
            return summary;
        } catch (error) {
            console.warn('Unable to collect form data for AI assistant:', error);
            return null;
        }
    }

    function buildStubResponse(config) {
        var requestText = config.requestText || '';
        var originalText = config.originalText || '';
        var separator = '';
        if (originalText && requestText) {
            separator = originalText.endsWith('\n') ? '' : '\n';
        }
        var updatedText = originalText + separator + requestText;
        var targetLabel = config.targetLabel || 'the text';
        var message = 'OK I changed ' + targetLabel + ' by ' + requestText;
        var contextSummary = summariseContext(config.contextData) || '';
        if (config.formSummary) {
            var formKeys = Object.keys(config.formSummary);
            if (formKeys.length > 0) {
                var formSummary = 'Form fields captured: ' + formKeys.join(', ');
                contextSummary = contextSummary ? contextSummary + '\n' + formSummary : formSummary;
            }
        }
        return {
            updatedText: updatedText,
            message: message,
            contextSummary: contextSummary
        };
    }

    function AiAssistant(root, target, requestField, outputField) {
        this.root = root;
        this.target = target;
        this.requestField = requestField;
        this.outputField = outputField;
        this.contextData = parseContext(root);
        this.targetLabel = root.getAttribute('data-ai-target-label') || 'the text';
    }

    AiAssistant.prototype.run = function () {
        if (!this.target || !this.requestField) {
            return;
        }

        var requestText = this.requestField.value || '';
        var originalText = this.target.value || '';
        var form = this.target.form || this.root.closest('form');
        var contextData = this.contextData || {};
        var formSummary = collectFormData(form);

        var result = buildStubResponse({
            requestText: requestText,
            originalText: originalText,
            targetLabel: this.targetLabel,
            contextData: contextData,
            formSummary: formSummary
        });

        this.target.value = result.updatedText;
        this.target.dispatchEvent(new Event('input', { bubbles: true }));

        if (this.outputField) {
            this.outputField.classList.remove('d-none');
            this.outputField.classList.remove('alert-danger');
            this.outputField.classList.add('alert-info');
            this.outputField.innerHTML = '';

            var heading = document.createElement('strong');
            heading.textContent = 'AI Response:';
            this.outputField.appendChild(heading);

            var message = document.createElement('div');
            message.textContent = result.message;
            this.outputField.appendChild(message);

            if (result.contextSummary) {
                var summary = document.createElement('div');
                summary.classList.add('small', 'text-muted', 'mt-1');
                summary.textContent = result.contextSummary;
                this.outputField.appendChild(summary);
            }
        }

        this.target.focus();
    };

    function initialiseAssistants() {
        var assistantMap = new Map();
        document.querySelectorAll('.ai-text-assistant').forEach(function (root) {
            var targetId = root.getAttribute('data-ai-target-id');
            if (!targetId) {
                return;
            }
            var target = document.getElementById(targetId);
            var requestField = root.querySelector('[data-ai-input]');
            var outputField = root.querySelector('[data-ai-output]');
            if (!target || !requestField) {
                return;
            }
            var assistant = new AiAssistant(root, target, requestField, outputField);
            assistantMap.set(targetId, assistant);
        });

        document.querySelectorAll('[data-ai-trigger]').forEach(function (button) {
            var targetId = button.getAttribute('data-ai-target-id');
            if (!targetId || !assistantMap.has(targetId)) {
                return;
            }
            normaliseButtonClasses(button);
            button.addEventListener('click', function () {
                assistantMap.get(targetId).run();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialiseAssistants);
    } else {
        initialiseAssistants();
    }
})();
