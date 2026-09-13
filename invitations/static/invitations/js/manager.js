document.querySelectorAll('[data-copy-path]').forEach((button) => {
  button.addEventListener('click', async () => {
    const path = button.dataset.copyPath;
    const url = `${window.location.origin}${path}`;
    try {
      await navigator.clipboard.writeText(url);
      const oldText = button.textContent;
      button.textContent = 'Copied';
      button.classList.add('copied');
      window.setTimeout(() => {
        button.textContent = oldText;
        button.classList.remove('copied');
      }, 1400);
    } catch (error) {
      window.prompt('Copy invitation link:', url);
    }
  });
});
