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

    function AiAssistant(root, target, requestField, outputField) {
        this.root = root;
        this.target = target;
        this.requestField = requestField;
        this.outputField = outputField;
        this.contextData = parseContext(root);
        this.targetLabel = root.getAttribute('data-ai-target-label') || 'the text';
        this.isRunning = false;
        this.triggerButtons = [];
    }

    AiAssistant.prototype.setLoadingState = function (isLoading) {
        this.isRunning = isLoading;
        this.triggerButtons.forEach(function (button) {
            button.disabled = isLoading;
        });
        if (this.outputField && isLoading) {
            this.outputField.classList.remove('d-none');
            this.outputField.classList.remove('alert-danger');
            this.outputField.classList.add('alert-info');
            this.outputField.textContent = 'Contacting AI stub…';
        }
    };

    AiAssistant.prototype._ensureOutputField = function () {
        if (!this.outputField) {
            return;
        }
        this.outputField.classList.remove('d-none');
        this.outputField.classList.remove('alert-danger');
        this.outputField.classList.add('alert-info');
        this.outputField.innerHTML = '';
    };

    AiAssistant.prototype._appendMessage = function (message) {
        if (!this.outputField) {
            return;
        }
        var heading = document.createElement('strong');
        heading.textContent = 'AI Response:';
        this.outputField.appendChild(heading);

        var messageElement = document.createElement('div');
        messageElement.textContent = message || '';
        this.outputField.appendChild(messageElement);
    };

    AiAssistant.prototype._appendSummary = function (summary) {
        if (!this.outputField || !summary) {
            return;
        }
        var summaryElement = document.createElement('div');
        summaryElement.classList.add('small', 'text-muted', 'mt-1');
        summaryElement.textContent = summary;
        this.outputField.appendChild(summaryElement);
    };

    AiAssistant.prototype._displayError = function (error) {
        if (!this.outputField) {
            return;
        }
        this.outputField.classList.remove('d-none');
        this.outputField.classList.remove('alert-info');
        this.outputField.classList.add('alert-danger');
        this.outputField.textContent = error;
    };

    AiAssistant.prototype._handleSuccess = function (result) {
        if (!result || typeof result !== 'object') {
            this._displayError('AI stub returned an unexpected response.');
            return;
        }

        var updatedText = result.updated_text || '';
        var message = result.message || '';
        var contextSummary = result.context_summary || '';

        if (this.target) {
            this.target.value = updatedText;
            this.target.dispatchEvent(new Event('input', { bubbles: true }));
        }

        this._ensureOutputField();
        this._appendMessage(message);
        this._appendSummary(contextSummary);

        if (this.target) {
            this.target.focus();
        }
    };

    AiAssistant.prototype._handleFailure = function (error) {
        var message = 'AI request failed.';
        if (error) {
            message += ' ' + error;
        }
        this._displayError(message);
        if (this.target) {
            this.target.focus();
        }
    };

    AiAssistant.prototype.run = function () {
        if (this.isRunning) {
            return;
        }

        if (!this.target || !this.requestField) {
            return;
        }

        var requestText = this.requestField.value || '';
        var originalText = this.target.value || '';
        var form = this.target.form || this.root.closest('form');
        var contextData = this.contextData || {};
        var formSummary = collectFormData(form);

        var payload = {
            request_text: requestText,
            original_text: originalText,
            target_label: this.targetLabel,
            context_data: contextData,
            form_summary: formSummary
        };

        var self = this;
        this.setLoadingState(true);

        fetch('/ai', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        }).then(function (response) {
            if (!response.ok) {
                return response.text().then(function (text) {
                    var errorDetail = text ? text.trim() : response.statusText;
                    throw new Error(errorDetail || 'Unexpected status ' + response.status);
                });
            }
            return response.json();
        }).then(function (data) {
            self._handleSuccess(data);
        }).catch(function (error) {
            self._handleFailure(error && error.message ? error.message : '');
        }).finally(function () {
            self.setLoadingState(false);
        });
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
            var assistant = assistantMap.get(targetId);
            assistant.triggerButtons.push(button);
            button.addEventListener('click', function () {
                assistant.run();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialiseAssistants);
    } else {
        initialiseAssistants();
    }
})();
