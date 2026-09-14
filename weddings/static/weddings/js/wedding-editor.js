(function () {
    const form = document.getElementById('wedding-editor-form');
    if (!form) return;

    const panels = Array.from(form.querySelectorAll('[data-step-panel]'));
    const stepButtons = Array.from(document.querySelectorAll('[data-step-target]'));
    const backButton = document.getElementById('wizard-back');
    const nextButton = document.getElementById('wizard-next');
    const finishButton = document.getElementById('wizard-finish');
    const dashboardButton = document.getElementById('wizard-dashboard');
    const progressBar = document.getElementById('wizard-progress-bar');
    const progressLabel = document.getElementById('wizard-progress-label');
    const progressCopy = document.getElementById('wizard-progress-copy');

    const progressText = {
        1: 'Start with the wedding identity.',
        2: 'Set the names guests will see.',
        3: 'Confirm the event timeline and timezone.',
        4: 'Review limits and choose Draft or Active.'
    };

    let currentStep = 1;

    const byId = (id) => document.getElementById(id);
    const field = (name) => form.querySelector(`[name="${name}"]`);
    const nameInput = field('name');
    const slugInput = field('slug');
    const brideInput = field('bride_name');
    const groomInput = field('groom_name');
    const startInput = field('start_date');
    const dateInput = field('wedding_date');
    const expireInput = field('expire_date');
    const timezoneInput = field('timezone');
    const locationInput = field('wedding_location');
    const mapInput = field('google_maps_url');
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

    function displayDate(value, includeTime) {
        if (!value) return 'Not set';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'Not set';
        const options = { month: 'short', day: 'numeric', year: 'numeric' };
        if (includeTime) {
            options.hour = 'numeric';
            options.minute = '2-digit';
        }
        return new Intl.DateTimeFormat('en', options).format(date);
    }

    function selectedStatus() {
        if (!statusInput) return 'Draft';
        return statusInput.options[statusInput.selectedIndex]?.text || 'Draft';
    }

    function updatePreview() {
        const weddingName = (nameInput && nameInput.value.trim()) || 'Your Wedding';
        const groom = (groomInput && groomInput.value.trim()) || 'Groom';
        const bride = (brideInput && brideInput.value.trim()) || 'Bride';
        const couple = `${groom} & ${bride}`;
        const status = selectedStatus();

        if (byId('preview-name')) byId('preview-name').textContent = weddingName;
        if (byId('preview-groom')) byId('preview-groom').textContent = groom;
        if (byId('preview-bride')) byId('preview-bride').textContent = bride;
        if (byId('preview-couple')) byId('preview-couple').textContent = couple;
        if (byId('couple-preview-groom')) byId('couple-preview-groom').textContent = groom;
        if (byId('couple-preview-bride')) byId('couple-preview-bride').textContent = bride;
        if (byId('preview-slug')) byId('preview-slug').textContent = (slugInput && slugInput.value) || 'your-wedding';
        if (byId('preview-timezone')) byId('preview-timezone').textContent = (timezoneInput && timezoneInput.value) || 'Asia/Yangon';
        const location = (locationInput && locationInput.value.trim()) || 'Not set';
        const mapUrl = (mapInput && mapInput.value.trim()) || '';
        if (byId('preview-location')) byId('preview-location').textContent = location;
        if (byId('review-location')) byId('review-location').textContent = location;
        const mapRow = byId('preview-map-row');
        const mapLink = byId('preview-map-link');
        const venueMapPreview = byId('venue-map-preview');
        const venueMapLink = byId('venue-map-link');
        if (mapRow) mapRow.hidden = !mapUrl;
        if (venueMapPreview) venueMapPreview.hidden = !mapUrl;
        if (mapLink) mapLink.href = mapUrl || '#';
        if (venueMapLink) venueMapLink.href = mapUrl || '#';
        if (byId('preview-status')) byId('preview-status').textContent = status;
        if (byId('preview-guests') && guestInput) byId('preview-guests').textContent = guestInput.value || '0';
        if (byId('preview-photos') && photoInput) byId('preview-photos').textContent = photoInput.value || '0';
        if (byId('preview-prints') && printInput) byId('preview-prints').textContent = printInput.value || '0';

        if (dateInput && dateInput.value) {
            if (byId('preview-date')) byId('preview-date').textContent = displayDate(dateInput.value, false);
            if (byId('preview-datetime')) byId('preview-datetime').textContent = displayDate(dateInput.value, true);
        } else {
            if (byId('preview-date')) byId('preview-date').textContent = 'Your special day';
            if (byId('preview-datetime')) byId('preview-datetime').textContent = 'Not set yet';
        }

        if (byId('review-name')) byId('review-name').textContent = weddingName;
        if (byId('review-couple')) byId('review-couple').textContent = couple;
        if (byId('review-date')) byId('review-date').textContent = dateInput && dateInput.value ? displayDate(dateInput.value, true) : 'Not set';
        if (byId('review-guests') && guestInput) byId('review-guests').textContent = guestInput.value || '0';
        if (byId('review-photos') && photoInput) byId('review-photos').textContent = photoInput.value || '0';
        if (byId('review-prints') && printInput) byId('review-prints').textContent = printInput.value || '0';
        if (byId('review-status-badge')) {
            byId('review-status-badge').textContent = status;
            byId('review-status-badge').classList.toggle('is-active', status.toLowerCase() === 'active');
        }
    }

    function setStep(step, options) {
        const settings = Object.assign({ validate: false }, options || {});
        if (step < 1 || step > 4) return;
        if (settings.validate && step > currentStep && !validateStep(currentStep)) return;

        currentStep = step;
        panels.forEach((panel) => {
            const active = Number(panel.dataset.stepPanel) === currentStep;
            panel.hidden = !active;
            panel.classList.toggle('active', active);
        });

        stepButtons.forEach((button) => {
            const stepNumber = Number(button.dataset.stepTarget);
            button.classList.toggle('active', stepNumber === currentStep);
            button.classList.toggle('complete', stepNumber < currentStep);
            if (stepNumber === currentStep) button.setAttribute('aria-current', 'step');
            else button.removeAttribute('aria-current');
        });

        if (backButton) backButton.hidden = currentStep === 1;
        if (dashboardButton) dashboardButton.hidden = currentStep !== 1;
        if (nextButton) nextButton.hidden = currentStep === 4;
        if (finishButton) finishButton.hidden = currentStep !== 4;
        if (progressBar) progressBar.style.width = `${currentStep * 25}%`;
        if (progressLabel) progressLabel.textContent = `Step ${currentStep} of 4`;
        if (progressCopy) progressCopy.textContent = progressText[currentStep];

        updatePreview();
        const heading = panels.find((panel) => Number(panel.dataset.stepPanel) === currentStep)?.querySelector('h2');
        if (heading && window.matchMedia('(max-width: 900px)').matches) {
            heading.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function showInvalid(input) {
        const wrap = input.closest('.field-wrap');
        if (wrap) wrap.classList.add('field-invalid');
        input.focus();
    }

    function clearInvalid(input) {
        const wrap = input.closest('.field-wrap');
        if (wrap) wrap.classList.remove('field-invalid');
    }

    function validateStep(step) {
        const panel = panels.find((item) => Number(item.dataset.stepPanel) === step);
        if (!panel) return true;
        const controls = Array.from(panel.querySelectorAll('input, select, textarea'));
        controls.forEach(clearInvalid);

        if (step === 1) {
            for (const input of [nameInput, slugInput].filter(Boolean)) {
                if (!input.value.trim()) {
                    showInvalid(input);
                    return false;
                }
            }
        }

        if (step === 3) {
            if (startInput && dateInput && startInput.value && dateInput.value) {
                const startDate = new Date(`${startInput.value}T00:00`);
                const weddingDate = new Date(dateInput.value);
                if (startDate > weddingDate) {
                    showInvalid(startInput);
                    return false;
                }
            }
            if (dateInput && expireInput && dateInput.value && expireInput.value) {
                if (new Date(expireInput.value) <= new Date(dateInput.value)) {
                    showInvalid(expireInput);
                    return false;
                }
            }
        }

        return true;
    }

    function stepContainingErrors() {
        for (const panel of panels) {
            if (panel.querySelector('.errorlist')) return Number(panel.dataset.stepPanel);
        }
        return null;
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

    [brideInput, groomInput, startInput, dateInput, expireInput, timezoneInput, locationInput, mapInput, statusInput, guestInput, photoInput, printInput]
        .filter(Boolean)
        .forEach((input) => {
            input.addEventListener('input', function () {
                clearInvalid(input);
                updatePreview();
            });
            input.addEventListener('change', updatePreview);
        });

    if (nextButton) nextButton.addEventListener('click', () => setStep(currentStep + 1, { validate: true }));
    if (backButton) backButton.addEventListener('click', () => setStep(currentStep - 1));

    stepButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const target = Number(button.dataset.stepTarget);
            setStep(target, { validate: target > currentStep });
        });
    });

    form.addEventListener('submit', function (event) {
        const submitter = event.submitter;
        if (submitter && submitter.value === 'draft') return;
        for (let step = 1; step <= 4; step += 1) {
            if (!validateStep(step)) {
                event.preventDefault();
                setStep(step);
                return;
            }
        }
    });

    updatePreview();
    const requestedStep = Number(new URLSearchParams(window.location.search).get('step'));
    const initialStep = stepContainingErrors() || ([1, 2, 3, 4].includes(requestedStep) ? requestedStep : 1);
    setStep(initialStep);
})();
