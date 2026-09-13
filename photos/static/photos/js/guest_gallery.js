(() => {
  const input = document.querySelector('[data-guest-files]');
  const label = document.querySelector('[data-guest-file-label]');
  if (input && label) {
    input.addEventListener('change', () => {
      const count = input.files ? input.files.length : 0;
      label.textContent = count ? `${count} photo${count === 1 ? '' : 's'} ready to share` : 'Tap to browse or open your camera';
    });
  }
  const form = document.querySelector('[data-guest-upload-form]');
  if (form) {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      if (button) {
        button.disabled = true;
        button.textContent = 'Uploading…';
      }
    });
  }
})();
