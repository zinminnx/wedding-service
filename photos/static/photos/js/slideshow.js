(() => {
  const body = document.body;
  const feedUrl = body.dataset.feedUrl;
  const image = document.querySelector('[data-slide-image]');
  const bg = document.querySelector('[data-slide-bg]');
  const empty = document.querySelector('[data-slide-empty]');
  const caption = document.querySelector('[data-slide-caption]');
  const count = document.querySelector('[data-slide-count]');
  let photos = [];
  let index = -1;
  let timer = null;

  const show = (nextIndex) => {
    if (!photos.length) {
      image.classList.remove('is-visible');
      empty.style.display = '';
      caption.classList.remove('is-visible');
      count.textContent = '0 moments';
      return;
    }
    index = ((nextIndex % photos.length) + photos.length) % photos.length;
    const photo = photos[index];
    image.classList.remove('is-visible');
    window.setTimeout(() => {
      image.src = photo.url;
      image.onload = () => image.classList.add('is-visible');
      bg.style.backgroundImage = `url("${photo.url.replace(/"/g, '\\"')}")`;
      empty.style.display = 'none';
      caption.textContent = photo.caption || '';
      caption.classList.toggle('is-visible', Boolean(photo.caption));
      count.textContent = `${photos.length} moment${photos.length === 1 ? '' : 's'}`;
    }, 250);
  };

  const schedule = () => {
    if (timer) window.clearInterval(timer);
    timer = window.setInterval(() => show(index + 1), 7000);
  };

  const refresh = async () => {
    try {
      const response = await fetch(feedUrl, { cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      const currentId = photos[index]?.id;
      photos = Array.isArray(data.photos) ? data.photos : [];
      let nextIndex = photos.findIndex((item) => item.id === currentId);
      if (nextIndex < 0) nextIndex = 0;
      show(nextIndex);
      schedule();
    } catch (_) {
      // Venue Wi-Fi may briefly drop. Keep the last loaded slide on screen.
    }
  };

  refresh();
  window.setInterval(refresh, 10000);
})();
