(function () {
    const form = document.getElementById('wedding-editor-form');
    if (!form) return;

    const byId = (id) => document.getElementById(id);
    const field = (name) => form.querySelector(`[name="${name}"]`);

    const nameInput = field('name');
    const slugInput = field('slug');
    const brideInput = field('bride_name');
    const groomInput = field('groom_name');
    const dateInput = field('wedding_date');
    const timezoneInput = field('timezone');
    const statusInput = field('status');
    const guestInput = field('guest_limit');
    const photoInput = field('photo_limit');
    const printInput = field('print_limit');

    let slugTouched = Boolean(slugInput && slugInput.value.trim());

    function slugify(value) {
        return value
            .toLowerCase()
            .trim()
            .replace(/&/g, ' and ')
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '')
            .slice(0, 255);
    }

    function updatePreview() {
        const groom = (groomInput && groomInput.value.trim()) || 'Groom';
        const bride = (brideInput && brideInput.value.trim()) || 'Bride';

        if (byId('preview-groom')) byId('preview-groom').textContent = groom;
        if (byId('preview-bride')) byId('preview-bride').textContent = bride;
        if (byId('preview-couple')) byId('preview-couple').textContent = `${groom} & ${bride}`;
        if (byId('preview-slug')) byId('preview-slug').textContent = (slugInput && slugInput.value) || 'your-wedding';
        if (byId('preview-timezone')) byId('preview-timezone').textContent = (timezoneInput && timezoneInput.value) || 'Asia/Yangon';
        if (byId('preview-status') && statusInput) byId('preview-status').textContent = statusInput.options[statusInput.selectedIndex]?.text || 'Draft';
        if (byId('preview-guests') && guestInput) byId('preview-guests').textContent = guestInput.value || '0';
        if (byId('preview-photos') && photoInput) byId('preview-photos').textContent = photoInput.value || '0';
        if (byId('preview-prints') && printInput) byId('preview-prints').textContent = printInput.value || '0';

        if (dateInput && dateInput.value) {
            const date = new Date(dateInput.value);
            if (!Number.isNaN(date.getTime())) {
                const dateOnly = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
                const full = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date);
                if (byId('preview-date')) byId('preview-date').textContent = dateOnly;
                if (byId('preview-datetime')) byId('preview-datetime').textContent = full;
            }
        }
    }

    if (nameInput && slugInput) {
        nameInput.addEventListener('input', function () {
            if (!slugTouched) slugInput.value = slugify(nameInput.value);
            updatePreview();
        });
        slugInput.addEventListener('input', function () {
            slugTouched = true;
            slugInput.value = slugify(slugInput.value);
            updatePreview();
        });
    }

    [brideInput, groomInput, dateInput, timezoneInput, statusInput, guestInput, photoInput, printInput]
        .filter(Boolean)
        .forEach((input) => input.addEventListener('input', updatePreview));

    updatePreview();
})();
