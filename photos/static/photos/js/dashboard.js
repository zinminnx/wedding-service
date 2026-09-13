(() => {
  const selectAll = document.querySelector('[data-select-all]');
  const checkboxes = () => Array.from(document.querySelectorAll('[data-photo-checkbox]'));
  if (selectAll) {
    selectAll.addEventListener('change', () => checkboxes().forEach((box) => { box.checked = selectAll.checked; }));
  }

  document.querySelectorAll('[data-confirm]').forEach((button) => {
    button.addEventListener('click', (event) => {
      if (!window.confirm(button.dataset.confirm || 'Are you sure?')) event.preventDefault();
    });
  });

  const fileInput = document.querySelector('[data-file-input]');
  const fileLabel = document.querySelector('[data-file-label]');
  if (fileInput && fileLabel) {
    fileInput.addEventListener('change', () => {
      const count = fileInput.files ? fileInput.files.length : 0;
      fileLabel.textContent = count ? `${count} photo${count === 1 ? '' : 's'} selected` : 'No files selected';
    });
  }

  document.querySelectorAll('[data-copy-button]').forEach((button) => {
    button.addEventListener('click', async () => {
      const input = button.closest('.photo-copy-row')?.querySelector('[data-copy-input]');
      if (!input) return;
      try {
        await navigator.clipboard.writeText(input.value);
        const original = button.textContent;
        button.textContent = 'Copied';
        setTimeout(() => { button.textContent = original; }, 1300);
      } catch (_) {
        input.select();
        document.execCommand('copy');
      }
    });
  });
})();
