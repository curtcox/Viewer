(function () {
    function onReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else {
            callback();
        }
    }

    onReady(() => {
        const textarea = document.getElementById('variables_json');
        const errorContainer = document.getElementById('variables-json-error');
        const submitButton = document.getElementById('variables-json-submit');
        if (!textarea || !errorContainer || !submitButton) {
            return;
        }

        const namePattern = /^[A-Za-z0-9._-]+$/;

        function showError(message) {
            errorContainer.textContent = message;
            errorContainer.classList.remove('d-none');
            submitButton.disabled = true;
            textarea.classList.add('is-invalid');
            const editor = document.getElementById('variables-json-editor');
            if (editor) {
                editor.classList.add('is-invalid');
            }
        }

        function clearError() {
            errorContainer.textContent = '';
            errorContainer.classList.add('d-none');
            submitButton.disabled = false;
            textarea.classList.remove('is-invalid');
            const editor = document.getElementById('variables-json-editor');
            if (editor) {
                editor.classList.remove('is-invalid');
            }
        }

        function validate() {
            const value = textarea.value || '';
            if (!value.trim()) {
                showError('Variables JSON cannot be empty.');
                return;
            }

            let parsed;
            try {
                parsed = JSON.parse(value);
            } catch (error) {
                showError(`Invalid JSON: ${error.message}`);
                return;
            }

            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
                showError('Variables JSON must be an object mapping variable names to values.');
                return;
            }

            for (const [name] of Object.entries(parsed)) {
                if (!namePattern.test(name)) {
                    showError(
                        `Invalid variable name "${name}". Variable names may only contain letters, numbers, dots, hyphens, and underscores.`
                    );
                    return;
                }
            }

            clearError();
        }

        textarea.addEventListener('input', validate);
        validate();
    });
})();
