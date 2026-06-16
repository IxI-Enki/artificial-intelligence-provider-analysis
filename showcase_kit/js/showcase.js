(function () {
  'use strict';

  function applyLang(lang) {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = el.getAttribute('data-' + lang);
      if (v !== null) el.innerHTML = v;
    });
    document.querySelectorAll('.lang-switch').forEach(function (s) {
      s.setAttribute('data-lang', lang);
    });
    try { localStorage.setItem('ixi-lang', lang); } catch (e) {}
  }

  var revealObserver = null;

  function observeReveals(root) {
    var scope = root || document;
    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var elements = scope.querySelectorAll('.reveal');
    if (reduced) {
      elements.forEach(function (el) { el.classList.add('in'); });
      return;
    }
    if (!revealObserver) {
      revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) e.target.classList.add('in');
          else e.target.classList.remove('in');
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    }
    elements.forEach(function (el) { revealObserver.observe(el); });
  }

  function initReveal() {
    observeReveals(document);

    var dio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) e.target.classList.add('is-visible');
        else e.target.classList.remove('is-visible');
      });
    }, { threshold: 0.35 });
    document.querySelectorAll('.sec-divider').forEach(function (el) { dio.observe(el); });
  }

  function loadJson(path) {
    return fetch(path, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function showOfflineBanner(show) {
    var el = document.getElementById('offline-banner');
    if (el) el.classList.toggle('is-visible', show);
  }

  function chartColors() {
    var s = getComputedStyle(document.documentElement);
    return {
      primary: s.getPropertyValue('--chart-primary').trim() || 'rgba(46,79,143,0.75)',
      secondary: s.getPropertyValue('--chart-secondary').trim() || 'rgba(114,173,203,0.75)',
      accent: s.getPropertyValue('--chart-accent').trim() || 'rgba(242,141,44,0.75)',
      ink: s.getPropertyValue('--ink').trim() || '#253650',
      muted: s.getPropertyValue('--muted').trim() || '#7a90a8'
    };
  }

  function wrapLabel(str, max) {
    if (!str || str.length <= max) return str;
    var words = str.split(/[\s/]+/);
    var lines = [];
    var line = '';
    words.forEach(function (w) {
      if ((line + w).length > max) {
        lines.push(line.trim());
        line = w + ' ';
      } else {
        line += w + ' ';
      }
    });
    lines.push(line.trim());
    return lines;
  }

  function tooltipTitle(items) {
    var label = items[0].chart.data.labels[items[0].dataIndex];
    return Array.isArray(label) ? label.join(' ') : label;
  }

  function setupAccordions(root) {
    (root || document).querySelectorAll('.accordion-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var panel = btn.nextElementSibling;
        var open = panel.classList.contains('open');
        document.querySelectorAll('.accordion-panel.open').forEach(function (p) {
          p.classList.remove('open');
          p.previousElementSibling.querySelector('.arrow').textContent = '+';
        });
        if (!open) {
          panel.classList.add('open');
          btn.querySelector('.arrow').textContent = '-';
        }
      });
    });
  }

  function formatDate(iso, lang) {
    if (!iso) return '-';
    try {
      return new Date(iso).toLocaleDateString(lang === 'de' ? 'de-AT' : 'en-GB', {
        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } catch (e) {
      return iso;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var lang = 'en';
    try { lang = localStorage.getItem('ixi-lang') || 'en'; } catch (e) {}
    applyLang(lang);
    document.querySelectorAll('.lang-switch .ls-opt').forEach(function (opt) {
      opt.addEventListener('click', function () { applyLang(opt.getAttribute('data-lang')); });
    });
    initReveal();
    setupAccordions();
  });

  window.Showcase = {
    applyLang: applyLang,
    loadJson: loadJson,
    showOfflineBanner: showOfflineBanner,
    chartColors: chartColors,
    wrapLabel: wrapLabel,
    tooltipTitle: tooltipTitle,
    setupAccordions: setupAccordions,
    formatDate: formatDate,
    observeReveals: observeReveals
  };
})();
