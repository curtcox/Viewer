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
        const queryInput = document.getElementById('search-query');
        const searchForm = document.getElementById('search-form');
        const resultsContainer = document.getElementById('search-results');
        const statusElement = document.getElementById('search-status');
        const endpointInput = document.getElementById('search-endpoint');
        const filterInputs = Array.from(document.querySelectorAll('[data-search-category]'));
        const countElements = Array.from(document.querySelectorAll('[data-search-count]'));
        const apiUrl = endpointInput ? endpointInput.value : null;

        if (!queryInput || !resultsContainer || !statusElement || !apiUrl) {
            return;
        }

        const categoryOrder = filterInputs.map((input) => input.dataset.searchCategory);
        const categoryLinks = {
            aliases: '/aliases',
            servers: '/servers',
            variables: '/variables',
            secrets: '/secrets/',
            cids: '/uploads',
        };
        let debounceHandle = null;
        let activeController = null;
        let requestSequence = 0;

        function resetCounts() {
            countElements.forEach((element) => {
                element.textContent = '0';
            });
        }

        function clearResults(message) {
            if (activeController) {
                activeController.abort();
                activeController = null;
            }
            resultsContainer.innerHTML = '';
            resetCounts();
            if (typeof message === 'string') {
                statusElement.textContent = message;
            }
        }

        function getSelectedCategories() {
            return filterInputs
                .filter((input) => input.checked)
                .map((input) => input.dataset.searchCategory)
                .filter(Boolean);
        }

        function updateCounts(categories) {
            countElements.forEach((element) => {
                const category = element.getAttribute('data-search-count');
                const info = categories && categories[category] ? categories[category] : null;
                const value = info && typeof info.count === 'number' ? info.count : 0;
                element.textContent = value;
            });
        }

        function renderResults(categories) {
            resultsContainer.innerHTML = '';
            let totalMatches = 0;

            const baseOrder = categoryOrder.length ? categoryOrder.slice() : Object.keys(categories || {});
            const seen = new Set();
            const displayOrder = [];

            function pushKey(key) {
                if (!key || seen.has(key)) {
                    return;
                }
                seen.add(key);
                displayOrder.push(key);
            }

            baseOrder.forEach((key) => {
                if (key === 'cids') {
                    return;
                }
                pushKey(key);
            });

            Object.keys(categories || {}).forEach((key) => {
                if (key === 'cids') {
                    return;
                }
                pushKey(key);
            });

            if (baseOrder.includes('cids') || (categories && Object.prototype.hasOwnProperty.call(categories, 'cids'))) {
                pushKey('cids');
            }

            displayOrder.forEach((key) => {
                const category = categories[key];
                if (!category) {
                    return;
                }
                const items = Array.isArray(category.items) ? category.items : [];
                const label = category.label || key;
                const count = typeof category.count === 'number' ? category.count : items.length;
                totalMatches += count;
                if (items.length === 0) {
                    return;
                }

                const section = document.createElement('section');
                section.className = 'mb-4';

                const heading = document.createElement('h2');
                heading.className = 'h5 mb-3 text-uppercase text-muted';
                const destination = categoryLinks[key];
                if (destination) {
                    const link = document.createElement('a');
                    link.href = destination;
                    link.className = 'text-decoration-none text-muted';
                    link.textContent = `${label}`;
                    heading.appendChild(link);
                } else {
                    heading.textContent = `${label}`;
                }
                section.appendChild(heading);

                items.forEach((item) => {
                    const card = document.createElement('div');
                    card.className = 'card shadow-sm mb-3 position-relative';

                    const body = document.createElement('div');
                    body.className = 'card-body';

                    const title = document.createElement('h3');
                    title.className = 'h5 card-title mb-2';
                    const nameHtml = typeof item.name_highlighted === 'string'
                        ? item.name_highlighted
                        : escapeHtml(item.name || '');

                    if (item.url) {
                        const link = document.createElement('a');
                        link.href = item.url;
                        link.className = 'stretched-link text-decoration-none';
                        link.innerHTML = nameHtml;
                        title.appendChild(link);
                    } else {
                        title.innerHTML = nameHtml;
                    }
                    body.appendChild(title);

                    const details = Array.isArray(item.details) ? item.details : [];
                    details.forEach((detail) => {
                        if (!detail || typeof detail !== 'object') {
                            return;
                        }
                        const wrapper = document.createElement('div');
                        wrapper.className = 'mb-2';

                        if (detail.label) {
                            const labelEl = document.createElement('div');
                            labelEl.className = 'small text-uppercase text-muted fw-semibold mb-1';
                            labelEl.textContent = detail.label;
                            wrapper.appendChild(labelEl);
                        }

                        const valueEl = document.createElement('div');
                        valueEl.className = 'fw-medium';
                        valueEl.innerHTML = typeof detail.value === 'string'
                            ? detail.value
                            : escapeHtml(String(detail.value || ''));
                        wrapper.appendChild(valueEl);

                        body.appendChild(wrapper);
                    });

                    if (details.length === 0) {
                        const fallback = document.createElement('p');
                        fallback.className = 'text-muted small mb-0';
                        fallback.textContent = 'Matching name only';
                        body.appendChild(fallback);
                    }

                    card.appendChild(body);
                    section.appendChild(card);
                });

                resultsContainer.appendChild(section);
            });

            return totalMatches;
        }

        function performSearch() {
            const query = (queryInput.value || '').trim();
            const enabledCategories = getSelectedCategories();

            if (!query) {
                clearResults('Start typing to search your workspace.');
                return;
            }

            if (enabledCategories.length === 0) {
                clearResults('Select at least one category to search.');
                return;
            }

            if (activeController) {
                activeController.abort();
            }
            activeController = new AbortController();
            const thisRequest = ++requestSequence;

            const params = new URLSearchParams();
            params.set('q', query);
            filterInputs.forEach((input) => {
                const category = input.dataset.searchCategory;
                if (!category) {
                    return;
                }
                params.set(category, input.checked ? '1' : '0');
            });

            statusElement.textContent = 'Searching…';

            fetch(`${apiUrl}?${params.toString()}`, {
                signal: activeController.signal,
                headers: {
                    'Accept': 'application/json',
                },
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Search failed with status ${response.status}`);
                    }
                    return response.json();
                })
                .then((payload) => {
                    if (thisRequest !== requestSequence) {
                        return;
                    }
                    const categories = payload && payload.categories ? payload.categories : {};
                    updateCounts(categories);
                    const totalMatches = renderResults(categories);
                    if (totalMatches === 0) {
                        statusElement.textContent = 'No matches found.';
                    } else {
                        statusElement.textContent = `Showing ${totalMatches} match${totalMatches === 1 ? '' : 'es'}.`;
                    }
                })
                .catch((error) => {
                    if (error.name === 'AbortError') {
                        return;
                    }
                    clearResults('Unable to complete the search. Please try again.');
                    console.error('Search request failed:', error);
                })
                .finally(() => {
                    if (thisRequest === requestSequence) {
                        activeController = null;
                    }
                });
        }

        function scheduleSearch() {
            if (debounceHandle) {
                clearTimeout(debounceHandle);
            }
            debounceHandle = setTimeout(performSearch, 250);
        }

        queryInput.addEventListener('input', scheduleSearch);
        filterInputs.forEach((input) => {
            input.addEventListener('change', scheduleSearch);
        });

        if (searchForm) {
            searchForm.addEventListener('submit', (event) => {
                event.preventDefault();
                performSearch();
            });
        }
    });
})();
