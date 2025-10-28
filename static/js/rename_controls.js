(function () {
    function onReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    }

    function setButtonLabel(button, label) {
        if (!button) {
            return;
        }
        const text = typeof label === 'string' ? label : '';
        if (button.tagName === 'INPUT') {
            button.value = text;
        } else {
            button.textContent = text;
        }
    }

    function toggleButton(button, show) {
        if (!button) {
            return;
        }
        if (show) {
            button.classList.remove('d-none');
            button.removeAttribute('aria-hidden');
            button.disabled = false;
        } else {
            if (!button.classList.contains('d-none')) {
                button.classList.add('d-none');
            }
            button.setAttribute('aria-hidden', 'true');
            button.disabled = true;
        }
    }

    function buildLabel(template, fallbackPrefix, name) {
        const safeName = typeof name === 'string' ? name : '';
        if (typeof template === 'string' && template.includes('__name__')) {
            return template.replace(/__name__/g, safeName);
        }
        if (typeof template === 'string' && template.trim().length > 0) {
            return template;
        }
        if (typeof fallbackPrefix === 'string' && fallbackPrefix.length > 0) {
            return `${fallbackPrefix}${safeName}`;
        }
        return safeName;
    }

    function initRenameControl(container) {
        if (!container) {
            return;
        }

        const nameFieldId = container.getAttribute('data-name-field');
        if (!nameFieldId) {
            return;
        }

        const nameField = document.getElementById(nameFieldId);
        if (!nameField) {
            return;
        }

        const saveButton = container.querySelector('[data-primary-save]');
        if (!saveButton) {
            return;
        }

        const saveAsButton = container.querySelector('[data-save-as-button]');
        const defaultLabel = saveButton.getAttribute('data-default-label') || saveButton.value || saveButton.textContent || 'Save';
        const renameTemplate = container.getAttribute('data-rename-template') || '';
        const saveAsTemplate = container.getAttribute('data-save-as-template') || '';
        const originalName = (container.getAttribute('data-original-name') || '').trim();
        const patternSource = container.getAttribute('data-name-pattern');

        let namePattern = null;
        if (patternSource) {
            try {
                namePattern = new RegExp(patternSource);
            } catch (error) {
                namePattern = null;
            }
        }

        function isValidName(value) {
            if (typeof value !== 'string') {
                return false;
            }
            const candidate = value.trim();
            if (!candidate) {
                return false;
            }
            if (!namePattern) {
                return true;
            }
            try {
                return namePattern.test(candidate);
            } catch (error) {
                return true;
            }
        }

        function updateButtons() {
            const rawValue = typeof nameField.value === 'string' ? nameField.value : '';
            const trimmedValue = rawValue.trim();
            const hasOriginal = originalName.length > 0;
            const differentName = hasOriginal && trimmedValue && trimmedValue !== originalName;
            const offerRename = differentName && isValidName(trimmedValue);

            if (offerRename) {
                const renameLabel = buildLabel(renameTemplate, 'Rename to ', trimmedValue);
                const saveAsLabel = buildLabel(saveAsTemplate, 'Save As ', trimmedValue);
                setButtonLabel(saveButton, renameLabel);
                if (saveAsButton) {
                    setButtonLabel(saveAsButton, saveAsLabel);
                    toggleButton(saveAsButton, true);
                }
                container.setAttribute('data-rename-active', 'true');
            } else {
                setButtonLabel(saveButton, defaultLabel);
                if (saveAsButton) {
                    toggleButton(saveAsButton, false);
                    setButtonLabel(saveAsButton, buildLabel(saveAsTemplate, 'Save As ', trimmedValue));
                }
                container.removeAttribute('data-rename-active');
            }
        }

        nameField.addEventListener('input', updateButtons);
        nameField.addEventListener('change', updateButtons);

        updateButtons();
    }

    onReady(() => {
        const containers = document.querySelectorAll('[data-rename-control]');
        if (!containers || containers.length === 0) {
            return;
        }
        containers.forEach((container) => {
            initRenameControl(container);
        });
    });
})();
