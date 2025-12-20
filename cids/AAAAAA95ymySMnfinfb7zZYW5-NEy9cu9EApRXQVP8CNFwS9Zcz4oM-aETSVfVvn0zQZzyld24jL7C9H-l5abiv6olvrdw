(function () {
  const tableBody = document.getElementById('cookie-rows');
  const emptyState = document.getElementById('empty-state');
  const addForm = document.getElementById('add-cookie-form');
  const toast = document.getElementById('toast');
  const expiresSelect = document.getElementById('cookie-expiry');
  const pathInput = document.getElementById('cookie-path');

  function showToast(message, tone = 'info') {
    toast.textContent = message;
    toast.setAttribute('data-tone', tone);
    toast.classList.add('toast--visible');
    window.setTimeout(() => toast.classList.remove('toast--visible'), 2600);
  }

  function parseCookies() {
    const raw = document.cookie;
    if (!raw) return [];
    return raw.split(';').map((pair) => {
      const [name, ...rest] = pair.split('=');
      return {
        name: decodeURIComponent(name.trim()),
        value: decodeURIComponent(rest.join('=').trim()),
      };
    }).filter((cookie) => cookie.name);
  }

  function serializeCookie(name, value, options = {}) {
    const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
    if (options.path) {
      parts.push(`path=${options.path}`);
    }
    if (options.maxAge) {
      parts.push(`max-age=${options.maxAge}`);
    }
    if (options.expires instanceof Date) {
      parts.push(`expires=${options.expires.toUTCString()}`);
    }
    return parts.join('; ');
  }

  function setCookie(name, value, { days, path }) {
    const opts = { path: path || '/' };
    if (Number.isFinite(days)) {
      const expireDate = new Date();
      expireDate.setDate(expireDate.getDate() + days);
      opts.expires = expireDate;
    }
    document.cookie = serializeCookie(name, value, opts);
  }

  function deleteCookie(name, path) {
    document.cookie = serializeCookie(name, '', {
      path: path || '/',
      expires: new Date(0),
    });
  }

  function renderRows() {
    const cookies = parseCookies();
    tableBody.innerHTML = '';
    if (!cookies.length) {
      emptyState.hidden = false;
      return;
    }
    emptyState.hidden = true;

    cookies.forEach((cookie) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td class="table__name">${cookie.name}</td>
        <td><input class="table__value-input" type="text" aria-label="Value for ${cookie.name}" value="${cookie.value}" /></td>
        <td class="table__actions">
          <button class="button button--secondary" data-action="save">Save</button>
          <button class="button button--danger" data-action="delete">Delete</button>
        </td>
      `;

      const valueInput = row.querySelector('input');
      const saveButton = row.querySelector('[data-action="save"]');
      const deleteButton = row.querySelector('[data-action="delete"]');

      saveButton.addEventListener('click', () => {
        setCookie(cookie.name, valueInput.value, {
          days: Number(expiresSelect.value),
          path: pathInput.value,
        });
        showToast(`Saved ${cookie.name}`);
        renderRows();
      });

      deleteButton.addEventListener('click', () => {
        deleteCookie(cookie.name, pathInput.value);
        showToast(`Deleted ${cookie.name}`, 'danger');
        renderRows();
      });

      tableBody.appendChild(row);
    });
  }

  addForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const name = document.getElementById('new-name').value.trim();
    const value = document.getElementById('new-value').value;
    const days = Number(expiresSelect.value);
    const path = pathInput.value;

    if (!name) {
      showToast('Cookie name is required', 'danger');
      return;
    }

    setCookie(name, value, { days, path });
    showToast(`Added ${name}`);
    addForm.reset();
    expiresSelect.value = '30';
    pathInput.value = '/';
    renderRows();
  });

  document.getElementById('refresh-btn').addEventListener('click', renderRows);

  renderRows();
})();
