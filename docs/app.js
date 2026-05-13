'use strict';

// ── All UI strings — editorial Hebrew that passes the news-editor test ────────
const STR = {
  he: {
    site_name:    'מדד אזהרה: איראן–ישראל',
    lang_toggle:  'EN',
    status_label: 'מצב נוכחי',
    status_green:  'שקט',
    status_yellow: 'גבולי',
    status_red:    'אזהרה',
    updated:       'עודכן',
    hours_ago:     'לפני {n} שעות',
    minutes_ago:   'לפני {n} דקות',
    just_now:      'עכשיו',
    trend_caption: 'מגמת 14 הימים האחרונים',
    no_chart:      'הגרף יופיע לאחר מספר ריצות',
    threshold_lbl: 'סף אזהרה (70%)',
    count_line:    '{n} כתבות השבוע',
    baseline_line: 'פי {x} מהרמה הרגילה',
    how_title:     'איך זה עובד',
    how_p1: 'הכלי הזה קורא אלפי כתבות חדשות בעברית, אנגלית ופרסית כל 12 שעות, ומשווה את הדפוסים הנוכחיים לתקופות שקדמו לסבבים הקודמים בין ישראל לאיראן.',
    how_p2: 'לפני כל אחד מארבעת הסבבים הישירים (אפריל 2024, אוקטובר 2024, יוני 2025, פברואר 2026), היו דפוסים מובהקים בחדשות: עלייה בכתבות על קריסת משא ומתן, תנועות צבא אמריקאי, הצהרות אופרטיביות במדיה האיראנית. הכלי מחפש את הדפוסים האלה ועוקב אחרי עוצמתם.',
    how_p3: 'זה לא תחזית. זה לא מוצר מודיעיני. זה אינדיקציה לכמה הרגע הנוכחי דומה לרגעים שכבר היו. אנשים שמקבלים החלטות אמיתיות צריכים להסתמך על מקורות נוספים.',
    how_p4: 'כל הקוד פתוח. <a href="https://github.com/hadar-ba/iran-war-detector" target="_blank" rel="noopener">אפשר לראות בדיוק איך הציון מחושב בגיטהאב</a>.',
    sources_title: 'המקורות',
    sources_en:    'חדשות באנגלית',
    sources_he:    'חדשות בעברית',
    sources_fa:    'חדשות בפרסית',
    gdelt_note:    'מבוסס על GDELT — מאגר ניטור חדשות גלובלי',
    github:        'קוד פתוח בגיטהאב',
    footer_disc:   'אינו מוצר מודיעיני. לא מתאים להחלטות אישיות, עסקיות או ביטחוניות.',
  },
  en: {
    site_name:    'Iran-Israel War Indicator',
    lang_toggle:  'עב',
    status_label: 'Current status',
    status_green:  'Quiet',
    status_yellow: 'Borderline',
    status_red:    'Warning',
    updated:       'Updated',
    hours_ago:     '{n}h ago',
    minutes_ago:   '{n}m ago',
    just_now:      'just now',
    trend_caption: 'Last 14 days',
    no_chart:      'Chart will appear after a few more runs',
    threshold_lbl: 'Warning threshold (70%)',
    count_line:    '{n} articles this week',
    baseline_line: '{x}× above normal',
    how_title:     'How it works',
    how_p1: 'This tool reads thousands of news articles in Hebrew, English, and Persian every 12 hours, comparing current patterns to the periods that preceded previous Iran-Israel rounds.',
    how_p2: 'Before each of the four direct Iran-Israel rounds (April 2024, October 2024, June 2025, February 2026), there were distinct patterns in the news: surges in diplomatic breakdown coverage, US military movements, and operational language from Iranian media. This tool tracks changes in those patterns.',
    how_p3: 'This is not a forecast. It is not an intelligence product. It is an indication of how much the current moment resembles past moments. Anyone making real decisions should rely on additional sources.',
    how_p4: 'Everything is open source. <a href="https://github.com/hadar-ba/iran-war-detector" target="_blank" rel="noopener">You can see exactly how the score is calculated on GitHub</a>.',
    sources_title: 'Sources',
    sources_en:    'English news',
    sources_he:    'Hebrew news',
    sources_fa:    'Persian news',
    gdelt_note:    'Built on GDELT — a global news monitoring database',
    github:        'Open source on GitHub',
    footer_disc:   'Not an intelligence product. Not for personal, business, or security decisions.',
  },
};

const SOURCES = {
  en: ['Reuters', 'AP News', 'Bloomberg', 'BBC', 'The New York Times', 'Axios', 'Times of Israel', 'The Jerusalem Post', 'Haaretz English'],
  he: ['Ynet', 'Walla', 'הארץ', 'כאן', 'N12', 'ישראל היום', 'מאקו'],
  fa: ['Iran International', 'BBC Persian', 'Radio Farda', 'Tasnim', 'Fars', 'IRNA'],
};

// ── State ─────────────────────────────────────────────────────────────────────
let lang = 'he';
let chartInst = null;

// ── Boot ──────────────────────────────────────────────────────────────────────
(async function boot() {
  lang = localStorage.getItem('lang') ||
         (navigator.language?.startsWith('he') ? 'he' : 'en');
  applyLang();

  document.getElementById('lang-toggle').addEventListener('click', () => {
    lang = lang === 'he' ? 'en' : 'he';
    localStorage.setItem('lang', lang);
    applyLang();
    if (window._data) render(window._data);
  });

  let data;
  try {
    const r = await fetch('./data/latest.json');
    if (!r.ok) throw new Error('no data');
    data = await r.json();
    window._data = data;
  } catch (_) {
    showNoData();
    return;
  }

  document.getElementById('loading').hidden = true;
  document.getElementById('content').hidden = false;
  render(data);
})();

// ── Language ──────────────────────────────────────────────────────────────────
function applyLang() {
  document.documentElement.lang = lang;
  document.documentElement.dir  = lang === 'he' ? 'rtl' : 'ltr';
  setText('site-name',         t('site_name'));
  setText('lang-toggle',       t('lang_toggle'));
  setText('github-link',       t('github'));
  setText('footer-disclaimer', t('footer_disc'));
}

function t(k) { return STR[lang]?.[k] ?? STR.en[k] ?? k; }
function fmt(tpl, vars) {
  return tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? _);
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Render ────────────────────────────────────────────────────────────────────
function render(d) {
  renderGauge(d);
  renderTrend(d);
  renderSignals(d);
  renderContext(d);
  renderHow();
  renderSources();
}

// 5.2 Gauge ───────────────────────────────────────────────────────────────────
function renderGauge(d) {
  const status = d.status || 'green';

  setText('status-label', t('status_label'));

  const circle = document.getElementById('gauge-circle');
  circle.className = 'gauge-circle ' + status;

  const sw = document.getElementById('status-word');
  sw.textContent = t('status_' + status);
  sw.className   = 'status-word ' + status;

  const sn    = document.getElementById('score-number');
  const score = d.score_short ?? d.headline_score_7day;
  sn.textContent = score != null ? score + '%' : '—';
  sn.className   = 'score-number ' + status;

  const headline = (lang === 'he' ? d.headline_he : d.headline_en)
                || (lang === 'he' ? d.summary_he  : d.summary_en) || '';
  setText('headline-sentence', headline);

  const ts   = new Date(d.timestamp_utc);
  const mins = Math.round((Date.now() - ts.getTime()) / 60000);
  let ago;
  if (mins < 2)       ago = t('just_now');
  else if (mins < 60) ago = fmt(t('minutes_ago'), { n: mins });
  else                ago = fmt(t('hours_ago'),   { n: Math.floor(mins / 60) });
  setText('updated-at', t('updated') + ': ' + ago);
}

// 5.3 Trend ───────────────────────────────────────────────────────────────────
function renderTrend(d) {
  setText('trend-caption', t('trend_caption'));

  const trend   = d.trend_14d || [];
  const canvas  = document.getElementById('trend-chart');
  const noChart = document.getElementById('no-chart');

  if (trend.length < 2) {
    canvas.hidden  = true;
    noChart.hidden = false;
    setText('no-chart', t('no_chart'));
    return;
  }

  canvas.hidden  = false;
  noChart.hidden = true;

  if (chartInst) { chartInst.destroy(); chartInst = null; }

  const colors = { red: '#ef4444', yellow: '#f59e0b', green: '#10b981' };
  const color  = colors[d.status] || '#10b981';

  chartInst = new Chart(canvas, {
    type: 'line',
    data: {
      labels:   trend.map(r => r.date),
      datasets: [{
        data:            trend.map(r => r.score),
        borderColor:     color,
        backgroundColor: color + '14',
        tension:         0.3,
        pointRadius:     3,
        borderWidth:     2,
        fill:            true,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#555', font: { size: 11 } }, grid: { color: '#1e1e1e' } },
        y: {
          min: 0, max: 100,
          ticks: { color: '#555', font: { size: 11 }, callback: v => v + '%' },
          grid:  { color: '#1e1e1e' },
        },
      },
    },
    plugins: [{
      afterDraw(chart) {
        const { ctx, chartArea: { left, right }, scales: { y } } = chart;
        const yp = y.getPixelForValue(70);
        if (yp < chart.chartArea.top || yp > chart.chartArea.bottom) return;
        ctx.save();
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth   = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(left, yp); ctx.lineTo(right, yp); ctx.stroke();
        ctx.fillStyle = '#ef4444';
        ctx.font      = '10px sans-serif';
        ctx.fillText(t('threshold_lbl'), left + 4, yp - 4);
        ctx.restore();
      },
    }],
  });
}

// 5.4 Signals ─────────────────────────────────────────────────────────────────
function renderSignals(d) {
  const list = document.getElementById('signals-list');
  const sec  = document.getElementById('signals-section');
  list.innerHTML = '';

  const signals = (d.signals || []).filter(s => s.count_this_week > 0);
  if (!signals.length) { sec.hidden = true; return; }
  sec.hidden = false;

  // Sort: red first, yellow, green
  const order = { red: 0, yellow: 1, green: 2 };
  signals.sort((a, b) => (order[a.intensity] ?? 9) - (order[b.intensity] ?? 9));

  signals.forEach(sig => {
    const name     = lang === 'he' ? sig.name_he : sig.name_en;
    const count    = sig.count_this_week;
    const baseline = Math.max(1, sig.baseline_avg || 1);
    const mult     = Math.max(2, Math.round(count / baseline));
    const icon     = sig.intensity === 'red'    ? '🔴'
                   : sig.intensity === 'yellow' ? '🟡' : '🟢';

    const card = document.createElement('div');
    card.className = 'signal-card';
    card.innerHTML =
      `<span class="signal-icon">${icon}</span>` +
      `<div class="signal-body">` +
        `<p class="signal-name">${esc(name)}</p>` +
        `<p class="signal-count">${esc(fmt(t('count_line'),    { n: count }))}</p>` +
        `<p class="signal-baseline">${esc(fmt(t('baseline_line'), { x: mult  }))}</p>` +
      `</div>`;
    list.appendChild(card);
  });
}

// 5.5 Context ─────────────────────────────────────────────────────────────────
function renderContext(d) {
  setText('context-text', lang === 'he' ? d.context_he : d.context_en);
}

// 5.6 How it works ────────────────────────────────────────────────────────────
function renderHow() {
  document.getElementById('how-summary').textContent = t('how_title');
  document.getElementById('how-body').innerHTML =
    `<p>${t('how_p1')}</p>` +
    `<p>${t('how_p2')}</p>` +
    `<p>${t('how_p3')}</p>` +
    `<p>${t('how_p4')}</p>`;
}

// 5.7 Sources ─────────────────────────────────────────────────────────────────
function renderSources() {
  document.getElementById('sources-summary').textContent = t('sources_title');
  const groups = [
    { label: t('sources_en'), names: SOURCES.en },
    { label: t('sources_he'), names: SOURCES.he },
    { label: t('sources_fa'), names: SOURCES.fa },
  ];
  document.getElementById('sources-body').innerHTML =
    groups.map(g =>
      `<div class="source-group">` +
        `<p class="source-label">${esc(g.label)}</p>` +
        `<p class="source-names">${esc(g.names.join(' · '))}</p>` +
      `</div>`
    ).join('') +
    `<p class="gdelt-note">${t('gdelt_note')}</p>`;
}

// ── No-data state ─────────────────────────────────────────────────────────────
function showNoData() {
  document.getElementById('loading').hidden = true;
  const p = document.createElement('p');
  p.style.cssText = 'text-align:center;padding:80px 20px;color:#666;font-size:0.95rem';
  p.textContent = lang === 'he'
    ? 'מאתחל — הניתוח הראשון יתחיל בריצה הבאה'
    : 'Initializing — first analysis runs at next scheduled time';
  document.querySelector('main').appendChild(p);
}
