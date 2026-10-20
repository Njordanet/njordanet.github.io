/**
 * site.js - Global animations, theme & navigation behavior for njorda.net
 */
(function() {
  function getActiveTheme() {
    const saved = localStorage.getItem('njorda_theme');
    if (saved) return saved;
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('njorda_theme', theme);
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
      themeBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
      const label = theme === 'dark' ? 'Switch to warm daylight' : 'Switch to cozy midnight';
      themeBtn.setAttribute('title', label);
      themeBtn.setAttribute('aria-label', label);
    }
  }

  function initTheme() {
    const theme = getActiveTheme();
    document.documentElement.setAttribute('data-theme', theme);
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
      themeBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
      const label = theme === 'dark' ? 'Switch to warm daylight' : 'Switch to cozy midnight';
      themeBtn.setAttribute('title', label);
      themeBtn.setAttribute('aria-label', label);

      themeBtn.onclick = function() {
        const current = getActiveTheme();
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      };
    }
  }

  function initPage() {
    initTheme();

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
