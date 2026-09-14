(function () {
    const builder = document.querySelector('[data-section-builder]');
    if (!builder) return;
    const list = builder.querySelector('[data-section-list]');
    if (!list) return;

    function rows() {
        return Array.from(list.querySelectorAll('[data-section-row]'));
    }

    function updateLabels() {
        rows().forEach((row, index) => {
            const fixed = row.querySelector('.fixed-order');
            if (fixed) fixed.textContent = String(index + 1).padStart(2, '0');
            const checkbox = row.querySelector('input[type="checkbox"][name="section_enabled"]');
            const label = row.querySelector('.section-switch b');
            if (checkbox && label) label.textContent = checkbox.checked && !checkbox.disabled ? 'On' : 'Off';
        });
    }

    list.addEventListener('click', function (event) {
        const button = event.target.closest('button[data-move]');
        if (!button) return;
        const row = button.closest('[data-section-row]');
        if (!row || row.dataset.key === 'hero') return;
        const all = rows();
        const index = all.indexOf(row);
        if (button.dataset.move === 'up' && index > 1) {
            list.insertBefore(row, all[index - 1]);
        } else if (button.dataset.move === 'down' && index >= 1 && index < all.length - 1) {
            list.insertBefore(all[index + 1], row);
        }
        updateLabels();
    });

    list.addEventListener('change', updateLabels);
    updateLabels();
})();
