/**
 * site.js - Global animations & navigation behavior for njorda.net
 */
(function() {
  function initPage() {
    // 1. Highlight active navigation link with entrance animation on EVERY page
    const rawPath = window.location.pathname;
    let currentPath = rawPath.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
    if (!currentPath || currentPath === '') currentPath = '/';

    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (!href) return;
      if (link.getAttribute('target') === '_blank' || href.startsWith('http')) return;

      let linkPath = href.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
      if (!linkPath || linkPath === '') linkPath = '/';

      const isMatch = (currentPath === '/' && linkPath === '/') ||
                      (currentPath !== '/' && linkPath === currentPath);

      if (isMatch) {
        link.classList.remove('active');
        // Force reflow to re-trigger the CSS appearance animation every time
        void link.offsetWidth;
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // 2. Typewriter effect on subheader tagline (runs every time the page is shown)
    const taglineEl = document.querySelector('.tagline i');
    if (taglineEl) {
      if (!taglineEl.getAttribute('data-full-text')) {
        taglineEl.setAttribute('data-full-text', taglineEl.textContent.trim());
      }
      const fullText = taglineEl.getAttribute('data-full-text');
      if (fullText) {
        if (taglineEl._typeTimeout) {
          clearTimeout(taglineEl._typeTimeout);
        }
        taglineEl.textContent = '';
        taglineEl.classList.add('typing-cursor');

        let charIdx = 0;
        // Snappy typewriter speed: completes in under 1 second
        const speed = Math.max(14, Math.min(26, 950 / fullText.length));

        function typeNext() {
          if (charIdx < fullText.length) {
            taglineEl.textContent += fullText.charAt(charIdx);
            charIdx++;
            taglineEl._typeTimeout = setTimeout(typeNext, speed);
          }
        }
        taglineEl._typeTimeout = setTimeout(typeNext, 80);
      }
    }
  }

  // Run on initial DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPage);
  } else {
    initPage();
  }

  // Run on pageshow (ensures it replays every time on back/forward navigation or refresh)
  window.addEventListener('pageshow', initPage);
})();
