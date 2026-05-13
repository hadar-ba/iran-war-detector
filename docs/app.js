/* Iran-Israel War Indicator — dashboard logic */

let lang = 'he';
let latestData = null;
let historyData = null;
let trendChart = null;

const PERIOD_LABELS_EN = {
  PRE_APR24:   "Pre-April 2024 (Iran's first direct strike on Israel)",
  PRE_OCT24:   "Pre-October 2024 (Iran's missile barrage)",
  PRE_FEB26:   "Pre-February 2026 (Operation Lion's Roar)",
  POST_FEB26:  "Post-February 2026 (post-ceasefire)",
  QUIET_JAN26: "January 2026 (quiet period)",
};
const PERIOD_LABELS_HE = {
  PRE_APR24:   "טרום אפריל 2024 (המתקפה הישירה הראשונה של איראן על ישראל)",
  PRE_OCT24:   "טרום אוקטובר 2024 (מטח הטילים האיראני)",
  PRE_FEB26:   "טרום פברואר 2026 (מבצע 'שאגת הארי')",
  POST_FEB26:  "פוסט פברואר 2026 (אחרי הפסקת האש)",
  QUIET_JAN26: "ינואר 2026 (תקופת שקט)",
};

function t(key) {
  return (I18N[lang] && I18N[lang][key] != null) ? I18N[lang][key] : (I18N['en'][key] || key);
}

function fmt(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? vars[k] : '{' + k + '}'));
}

function periodLabel(id) {
  const map = lang === 'he' ? PERIOD_LABELS_HE : PERIOD_LABELS_EN;
  return map[id] || id;
}

function formatDate(isoStr) {
  const d = new Date(isoStr);
  if (isNaN(d)) return isoStr;
  const opts = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' };
  const locale = lang === 'he' ? 'he-IL' : 'en-US';
  return d.toLocaleString(locale, opts) + ' UTC';
}

function pct(score) {
  if (score == null) return t('na');
  return Math.round(score * 100) + '%';
}

function scoreClass(score) {
  if (score == null) return 'ok-score';
  if (score >= 0.70) return 'warn-score';
  if (score >= 0.50) return 'mid-score';
  return 'ok-score';
}

function signalIcon(intensity) {
  if (intensity === 'high')     return '🔴';
  if (intensity === 'elevated') return '🟡';
  if (intensity === 'baseline') return '🟢';
  return '⚪';
}

// ——— Language toggle ———

function setLang(newLang) {
  lang = newLang;
  localStorage.setItem('lang', lang);
  const html = document.documentElement;
  html.lang = lang;
  html.dir  = lang === 'he' ? 'rtl' : 'ltr';
  if (latestData) render();
  else renderStaticStrings();
}

function initLang() {
  const stored = localStorage.getItem('lang');
  if (stored === 'en' || stored === 'he') { lang = stored; }
  else { lang = navigator.language?.startsWith('he') ? 'he' : 'en'; }
  document.documentElement.lang = lang;
  document.documentElement.dir  = lang === 'he' ? 'rtl' : 'ltr';
}

// ——— Boot ———

async function boot() {
  initLang();
  renderStaticStrings();
  document.getElementById('lang-toggle').addEventListener('click', () => {
    setLang(lang === 'he' ? 'en' : 'he');
  });

  try {
    const [lr, hr] = await Promise.all([
      fetch('./data/latest.json'),
      fetch('./data/history.json').catch(() => null),
    ]);
    if (!lr.ok) throw new Error('no data');
    latestData  = await lr.json();
    historyData = hr && hr.ok ? await hr.json() : null;
  } catch (_) {
    showNoData();
    return;
  }
  render();
}

function renderStaticStrings() {
  document.title = t('site_title');
  setText('site-title',    t('site_title'));
  setText('site-subtitle', t('site_subtitle'));
  setText('lang-toggle',   t('lang_toggle'));
  setText('loading-text',  t('loading'));
  setText('loading-sub',   t('loading_sub'));
}

function showNoData() {
  document.getElementById('loading').hidden = true;
  const el = document.createElement('p');
  el.className = 'loading-text';
  el.style.textAlign = 'center';
  el.style.padding = '60px 16px';
  el.style.color = 'var(--text-muted)';
  el.textContent = t('no_data');
  document.querySelector('main').appendChild(el);
}

// ——— Main render ———

function render() {
  const d = latestData;

  renderStaticStrings();

  // Staleness check
  const ts = new Date(d.timestamp_utc);
  const hoursAgo = (Date.now() - ts.getTime()) / 3_600_000;
  const staleBanner = document.getElementById('stale-banner');
  if (hoursAgo > 24) {
    staleBanner.textContent = fmt(t('stale_warning'), { h: Math.floor(hoursAgo) });
    staleBanner.hidden = false;
  } else {
    staleBanner.hidden = true;
  }

  renderHeadline(d);
  renderContext(d);
  renderSignals(d);
  renderTrend(historyData);
  renderDetails(d);
  renderMethodology();
  renderSources();
  renderFooter(d);

  document.getElementById('loading').hidden       = true;
  document.getElementById('main-content').hidden  = false;
}

// ——— Section A: Headline ———

function renderHeadline(d) {
  const status = d.status || 'green';
  const score7  = d.headline_score_7day;
  const score21 = d.headline_score_21day;

  const section = document.getElementById('section-headline');
  section.setAttribute('data-status', status);

  // Traffic light
  const tl = document.getElementById('traffic-light');
  tl.className = 'traffic-light ' + status;

  // Status label
  setText('status-label', t('status_' + status));

  // Score
  setText('headline-score-7d', score7 != null ? score7 + '%' : t('na'));
  setText('headline-label-7d', t('headline_label_7d'));

  // Score jump badge
  const jump = d.score_jump;
  const badge = document.getElementById('score-jump-badge');
  if (jump != null && Math.abs(jump) >= 20) {
    const up = jump > 0;
    badge.textContent = fmt(t(up ? 'jump_up' : 'jump_down'), { n: Math.abs(jump) });
    badge.className = 'score-jump-badge ' + (up ? 'up' : 'down');
    badge.hidden = false;
  } else {
    badge.hidden = true;
  }

  // 21d score
  setText('headline-score-21d', score21 != null ? score21 + '%' : t('na'));
  setText('headline-label-21d', t('headline_label_21d'));

  // Timestamp
  setText('last-updated-label', t('last_updated'));
  setText('last-updated-value', formatDate(d.timestamp_utc));

  // Summary + closest period
  setText('summary-text', lang === 'he' ? d.summary_he : d.summary_en);
  const labelKey = lang === 'he' ? 'closest_pre_period_label_he' : 'closest_pre_period_label_en';
  const closest = d[labelKey];
  if (closest) {
    setText('closest-period', closest);
  } else {
    document.getElementById('closest-period').hidden = true;
  }
}

// ——— Section B: Context ———

function renderContext(d) {
  setText('context-heading', t('section_context'));
  setText('context-text', lang === 'he' ? d.context_he : d.context_en);

  const noteEl = document.getElementById('partial-note');
  if (d.data_quality_notes && d.data_quality_notes.length) {
    noteEl.textContent = t('partial_note');
    noteEl.hidden = false;
  } else {
    noteEl.hidden = true;
  }
}

// ——— Section C: Signals ———

function renderSignals(d) {
  setText('signals-heading', t('section_signals'));
  const container = document.getElementById('signals-list');
  container.innerHTML = '';

  const signals = d.signals || [];
  if (!signals.length) {
    const p = document.createElement('p');
    p.textContent = t('signals_empty');
    p.className = 'context-text';
    container.appendChild(p);
    return;
  }

  const allBaseline = signals.every(s => s.intensity === 'baseline');
  if (allBaseline) {
    const p = document.createElement('p');
    p.textContent = t('signals_empty');
    p.className = 'context-text';
    container.appendChild(p);
    return;
  }

  signals.forEach(sig => {
    const name = lang === 'he' ? sig.name_he : sig.name_en;
    const desc = lang === 'he' ? sig.description_he : sig.description_en;
    const count = sig.count_current;

    // Build the count + ratio line
    let metaParts = [];
    if (count == null) {
      metaParts.push(t('signal_count_na'));
    } else {
      metaParts.push(fmt(t('signal_count'), { n: count }));
    }
    if (sig.ratio_wow != null) {
      metaParts.push(fmt(t('signal_wow'), { r: sig.ratio_wow }));
    }
    if (sig.ratio_mom != null) {
      metaParts.push(fmt(t('signal_mom'), { r: sig.ratio_mom }));
    }
    const countText = metaParts.join(' · ');

    const card = document.createElement('div');
    card.className = 'signal-card';
    card.innerHTML = `
      <span class="signal-icon">${signalIcon(sig.intensity)}</span>
      <span class="signal-name">${escHtml(name)}</span>
      <span class="signal-desc">${escHtml(desc)}</span>
      <span class="signal-count">${escHtml(countText)}</span>
    `;
    container.appendChild(card);
  });
}

// ——— Section D: Trend ———

function renderTrend(history) {
  setText('trend-heading', t('section_trend'));
  const canvas = document.getElementById('trend-chart');
  const placeholder = document.getElementById('trend-no-history');

  const runs = history?.runs || [];
  if (runs.length < 2) {
    canvas.hidden = true;
    placeholder.textContent = t('trend_no_history');
    placeholder.hidden = false;
    return;
  }
  canvas.hidden = false;
  placeholder.hidden = true;

  const labels = runs.map(r => {
    const d = new Date(r.timestamp_utc);
    return d.toLocaleDateString(lang === 'he' ? 'he-IL' : 'en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  });
  const scores7  = runs.map(r => r.headline_score_7day);
  const scores21 = runs.map(r => r.headline_score_21day);

  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }

  trendChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: t('trend_7d'),
          data: scores7,
          borderColor: '#60a5fa',
          backgroundColor: 'rgba(96,165,250,0.08)',
          tension: 0.3,
          pointRadius: 3,
          borderWidth: 2,
        },
        {
          label: t('trend_21d'),
          data: scores21,
          borderColor: '#a78bfa',
          backgroundColor: 'rgba(167,139,250,0.05)',
          tension: 0.3,
          pointRadius: 3,
          borderWidth: 2,
          borderDash: [4, 4],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#8a8a8a', font: { size: 12 } },
        },
        annotation: {},
      },
      scales: {
        x: {
          ticks: { color: '#8a8a8a', maxRotation: 45, font: { size: 11 } },
          grid:  { color: '#2a2a2a' },
        },
        y: {
          min: 0,
          max: 100,
          ticks: {
            color: '#8a8a8a',
            font: { size: 11 },
            callback: v => v + '%',
          },
          grid: { color: '#2a2a2a' },
        },
      },
    },
    plugins: [{
      afterDraw(chart) {
        const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = chart;
        const drawLine = (val, color, label) => {
          const yPos = y.getPixelForValue(val);
          if (yPos < top || yPos > bottom) return;
          ctx.save();
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.setLineDash([5, 5]);
          ctx.beginPath();
          ctx.moveTo(left, yPos);
          ctx.lineTo(right, yPos);
          ctx.stroke();
          ctx.fillStyle = color;
          ctx.font = '10px ' + (lang === 'he' ? 'Heebo' : 'Inter') + ', sans-serif';
          ctx.fillText(label, left + 4, yPos - 3);
          ctx.restore();
        };
        drawLine(50, '#f59e0b', t('trend_threshold_50'));
        drawLine(70, '#ef4444', t('trend_threshold_70'));
      },
    }],
  });
}

// ——— Section E: Details ———

function renderDetails(d) {
  setText('details-heading', t('section_details'));
  setText('details-hint',    t('section_details_hint'));

  const container = document.getElementById('details-content');
  container.innerHTML = '';

  const renderWindow = (rows, windowKey) => {
    const label = document.createElement('p');
    label.className = 'details-window-label';
    label.textContent = t(windowKey);
    container.appendChild(label);

    const table = document.createElement('div');
    table.className = 'ref-table';

    rows.forEach(row => {
      const score = row.composite_score;
      const subs  = row.sub_scores || {};

      const subParts = [
        ['confluence',           t('details_col_conf')],
        ['cross_lang_correlation', t('details_col_lang')],
        ['raw_volume',           t('details_col_vol')],
        ['source_diversity',     t('details_col_div')],
        ['tone',                 t('details_col_tone')],
      ].map(([key, label]) => {
        const val = subs[key];
        const display = val != null ? pct(val) : t('na');
        return `<span class="sub-score"><strong>${escHtml(label)}</strong> ${escHtml(display)}</span>`;
      }).join('');

      const rowEl = document.createElement('div');
      rowEl.className = 'ref-row' + (row.warn ? ' warn-row' : '');
      rowEl.innerHTML = `
        <div>
          <div class="ref-row-name">${escHtml(periodLabel(row.reference_id))}</div>
          <div class="ref-row-type">${escHtml(row.reference_type || '')}</div>
        </div>
        <div class="ref-row-score ${escHtml(scoreClass(score))}">${pct(score)}</div>
        <div class="ref-row-subs">${subParts}</div>
      `;
      table.appendChild(rowEl);
    });
    container.appendChild(table);
  };

  renderWindow(d.comparison_table_7day  || [], 'details_window_7d');
  renderWindow(d.comparison_table_21day || [], 'details_window_21d');
}

// ——— Section F: Methodology ———

function renderMethodology() {
  setText('methodology-heading', t('section_methodology'));
  const el = document.getElementById('methodology-content');
  el.innerHTML = `
    <h3>${escHtml(t('method_title'))}</h3>
    <p>${escHtml(t('method_body'))}</p>
    <h3>${escHtml(t('method_limits'))}</h3>
    <p>${escHtml(t('method_limits_body'))}</p>
    <div class="disclaimer-box">${escHtml(t('method_disclaimer'))}</div>
  `;
}

// ——— Section G: Sources ———

function renderSources() {
  setText('sources-heading', t('section_sources'));
  const sources = {
    en: ['Reuters', 'AP News', 'BBC', 'Haaretz (English)', 'Jerusalem Post', 'Times of Israel'],
    he: ['ינט', 'הארץ', 'ישראל היום', 'וואלה', 'מאקו'],
    fa: ['Radio Farda', 'Iran International', 'BBC Persian'],
  };
  const el = document.getElementById('sources-content');
  el.innerHTML = `
    <p>${escHtml(t('sources_gdelt'))}</p>
    <p><strong>${escHtml(t('sources_en'))}</strong> ${escHtml(sources.en.join(', '))}</p>
    <p><strong>${escHtml(t('sources_he'))}</strong> ${escHtml(sources.he.join(', '))}</p>
    <p><strong>${escHtml(t('sources_fa'))}</strong> ${escHtml(sources.fa.join(', '))}</p>
  `;
}

// ——— Section H: Footer ———

function renderFooter(d) {
  setText('footer-gdelt',      t('footer_gdelt'));
  setText('footer-repo',       t('footer_repo'));
  setText('footer-disclaimer', t('footer_disclaimer'));
}

// ——— Helpers ———

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ——— Start ———

document.addEventListener('DOMContentLoaded', boot);
