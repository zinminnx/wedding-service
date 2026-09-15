(function () {
  function syncRsvpPressed(form) {
    form.querySelectorAll('[data-choice]').forEach(function (button) {
      button.setAttribute('aria-pressed', button.classList.contains('active') ? 'true' : 'false');
    });
  }

  document.querySelectorAll('[data-rsvp-form]').forEach(function (form) {
    form.querySelectorAll('[data-choice]').forEach(function (button) {
      button.addEventListener('click', function () {
        window.requestAnimationFrame(function () { syncRsvpPressed(form); });
      });
    });
    syncRsvpPressed(form);
  });

  document.querySelectorAll('[data-gift-form]').forEach(function (form) {
    var proof = form.querySelector('[data-gift-proof]');
    var cards = form.querySelectorAll('.gift-choice-card');

    function syncGiftUI() {
      var selected = form.querySelector('input[name="gift_choice"]:checked');
      cards.forEach(function (card) {
        var input = card.querySelector('input[name="gift_choice"]');
        card.classList.toggle('is-selected', !!input && input.checked);
      });
      if (proof) {
        proof.classList.toggle('is-hidden', !selected || selected.value !== 'DIGITAL');
      }
    }

    form.querySelectorAll('input[name="gift_choice"]').forEach(function (radio) {
      radio.addEventListener('change', syncGiftUI);
    });
    syncGiftUI();
  });
})();
