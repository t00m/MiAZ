/* ===========================================================================
   MiAZYearReport view layer

   The Python side publishes every aggregated number as one JSON payload
   (window.__MIAZ_REPORT__) and this file renders it. Switching years swaps the
   content in place: no reload, no second file, nothing fetched. The selection
   lives in location.hash so the Back button of the embedded browser walks the
   year history and a refresh restores the view.
   ========================================================================== */

(function () {
  'use strict';

  var D = window.__MIAZ_REPORT__ || { years: [], overview: {}, labels: {}, meta: {} };
  var L = D.labels || {};
  var MONTHS = D.months || [];
  var LOCALE = D.meta && D.meta.locale ? D.meta.locale.replace('_', '-') : undefined;

  var view = document.getElementById('view');
  var yearSelect = document.getElementById('year');
  var periodSelect = document.getElementById('period');
  var tip = document.getElementById('tip');
  var current = null;

  /* ── helpers ───────────────────────────────────────────────────────────── */

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function num(value) {
    try { return Number(value).toLocaleString(LOCALE); } catch (e) { return String(value); }
  }

  /* Fill a "{name}" template from the payload's label table. */
  function t(key, values) {
    var text = L[key] || key;
    if (!values) { return text; }
    return text.replace(/\{(\w+)\}/g, function (match, name) {
      return name in values ? String(values[name]) : match;
    });
  }

  /* "Since last 6 months" reads as "documents since last 6 months" once the
     first letter drops to lower case. */
  function lowerFirst(text) {
    return text ? text.charAt(0).toLowerCase() + text.slice(1) : text;
  }

  function pct(value) { return (value >= 0 ? '+' : '−') + Math.abs(Math.round(value)) + '%'; }

  function deltaText(delta) {
    if (!delta) { return ''; }
    var arrow = delta.diff > 0 ? '▲' : (delta.diff < 0 ? '▼' : '▬');
    return arrow + ' ' + pct(delta.pct);
  }

  function bar(value, max, tipText, muted) {
    var width = max > 0 ? Math.max(value / max * 100, 0.6) : 0;
    return '<div class="plot"><div class="bar' + (muted ? ' quiet' : '') + '" style="width:' +
      width.toFixed(2) + '%" data-tip="' + esc(tipText) + '"></div></div>';
  }

  /* Ranked list of {label, count} rows with a bar each. */
  function rankList(rows, options) {
    options = options || {};
    if (!rows.length) { return '<p class="tags empty-note">' + esc(t('none')) + '</p>'; }
    var max = rows[0].count;
    var total = options.total || 0;
    var html = '<div class="rank' + (options.numbered ? ' numbered' : '') + '">';
    rows.forEach(function (row, index) {
      var share = total ? ' <span class="share">' + (row.count / total * 100).toFixed(1) + '%</span>' : '';
      if (options.numbered) { html += '<div class="idx">' + (index + 1) + '</div>'; }
      html += '<div class="name" title="' + esc(row.label) + '">' + esc(row.label) + '</div>';
      html += '<div class="track">' + bar(row.count, max, t('docs_on', { n: num(row.count), name: row.label }), row.muted) +
        '<span class="count">' + num(row.count) + '</span>' + share + '</div>';
    });
    return html + '</div>';
  }

  function dataTable(head, rows) {
    var html = '<details class="data"><summary>' + esc(t('show_table')) + '</summary><table><thead><tr>';
    head.forEach(function (cell) { html += '<th>' + esc(cell) + '</th>'; });
    html += '</tr></thead><tbody>';
    rows.forEach(function (row) {
      html += '<tr>';
      row.forEach(function (cell) { html += '<td>' + esc(cell) + '</td>'; });
      html += '</tr>';
    });
    return html + '</tbody></table></details>';
  }

  /* Long tag lists stop being readable, so the tail is summed up instead. */
  var TAG_CAP = 36;

  function tagList(values) {
    if (!values || !values.length) { return '<p class="tags empty-note">' + esc(t('none')) + '</p>'; }
    var shown = values.slice(0, TAG_CAP);
    var html = '<div class="tags">' + shown.map(function (value) {
      return '<span>' + esc(value) + '</span>';
    }).join('');
    if (values.length > shown.length) {
      html += '<span class="rest">' + esc(t('and_more', { n: values.length - shown.length })) + '</span>';
    }
    return html + '</div>';
  }

  /* ── overview ──────────────────────────────────────────────────────────── */

  function heatClass(value, max) {
    if (!value) { return ''; }
    var ratio = max > 0 ? value / max : 0;
    if (ratio > 0.8) { return ' s5'; }
    if (ratio > 0.6) { return ' s4'; }
    if (ratio > 0.4) { return ' s3'; }
    if (ratio > 0.2) { return ' s2'; }
    return ' s1';
  }

  function renderHeatmap(heat) {
    var head = '<div class="heat-head"><div>' + esc(t('year')) + '</div>';
    MONTHS.forEach(function (name) { head += '<div>' + esc(name.charAt(0)) + '</div>'; });
    head += '<div>' + esc(t('total')) + '</div></div>';

    var body = '<div class="heat">';
    heat.rows.forEach(function (row) {
      body += '<div class="heat-row"><button class="yr" data-year="' + esc(row.year) + '">' + esc(row.year) + '</button>';
      row.months.forEach(function (count, index) {
        var label = MONTHS[index] + ' ' + row.year + ', ' + t('n_documents', { n: num(count) });
        body += '<div class="cell' + heatClass(count, heat.max) + '" data-tip="' + esc(label) +
          '" data-year="' + esc(row.year) + '"></div>';
      });
      body += '<div class="sum">' + num(row.total) + '</div></div>';
    });
    body += '</div>';

    var legend = '<div class="legend"><span>' + esc(t('less')) + '</span>' +
      '<span class="swatch" style="background:var(--cell-empty)"></span>' +
      '<span class="swatch" style="background:var(--seq-1)"></span>' +
      '<span class="swatch" style="background:var(--seq-2)"></span>' +
      '<span class="swatch" style="background:var(--seq-3)"></span>' +
      '<span class="swatch" style="background:var(--seq-4)"></span>' +
      '<span class="swatch" style="background:var(--seq-5)"></span>' +
      '<span>' + esc(t('more')) + '</span></div>';

    var table = dataTable([t('year')].concat(MONTHS).concat([t('total')]),
      heat.rows.map(function (row) {
        return [row.year].concat(row.months.map(num)).concat([num(row.total)]);
      }));

    return '<section><h2>' + esc(t('heatmap')) + '</h2><p class="note">' + esc(t('heatmap_note')) + '</p>' +
      head + body + legend + table + '</section>';
  }

  function renderTrend(trend) {
    if (!trend.length) { return ''; }
    var max = Math.max.apply(null, trend.map(function (row) { return row.total; }));
    var html = '<section><h2>' + esc(t('per_year')) + '</h2><p class="note">' + esc(t('per_year_note')) + '</p><div class="trend">';
    trend.forEach(function (row) {
      html += '<button class="yr" data-year="' + esc(row.year) + '">' + esc(row.year) + '</button>';
      html += '<div class="track">' + bar(row.total, max, t('docs_in', { n: num(row.total), year: row.year })) +
        '<span class="count">' + num(row.total) + '</span>' +
        '<span class="delta">' + esc(deltaText(row.delta)) + '</span></div>';
    });
    html += '</div>' + dataTable([t('year'), t('documents'), t('change')],
      trend.map(function (row) {
        return [row.year, num(row.total), row.delta ? deltaText(row.delta) : '–'];
      })) + '</section>';
    return html;
  }

  function moverChip(mover) {
    if (mover.movement === 'new') { return '<span class="chip new">' + esc(t('mv_new')) + '</span>'; }
    if (mover.movement === 'gone') { return '<span class="chip gone">' + esc(t('mv_gone')) + '</span>'; }
    if (mover.movement === 'up') {
      return '<span class="chip up">' + esc(t('mv_up', { from: mover.previous_rank, to: mover.rank })) + '</span>';
    }
    if (mover.movement === 'down') {
      return '<span class="chip down">' + esc(t('mv_down', { from: mover.previous_rank, to: mover.rank })) + '</span>';
    }
    return '<span class="chip">' + esc(t('mv_same', { rank: mover.rank })) + '</span>';
  }

  function moverList(title, movers) {
    var html = '<div><h3>' + esc(title) + '</h3><ol>';
    movers.forEach(function (mover, index) {
      html += '<li><span class="idx">' + (index + 1) + '</span>' +
        '<span class="name" title="' + esc(mover.label) + '">' + esc(mover.label) + '</span>' +
        '<span class="total">' + num(mover.total) + '</span>' + moverChip(mover) + '</li>';
    });
    return html + '</ol></div>';
  }

  function renderMovers(movers, latest) {
    if (!movers.sender.length && !movers.purpose.length) { return ''; }
    return '<section><h2>' + esc(t('movers')) + '</h2><p class="note">' +
      esc(t('movers_note', { year: latest })) + '</p><div class="movers">' +
      moverList(t('senders'), movers.sender) + moverList(t('purposes'), movers.purpose) +
      '</div></section>';
  }

  function fact(key, value, sub) {
    return '<div class="fact"><div class="k">' + esc(key) + '</div><div class="v">' + esc(value) + '</div>' +
      (sub ? '<div class="s">' + esc(sub) + '</div>' : '') + '</div>';
  }

  function renderFacts(over) {
    var m = over.milestones || {};
    if (!m.first_date) { return ''; }
    var facts = fact(t('first_document'), m.first_date, m.first_label) +
      fact(t('latest_document'), m.last_date, m.last_label) +
      fact(t('busiest_year'), m.busiest_year.year, t('n_documents', { n: num(m.busiest_year.total) })) +
      fact(t('quietest_year'), m.quietest_year.year, t('n_documents', { n: num(m.quietest_year.total) }));
    if (m.streak) {
      facts += fact(t('streak'), t('n_months', { n: m.streak.months }), m.streak.range);
    }
    var html = '<section><h2>' + esc(t('firsts')) + '</h2><div class="facts">' + facts + '</div>';
    if ((over.new_senders && over.new_senders.length) || (over.quiet_senders && over.quiet_senders.length)) {
      html += '<div class="stack" style="margin-top:22px">' +
        '<div><p class="subhead">' + esc(t('appeared_in', { year: m.latest_year })) + '</p>' + tagList(over.new_senders) + '</div>' +
        '<div><p class="subhead">' + esc(t('silent_in', { year: m.latest_year })) + '</p>' + tagList(over.quiet_senders) + '</div>' +
        '</div>';
    }
    return html + '</section>';
  }

  function renderOverview() {
    var over = D.overview;
    if (!over || !over.total) {
      return '<div class="empty">' + esc(t('empty')) + '</div>';
    }
    var d = over.distinct || {};
    var hero = '<section><div class="hero"><span class="figure">' + num(over.total) + '</span>' +
      '<span class="figure-label">' + esc(t('documents_over', { n: over.year_count })) + '</span>' +
      '<span class="span">' + esc(over.span) + '</span></div><div class="tiles">' +
      tile(t('senders'), num(d.sender)) + tile(t('purposes'), num(d.purpose)) +
      tile(t('concepts'), num(d.concept)) + tile(t('groups'), num(d.group)) +
      tile(t('countries'), num(d.country)) + '</div></section>';

    return hero + renderTrend(over.trend || []) + renderHeatmap(over.heatmap) +
      renderMap(over.countries) + renderMovers(over.movers, (over.milestones || {}).latest_year) +
      renderFacts(over);
  }

  function tile(label, value, hint, small) {
    return '<div class="tile"><div class="label">' + esc(label) + '</div>' +
      '<div class="value' + (small ? ' small' : '') + '">' + esc(value) + '</div>' +
      (hint ? '<div class="hint">' + esc(hint) + '</div>' : '') + '</div>';
  }

  /* ── the map ───────────────────────────────────────────────────────────── */

  /* The countries of the current selection, shaded on the same scale as the
     activity heatmap. The outlines are inlined once in a <template>; each view
     clones them and paints the codes it has. */
  function renderMap(countries) {
    if (!countries || !countries.length) { return ''; }
    var list = countries.map(function (row) {
      return { label: row.label, count: row.count };
    });
    return '<section><h2>' + esc(t('map_head')) + '</h2><p class="note">' + esc(t('map_note')) + '</p>' +
      '<div class="mapwrap"><div class="mapbox" data-countries="' +
      esc(JSON.stringify(countries)) + '"></div>' +
      '<div class="maplist">' + rankList(list, { numbered: true }) + '</div></div></section>';
  }

  function paintMaps() {
    var template = document.getElementById('worldmap');
    if (!template || !template.content) { return; }
    var boxes = view.querySelectorAll('.mapbox');
    for (var i = 0; i < boxes.length; i++) {
      var box = boxes[i];
      var countries = [];
      try { countries = JSON.parse(box.dataset.countries || '[]'); } catch (e) { countries = []; }
      box.innerHTML = '';
      box.appendChild(template.content.cloneNode(true));

      var max = countries.length ? countries[0].count : 0;
      countries.forEach(function (row) {
        var shade = heatClass(row.count, max) || ' s1';
        var label = row.label + ', ' + t('n_documents', { n: num(row.count) });
        ['', 'pin-'].forEach(function (prefix) {
          var shape = box.querySelector('[id="' + prefix + row.code + '"]');
          if (!shape) { return; }
          shape.setAttribute('class', (prefix ? 'pin on' : 'here') + shade);
          shape.setAttribute('data-tip', label);
        });
      });
    }
  }

  /* ── one year or one period ────────────────────────────────────────────── */

  function renderTimeline(block) {
    var entries = block.timeline || [];
    var max = entries.reduce(function (best, entry) { return Math.max(best, entry.count); }, 0);
    /* Every column keeps its tick, but a label on each one turns to mush past
       a dozen or so, so they thin out as the window grows. */
    var every = entries.length > 30 ? 6 : (entries.length > 14 ? 2 : 1);
    var columns = '<div class="columns" style="grid-template-columns:repeat(' + entries.length + ',1fr)">';
    var axis = '<div class="month-axis" style="grid-template-columns:repeat(' + entries.length + ',1fr)">';

    entries.forEach(function (entry, index) {
      var height = max > 0 ? Math.max(entry.count / max * 100, entry.count ? 1.5 : 0) : 0;
      var isPeak = entry.count === max && entry.count > 0;
      columns += '<div class="col' + (isPeak ? '' : ' quiet') + '">' +
        '<span class="cap">' + (isPeak ? num(entry.count) : '') + '</span>' +
        '<div class="stem" style="height:' + height.toFixed(2) + '%" data-tip="' +
        esc(entry.full + ', ' + t('n_documents', { n: num(entry.count) })) + '"></div></div>';
      axis += '<div>' + esc(index % every === 0 ? entry.label : '') + '</div>';
    });

    var note = block.unit === 'year' ? 'rhythm_note_year' : 'rhythm_note';
    return '<section><h2>' + esc(t(block.kind === 'period' ? 'rhythm_period' : 'rhythm')) + '</h2>' +
      '<p class="note">' + esc(t(note, {
        avg: block.average, busy: block.busiest_label, active: block.active,
      })) + '</p>' + columns + '</div>' + axis + '</div>' +
      dataTable([t(block.unit === 'year' ? 'year' : 'month'), t('documents')],
        entries.map(function (entry) { return [entry.full, num(entry.count)]; })) + '</section>';
  }

  function renderScope(block) {
    if (!block.total) {
      return '<div class="empty">' + esc(t('nothing_here')) + '</div>';
    }
    var isYear = block.kind === 'year';
    var hero = '<section><div class="hero"><span class="figure">' + num(block.total) + '</span>' +
      '<span class="figure-label">' + esc(isYear ? t('documents_in', { year: block.year })
        : t('documents') + ' ' + lowerFirst(block.title)) + '</span>' +
      '<span class="span">' + esc(isYear ? block.span : block.range) + '</span></div><div class="tiles">' +
      tile(isYear ? t('vs_previous') : t('vs_period'), block.delta ? deltaText(block.delta) : '–',
        isYear ? (block.previous ? t('vs_year', { year: block.previous }) : t('no_prior')) : block.previous, true) +
      tile(t('distinct_senders'), num(block.distinct.sender)) +
      tile(t(block.unit === 'year' ? 'busiest_year' : 'busiest_month'), block.busiest_label || '–', null, true) +
      tile(t('leading_purpose'), block.leading_purpose || '–',
        block.leading_purpose ? t('n_documents', { n: num(block.leading_count) }) : null, true) +
      '</div></section>';

    var duo = '<section><h2>' + esc(t('who_and_what')) + '</h2><p class="note">' + esc(t('top_note')) + '</p>' +
      '<div class="duo"><div><h3 class="subhead">' + esc(t('senders')) + '</h3>' +
      rankList(block.senders, { numbered: true }) + '</div>' +
      '<div><h3 class="subhead">' + esc(t('concepts')) + '</h3>' +
      rankList(block.concepts, { numbered: true }) + '</div></div></section>';

    var purposes = '<section><h2>' + esc(t('purposes_head')) + '</h2><p class="note">' + esc(t('purposes_note')) + '</p>' +
      rankList(block.purposes, { total: block.total }) + '</section>';

    var fresh = isYear ? '<section><h2>' + esc(t('new_this_year')) + '</h2><p class="note">' + esc(t('new_note')) + '</p>' +
      '<div class="stack"><div><p class="subhead">' + esc(t('senders')) + '</p>' + tagList(block.new_senders) + '</div>' +
      '<div><p class="subhead">' + esc(t('purposes')) + '</p>' + tagList(block.new_purposes) + '</div></div></section>' : '';

    return hero + renderTimeline(block) + duo + purposes + renderMap(block.countries) + fresh;
  }

  /* ── selection ─────────────────────────────────────────────────────────── */

  function blockByKey(key) {
    var pools = [D.years || [], D.periods || []];
    for (var p = 0; p < pools.length; p++) {
      for (var i = 0; i < pools[p].length; i++) {
        if (pools[p][i].key === key) { return pools[p][i]; }
      }
    }
    return null;
  }

  function render(key) {
    var block = key === 'all' ? null : blockByKey(key);
    if (!block && key !== 'all') { key = 'all'; }
    current = key;
    view.innerHTML = block ? renderScope(block) : renderOverview();
    paintMaps();
    view.classList.remove('reveal');
    void view.offsetWidth;
    view.classList.add('reveal');

    var isPeriod = block !== null && block.kind === 'period';
    yearSelect.value = isPeriod ? '' : key;
    periodSelect.value = isPeriod ? key : '';

    var scope = document.getElementById('scope');
    if (scope) { scope.textContent = block ? block.title : t('all_years'); }
    document.title = (block ? block.title : t('title_all')) + ' · ' + D.meta.repo;
  }

  function select(key) {
    if (key === current) { return; }
    /* Writing the hash pushes a history entry, so the embedded browser's Back
       button walks the selections the reader visited. */
    window.location.hash = key;
  }

  function keyFromHash() {
    var key = (window.location.hash || '').replace(/^#/, '');
    return key && (key === 'all' || blockByKey(key)) ? key : 'all';
  }

  /* ── selectors, tooltip, theme ─────────────────────────────────────────── */

  function options(placeholder, first, blocks) {
    var html = '<option value="" disabled>' + esc(placeholder) + '</option>';
    if (first) { html += '<option value="' + esc(first.key) + '">' + esc(first.label) + '</option>'; }
    blocks.forEach(function (block) {
      html += '<option value="' + esc(block.key) + '">' + esc(block.title) + '</option>';
    });
    return html;
  }

  function buildSelectors() {
    yearSelect.innerHTML = options(t('no_year'), { key: 'all', label: t('all_years') }, D.years || []);
    periodSelect.innerHTML = options(t('no_period'), null, D.periods || []);
    if (!(D.periods || []).length) { periodSelect.disabled = true; }

    /* Both selectors pick a date range, so only one of them can own the view:
       choosing in one clears the other. */
    yearSelect.addEventListener('change', function () { select(yearSelect.value); });
    periodSelect.addEventListener('change', function () { select(periodSelect.value); });
  }

  function bindTooltip() {
    document.addEventListener('mouseover', function (event) {
      var target = event.target && event.target.closest && event.target.closest('[data-tip]');
      if (!target) { return; }
      tip.textContent = target.dataset.tip;
      tip.classList.add('on');
    });
    document.addEventListener('mousemove', function (event) {
      if (!tip.classList.contains('on')) { return; }
      tip.style.left = event.clientX + 'px';
      tip.style.top = event.clientY + 'px';
    });
    document.addEventListener('mouseout', function (event) {
      if (event.target && event.target.closest && event.target.closest('[data-tip]')) { tip.classList.remove('on'); }
    });
  }

  function storedTheme() {
    try { return window.localStorage.getItem('miaz-year-report-theme'); } catch (e) { return null; }
  }

  function bindTheme() {
    var button = document.getElementById('theme');
    var saved = storedTheme();
    if (saved) { document.documentElement.dataset.theme = saved; }

    function dark() {
      var forced = document.documentElement.dataset.theme;
      if (forced) { return forced === 'dark'; }
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function paint() { button.textContent = dark() ? '☀' : '◑'; }

    button.addEventListener('click', function () {
      var next = dark() ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { window.localStorage.setItem('miaz-year-report-theme', next); } catch (e) { /* file:// */ }
      paint();
    });
    paint();
  }

  function bindPrint() {
    document.getElementById('print').addEventListener('click', function () { window.print(); });
    /* Hover tooltips do not print, so the data tables are opened for the
       printed copy and folded back afterwards. */
    var opened = [];
    window.addEventListener('beforeprint', function () {
      opened = [];
      var tables = document.querySelectorAll('details.data:not([open])');
      for (var i = 0; i < tables.length; i++) { tables[i].open = true; opened.push(tables[i]); }
    });
    window.addEventListener('afterprint', function () {
      opened.forEach(function (item) { item.open = false; });
      opened = [];
    });
  }

  /* Clicking a year in the trend list or a cell in the heatmap jumps there. */
  function bindJumps() {
    view.addEventListener('click', function (event) {
      var target = event.target.closest('[data-year]');
      if (target) { select(target.dataset.year); }
    });
  }

  buildSelectors();
  bindTooltip();
  bindTheme();
  bindPrint();
  bindJumps();
  window.addEventListener('hashchange', function () { render(keyFromHash()); });
  render(keyFromHash());
})();
