document.querySelectorAll('[data-rsvp-form]').forEach((form) => {
  const responseInput = form.querySelector('[data-rsvp-value]');
  const partyPanel = form.querySelector('[data-party-panel]');
  const warning = form.querySelector('[data-party-warning]');
  const limit = Number(form.dataset.partyLimit || 1);
  const adults = form.querySelector('#adults');
  const children = form.querySelector('#children');

  const total = () => Number(adults.value || 0) + Number(children.value || 0);

  const renderParty = () => {
    const attending = responseInput.value === 'ATTENDING';
    partyPanel.classList.toggle('is-hidden', !attending);
    if (attending && total() < 1) adults.value = 1;
  };

  form.querySelectorAll('[data-choice]').forEach((button) => {
    button.addEventListener('click', () => {
      form.querySelectorAll('[data-choice]').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      responseInput.value = button.dataset.value;
      renderParty();
    });
  });

  form.querySelectorAll('[data-step]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.target === 'adults' ? adults : children;
      const step = Number(button.dataset.step);
      const next = Math.max(0, Number(target.value || 0) + step);
      const projected = total() - Number(target.value || 0) + next;

      if (projected > limit) {
        warning.textContent = `Your invitation allows up to ${limit} guest${limit === 1 ? '' : 's'}.`;
        return;
      }

      target.value = next;
      warning.textContent = '';
      if (total() < 1) adults.value = 1;
    });
  });

  form.addEventListener('submit', (event) => {
    if (!responseInput.value) {
      event.preventDefault();
      warning.textContent = 'Please choose attending, not attending, or maybe.';
      form.querySelector('[data-choice-group]').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });

  renderParty();
});
