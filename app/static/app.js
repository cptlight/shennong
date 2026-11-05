/* =====================================================================================
   SHENNONG Workbench — vanilla ES2020, no framework, no build step, no network.
   Every panel fetches its own data and states whether that data is real or a DEMO FIXTURE.
   ===================================================================================== */
'use strict';

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const CJK = /[\u3400-\u9fff\uf900-\ufaff]/;
const langAttr = (s) => (CJK.test(String(s || '')) ? ' lang="zh-Hant"' : '');

const fmt = (n) => (typeof n === 'number' && isFinite(n) ? n.toLocaleString('en-US') : '—');
const pct = (x) => `${Math.round((x || 0) * 100)}%`;

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json();
}

/* ---------------------------------------------------------------- data badges */
function badge(el, fixture, label, source) {
  if (!el) return;
  el.innerHTML = `<span class="pill ${fixture ? 'pill-fixture' : 'pill-live'}"
      title="source: ${esc(source || '')}">${fixture ? 'DEMO FIXTURE' : 'LIVE DATA'}${label ? ' · ' + esc(label) : ''}</span>`;
}

/* ---------------------------------------------------------------- tabs */
const TABS = ['candidates', 'hypotheses', 'graph', 'ask', 'corpus', 'method'];

function selectTab(name, focus = false) {
  TABS.forEach((t) => {
    const btn = $(`#tab-${t}`);
    const panel = $(`#panel-${t}`);
    const on = t === name;
    btn.setAttribute('aria-selected', String(on));
    btn.tabIndex = on ? 0 : -1;
    panel.hidden = !on;
    panel.classList.toggle('is-active', on);
    if (on && focus) btn.focus();
  });
  if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name);
  if (name === 'graph') drawGraph();
}

function initTabs() {
  $$('.tabs [role="tab"]').forEach((btn) => {
    btn.addEventListener('click', () => selectTab(btn.dataset.panel));
    btn.addEventListener('keydown', (e) => {
      const i = TABS.indexOf(btn.dataset.panel);
      let j = null;
      if (e.key === 'ArrowRight') j = (i + 1) % TABS.length;
      if (e.key === 'ArrowLeft') j = (i - 1 + TABS.length) % TABS.length;
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = TABS.length - 1;
      if (j !== null) { e.preventDefault(); selectTab(TABS[j], true); }
    });
  });
  const initial = (location.hash || '').replace('#', '');
  selectTab(TABS.includes(initial) ? initial : 'hypotheses');
}

/* ================================================================= state */
const STATE = {
  meta: null,
  hyps: null,
  kg: null,
  filtered: [],
  nodeFilter: null,
  hypByNode: new Map(),
  graphDrawn: false,
  selectedNode: null,
  edgeIndex: new Map(),
};

/* ================================================================= meta / status */
async function loadMeta() {
  const m = await api('/api/meta');
  STATE.meta = m;
  if (m.tagline) $('#tagline').textContent = m.tagline;

  const pills = $('#status-pills');
  pills.innerHTML =
    `<span class="pill ${m.fixture_count ? 'pill-fixture' : 'pill-live'}">${m.live_count}/${m.status.length} live</span>` +
    `<span class="pill pill-quiet" title="Ask backend in use">${esc(m.rag_backend)}</span>`;

  const broken = m.status.filter((s) => s.fixture);
  $('#foot-source').textContent = broken.length
    ? `${broken.length}/${m.status.length} panels on demo fixture`
    : `all ${m.status.length} panels on real artefacts`;

  // tell the user once, in plain language, if the demo is on fixtures
  if (m.any_fixture) {
    const banner = document.createElement('div');
    banner.className = 'banner';
    banner.style.margin = '0 0 .2rem';
    banner.setAttribute('role', 'note');
    banner.innerHTML = `<strong>This instance is showing DEMO FIXTURE data for ` +
      `${broken.length} of ${m.status.length} panels.</strong> Fixtures exist so the interface could be built ` +
      `before the pipeline landed; they are not results. Run <code>make app-data</code> (and ` +
      `<code>make eval</code>) then reload to see measured output.`;
    $('#main').prepend(banner);
  }
}


/* ================================================================= CANDIDATES */
function theoryChips(t) {
  const out = [];
  if (t.nature) out.push(`<span class="tv-nature">${esc(t.nature)}</span>`);
  (t.flavors || []).forEach((f) => out.push(`<span class="tv-flavor">${esc(f)}</span>`));
  if ((t.channels || []).length) out.push(`<span class="tv-channel">歸${esc(t.channels.join('·'))}</span>`);
  if (t.direction) out.push(`<span>${esc(t.direction)}</span>`);
  if (t.grade) out.push(`<span class="tv-grade">${esc(t.grade)}</span>`);
  if (t.rasa) out.push(`<span class="tv-flavor">rasa ${esc(t.rasa)}</span>`);
  if (t.virya) out.push(`<span class="tv-flavor">vīrya ${esc(t.virya)}</span>`);
  return out.length ? `<div class="tv">${out.join('')}</div>` : '<span class="muted">—</span>';
}

function candCard(c) {
  const sev = (c.safety && c.safety.severity) || 'none';
  const lead = c.classical_lead || {};
  const mech = c.mechanism || {};
  const d = c.development_path || [];
  const risk = c.residual_risk || [];
  const smi = c.smiles;
  const cl = c.classical_line || {};
  const dl = c.druglikeness || {};
  const ro5 = dl.rule_of_five || {};
  const ruleRow = (k, label, threshold, unit) => {
    const r = ro5[k] || {};
    const v = r.value;
    const pass = r.pass_;
    return `<tr><td>${esc(label)}</td>
      <td class="num">${v === null || v === undefined ? '—' : Number(v).toFixed(2)}</td>
      <td class="num am">${esc(threshold)}${unit || ''}</td>
      <td>${pass === true ? '<span class="badge badge-sev-none">pass</span>'
            : pass === false ? '<span class="badge badge-sev-high">fail</span>'
            : '<span class="badge">pending structure</span>'}</td></tr>`;
  };
  const extraRows = [
    ['TPSA', dl.tpsa, 140, ' Å²'], ['rings', dl.rings, null, ''],
    ['rotatable bonds', dl.rotatable, 10, ''],
  ].filter(([, v]) => v !== null && v !== undefined).map(([label, v, th, u]) => `
    <tr><td>${esc(label)}</td><td class="num">${Number(v).toFixed(2)}</td>
      <td class="num am">${th === null ? '' : esc(th) + esc(u)}</td>
      <td>${th === null ? '' : (v <= th ? '<span class="badge badge-sev-none">within Veber</span>'
                                  : '<span class="badge badge-sev-caution">above Veber</span>')}</td></tr>`).join('');
  const overall = dl.overall;
  const evaluated = dl.evaluated ?? 0;
  return `<details class="cand" data-id="${esc(c.id)}" data-status="${esc(c.status)}">
    <summary>
      <span class="c-rank" data-k="rank">${c.rank}</span>
      <span class="c-name" data-k="candidate"${langAttr(c.name_cn)}>${esc(c.name)}
        ${c.name_cn ? `<em>${esc(c.name_cn)}</em>` : ''}</span>
      <span class="c-lead" data-k="classical lead"${langAttr(lead.drug)}>
        <b>${esc(lead.drug || '—')}</b>
        <span>${esc(lead.drug_en || '')}</span>
        <span>${esc(lead.formula_role || '')}</span></span>
      <span data-k="theory vector">${theoryChips(c.theory)}</span>
      <span class="c-mech" data-k="mechanism">${esc(mech.target_class || '—')}</span>
      <span class="c-mw" data-k="MW / formula">${c.mw ? c.mw.toFixed(1) : '—'}<small>${esc(c.formula || '—')}</small></span>
      <span class="c-nov" data-k="novelty">
        <span class="bar bar-novelty" role="img" aria-label="novelty ${c.novelty.score.toFixed(2)}">
          <i style="width:${Math.max(2, Math.round(c.novelty.score * 100))}%"></i></span>
        <b>${c.novelty.score.toFixed(2)}</b></span>
      <span data-k="status"><span class="badge badge-sev-${esc(sev)}">${esc(c.status)}</span></span>
    </summary>
    <div class="cand-body">
      ${cl && cl.text ? `<figure class="classical ${cl.integrity === 'unmatched' ? 'classical-bad' : ''}">
        ${cl.integrity === 'unmatched'
          ? `<div class="prov-warn"><strong>Provenance check failed.</strong> ${esc(cl.integrity_note)}
               The span below is <em>not</em> evidence for this candidate and must not be cited as such.</div>`
          : ''}
        <blockquote lang="zh-Hant">${esc(cl.text)}</blockquote>
        <figcaption>
          <span class="cl-src">${esc(cl.source || '')}${cl.locator ? ' · ' + esc(cl.locator) : ''}</span>
          ${cl.year ? `<span class="badge">${esc(cl.year)} CE</span>` : ''}
          ${cl.span_kind ? `<span class="badge">${esc(cl.span_kind)}</span>` : ''}
          <span class="badge ${cl.integrity === 'ok' ? 'badge-sev-none' : cl.integrity === 'unmatched' ? 'badge-sev-high' : ''}">
            provenance: ${esc(cl.integrity || 'unknown')}</span>
          ${cl.translation ? `<p class="cl-tr">${esc(cl.translation)}</p>` : ''}
        </figcaption>
      </figure>` : ''}
      <div class="split">
        <div class="block"><h4>Why the theory predicts this</h4>
          <p style="margin:0">${esc(c.theory_justification || '—')}</p></div>
        <div class="block"><h4>Proposed mechanism</h4>
          <p style="margin:0 0 .35rem"><strong>${esc(mech.target_class || '—')}</strong></p>
          <p class="muted" style="margin:0;font-size:.82rem">${esc(mech.pathway || '')}</p>
          ${mech.evidence_level ? `<p style="margin:.4rem 0 0"><span class="badge">evidence: ${esc(mech.evidence_level)}</span></p>` : ''}
        </div>
      </div>
      <div class="block"><h4>Molecule &amp; computed drug-likeness</h4>
        ${smi
          ? `<div class="smiles">${esc(smi)}</div>`
          : `<div class="smiles none">${esc(c.structure_note || 'structure not resolved — left null rather than invented')}</div>`}
        <p class="muted" style="margin:.4rem 0 .5rem;font-size:.76rem">
          <span class="badge">${esc(c.structure_status)}</span>
          ${c.formula ? `<span class="badge">${esc(c.formula)}</span>` : ''}
          ${c.mw ? `<span class="badge">MW ${c.mw.toFixed(2)} — computed from formula</span>` : ''}
        </p>
        <p class="muted" style="margin:.1rem 0 .45rem;font-size:.78rem">
          <span class="badge ${evaluated === 4 ? (overall === false ? 'badge-sev-high' : 'badge-sev-none') : 'badge-sev-caution'}">
            ${evaluated} of 4 Lipinski rules evaluated</span>
          ${overall === true ? '<span class="badge badge-sev-none">passes rule of five</span>' : ''}
          ${overall === false ? `<span class="badge badge-sev-high">fails ${esc(dl.violations ?? '')} rule(s)</span>` : ''}
          ${dl.veber === true ? '<span class="badge badge-sev-none">Veber pass</span>' : ''}
          ${dl.sa_score !== null && dl.sa_score !== undefined ? `<span class="badge">SA heuristic ${esc(dl.sa_score)}</span>` : ''}
        </p>
        <div class="wrap-scroll"><table class="data">
          <thead><tr><th>Lipinski rule of five</th><th class="num">value</th><th class="num">threshold</th><th>verdict</th></tr></thead>
          <tbody>
            ${ruleRow('mw', 'molecular weight', 500, ' Da')}
            ${ruleRow('logp', 'logP', 5, '')}
            ${ruleRow('hbd', 'H-bond donors', 5, '')}
            ${ruleRow('hba', 'H-bond acceptors', 10, '')}
            ${extraRows}
          </tbody></table></div>
        <p class="muted" style="font-size:.74rem;margin:.4rem 0 0">${esc(dl.note || '')}</p></div>
      <div class="split">
        <div class="block"><h4>Development path</h4>
          ${d.length ? `<ol class="steps">${d.map((x) => `<li>${esc(typeof x === 'string' ? x : x.step)}
            ${x && x.kind ? `<span class="badge">${esc(x.kind)}</span>` : ''}</li>`).join('')}</ol>`
            : '<p class="muted">none recorded</p>'}</div>
        <div class="block"><h4>Residual risk</h4>
          ${risk.length ? `<ul class="bullets">${risk.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`
            : '<p class="muted">none recorded</p>'}</div>
      </div>
      ${Array.isArray(c.safety.flags) && c.safety.flags.length
        ? `<div class="block block-safety"><h4>Safety annotations (severity: ${esc(sev)})</h4>
             <ul>${c.safety.flags.map((f) => `<li>${esc(f)}</li>`).join('')}</ul></div>` : ''}
      ${c.falsification_plan ? `<div class="block block-falsify"><h4>Falsification plan — the assay that would kill it</h4>
        <p style="margin:0">${esc(c.falsification_plan)}</p></div>` : ''}
      ${c.uncertainty ? `<div class="block block-uncertainty"><h4>Uncertainty</h4>
        <p style="margin:0">${esc(c.uncertainty)}</p></div>` : ''}
      ${(c.provenance && c.provenance.length) ? `<div class="block"><h4>Evidence spans</h4>
        ${provenanceHTML(c.provenance)}</div>` : ''}
      <div class="block"><h4>Novelty claim</h4>
        <p style="margin:0">${esc(c.novelty.basis || '—')}</p>
        ${c.novelty.prior_art ? `<p class="muted" style="margin:.3rem 0 0;font-size:.78rem">prior art: ${esc(c.novelty.prior_art)}</p>` : ''}
      </div>
    </div>
  </details>`;
}

function applyCandFilters() {
  if (!STATE.cands) return;
  const sortBy = $('#cand-sort').value;
  const status = $('#cand-status').value;
  const q = $('#cand-search').value.trim().toLowerCase();
  const list = [...STATE.cands.candidates].sort((a, b) => {
    if (sortBy === 'mw') return (b.mw || 0) - (a.mw || 0);
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    if (sortBy === 'rank') return a.rank - b.rank;
    return b.novelty.score - a.novelty.score;
  });
  const shown = list.filter((c) => {
    if (status && c.status !== status) return false;
    if (!q) return true;
    const lead = c.classical_lead || {};
    const hay = [c.name, c.name_cn, c.formula, c.theory_justification, (c.mechanism || {}).target_class,
                 lead.drug, lead.drug_en, lead.formula_role, (c.theory.flavors || []).join('')].join(' ').toLowerCase();
    return hay.includes(q);
  });
  const warn = (STATE.cands.counts && STATE.cands.counts.unmatched_lines)
    ? `<div class="banner banner-warn" role="note">
         <strong>${STATE.cands.counts.unmatched_lines} of ${STATE.cands.counts.total} candidates fail the
         provenance check.</strong>
         The classical line attached to each of those candidates does not contain the drug name it is attributed
         to, so it is shown as <em>unverified</em> rather than as evidence. This is an extraction bug in the
         span locator, surfaced on purpose: an attribution you cannot check is worse than no attribution.
       </div>` : '';
  $('#cand-list').innerHTML = warn + (shown.length ? shown.map(candCard).join('')
    : `<div class="empty"><strong>No candidate matches.</strong> Widen the search or clear the status filter.</div>`);
}

async function loadCandidates() {
  const d = await api('/api/candidates');
  STATE.cands = d;
  badge($('#cand-badge'), d.fixture, d.source, d.source);
  const c = d.counts || {};
  $('#cand-summary').innerHTML = `<div class="stat-grid">
    <div class="stat"><div class="stat-v">${fmt(c.total)}</div><div class="stat-k">candidates</div>
      <div class="stat-sub">lead → molecule → development path</div></div>
    <div class="stat"><div class="stat-v">${fmt(c.resolved)}</div><div class="stat-k">structures resolved</div>
      <div class="stat-sub">null where unresolved, never invented</div></div>
    <div class="stat"><div class="stat-v">${(c.mean_novelty ?? 0).toFixed(2)}</div><div class="stat-k">mean novelty</div>
      <div class="stat-sub">vs modern literature</div></div>
    <div class="stat" style="border-top-color:${(c.unmatched_lines || 0) ? 'var(--cinnabar)' : 'var(--verdigris)'}">
      <div class="stat-v" style="color:${(c.unmatched_lines || 0) ? 'var(--cinnabar-d)' : 'inherit'}">${fmt(c.unmatched_lines || 0)}</div>
      <div class="stat-k">provenance failures</div>
      <div class="stat-sub">quoted lines that do not name their drug</div></div>
    <div class="stat"><div class="stat-v">${Object.keys(c.by_status || {}).length}</div><div class="stat-k">status classes</div>
      <div class="stat-sub">${esc(Object.entries(c.by_status || {}).map(([k, v]) => `${k} ${v}`).join(' · '))}</div></div>
  </div>`;
  const sel = $('#cand-status');
  sel.innerHTML = '<option value="">all</option>' + Object.entries(c.by_status || {})
    .map(([k, n]) => `<option value="${esc(k)}">${esc(k)} (${n})</option>`).join('');
  applyCandFilters();
}

function initCandidateControls() {
  ['cand-sort', 'cand-status', 'cand-search'].forEach((id) =>
    $('#' + id).addEventListener('input', applyCandFilters));
}

/* ================================================================= HYPOTHESES */
const CLASS_TONE = {
  paozhi: 'badge-class',
  yiming_tongwu: 'badge-class',
  junchen_zuoshi: 'badge-class',
  peiwu_jinji: 'badge-class',
  weiyanjiu: 'badge-class',
  binwei_daiyong: 'badge-class',
  control: 'badge-ctrl',
};

function chainHTML(chain) {
  const cells = [
    ['plant', 'plant / drug', chain.plant],
    ['preparation', 'preparation', chain.preparation],
    ['chemotype', 'chemotype', chain.chemotype],
    ['target', 'target', chain.target],
    ['indication', 'indication', chain.indication],
  ];
  return `<div class="chain">${cells.map(([k, label, v]) => `
    <div class="chain-cell is-${k}">
      <span class="chain-k">${label}</span>
      <div class="chain-v"${langAttr(v)}>${esc(v || '—')}</div>
    </div>`).join('')}</div>`;
}

function scoreBars(s) {
  const keys = [['novelty', 'novelty'], ['plausibility', 'plausibility'],
                ['testability', 'testability'], ['evidence', 'evidence']];
  return `<div class="scores">${keys.map(([k, label]) => `
    <div class="score">
      <div class="score-top"><span class="score-k">${label}</span><span class="score-v">${(s[k] ?? 0).toFixed(2)}</span></div>
      <div class="bar bar-${k}" role="img" aria-label="${label} ${(s[k] ?? 0).toFixed(2)} of 1">
        <i style="width:${Math.max(2, Math.round((s[k] ?? 0) * 100))}%"></i>
      </div>
    </div>`).join('')}</div>`;
}

function provenanceHTML(prov) {
  if (!prov || !prov.length) return `<p class="muted">No provenance spans attached.</p>`;
  return `<ul class="prov">${prov.map((p) => {
    const bits = [];
    bits.push(`<span class="badge">tier ${esc(p.tier ?? '?')}</span>`);
    if (p.licence) {
      const l = String(p.licence);
      const cls = /UNVERIFIED/i.test(l) ? 'lic-unv' : /CC/i.test(l) ? 'lic-cc' : 'lic-pd';
      bits.push(`<span class="lic ${cls}">${esc(l)}</span>`);
    }
    if (p.span_kind) bits.push(`<span class="badge">${esc(p.span_kind)}</span>`);
    if (p.tradition) bits.push(`<span class="badge">${esc(p.tradition)}</span>`);
    return `<li>
      <div class="prov-top">
        <span class="prov-title"${langAttr(p.title)}>${esc(p.title || p.source_id)}</span>
        <span class="am">${esc(p.author || '')}${p.year ? ' · ' + esc(p.year) : ''}</span>
        ${p.locator ? `<span class="prov-loc">${esc(p.locator)}</span>` : ''}
      </div>
      <div class="prov-span"${langAttr(p.span)}>${esc(p.span || '')}</div>
      <div class="prov-top">${bits.join('')}</div>
    </li>`;
  }).join('')}</ul>`;
}

function blocksHTML(h) {
  const d = h.dossier || {};
  const sev = (h.safety && h.safety.severity) || 'none';
  const out = [];

  out.push(`<div class="block block-falsify"><h4>Falsification plan — the experiment that could kill it</h4>
    <p style="margin:0">${esc(h.falsification_plan || 'No falsification plan attached — treat this as an incomplete hypothesis.')}</p></div>`);

  out.push(`<div class="block block-uncertainty"><h4>Uncertainty — what we are least sure about</h4>
    <p style="margin:0">${esc(h.uncertainty || 'No uncertainty note attached.')}</p></div>`);

  if (Array.isArray(h.safety && h.safety.flags) && h.safety.flags.length) {
    out.push(`<div class="block block-safety"><h4>Safety annotations (severity: ${esc(sev)})</h4>
      <ul>${h.safety.flags.map((f) => `<li>${esc(f)}</li>`).join('')}</ul></div>`);
  }

  if (d.rationale) {
    out.push(`<div class="block"><h4>Why this is a hypothesis and not a coincidence</h4>
      <p style="margin:0">${esc(d.rationale)}</p></div>`);
  }
  if (Array.isArray(d.mechanistic_chain) && d.mechanistic_chain.length) {
    out.push(`<div class="block"><h4>Mechanistic chain</h4>
      <ol class="steps">${d.mechanistic_chain.map((s) => `<li>${esc(s)}</li>`).join('')}</ol></div>`);
  }

  out.push(`<div class="block"><h4>Provenance — every span, source, licence</h4>${provenanceHTML(h.provenance)}</div>`);

  const prior = Array.isArray(d.prior_art_refs) ? d.prior_art_refs : [];
  if (prior.length || d.cost_estimate || (Array.isArray(d.next_steps) && d.next_steps.length)) {
    out.push(`<div class="split">
      <div class="block"><h4>Position in the literature</h4>
        ${prior.length ? `<ul class="bullets">${prior.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>` : '<p class="muted">none recorded</p>'}
        ${d.cost_estimate ? `<p style="margin:.5rem 0 0"><strong>Cost to test:</strong> ${esc(d.cost_estimate)}</p>` : ''}
      </div>
      <div class="block"><h4>Next steps</h4>
        ${Array.isArray(d.next_steps) && d.next_steps.length
          ? `<ul class="bullets">${d.next_steps.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>`
          : '<p class="muted">none recorded</p>'}
      </div></div>`);
  }
  return out.join('');
}

function hypCard(h) {
  const sev = (h.safety && h.safety.severity) || 'none';
  const sevLabel = sev === 'high' ? 'HIGH SAFETY SIGNAL' : sev === 'caution' ? 'CAUTION' : 'no flag';
  const classBadge = `<span class="badge ${CLASS_TONE[h.discovery_class] || 'badge-class'}">${esc(h.discovery_class_label)}</span>`;
  return `<article class="hyp ${h.is_control ? 'hyp-control is-control' : ''}" id="hyp-${esc(h.id)}"
      data-id="${esc(h.id)}" data-class="${esc(h.discovery_class)}">
    <div class="hyp-head">
      <div class="rank" aria-hidden="true">${h.rank}</div>
      <div class="hyp-title">
        <h3>${esc(h.title)}</h3>
        <div class="hyp-meta">
          ${classBadge}
          <span class="badge badge-sev-${esc(sev)}">${sevLabel}</span>
          ${h.is_control ? '<span class="badge badge-ctrl">NEGATIVE CONTROL</span>' : ''}
          <span class="badge">${esc(h.id)}</span>
        </div>
      </div>
    </div>
    ${chainHTML(h.chain)}
    <div class="hyp-body">
      ${scoreBars(h.scores)}
      <div class="composite">
        <div class="composite-k">composite</div>
        <div class="composite-v">${(h.scores.composite ?? 0).toFixed(3)}</div>
        <div class="composite-spark">rank ${h.rank}</div>
      </div>
    </div>
    <details class="dossier">
      <summary>Full dossier — falsification plan, provenance, safety, uncertainty</summary>
      <div class="dossier-body">${blocksHTML(h)}</div>
    </details>
  </article>`;
}

function applyHypFilters() {
  const rankBy = $('#rank-by').value;
  const classFilter = $('#class-filter').value;
  const q = $('#hyp-search').value.trim().toLowerCase();
  const nodeIds = STATE.nodeFilter ? new Set(STATE.nodeFilter) : null;

  const list = [...STATE.hyps.hypotheses].sort((a, b) => {
    if (rankBy === 'composite') return (b.scores.composite - a.scores.composite);
    return (b.scores[rankBy] ?? 0) - (a.scores[rankBy] ?? 0);
  });

  const shown = list.filter((h) => {
    if (classFilter && h.discovery_class !== classFilter && !(classFilter === 'control' && h.is_control)) return false;
    if (nodeIds && !nodeIds.has(h.id)) return false;
    if (q) {
      const hay = [h.title, h.id, h.discovery_class_label, ...Object.values(h.chain)].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  STATE.filtered = shown;
  const wrap = $('#hyp-list');
  if (!shown.length) {
    wrap.innerHTML = `<div class="empty"><strong>No hypothesis matches those filters.</strong>
      Widen the search, or clear the graph node filter.</div>`;
    return;
  }
  // Keep the visual order consistent with the chosen sort, but show the stored rank as a badge.
  wrap.innerHTML = shown.map(hypCard).join('');

  const note = $('#rank-by');
  note.title = `Sorted by ${rankBy}; each card shows the composite rank from the 使 Shǐ stage.`;
}

function initHypothesisControls() {
  $('#rank-by').addEventListener('change', applyHypFilters);
  $('#class-filter').addEventListener('change', applyHypFilters);
  let t = null;
  $('#hyp-search').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(applyHypFilters, 120);
  });
  $('#clear-filters').addEventListener('click', () => {
    $('#hyp-search').value = '';
    $('#rank-by').value = 'composite';
    $('#class-filter').value = '';
    clearNodeFilter();
    applyHypFilters();
  });
  $('#node-filter-clear').addEventListener('click', () => { clearNodeFilter(); applyHypFilters(); });
}

function clearNodeFilter() {
  STATE.nodeFilter = null;
  $('#active-node-filter').hidden = true;
}

function setNodeFilter(label, ids) {
  STATE.nodeFilter = ids;
  $('#node-filter-label').textContent = label;
  $('#active-node-filter').hidden = false;
  applyHypFilters();
  selectTab('hypotheses');
  const first = STATE.filtered[0];
  if (first) setTimeout(() => {
    const el = document.getElementById('hyp-' + first.id);
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, 60);
}

async function loadHypotheses() {
  const d = await api('/api/hypotheses');
  STATE.hyps = d;
  badge($('#hyp-badge'), d.fixture, d.source, d.source);

  const sel = $('#class-filter');
  const entries = Object.entries(d.by_class || {}).sort((a, b) => b[1] - a[1]);
  sel.innerHTML = '<option value="">all classes</option>' + entries.map(([k, n]) => {
    const label = (d.hypotheses.find((h) => h.discovery_class === k) || {}).discovery_class_label || k;
    return `<option value="${esc(k)}">${esc(label)} (${n})</option>`;
  }).join('');

  const c = d.counts || {};
  const summary = document.createElement('div');
  summary.className = 'stat-grid';
  summary.innerHTML = [
    ['ranked', c.total ?? 0, 'across the six discovery classes'],
    ['classes covered', c.classes ?? 0, 'one module each'],
    ['discovery', c.discovered ?? 0, 'excluding controls'],
    ['controls', c.controls ?? 0, 'published beside the results'],
  ].map(([k, v, sub]) => `<div class="stat"><div class="stat-v">${fmt(v)}</div>
      <div class="stat-k">${k}</div><div class="stat-sub">${esc(sub)}</div></div>`).join('');
  $('#hyp-list').before(summary);

  if (d.pipeline) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.style.margin = '-.6rem 0 .9rem';
    p.textContent = `Pipeline: ${d.pipeline} · generated ${d.generated_at || 'unknown'} · source ${d.source}`;
    summary.after(p);
  }
  applyHypFilters();
  buildHypothesisNodeIndex();
}

/* ================================================================= GRAPH */
const NODE_COLOR = {
  taxon: '#6FBF73', drug: '#E8B44A', compound: '#6FA8DC', target: '#D98CB3',
  indication: '#E06C5A', process: '#B49BE0', formula: '#F0D264', source: '#9AA0A6',
  concept: '#7FD1C1', role: '#7FD1C1', other: '#B9B2A6',
};
const nodeColor = (t) => NODE_COLOR[t] || NODE_COLOR.other;

function buildEdgeIndex() {
  const idx = new Map();
  for (const e of STATE.kg.edges) {
    if (!idx.has(e.source)) idx.set(e.source, []);
    if (!idx.has(e.target)) idx.set(e.target, []);
    idx.get(e.source).push({ other: e.target, rel: e.rel, dir: 'out' });
    idx.get(e.target).push({ other: e.source, rel: e.rel, dir: 'in' });
  }
  STATE.edgeIndex = idx;
}

function degreeOf(id) { return (STATE.edgeIndex.get(id) || []).length; }

function drawGraph() {
  if (!STATE.kg || STATE.graphDrawn) return;
  STATE.graphDrawn = true;
  const { nodes, edges, layout } = STATE.kg;
  const eG = $('#kg-edges');
  const nG = $('#kg-nodes');
  const pos = (id) => layout[id] || [620, 420];

  eG.innerHTML = edges.map((e, i) => {
    const a = pos(e.source), b = pos(e.target);
    return `<line data-i="${i}" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"
      stroke="rgba(246,240,227,.13)" stroke-width="0.9" />`;
  }).join('');

  const sorted = [...nodes].sort((a, b) => degreeOf(b.id) - degreeOf(a.id));
  nG.innerHTML = sorted.map((n) => {
    const deg = degreeOf(n.id);
    const r = 4.2 + Math.min(9, Math.sqrt(deg) * 2.3);
    const [x, y] = pos(n.id);
    const showLabel = deg >= 3;
    const label = String(n.label || n.id).slice(0, 20);
    const wide = deg >= 8;
    return `<g data-id="${esc(n.id)}" tabindex="-1" role="button"
        aria-label="${esc(n.label || n.id)} (${esc(n.type || 'node')}, ${deg} connections)">
      <circle class="core" cx="${x}" cy="${y}" r="${r}" fill="${nodeColor(n.type)}"
        stroke="rgba(23,20,15,.75)" stroke-width="1.2" />
      ${showLabel ? `<text class="node-label ${wide ? 'lg' : ''}" x="${x}" y="${y + r + 9}"
        text-anchor="middle">${esc(label)}</text>` : ''}
    </g>`;
  }).join('');

  // legend
  const types = [...new Set(nodes.map((n) => n.type))].sort();
  $('#kg-legend').innerHTML = types.map((t) =>
    `<span><i style="background:${nodeColor(t)}"></i>${esc(t)}</span>`).join('');
  $('#graph-count').textContent = `${nodes.length} nodes · ${edges.length} edges · precomputed layout`;

  $$('#kg-nodes g').forEach((g) => {
    g.addEventListener('click', () => selectNode(g.dataset.id));
    g.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectNode(g.dataset.id); }
    });
    g.addEventListener('mouseenter', () => highlight(g.dataset.id));
    g.addEventListener('mouseleave', () => highlight(STATE.selectedNode));
  });
}

function neighboursOf(id) {
  const set = new Set([id]);
  (STATE.edgeIndex.get(id) || []).forEach((e) => set.add(e.other));
  return set;
}

function highlight(id) {
  if (!id) {
    $$('#kg-edges line').forEach((l) => {
      l.setAttribute('stroke', 'rgba(246,240,227,.13)');
      l.setAttribute('stroke-width', '0.9');
    });
    $$('#kg-nodes g circle.core').forEach((c) => { c.setAttribute('stroke', 'rgba(23,20,15,.75)'); c.setAttribute('stroke-width', '1.2'); });
    $$('#kg-nodes text').forEach((t) => t.classList.remove('hl'));
    return;
  }
  const nb = neighboursOf(id);
  const nodes = STATE.kg.nodes;
  const posOf = (n) => STATE.kg.layout[n] || [0, 0];
  const edgeNodes = STATE.kg.edges;
  $$('#kg-edges line').forEach((l, i) => {
    const e = edgeNodes[i];
    const on = e && (e.source === id || e.target === id);
    l.setAttribute('stroke', on ? 'rgba(232,180,74,.75)' : 'rgba(246,240,227,.055)');
    l.setAttribute('stroke-width', on ? '1.8' : '0.8');
  });
  $$('#kg-nodes g').forEach((g) => {
    const isNb = nb.has(g.dataset.id);
    g.style.opacity = isNb ? '1' : '.28';
    const c = $('circle.core', g);
    if (c) {
      c.setAttribute('stroke', isNb ? '#F6F0E3' : 'rgba(23,20,15,.75)');
      c.setAttribute('stroke-width', isNb ? '1.9' : '1.2');
    }
    const t = $('text', g);
    if (t) t.classList.toggle('hl', g.dataset.id === id);
  });
  void nodes; void posOf;
}

function nodeMatches(node) {
  // hypotheses whose chain text references this node, or one of its direct neighbours
  const ids = new Set();
  const label = String(node.label || '').toLowerCase();
  const shortId = node.id.split(':').slice(1).join(':');
  const needles = [label, shortId.toLowerCase()].filter((s) => s && s.length > 1);
  const neigh = (STATE.edgeIndex.get(node.id) || []).map((e) => e.other);
  const allNodeIds = new Set([node.id, ...neigh]);
  const labels = new Set(needles);
  for (const otherId of allNodeIds) {
    const other = STATE.kg.nodes.find((n) => n.id === otherId);
    if (other && other.label) labels.add(String(other.label).toLowerCase());
  }
  for (const h of (STATE.hyps ? STATE.hyps.hypotheses : [])) {
    const hay = ([h.title, ...Object.values(h.chain)].join(' ') + ' ' + ((h.provenance || []).map((p) => p.title || '').join(' '))).toLowerCase();
    for (const needle of labels) {
      if (needle.length > 1 && hay.includes(needle)) { ids.add(h.id); break; }
    }
  }
  return [...ids];
}

function buildHypothesisNodeIndex() {
  if (!STATE.kg || !STATE.hyps) return;
  for (const n of STATE.kg.nodes) STATE.hypByNode.set(n.id, null);
}

function selectNode(id) {
  STATE.selectedNode = id;
  highlight(id);
  const node = STATE.kg.nodes.find((n) => n.id === id);
  if (!node) return;
  const nb = (STATE.edgeIndex.get(id) || []);
  const matches = nodeMatches(node);
  $('#node-inspector').innerHTML = `
    <div class="k">${esc(node.type || 'node')}</div>
    <h4${langAttr(node.label)}>${esc(node.label || node.id)}</h4>
    <div class="prov-loc">${esc(node.id)} · ${nb.length} connections</div>
    ${matches.length
      ? `<button class="btn-ghost" type="button" id="insp-filter" style="margin-top:.5rem">
           Filter hypotheses by this node (${matches.length})</button>`
      : `<p class="muted" style="margin-top:.5rem;font-size:.76rem">No hypothesis chain references this
           node directly. It is graph context — useful for reading, not for ranking.</p>`}
    <ul class="neigh">${nb.slice(0, 24).map((e) => {
      const other = STATE.kg.nodes.find((n) => n.id === e.other) || { label: e.other };
      return `<li><span class="rel">${e.dir === 'out' ? '→' : '←'} ${esc(e.rel || '')}</span>
        <button type="button" data-node="${esc(e.other)}"${langAttr(other.label)}>${esc(other.label)}</button></li>`;
    }).join('')}</ul>`;
  const btn = $('#insp-filter');
  if (btn) btn.addEventListener('click', () => setNodeFilter(node.label || node.id, matches));
  $$('#node-inspector .neigh button').forEach((b) =>
    b.addEventListener('click', () => selectNode(b.dataset.node)));
}

function initNodeSearch() {
  const input = $('#node-search');
  let t = null;
  input.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      const q = input.value.trim().toLowerCase();
      const wrap = $('#node-results');
      if (!q) { wrap.innerHTML = ''; return; }
      const hits = STATE.kg.nodes.filter((n) =>
        String(n.label || '').toLowerCase().includes(q) || n.id.toLowerCase().includes(q)).slice(0, 40);
      wrap.innerHTML = hits.length
        ? hits.map((n) => `<button type="button" data-node="${esc(n.id)}"${langAttr(n.label)}>
            <span class="dot" style="background:${nodeColor(n.type)}"></span>
            <span>${esc(n.label || n.id)}</span>
            <span class="prov-loc" style="margin-left:auto">${esc(n.type)}</span></button>`).join('')
        : `<p class="muted" style="font-size:.8rem">no node matches “${esc(q)}”</p>`;
      $$('#node-results button').forEach((b) => b.addEventListener('click', () => {
        selectNode(b.dataset.node);
        $('#node-inspector').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }));
    }, 110);
  });
}

async function loadKG() {
  const d = await api('/api/kg');
  STATE.kg = d;
  badge($('#kg-badge'), d.fixture, d.source, d.source);
  buildEdgeIndex();
  if ($('#panel-graph').hidden === false) drawGraph();
}

/* ================================================================= ASK */
const EXAMPLES = [
  'What does 雷公炮炙論 say about preparing 附子?',
  'why is 關木通 dangerous',
  'what does the corpus say about 十八反',
  'role of 使 in a formula',
  'what does 本草綱目 say about 三七',
  'how do I prepare aconite at home',
];

function renderAsk(res) {
  const out = $('#ask-out');
  const mode = res.mode || 'unknown';
  const refused = !!res.refused;
  const blocked = (res.safety && res.safety.allowed === false) || mode === 'policy-screen';
  const cls = blocked ? 'is-blocked' : refused ? 'is-refused' : '';
  const conf = typeof res.confidence === 'number' ? res.confidence : null;

  const badges = [
    `<span class="badge">mode: ${esc(mode)}</span>`,
    refused
      ? `<span class="badge badge-sev-caution">REFUSED${res.refusal_reason ? ' · ' + esc(res.refusal_reason) : ''}</span>`
      : `<span class="badge badge-sev-none">GROUNDED · ${res.citations ? res.citations.length : 0} citations</span>`,
    conf !== null ? `<span class="badge">confidence ${conf.toFixed(2)}</span>` : '',
  ].join('');

  const cites = (res.citations || []).map((c) => {
    const l = String(c.licence || '');
    const lc = /UNVERIFIED/i.test(l) ? 'lic-unv' : /CC/i.test(l) ? 'lic-cc' : 'lic-pd';
    return `<li>
      <div class="cite-head">
        <span class="cite-title"${langAttr(c.title)}>${esc(c.title || c.source_id)}</span>
        <span class="am">${esc(c.author || '')}${c.year ? ' · ' + esc(c.year) : ''}</span>
        ${c.locator ? `<span class="prov-loc">${esc(c.locator)}</span>` : ''}
        <span class="badge">tier ${esc(c.tier ?? '?')}</span>
        ${c.licence ? `<span class="lic ${lc}">${esc(c.licence)}</span>` : ''}
        ${c.span_kind ? `<span class="badge">${esc(c.span_kind)}</span>` : ''}
      </div>
      <div class="cite-span"${langAttr(c.span)}>${esc(c.span || '')}</div>
    </li>`;
  }).join('');

  out.innerHTML = `<div class="ask-card ${cls}">
    <div class="ask-meta">${badges}</div>
    <div class="ask-q">${esc(res.query || '')}</div>
    <div class="ask-answer">${esc(res.answer || '')}</div>
    ${res.mode_note ? `<p class="muted" style="font-size:.76rem;margin:.7rem 0 0">${esc(res.mode_note)}</p>` : ''}
    ${cites ? `<ol class="cites">${cites}</ol>` : ''}
  </div>`;
}

function initAsk() {
  const form = $('#ask-form');
  const input = $('#ask-q');
  const examples = $('#ask-examples');
  examples.innerHTML = EXAMPLES.map((q) =>
    `<button type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
  $$('#ask-examples button').forEach((b) => b.addEventListener('click', () => {
    input.value = b.dataset.q;
    form.requestSubmit();
  }));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    const out = $('#ask-out');
    out.innerHTML = `<div class="ask-card"><p class="muted" style="margin:0">Retrieving from the loaded corpus…</p></div>`;
    try {
      const res = await api('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      renderAsk(res);
    } catch (err) {
      out.innerHTML = `<div class="ask-card is-blocked"><div class="ask-answer">The Ask endpoint failed:
        ${esc(err.message)}. The Workbench keeps working — try another panel.</div></div>`;
    }
  });

  api('/api/meta').then((m) => {
    badge($('#ask-badge'), m.status.find((s) => s.key === 'passages').fixture,
      m.rag_backend, (m.status.find((s) => s.key === 'passages') || {}).source);
  }).catch(() => {});
}

/* ================================================================= CORPUS */
const TIER_NAMES = {
  0: 'Ontology — the domain structure',
  1: 'Foundational biology & chemistry substrate',
  2: 'Asian materia medica — the core',
  3: 'Asian alchemy & esoteric pharmacy',
  4: 'Acupuncture & channels',
  5: 'Structured open data — ground truth',
};

function hbars(entries, total, labelFn) {
  const max = Math.max(1, ...entries.map((e) => e[1]));
  return `<div class="hbars">${entries.map(([k, n]) => `
    <div class="hbar">
      <span class="hbar-k">${esc(labelFn ? labelFn(k) : k)}</span>
      <span class="hbar-track"><i style="width:${Math.max(3, Math.round(n / max * 100))}%"></i></span>
      <span class="hbar-v">${n}${total ? ` · ${pct(n / total)}` : ''}</span>
    </div>`).join('')}</div>`;
}

function stagesHTML(stages) {
  if (!stages || !stages.length) return '';
  return `<div class="pipeline">${stages.map((s) => `
    <div class="stage">
      <span class="stage-cn"${langAttr(s.cn)}>${esc(s.cn || '·')}</span><span class="stage-py">${esc(s.stage)}</span>
      <div class="stage-what"><strong>${esc(s.label)}</strong><br>${esc(s.detail)}</div>
    </div>`).join('')}</div>`;
}

function renderCorpus(d) {
  badge($('#corpus-badge'), d.fixture, d.source, d.source);
  const s = d.stats || {};
  const tiers = Object.entries(s.tiers || {}).sort((a, b) => Number(a[0]) - Number(b[0]));
  const langs = Object.entries(s.langs || {}).sort((a, b) => b[1] - a[1]);
  const trad = Object.entries(s.traditions || {}).sort((a, b) => b[1] - a[1]);
  const lic = Object.entries(s.licences || {}).sort((a, b) => b[1] - a[1]);

  const stats = `<div class="stat-grid">
    <div class="stat"><div class="stat-v">${fmt(s.fetched)}</div><div class="stat-k">sources fetched</div>
      <div class="stat-sub">${fmt(s.kept)} kept · ${fmt(s.excluded)} excluded</div></div>
    <div class="stat"><div class="stat-v">${s.chars ? (s.chars / 1e6).toFixed(1) + 'M' : '—'}</div>
      <div class="stat-k">characters</div><div class="stat-sub">after clean, before dedupe</div></div>
    <div class="stat"><div class="stat-v">${fmt(langs.length)}</div><div class="stat-k">languages</div>
      <div class="stat-sub">${esc(langs.map(([k]) => k).slice(0, 6).join(' · '))}</div></div>
    <div class="stat"><div class="stat-v">${s.year_min != null ? `${s.year_min}–${s.year_max}` : '—'}</div>
      <div class="stat-k">years spanned</div><div class="stat-sub">from the registry, not estimated</div></div>
  </div>`;

  const tierBlock = `<div class="card"><h3>Tier structure</h3>
    <p class="sub">Derived from the axioms in <code>docs/FIRST_PRINCIPLES.md</code> — the registry is a proof
    obligation, not a wish list. The Western herbal tradition appears only as a ≤3% labelled comparative control.</p>
    <div class="tier-map">${tiers.map(([t, n]) => `
      <div class="tier"><div class="tier-n">TIER ${esc(t)}</div>
        <div class="tier-v">${n}</div>
        <div class="tier-d">${esc(TIER_NAMES[t] || '')}</div></div>`).join('')}</div></div>`;

  const eras = Object.entries(s.eras || {});
  const eraBlock = eras.length ? `<div class="card"><h3>Sources by era</h3>
    <p class="sub">Computed from the registry's <code>year</code> field — the span of the record the model reads,
      not an estimate.</p>
    ${hbars(eras, s.kept)}</div>` : '';

  const licenceBlock = `<div class="card"><h3>Licence posture</h3>
    <p class="sub">Anything whose licence is not verifiable is marked <span class="lic lic-unv">UNVERIFIED</span>,
    excluded from training and cited only. Nothing restricted is redistributed.</p>
    ${hbars(lic, s.kept, (k) => k)}</div>`;

  const tradBlock = `<div class="card"><h3>Traditions &amp; languages</h3>
    <div class="split">
      <div><h4 class="tier-n">BY TRADITION</h4>${hbars(trad, s.kept, (k) => k)}</div>
      <div><h4 class="tier-n">BY LANGUAGE</h4>${hbars(langs, s.kept, (k) => k)}</div>
    </div></div>`;

  const rows = (d.sources || []).map((r) => {
    const l = String(r.licence || '');
    const lc = /UNVERIFIED/i.test(l) ? 'lic-unv' : /CC/i.test(l) ? 'lic-cc' : 'lic-pd';
    const bad = r.status && r.status !== 'ok';
    return `<tr${bad ? ' style="opacity:.62"' : ''}>
      <td${langAttr(r.title)}>${esc(r.title)}${r.title_en ? `<br><span class="am">${esc(r.title_en)}</span>` : ''}</td>
      <td>${esc(r.author || '')}</td>
      <td class="num">${esc(r.year ?? '—')}</td>
      <td>${esc(r.tradition || '')}</td>
      <td>${esc(r.lang || '')}</td>
      <td class="num">${esc(r.tier ?? '')}</td>
      <td><span class="lic ${lc}">${esc(r.licence || '?')}</span></td>
      <td class="num">${r.chars ? fmt(r.chars) : '—'}</td>
      <td>${bad ? `<span class="badge badge-sev-high">${esc(r.status)}</span>` : '<span class="badge badge-sev-none">ok</span>'}</td>
    </tr>`;
  }).join('');

  $('#corpus-body').innerHTML = stats + tierBlock + eraBlock + tradBlock + licenceBlock + `
    ${stagesHTML(d.stages)}
    <div class="card"><h3>Source ledger</h3>
      <p class="sub">${d.sources.length} entries. Every row is one registry record with provenance, licence and tier.</p>
      <div class="wrap-scroll"><table class="data">
        <thead><tr><th>Title</th><th>Author</th><th>Year</th><th>Tradition</th><th>Lang</th>
          <th>Tier</th><th>Licence</th><th>Chars</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody></table></div></div>`;
}

async function loadCorpus() {
  const d = await api('/api/corpus');
  renderCorpus(d);
}

/* ================================================================= METHODOLOGY */
function lossChart(metrics) {
  const curve = metrics.loss_curve.filter((p) => typeof p.loss === 'number');
  if (curve.length < 2) return '';
  const W = 760, H = 260, P = { l: 44, r: 14, t: 14, b: 30 };
  const xs = curve.map((p) => p.step);
  const vals = curve.map((p) => p.loss).concat(curve.filter((p) => typeof p.val_loss === 'number').map((p) => p.val_loss));
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = 0, y1 = Math.max(...vals) * 1.06;
  const sx = (x) => P.l + (x - x0) / Math.max(1, x1 - x0) * (W - P.l - P.r);
  const sy = (y) => H - P.b - (y - y0) / Math.max(1e-9, y1 - y0) * (H - P.t - P.b);
  const path = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(' ');
  const trainPts = curve.map((p) => [p.step, p.loss]);
  const valPts = curve.filter((p) => typeof p.val_loss === 'number').map((p) => [p.step, p.val_loss]);
  const yTicks = [0, .25, .5, .75, 1].map((f) => y0 + (y1 - y0) * f);
  const xTicks = [0, .25, .5, .75, 1].map((f) => x0 + (x1 - x0) * f);
  return `<div class="chart">
    <svg viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Training loss curve: ${curve.length} logged points from step ${x0} to ${x1}">
      ${yTicks.map((v) => `<line class="grid-line" x1="${P.l}" x2="${W - P.r}" y1="${sy(v)}" y2="${sy(v)}"/>
        <text class="axis" x="${P.l - 6}" y="${sy(v) + 3}" text-anchor="end">${v.toFixed(2)}</text>`).join('')}
      ${xTicks.map((v) => `<text class="axis" x="${sx(v)}" y="${H - 10}" text-anchor="middle">${Math.round(v)}</text>`).join('')}
      <path class="train-line" d="${path(trainPts)}"/>
      ${valPts.length ? `<path class="val-line" d="${path(valPts)}"/>` : ''}
      <text class="axis" x="${W - P.r}" y="${H - 10}" text-anchor="end">step</text>
    </svg>
    <div class="chart-legend"><span><i></i>train loss</span>${valPts.length ? '<span class="val"><i></i>val loss</span>' : ''}</div>
  </div>`;
}

function evalBlock(ev, hypCounts) {
  if (!ev.report) {
    return `<div class="empty"><strong>No measured evaluation yet.</strong>
      The panel is deliberately empty rather than filled with invented numbers — the negative controls are the
      entire point of this section, and a fake one is worse than none.
      <p style="margin:.6rem 0 0">Produce it with <code>${esc(ev.awaiting || 'make eval')}</code>.</p></div>`;
  }
  const r = ev.report;
  const benches = Object.entries(r.benchmarks || {});
  const benchRows = benches.map(([name, v]) => `<tr>
      <td>${esc(name)}</td>
      <td class="num">${typeof v.score === 'number' ? v.score.toFixed(3) : esc(v.score)}</td>
      <td class="num">${esc(v.n ?? '—')}</td></tr>`).join('');

  const nc = r.negative_controls || {};
  const ctrlCard = (key, title, blurb) => {
    const v = nc[key];
    if (!v) {
      return `<div class="ctrl"><h4>${esc(title)}</h4>
        <div class="rho">—</div><div class="verdict" style="color:var(--muted)">not yet measured</div>
        <p>${esc(blurb)}</p></div>`;
    }
    if (key === 'null_model') {
      const drop = v.score_drop;
      const strong = typeof drop === 'number' && Math.abs(drop) > 0.3;
      return `<div class="ctrl"><h4>${esc(title)}</h4>
        <div class="rho">${typeof drop === 'number' ? drop.toFixed(3) : esc(drop)}</div>
        <div class="verdict" style="color:${strong ? 'var(--verdigris)' : 'var(--cinnabar)'}">
          ${strong ? 'scores collapse ✓' : 'scores do NOT collapse'}</div>
        <p>${esc(blurb)}</p></div>`;
    }
    const rho = v.rho, p = v.p;
    const sig = typeof p === 'number' && p < 0.05 && Math.abs(rho) > 0.2;
    return `<div class="ctrl"><h4>${esc(title)}</h4>
      <div class="rho">ρ = ${typeof rho === 'number' ? rho.toFixed(3) : esc(rho)}${typeof p === 'number' ? ` <span class="am" style="font-size:.7rem">p=${p.toFixed(3)}</span>` : ''}</div>
      <div class="verdict" style="color:${sig ? 'var(--cinnabar)' : 'var(--verdigris)'}">
        ${sig ? 'SIGNAL — reasoning principle predicts action' : 'no predictive signal (the expected null)'}</div>
      <p>${esc(blurb)}</p></div>`;
  };


  const dd = r.drug_discovery || {};
  const tp = dd.theory_predictivity || {};
  const theoryCards = Object.entries(tp).map(([key, v]) => {
    const metric = (v.metric || '').toLowerCase();
    const val = typeof v.value === 'number' ? v.value : null;
    const p = typeof v.p === 'number' ? v.p : null;
    const above = val !== null && (metric === 'auc' ? val > 0.55 : Math.abs(val) > 0.1);
    const sig = p !== null && p < 0.05;
    const strong = above && sig;
    const cls = strong ? 'is-strong' : 'is-null';
    const verdict = strong ? 'predicts above chance' : (above ? 'trend, not significant' : 'no predictive signal');
    return `<div class="theory ${cls}">
      <div class="k" style="font-family:var(--mono);font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">
        ${esc(key)}${v.fixture ? ' · <span style="color:var(--cinnabar-d);font-weight:700">DEMO FIXTURE</span>' : ''}</div>
      <div class="tv-big">${val === null ? '—' : val.toFixed(3)}
        <span style="font-size:.62rem;font-weight:400;color:var(--muted)">${esc(metric)}</span></div>
      <div class="verdict" style="color:${strong ? 'var(--verdigris)' : 'var(--brass)'}">${verdict}</div>
      <div class="tv-hyp">${esc(v.hypothesis || '')}</div>
      <div class="tv-meta">n = ${esc(v.n ?? '—')} · p = ${p === null ? '—' : p.toFixed(3)} · vs permutation null</div>
    </div>`;
  }).join('');

  const ddCard = dd && Object.keys(dd).length && !dd.theory_predictivity ? '' : '';
  void ddCard;

  const discoveryCard = `<div class="card"><h3>Drug discovery output</h3>
    <p class="sub">The terminal artefact of the pipeline (brief §11.4–11.5): candidates, not answers.</p>
    <div class="stat-grid">
      <div class="stat"><div class="stat-v">${fmt(dd.candidates ?? '—')}</div><div class="stat-k">candidates</div>
        <div class="stat-sub">ranked leads with development paths</div></div>
      <div class="stat"><div class="stat-v">${typeof dd.mean_novelty === 'number' ? dd.mean_novelty.toFixed(2) : '—'}</div>
        <div class="stat-k">mean novelty</div><div class="stat-sub">against modern chemistry</div></div>
      <div class="stat"><div class="stat-v">${typeof dd.lipinski_pass_rate === 'number' ? pct(dd.lipinski_pass_rate) : '—'}</div>
        <div class="stat-k">Lipinski pass rate</div><div class="stat-sub">computed descriptors where structures resolve</div></div>
    </div>
    ${dd.note ? `<p class="muted" style="font-size:.78rem;margin:.6rem 0 0">${esc(dd.note)}</p>` : ''}
  </div>`;

  const theoryCard = theoryCards ? `<div class="card"><h3>The central experiment — does Asian theory predict chemistry?</h3>
    <p class="sub">Asian property vectors (四氣五味, 歸經, rasa/guṇa/vīrya/vipāka) are used as a feature vector and
      tested against measured molecular and target properties, with a permutation null. A positive result is the
      headline finding. A null is an honest, publishable negative — either way it is reported with numbers.</p>
    <div class="theory-grid">${theoryCards}</div>
    <p class="muted" style="font-size:.78rem;margin:.7rem 0 0">Method, thresholds and the permutation procedure are
      published in <code>docs/EVALUATION.md</code>; the null distribution is recomputed on every run.</p>
  </div>` : '';

  return `${theoryCard}${discoveryCard}
    <div class="card"><h3>Benchmarks</h3>
      <p class="sub">Generated ${esc(r.generated_at || 'unknown')} · source <code>${esc(ev.source)}</code></p>
      ${benches.length ? `<div class="wrap-scroll"><table class="data">
        <thead><tr><th>Benchmark</th><th class="num">Score</th><th class="num">n</th></tr></thead>
        <tbody>${benchRows}</tbody></table></div>` : '<p class="muted">No benchmark rows in the report.</p>'}
    </div>
    <div class="card"><h3>Negative controls</h3>
      <p class="sub">Published beside the results, reported honestly even when the answer is "no signal".
        These are the questions we are prepared to be wrong about in public.</p>
      <div class="ctrl-grid">
        ${ctrlCard('quxiangbilei', '取象比類 — analogical reasoning',
          'Does colour, shape or habitat resemblance predict target organ? If this shows signal, our extraction is reading resemblance language, not pharmacology.')}
        ${ctrlCard('ayurveda_rasa', 'Ayurvedic ṣaḍrasa — the six tastes',
          'Do the six tastes predict pharmacological action beyond chance? A foundational Ayurvedic principle, tested as a hypothesis rather than assumed.')}
        ${ctrlCard('null_model', 'Null model — shuffled edges',
          'Plant↔use edges are shuffled and discovery scores recomputed. Real findings must collapse; if they do not, the scoring is measuring the pipeline.')}
      </div>
    </div>
    <div class="card"><h3>Hypotheses by class</h3>
      <p class="sub">${fmt(r.hypotheses ? r.hypotheses.n : hypCounts.total)} ranked
        · mean novelty ${r.hypotheses && typeof r.hypotheses.mean_novelty === 'number' ? r.hypotheses.mean_novelty.toFixed(3) : '—'}</p>
      ${r.hypotheses && r.hypotheses.by_class ? hbars(Object.entries(r.hypotheses.by_class)) : '<p class="muted">not reported</p>'}
    </div>`;
}

function metricsBlock(m) {
  if (!m.metrics) {
    return `<div class="empty"><strong>No training run recorded yet.</strong>
      This chart is intentionally blank. A loss curve is the one artefact that cannot be approximated —
      it either was logged by a real run or it is fiction.
      <p style="margin:.6rem 0 0">Produce it with <code>${esc(m.awaiting || 'make train-mini')}</code>; the
      Workbench picks up <code>training/runs/*/metrics.json</code> automatically (brief §10.6).</p></div>`;
  }
  const x = m.metrics;
  const strip = [
    ['params', typeof x.params === 'number' ? fmt(x.params) : '—'],
    ['tokens seen', typeof x.tokens_seen === 'number' ? fmt(x.tokens_seen) : '—'],
    ['steps', typeof x.steps === 'number' ? fmt(x.steps) : '—'],
    ['final train loss', typeof x.final_train_loss === 'number' ? x.final_train_loss.toFixed(3) : '—'],
    ['final val loss', typeof x.final_val_loss === 'number' ? x.final_val_loss.toFixed(3) : '—'],
    ['val ppl', typeof x.val_ppl === 'number' ? x.val_ppl.toFixed(1) : '—'],
    ['bits/byte', typeof x.bits_per_byte === 'number' ? x.bits_per_byte.toFixed(2) : '—'],
    ['tokens/s', typeof x.tokens_per_s === 'number' ? fmt(x.tokens_per_s) : '—'],
  ].map(([k, v]) => `<div>${k}<b>${esc(v)}</b></div>`).join('');
  return `<div class="card"><h3>Training run — ${esc(x.run_id || 'run')}</h3>
    <p class="sub">${esc(m.source)} · ${esc(x.created_at || '')} · seed ${esc(x.seed ?? '—')}
      · torch ${esc(x.torch_version || '—')}</p>
    ${lossChart(x)}
    <div class="metric-strip">${strip}</div>
  </div>`;
}

function renderMethod(d) {
  const ev = d.eval, m = d.metrics;
  badge($('#method-badge'), ev.fixture || m.fixture,
    [ev.fixture ? 'eval: fixture' : 'eval: live', m.fixture ? 'run: absent' : 'run: live'].join(' · '),
    ev.source);

  const stages = (d.pipeline || []).map((s) => `
    <div class="stage">
      <span class="stage-cn"${langAttr(s.cn)}>${esc(s.cn)}</span><span class="stage-py">${esc(s.py)} · ${esc(s.en)}</span>
      <div class="stage-what">${esc(s.what)}</div>
      <div class="stage-out">→ ${esc(s.out)}</div>
    </div>`).join('');

  $('#method-body').innerHTML = `
    <div class="card"><h3>采 → 制 → 配 → 使</h3>
      <p class="sub">The four classical operations of Chinese pharmacy, used as the pipeline vocabulary
        everywhere: code, CLI, docs and this interface.</p>
      <div class="pipeline">${stages}</div>
      <p class="muted" style="font-size:.8rem;margin:0">Scoring rule:
        <code>composite = novelty^0.30 × plausibility^0.30 × testability^0.25 × evidence^0.15</code>.
        A sensitivity sweep over the exponents is reported in <code>docs/EVALUATION.md</code>, because a weighted
        product is a design choice and should be visible as one.</p>
    </div>
    ${metricsBlock(m)}
    ${evalBlock(ev, d.hypotheses || {})}
    <div class="card"><h3>Reproduce</h3>
      <div class="wrap-scroll"><table class="data"><tbody>
        <tr><td><code>make setup</code></td><td>environment</td></tr>
        <tr><td><code>make corpus</code></td><td>采 Cǎi — fetch, clean, dedupe, registry</td></tr>
        <tr><td><code>make tokenizer</code></td><td>domain BPE over zh-classical / sa / en</td></tr>
        <tr><td><code>make train-mini</code></td><td>from-scratch shennong-mini, real logs</td></tr>
        <tr><td><code>make eval</code></td><td>benchmarks + negative controls → <code>eval/report.json</code></td></tr>
        <tr><td><code>make app-data</code></td><td>shi / pei / cai exports into <code>app/data</code></td></tr>
        <tr><td><code>make workbench</code></td><td>this interface</td></tr>
      </tbody></table></div>
    </div>`;
}

async function loadMethod() {
  const d = await api('/api/methodology');
  renderMethod(d);
}

/* ================================================================= boot */
(async function boot() {
  initTabs();
  initCandidateControls();
  initHypothesisControls();
  initNodeSearch();
  initAsk();

  try { await loadMeta(); } catch (e) { console.error(e); }
  try { await loadCandidates(); } catch (e) { console.error(e); }
  try { await loadKG(); } catch (e) { console.error(e); }
  try { await loadHypotheses(); } catch (e) { console.error(e); }
  try { await loadCorpus(); } catch (e) { console.error(e); }
  try { await loadMethod(); } catch (e) { console.error(e); }

  if (location.hash === '#graph') drawGraph();
})();
