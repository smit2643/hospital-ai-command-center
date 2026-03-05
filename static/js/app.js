(function () {
  document.documentElement.classList.add('js');
  function enhanceForms() {
    const controls = document.querySelectorAll('input, select, textarea');
    controls.forEach((el) => {
      if (el.type === 'hidden' || el.type === 'checkbox' || el.type === 'radio') return;
      if (!el.classList.contains('form-control') && !el.classList.contains('form-select')) {
        if (el.tagName === 'SELECT') el.classList.add('form-select');
        else el.classList.add('form-control');
      }
    });
  }

  function initTableFilter() {
    const input = document.querySelector('[data-table-filter]');
    const table = document.querySelector('[data-filter-table]');
    if (!input || !table) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    input.addEventListener('input', function () {
      const q = input.value.toLowerCase().trim();
      rows.forEach((row) => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    });
  }

  function animateNumbers() {
    document.querySelectorAll('[data-counter]').forEach((node) => {
      const target = Number(node.getAttribute('data-counter'));
      if (!Number.isFinite(target)) return;
      let current = 0;
      const step = Math.max(1, Math.round(target / 36));
      const timer = setInterval(() => {
        current += step;
        if (current >= target) {
          current = target;
          clearInterval(timer);
        }
        node.textContent = current;
      }, 20);
    });
  }

  function initFileHint() {
    const file = document.querySelector('input[type="file"]');
    const target = document.querySelector('[data-file-name]');
    if (!file || !target) return;
    file.addEventListener('change', function () {
      target.textContent = file.files && file.files[0] ? file.files[0].name : 'No file selected';
    });
  }

  function initTabs() {
    const buttons = document.querySelectorAll('[data-tab-btn]');
    const panels = document.querySelectorAll('[data-tab-panel]');
    if (!buttons.length || !panels.length) return;

    buttons.forEach((btn) => {
      btn.addEventListener('click', function () {
        const key = btn.getAttribute('data-tab-btn');
        buttons.forEach((b) => b.classList.toggle('is-active', b === btn));
        panels.forEach((panel) => {
          panel.classList.toggle('is-active', panel.getAttribute('data-tab-panel') === key);
        });
      });
    });
  }

  function initBars() {
    document.querySelectorAll('[data-progress]').forEach((el) => {
      const value = Math.max(0, Math.min(100, Number(el.getAttribute('data-progress')) || 0));
      requestAnimationFrame(() => {
        el.style.width = value + '%';
      });
    });
  }

  function initRings() {
    document.querySelectorAll('[data-ring]').forEach((el) => {
      const value = Math.max(0, Math.min(100, Number(el.getAttribute('data-ring')) || 0));
      el.style.setProperty('--ring', value + '%');
    });
  }

  function initTilt() {
    const cards = document.querySelectorAll('[data-tilt]');
    cards.forEach((card) => {
      card.addEventListener('mousemove', (e) => {
        if (window.matchMedia('(max-width: 900px)').matches) return;
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const rotateY = ((x / rect.width) - 0.5) * 6;
        const rotateX = ((0.5 - y / rect.height)) * 5;
        card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
      });
    });
  }

  function initRevealObserver() {
    const items = document.querySelectorAll('.reveal');
    if (!items.length) return;
    if (!('IntersectionObserver' in window)) {
      items.forEach((item) => item.classList.add('in-view'));
      return;
    }
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    items.forEach((item) => obs.observe(item));
  }

  enhanceForms();
  initTableFilter();
  animateNumbers();
  initFileHint();
  initTabs();
  initBars();
  initRings();
  initTilt();
  initRevealObserver();
})();
