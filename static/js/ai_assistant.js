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

    function createHiddenInput(name, value) {
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        return input;
    }

    function AiAssistant(root, target, requestField, outputField) {
        this.root = root;
        this.target = target;
        this.requestField = requestField;
        this.outputField = outputField;
        this.contextData = parseContext(root);
        this.targetLabel = root.getAttribute('data-ai-target-label') || 'the text';
        this.entityType = root.getAttribute('data-ai-entity-type') || '';
        this.entityName = root.getAttribute('data-ai-entity-name') || '';
        this.entityNameFieldId = root.getAttribute('data-ai-entity-name-field') || '';
        var historyLimitValue = parseInt(root.getAttribute('data-ai-history-limit') || '10', 10);
        this.historyLimit = isNaN(historyLimitValue) ? 10 : historyLimitValue;
        this.historyList = root.querySelector('[data-ai-history-list]');
        this.historyEmpty = root.querySelector('[data-ai-history-empty]');
        this.changeField = root.querySelector('[data-change-message-store]');
        this.form = (this.target && this.target.form) || root.closest('form');
        this.isRunning = false;
        this.triggerButtons = [];
        this.lastRequestText = '';

        if (this.form && this.changeField) {
            var self = this;
            this.form.addEventListener('submit', function () {
                if (self.requestField) {
                    self.changeField.value = self.requestField.value || '';
                }
                var resolvedName = self._resolveEntityName();
                if (resolvedName) {
                    self.entityName = resolvedName;
                }
            });
        }
    }

    AiAssistant.prototype._resolveEntityName = function () {
        if (this.entityName && this.entityName.trim() !== '') {
            return this.entityName.trim();
        }
        if (!this.entityNameFieldId) {
            return '';
        }
        var nameField = document.getElementById(this.entityNameFieldId);
        if (!nameField || typeof nameField.value !== 'string') {
            return '';
        }
        return nameField.value.trim();
    };

    AiAssistant.prototype._getCsrfToken = function () {
        if (!this.form) {
            return '';
        }
        var csrfInput = this.form.querySelector('input[name="csrf_token"]');
        if (csrfInput && typeof csrfInput.value === 'string') {
            return csrfInput.value;
        }
        return '';
    };

    AiAssistant.prototype._bindHistoryItems = function () {
        if (!this.historyList) {
            return;
        }
        var self = this;
        this.historyList.querySelectorAll('[data-ai-interaction]').forEach(function (button) {
            var payload = button.getAttribute('data-interaction');
            if (!payload) {
                return;
            }
            try {
                var data = JSON.parse(payload);
                button.addEventListener('click', function () {
                    self.applyInteraction(data);
                });
            } catch (error) {
                console.warn('Unable to parse interaction payload:', error);
            }
        });
    };

    AiAssistant.prototype.applyInteraction = function (interaction) {
        if (!interaction) {
            return;
        }
        if (this.target && Object.prototype.hasOwnProperty.call(interaction, 'content')) {
            this.target.value = interaction.content || '';
            this.target.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (this.requestField && Object.prototype.hasOwnProperty.call(interaction, 'message')) {
            this.requestField.value = interaction.message || '';
        }
        if (this.changeField && Object.prototype.hasOwnProperty.call(interaction, 'message')) {
            this.changeField.value = interaction.message || '';
        }
        if (this.target) {
            this.target.focus();
        } else if (this.requestField) {
            this.requestField.focus();
        }
    };

    AiAssistant.prototype.updateHistory = function (items) {
        if (!this.historyList) {
            return;
        }

        this.historyList.innerHTML = '';
        var hasItems = Array.isArray(items) && items.length > 0;
        if (!hasItems) {
            if (this.historyEmpty) {
                this.historyEmpty.classList.remove('d-none');
            }
            return;
        }

        if (this.historyEmpty) {
            this.historyEmpty.classList.add('d-none');
        }

        var self = this;
        items.slice(0, this.historyLimit).forEach(function (item) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'list-group-item list-group-item-action';
            button.setAttribute('data-ai-interaction', '');
            try {
                button.setAttribute('data-interaction', JSON.stringify(item));
            } catch (error) {
                button.removeAttribute('data-interaction');
            }

            var header = document.createElement('div');
            header.className = 'd-flex justify-content-between align-items-center mb-1';

            var badge = document.createElement('span');
            badge.className = 'badge bg-light text-dark border';
            badge.textContent = item.action_display || '';
            header.appendChild(badge);

            var timestamp = document.createElement('small');
            timestamp.className = 'text-muted';
            timestamp.textContent = item.timestamp || '';
            header.appendChild(timestamp);

            var preview = document.createElement('div');
            preview.className = 'text-truncate';
            preview.textContent = item.preview || '';

            button.appendChild(header);
            button.appendChild(preview);
            button.addEventListener('click', function () {
                self.applyInteraction(item);
            });

            self.historyList.appendChild(button);
        });
    };

    AiAssistant.prototype._logInteraction = function (action, message, content) {
        if (!this.entityType) {
            return;
        }
        var resolvedName = this._resolveEntityName();
        if (!resolvedName) {
            return;
        }

        this.entityName = resolvedName;

        var payload = {
            entity_type: this.entityType,
            entity_name: resolvedName,
            action: action,
            message: message || '',
            content: content || ''
        };

        var self = this;
        fetch('/api/interactions', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('Unable to record interaction');
            }
            return response.json();
        }).then(function (data) {
            if (data && Array.isArray(data.interactions)) {
                self.updateHistory(data.interactions);
            }
        }).catch(function () {
            /* Ignore interaction logging errors to avoid interrupting the UI flow. */
        });
    };

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

        if (this.changeField && this.requestField) {
            this.changeField.value = this.requestField.value || '';
        }

        if (this.target) {
            this.target.focus();
        }

        this._logInteraction('ai', this.lastRequestText || '', updatedText);
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

    AiAssistant.prototype.buildRequestPayload = function () {
        if (!this.target || !this.requestField) {
            return null;
        }

        var form = this.form || this.root.closest('form');
        var contextData = this.contextData || {};
        var formSummary = collectFormData(form);

        return {
            request_text: this.requestField.value || '',
            original_text: this.target.value || '',
            target_label: this.targetLabel,
            context_data: contextData,
            form_summary: formSummary,
        };
    };

    AiAssistant.prototype.submitToEditor = function () {
        var payload = this.buildRequestPayload();
        if (!payload) {
            return;
        }

        var submission = document.createElement('form');
        submission.method = 'post';
        submission.action = '/ai_editor';
        submission.classList.add('d-none');

        var csrfToken = this._getCsrfToken();
        if (csrfToken) {
            submission.appendChild(createHiddenInput('csrf_token', csrfToken));
        }

        try {
            submission.appendChild(createHiddenInput('payload', JSON.stringify(payload)));
        } catch (error) {
            /* If JSON serialization fails, fall back to individual fields only. */
        }

        Object.keys(payload).forEach(function (key) {
            var value = payload[key];
            var serialised = value;
            if (value === null) {
                serialised = JSON.stringify(null);
            } else if (typeof value === 'undefined') {
                serialised = '';
            } else if (typeof value === 'object') {
                try {
                    serialised = JSON.stringify(value);
                } catch (error) {
                    serialised = '';
                }
            }
            submission.appendChild(createHiddenInput(key, serialised));
        });

        document.body.appendChild(submission);
        submission.submit();
    };

    AiAssistant.prototype.run = function () {
        if (this.isRunning) {
            return;
        }

        var payload = this.buildRequestPayload();
        if (!payload) {
            return;
        }

        this.lastRequestText = payload.request_text;
        var resolvedName = this._resolveEntityName();
        if (resolvedName) {
            this.entityName = resolvedName;
        }

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
            assistant._bindHistoryItems();
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

        document.querySelectorAll('[data-ai-request-editor]').forEach(function (link) {
            var targetId = link.getAttribute('data-ai-target-id');
            if (!targetId || !assistantMap.has(targetId)) {
                return;
            }
            var assistant = assistantMap.get(targetId);
            link.addEventListener('click', function (event) {
                event.preventDefault();
                assistant.submitToEditor();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialiseAssistants);
    } else {
        initialiseAssistants();
    }
})();
