(function () {
  'use strict';

  var charts = {};
  var data = null;

  function t(en, de) {
    return (document.documentElement.lang || 'en') === 'de' ? de : en;
  }

  function langKey(base) {
    return (document.documentElement.lang || 'en') === 'de' ? base + '_de' : base + '_en';
  }

  function logoHtml(logo, name, size) {
    if (!logo) return '';
    var cls = 'provider-logo' + (size ? ' provider-logo--' + size : '');
    return '<img class="' + cls + '" src="' + logo + '" alt="' + name + ' logo" loading="lazy" width="36" height="36">';
  }

  function renderMeta(manifest) {
    var el = document.getElementById('data-meta');
    if (!el || !manifest) return;
    var parts = [
      t('Last updated: ', 'Stand: ') + Showcase.formatDate(manifest.generated_at, document.documentElement.lang)
    ];
    if (manifest.stale_warning) {
      parts.push(' · ' + manifest.stale_warning);
    }
    el.textContent = parts.join('');
  }

  function liveFieldMeta(providers, field) {
    var live = null;
    var curated = false;
    providers.forEach(function (p) {
      var src = p.field_sources && p.field_sources[field];
      if (src && src.source === 'openrouter') {
        if (!live || src.fetched_at > live.fetched_at) live = src;
      } else {
        curated = true;
      }
    });
    return { live: live, hasCuratedFallback: curated };
  }

  function renderFreshness(elId, meta, curatedDate) {
    var el = document.getElementById(elId);
    if (!el) return;
    if (meta.live) {
      el.textContent = t(
        'Live from OpenRouter · ' + Showcase.formatDate(meta.live.fetched_at, 'en'),
        'Live von OpenRouter · ' + Showcase.formatDate(meta.live.fetched_at, 'de')
      );
      return;
    }
    var dateStr = curatedDate
      ? Showcase.formatDate(curatedDate, document.documentElement.lang)
      : t('unknown', 'unbekannt');
    el.textContent = t(
      'Curated YAML · verified ' + dateStr,
      'Kuratiertes YAML · verifiziert ' + dateStr
    );
  }

  function renderChartFreshness(providers, data) {
    var verified = data.verified_at;
    renderFreshness('context-freshness', liveFieldMeta(providers, 'context_tokens'), verified);
    renderFreshness('price-freshness', liveFieldMeta(providers, 'api_input_per_million'), verified);
  }

  function renderPrivacyFreshness(data) {
    var el = document.getElementById('privacy-freshness');
    if (!el) return;
    var dateStr = data.verified_at
      ? Showcase.formatDate(data.verified_at, document.documentElement.lang)
      : t('unknown', 'unbekannt');
    el.textContent = t(
      'Curated · verified ' + dateStr,
      'Kuratiert · verifiziert ' + dateStr
    );
  }

  function renderMcpFreshness(data) {
    var el = document.getElementById('mcp-freshness');
    if (!el) return;
    var reviewed = data.mcp_last_reviewed;
    var dateStr = reviewed
      ? Showcase.formatDate(reviewed, document.documentElement.lang)
      : t('unknown', 'unbekannt');
    el.textContent = t(
      'Curated reference · last reviewed ' + dateStr,
      'Kuratierte Referenz · zuletzt geprüft ' + dateStr
    );
  }

  function renderDetailsFreshness(data) {
    var el = document.getElementById('details-freshness');
    if (!el) return;
    var dateStr = data.verified_at
      ? Showcase.formatDate(data.verified_at, document.documentElement.lang)
      : t('unknown', 'unbekannt');
    el.textContent = t(
      'Curated · verified ' + dateStr,
      'Kuratiert · verifiziert ' + dateStr
    );
  }

  function renderCards(providers) {
    var grid = document.getElementById('provider-grid');
    if (!grid) return;
    grid.innerHTML = '';
    providers.forEach(function (p) {
      var card = document.createElement('div');
      card.className = 'card reveal';
      card.innerHTML =
        '<div class="provider-card-head">' +
        logoHtml(p.logo, p.name) +
        '<h3>' + p.name + '</h3>' +
        '</div>' +
        '<p class="mono" style="font-size:.72rem;color:var(--muted);margin:4px 0 8px">' + p.flagship_model + '</p>' +
        '<p style="font-size:.9rem;color:var(--muted)">' + (p[langKey('usp')] || p.usp_en) + '</p>';
      grid.appendChild(card);
    });
    Showcase.observeReveals(grid);
  }

  function renderPrivacy(providers) {
    var tbody = document.querySelector('#privacy-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    providers.forEach(function (p) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><span class="provider-cell">' + logoHtml(p.logo, p.name, 'sm') + '<strong>' + p.name + '</strong></span></td>' +
        '<td>' + p.training_default + '</td>' +
        '<td>' + p.zero_data_retention + '</td>' +
        '<td>' + p.gdpr_focus + '</td>';
      tbody.appendChild(tr);
    });
  }

  function renderMcp(clients) {
    var tbody = document.querySelector('#mcp-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    clients.forEach(function (c) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><strong>' + c.name + '</strong></td>' +
        '<td>' + c.remote_mcp + '</td>' +
        '<td>' + c.oauth21 + '</td>' +
        '<td>' + c.tools + '</td>' +
        '<td style="font-size:.82rem;color:var(--muted)">' + (c[langKey('notes')] || c.notes_en) + '</td>';
      tbody.appendChild(tr);
    });
  }

  function renderAccordions(providers) {
    var root = document.getElementById('accordion-root');
    if (!root) return;
    root.innerHTML = '';
    providers.forEach(function (p) {
      var pros = (p[langKey('pros')] || p.pros_en || []).map(function (x) { return '<li>' + x + '</li>'; }).join('');
      var cons = (p[langKey('cons')] || p.cons_en || []).map(function (x) { return '<li>' + x + '</li>'; }).join('');
      var ft = (p[langKey('fine_tuning')] || p.fine_tuning_en || []).map(function (x) { return '<li>' + x + '</li>'; }).join('');
      var ent = (p[langKey('enterprise')] || p.enterprise_en || []).map(function (x) { return '<li>' + x + '</li>'; }).join('');
      var item = document.createElement('div');
      item.className = 'accordion-item';
      item.innerHTML =
        '<button type="button" class="accordion-btn">' +
        '<span class="accordion-btn-label">' + logoHtml(p.logo, p.name, 'xs') + p.name + '</span>' +
        '<span class="arrow">+</span></button>' +
        '<div class="accordion-panel">' +
        '<p><strong>' + t('Pros', 'Vorteile') + '</strong></p><ul>' + pros + '</ul>' +
        '<p><strong>' + t('Cons', 'Nachteile') + '</strong></p><ul>' + cons + '</ul>' +
        '<p><strong>' + t('Fine-tuning', 'Fine-Tuning') + '</strong></p><ul>' + ft + '</ul>' +
        '<p><strong>' + t('Enterprise', 'Enterprise') + '</strong></p><ul>' + ent + '</ul>' +
        '</div>';
      root.appendChild(item);
    });
    Showcase.setupAccordions(root);
  }

  function renderChangelog(manifest) {
    var el = document.getElementById('changelog-list');
    if (!el || !manifest) return;
    el.innerHTML = '';
    (manifest.changelog || []).slice(0, 5).forEach(function (entry) {
      var li = document.createElement('li');
      li.textContent = Showcase.formatDate(entry.at, document.documentElement.lang) + ' — ' + entry.note;
      el.appendChild(li);
    });
  }

  function renderCharts(providers) {
    var colors = Showcase.chartColors();
    var ctxCanvas = document.getElementById('context-chart');
    var priceCanvas = document.getElementById('price-chart');
    if (!ctxCanvas || !priceCanvas) return;

    if (charts.context) charts.context.destroy();
    if (charts.price) charts.price.destroy();

    var sorted = providers.slice().sort(function (a, b) { return b.context_tokens - a.context_tokens; });

    charts.context = new Chart(ctxCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: sorted.map(function (p) { return Showcase.wrapLabel(p.name, 18); }),
        datasets: [{
          label: t('Context tokens', 'Kontext-Tokens'),
          data: sorted.map(function (p) { return p.context_tokens; }),
          backgroundColor: colors.secondary
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'logarithmic',
            ticks: {
              callback: function (v) {
                if (v >= 1000000) return (v / 1000000) + 'M';
                if (v >= 1000) return (v / 1000) + 'K';
                return v;
              }
            }
          }
        },
        plugins: { legend: { display: false }, tooltip: { callbacks: { title: Showcase.tooltipTitle } } }
      }
    });

    charts.price = new Chart(priceCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: providers.map(function (p) { return Showcase.wrapLabel(p.flagship_model, 16); }),
        datasets: [
          { label: t('Input / 1M tokens (USD)', 'Input / 1M Tokens (USD)'), data: providers.map(function (p) { return p.api_input_per_million; }), backgroundColor: colors.secondary },
          { label: t('Output / 1M tokens (USD)', 'Output / 1M Tokens (USD)'), data: providers.map(function (p) { return p.api_output_per_million; }), backgroundColor: colors.primary }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true } },
        plugins: { tooltip: { callbacks: { title: Showcase.tooltipTitle } } }
      }
    });
  }

  function init() {
    Promise.all([
      Showcase.loadJson('data/providers.json'),
      Showcase.loadJson('data/manifest.json')
    ]).then(function (res) {
      data = res[0];
      renderMeta(res[1]);
      renderCards(data.providers);
      renderPrivacy(data.providers);
      renderMcp(data.mcp_clients);
      renderAccordions(data.providers);
      renderChangelog(res[1]);
      renderChartFreshness(data.providers, data);
      renderPrivacyFreshness(data);
      renderMcpFreshness(data);
      renderDetailsFreshness(data);
      renderCharts(data.providers);
    }).catch(function () {
      Showcase.showOfflineBanner(true);
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
