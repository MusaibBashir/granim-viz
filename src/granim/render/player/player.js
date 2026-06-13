/* granim player: renders the embedded timeline. No dependencies. */
"use strict";

const DATA = JSON.parse(document.getElementById("granim-data").textContent);
const T = DATA.theme.tokens;
for (const [k, v] of Object.entries(T)) document.documentElement.style.setProperty(k, v);

const U = +T["--unit"], R = U * 0.38, PAD = 60;
const NS = "http://www.w3.org/2000/svg";
const svg = document.getElementById("svg");
let speed = DATA.meta.speed || 1;
const manualPos = new Map();  // nodes the user has dragged stay where they're dropped

/* ---------- positions ---------- */
const KF = DATA.keyframes.map(k => {
  const pos = {};
  for (const [id, [x, y]] of Object.entries(k.pos)) pos[id] = [x * U + PAD, y * U + PAD];
  return pos;
});
function kfPos(kf, id) {
  const m = manualPos.get(id);
  if (m) return m;  // a dragged node ignores layout keyframes and stays put
  for (let i = Math.min(kf, KF.length - 1); i >= 0; i--) if (KF[i][id]) return KF[i][id];
  for (let i = kf + 1; i < KF.length; i++) if (KF[i][id]) return KF[i][id];
  return [PAD, PAD];
}
/* ---------- camera: fit / wheel zoom / drag pan ---------- */
let vb = { x: 0, y: 0, w: 100, h: 100 };
function applyVB() {
  svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
}
function fit() {
  let xs = [], ys = [];
  for (const kf of KF) for (const [x, y] of Object.values(kf)) { xs.push(x); ys.push(y); }
  if (!xs.length) { xs = [0]; ys = [0]; }
  const M = U * 2.0;  // margin for node bodies, labels, badges and struct titles
  const x0 = Math.min(...xs) - M, y0 = Math.min(...ys) - M;
  vb = { x: x0, y: y0, w: Math.max(...xs) - x0 + M, h: Math.max(...ys) - y0 + M };
  applyVB();
}
function clientToSvg(e) {
  const r = svg.getBoundingClientRect();
  return [vb.x + (e.clientX - r.left) / r.width * vb.w,
          vb.y + (e.clientY - r.top) / r.height * vb.h];
}
let nodeDrag = null;
(function camera() {
  svg.addEventListener("wheel", e => {
    e.preventDefault();
    const k = e.deltaY > 0 ? 1.15 : 1 / 1.15;
    const r = svg.getBoundingClientRect();
    const px = vb.x + (e.clientX - r.left) / r.width * vb.w;
    const py = vb.y + (e.clientY - r.top) / r.height * vb.h;
    vb = { x: px - (px - vb.x) * k, y: py - (py - vb.y) * k, w: vb.w * k, h: vb.h * k };
    applyVB();
  }, { passive: false });
  let drag = null;
  svg.addEventListener("pointerdown", e => {
    const ng = e.target.closest && e.target.closest(".node");
    if (ng) {                                   // grab a node — edges follow it
      const id = ng.getAttribute("data-id");
      const [mx, my] = clientToSvg(e);
      const [nx, ny] = curPos.get(id) || [mx, my];
      nodeDrag = { id, dx: nx - mx, dy: ny - my };
      ng.classList.add("dragging");
    } else {                                    // empty canvas — pan
      drag = { cx: e.clientX, cy: e.clientY, x: vb.x, y: vb.y };
      svg.classList.add("panning");
    }
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", e => {
    if (nodeDrag) {
      const [mx, my] = clientToSvg(e);
      const x = mx + nodeDrag.dx, y = my + nodeDrag.dy;
      manualPos.set(nodeDrag.id, [x, y]);
      setPos(nodeDrag.id, x, y);
      repathEdges(); updateTitles();
      return;
    }
    if (!drag) return;
    const r = svg.getBoundingClientRect();
    vb.x = drag.x - (e.clientX - drag.cx) * vb.w / r.width;
    vb.y = drag.y - (e.clientY - drag.cy) * vb.h / r.height;
    applyVB();
  });
  const end = () => {
    if (nodeDrag) {
      const n = nodeEls.get(nodeDrag.id);
      if (n) n.g.classList.remove("dragging");
      nodeDrag = null;
    }
    drag = null; svg.classList.remove("panning");
  };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);
  svg.addEventListener("dblclick", e => {       // dbl-click a node releases it back to layout
    const ng = e.target.closest && e.target.closest(".node");
    if (ng) {
      const id = ng.getAttribute("data-id");
      manualPos.delete(id);
      const [tx, ty] = kfPos(shownKf, id);
      setPos(id, tx, ty); repathEdges(); updateTitles();
      e.stopPropagation();
      return;
    }
    fit();
  });
})();
fit();

/* ---------- per-step world states (seek + back-step) ---------- */
const STATES = (() => {
  const states = [];
  let nodes = new Map(), edges = new Map(), badges = new Map(), note = null;
  for (const st of DATA.steps) {
    nodes = new Map([...nodes].map(([k, v]) => [k, { ...v }]));
    edges = new Map(edges); badges = new Map(badges);
    for (const op of st.ops) {
      if (op.op === "node_add") nodes.set(op.id, { label: op.label, state: "default" });
      else if (op.op === "node_remove") nodes.delete(op.id);
      else if (op.op === "edge_set") edges.set(op.key, { src: op.src, dst: op.dst, slot: op.slot, w: op.w });
      else if (op.op === "edge_unset") edges.delete(op.key);
      else if (op.op === "edge_flip") { edges.delete(op.from_key); edges.set(op.key, { src: op.src, dst: op.dst, slot: op.slot }); }
      else if (op.op === "badge_set") { op.dst ? badges.set(op.slot, op.dst) : badges.delete(op.slot); }
      else if (op.op === "value_set") { const n = nodes.get(op.id); if (n) n.label = op.new; }
      else if (op.op === "state_set") { const n = nodes.get(op.id); if (n) n.state = op.state; }
      else if (op.op === "note") note = op.text || null;
    }
    states.push({ nodes, edges, badges, note, kf: st.kf });
  }
  return states;
})();

/* ---------- DOM helpers ---------- */
function el(name, attrs, parent) {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
const gEdges = el("g", { id: "g-edges" }, svg);
const gNodes = el("g", { id: "g-nodes" }, svg);
const gOver = el("g", { id: "g-over" }, svg);
(function defs() {
  const d = el("defs", {}, svg);
  for (const [id, cls] of [["arrow", "arrow"], ["arrow-flip", "arrow flip"]]) {
    const m = el("marker", { id, viewBox: "0 0 10 10", refX: 8.5, refY: 5, markerWidth: 8.5, markerHeight: 8.5, orient: "auto-start-reverse" }, d);
    el("path", { d: "M0,0 L10,5 L0,10 z", class: cls }, m);
  }
})();

const nodeEls = new Map(), edgeEls = new Map(), badgeEls = new Map();
const curPos = new Map();

function ease(p) { return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; }
function tween(dur, fn) {
  return new Promise(res => {
    const t0 = performance.now();
    (function f(t) {
      const p = Math.min(1, (t - t0) / dur);
      fn(ease(p));
      p < 1 ? requestAnimationFrame(f) : res();
    })(t0);
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const D = ms => ms / speed;

/* ---------- nodes ---------- */
function fitLabel(textEl, avail) {
  // scale text down to fit the shape's inner width; never below a legible floor
  textEl.style.fontSize = "17px";
  const w = textEl.getComputedTextLength();
  if (w > avail) textEl.style.fontSize = Math.max(9, 17 * avail / w).toFixed(1) + "px";
}
function makeNode(id, pos, label, state) {
  const meta = DATA.nodes[id] || {};
  const g = el("g", { class: "node", "data-state": state || "default", "data-id": id }, gNodes);
  let shape, avail;
  if (meta.shape === "cell") {
    shape = el("rect", { x: -U * 0.5, y: -U * 0.5, width: U, height: U, rx: +T["--radius"] }, g);
    avail = U * 0.84;
  } else if (meta.shape === "pill") {
    const pw = Math.max(R * 2.5, String(label).length * 8.5 + 16);
    shape = el("rect", { x: -pw / 2, y: -R, width: pw, height: R * 2, rx: R }, g);
    avail = pw - 14;
  } else {
    shape = el("circle", { r: R }, g);
    avail = R * 1.7;
  }
  shape.classList.add("shape");
  const text = el("text", { class: "nlabel", "text-anchor": "middle", dy: "0.35em" }, g);
  text.textContent = label;
  fitLabel(text, avail);
  g.setAttribute("transform", `translate(${pos[0]},${pos[1]})`);
  nodeEls.set(id, { g, shape, text });
  curPos.set(id, [...pos]);
  return nodeEls.get(id);
}
function setPos(id, x, y) {
  const n = nodeEls.get(id);
  if (n) n.g.setAttribute("transform", `translate(${x},${y})`);
  curPos.set(id, [x, y]);
}

/* ---------- structure titles (ga.graph(title=...) / @node(graph="name")) ---------- */
const structTitles = {};
for (const [sid, s] of Object.entries(DATA.structs || {})) if (s.title) structTitles[sid] = s.title;
const titleEls = new Map();
function updateTitles() {
  for (const [sid, title] of Object.entries(structTitles)) {
    const ids = (structMembers[sid] || []).filter(id => curPos.has(id));
    let t = titleEls.get(sid);
    if (!ids.length) { if (t) { t.remove(); titleEls.delete(sid); } continue; }
    let minx = Infinity, miny = Infinity, maxx = -Infinity;
    for (const id of ids) { const [x, y] = curPos.get(id); minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); }
    if (!t) { t = el("text", { class: "stitle", "text-anchor": "middle" }, gOver); t.textContent = title; titleEls.set(sid, t); }
    t.setAttribute("x", (minx + maxx) / 2);
    t.setAttribute("y", miny - R - 20);
  }
}

/* ---------- edges ---------- */
function isCustomSlot(slot) {
  return slot && slot !== "next" && slot !== "prev" && slot !== "edge" && !slot.startsWith("child");
}
function edgePath(key, src, dst, slot) {
  let [x1, y1] = curPos.get(src) || kfPos(0, src);
  let [x2, y2] = curPos.get(dst) || kfPos(0, dst);
  const dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy) || 1;
  const r1 = R * 1.05, r2 = R * 1.25;
  if (isCustomSlot(slot)) {
    const lift = U * 0.55 + d * 0.12;
    if (d < 1.5) { // self-loop
      return `M${x1 - r1 * 0.5},${y1 + r1} C${x1 - U},${y1 + U * 1.4} ${x1 + U},${y1 + U * 1.4} ${x2 + r2 * 0.5},${y2 + r2}`;
    }
    return `M${x1},${y1 + r1} Q${(x1 + x2) / 2},${(y1 + y2) / 2 + r1 + lift} ${x2},${y2 + r2}`;
  }
  const backward = (slot === "next" || slot === "prev") && x2 < x1 && Math.abs(dy) < U;
  if (backward) {
    const lift = U * 0.9;
    return `M${x1},${y1 - r1} Q${(x1 + x2) / 2},${y1 - r1 - lift} ${x2},${y2 - r2}`;
  }
  const sx = x1 + dx / d * r1, sy = y1 + dy / d * r1;
  const tx = x2 - dx / d * r2, ty = y2 - dy / d * r2;
  return `M${sx},${sy} L${tx},${ty}`;
}
function makeEdge(key, src, dst, slot, w) {
  const p = el("path", { class: "edge", d: edgePath(key, src, dst, slot), "marker-end": "url(#arrow)" }, gEdges);
  edgeEls.set(key, { el: p, src, dst, slot });
  const labelText = (w !== undefined && w !== null) ? w : (isCustomSlot(slot) ? slot : null);
  if (labelText !== null) {
    const t = el("text", { class: "ew", "text-anchor": "middle" }, gEdges);
    t.textContent = labelText;
    edgeEls.get(key).wEl = t;
    placeEdgeLabel(edgeEls.get(key));
  }
  return edgeEls.get(key);
}
function dropEdge(key) {
  const e = edgeEls.get(key);
  if (!e) return;
  e.el.remove(); if (e.wEl) e.wEl.remove();
  edgeEls.delete(key);
}
function placeEdgeLabel(e) {
  const [x1, y1] = curPos.get(e.src), [x2, y2] = curPos.get(e.dst);
  const below = isCustomSlot(e.slot);
  const d = Math.hypot(x2 - x1, y2 - y1);
  const dy = below ? (R + U * 0.34 + d * 0.07 + 12) : -6;
  e.wEl.setAttribute("x", (x1 + x2) / 2);
  e.wEl.setAttribute("y", (y1 + y2) / 2 + dy);
}
function repathEdges() {
  for (const e of edgeEls.values()) {
    e.el.setAttribute("d", edgePath(null, e.src, e.dst, e.slot));
    if (e.wEl) placeEdgeLabel(e);
  }
}
async function drawOn(path, dur) {
  const len = path.getTotalLength();
  path.style.strokeDasharray = len;
  path.style.strokeDashoffset = len;
  await tween(dur, p => { path.style.strokeDashoffset = len * (1 - p); });
  path.style.strokeDasharray = path.style.strokeDashoffset = "";
}
async function drawOff(path, dur) {
  const len = path.getTotalLength();
  path.style.strokeDasharray = len;
  await tween(dur, p => { path.style.strokeDashoffset = -len * p; });
}

/* ---------- animation primitives ---------- */
const PRIM = {
  async node_add(op, st) {
    const n = makeNode(op.id, kfPos(st.kf, op.id), op.label, "default");
    n.g.classList.add("enter");
    n.g.getBoundingClientRect();
    n.g.classList.remove("enter");
    updateTitles();
    await sleep(D(450));
  },
  async node_remove(op) {
    const n = nodeEls.get(op.id);
    if (!n) return;
    n.g.classList.add("exit");
    await sleep(D(350));
    n.g.remove(); nodeEls.delete(op.id);
    updateTitles();
  },
  async edge_set(op) {
    const e = makeEdge(op.key, op.src, op.dst, op.slot, op.w);
    await drawOn(e.el, D(450));
  },
  async edge_unset(op) {
    const e = edgeEls.get(op.key);
    if (!e) return;
    await drawOff(e.el, D(300));
    dropEdge(op.key);
  },
  async edge_flip(op) {
    const e = makeEdge(op.key, op.src, op.dst, op.slot);
    e.el.classList.add("flip");
    e.el.setAttribute("marker-end", "url(#arrow-flip)");
    const old = edgeEls.get(op.from_key);
    const jobs = [drawOn(e.el, D(600))];
    if (old && old !== e) jobs.push(drawOff(old.el, D(600)).then(() => dropEdge(op.from_key)));
    await Promise.all(jobs);
    setTimeout(() => { e.el.classList.remove("flip"); e.el.setAttribute("marker-end", "url(#arrow)"); }, D(900));
  },
  async read(op) {
    const pos = curPos.get(op.id);
    if (!pos) return;
    const c = el("circle", { class: "pulse", cx: pos[0], cy: pos[1], r: R }, gOver);
    await tween(D(350), p => { c.setAttribute("r", R * (1 + p * 0.8)); c.style.opacity = 0.8 * (1 - p); });
    c.remove();
  },
  async compare(op) {
    const jobs = [PRIM.read({ id: op.a })];
    if (op.b) jobs.push(PRIM.read({ id: op.b }));
    const pos = curPos.get(op.a);
    if (pos) {
      const t = el("text", { class: "cmp", x: pos[0], y: pos[1] - R - 14, "text-anchor": "middle" }, gOver);
      t.textContent = `${op.a_repr} ${op.sym} ${op.b_repr}  ${op.result ? "✓" : "✗"}`;
      jobs.push(tween(D(700), p => {
        t.setAttribute("y", pos[1] - R - 14 - p * 10);
        t.style.opacity = p < 0.7 ? 1 : (1 - p) / 0.3;
      }).then(() => t.remove()));
    }
    await Promise.all(jobs);
  },
  async value_set(op) {
    const n = nodeEls.get(op.id);
    if (!n) return;
    await tween(D(150), p => { n.text.style.opacity = 1 - p; });
    n.text.textContent = op.new;
    n.g.classList.add("vchange");
    await tween(D(250), p => { n.text.style.opacity = p; });
    setTimeout(() => n.g.classList.remove("vchange"), D(500));
  },
  async state_set(op) {
    const n = nodeEls.get(op.id);
    if (n) n.g.setAttribute("data-state", op.state);
    await sleep(D(350));
  },
  async badge_set(op) {
    placeStructBadge(op.slot, op.dst, true);
    await sleep(D(300));
  },
  async note(op) {
    setCaption(op.text);
    await sleep(D(250));
  },
};

/* ---------- caption (ga.note) ---------- */
const captionEl = document.getElementById("caption");
function setCaption(text) {
  captionEl.textContent = text || "";
  captionEl.classList.toggle("show", !!text);
}

/* ---------- badges (head/root + debug var refs/indices) ---------- */
function badge(name, cls) {
  let b = badgeEls.get(name);
  if (!b) {
    const g = el("g", { class: "badge " + cls }, gOver);
    const rect = el("rect", { rx: 6, height: 18, y: -13 }, g);
    const text = el("text", { "text-anchor": "middle", dy: "0.05em" }, g);
    text.textContent = name;
    const w = Math.max(name.length * 7.5 + 10, 22);
    rect.setAttribute("width", w); rect.setAttribute("x", -w / 2);
    b = { g, x: null, y: null };
    badgeEls.set(name, b);
  }
  return b;
}
function moveBadge(b, x, y, animate) {
  if (b.x === null || !animate) {
    b.g.setAttribute("transform", `translate(${x},${y})`);
    b.x = x; b.y = y;
    return Promise.resolve();
  }
  const [fx, fy] = [b.x, b.y];
  b.x = x; b.y = y;
  return tween(D(400), p => {
    b.g.setAttribute("transform", `translate(${fx + (x - fx) * p},${fy + (y - fy) * p})`);
  });
}
function placeStructBadge(slot, dst, animate) {
  const name = "⟶ " + slot;
  if (!dst) { const b = badgeEls.get(name); if (b) { b.g.remove(); badgeEls.delete(name); } return; }
  const pos = curPos.get(dst) || [PAD, PAD];
  moveBadge(badge(name, "sbadge"), pos[0], pos[1] - R - 38, animate);
}
const structMembers = {};
for (const [id, n] of Object.entries(DATA.nodes)) {
  if (n.struct) (structMembers[n.struct] = structMembers[n.struct] || []).push(id);
}
function updateVarBadges(vars, animate) {
  if (!DATA.meta.debug) return;
  const want = new Set();
  const perNode = {};
  for (const v of vars) {
    if (v.kind === "ref" && v.target && nodeEls.has(v.target)) {
      want.add(v.name);
      const stack = perNode[v.target] = perNode[v.target] || [];
      stack.push(v.name);
      const pos = curPos.get(v.target);
      moveBadge(badge(v.name, "vbadge"), pos[0], pos[1] - R - 16 - (stack.length - 1) * 22, animate);
    } else if (v.kind === "index" && v.struct) {
      const cells = structMembers[v.struct] || [];
      const i = parseInt(v.repr, 10);
      if (isNaN(i) || !cells.length) continue;
      want.add(v.name);
      const cell = cells[Math.min(Math.max(i, 0), cells.length - 1)];
      const pos = curPos.get(cell) || kfPos(0, cell);
      const x = i >= cells.length ? pos[0] + U : pos[0];
      moveBadge(badge(v.name, "ibadge"), x, pos[1] + U * 0.5 + 16, animate);
    }
  }
  for (const [name, b] of badgeEls) {
    if (!name.startsWith("⟶") && !want.has(name)) { b.g.remove(); badgeEls.delete(name); }
  }
}

/* ---------- keyframe motion ---------- */
let shownKf = -1;
async function moveToKf(kf, animate) {
  if (kf === shownKf) return;
  shownKf = kf;
  const moves = [];
  for (const id of nodeEls.keys()) {
    const [tx, ty] = kfPos(kf, id);
    const [fx, fy] = curPos.get(id);
    if (fx !== tx || fy !== ty) moves.push([id, fx, fy, tx, ty]);
  }
  if (!moves.length) { updateTitles(); return; }
  if (!animate) {
    for (const [id, , , tx, ty] of moves) setPos(id, tx, ty);
    repathEdges(); updateTitles();
    return;
  }
  await tween(D(500), p => {
    for (const [id, fx, fy, tx, ty] of moves) setPos(id, fx + (tx - fx) * p, fy + (ty - fy) * p);
    repathEdges(); updateTitles();
  });
}

/* ---------- panel / controls ---------- */
const $ = id => document.getElementById(id);
const IC = {
  prev: '<svg viewBox="0 0 24 24"><path d="M7 6h2.3v12H7zM17.5 6v12L9.8 12z"/></svg>',
  next: '<svg viewBox="0 0 24 24"><path d="M14.7 6H17v12h-2.3zM6.5 6v12l7.7-6z"/></svg>',
  play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><path d="M7 5h3.4v14H7zm6.6 0H17v14h-3.4z"/></svg>'
};
function setPlay(on) { $("playbtn").innerHTML = on ? IC.pause : IC.play; }
function nodeLabel(id) {
  const live = STATES[idx] && STATES[idx].nodes.get(id);
  return (live && live.label) || (DATA.nodes[id] && DATA.nodes[id].label) || id;
}
function esc(s) { return String(s ?? "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

/* per-step changes shown under the code (the "what just happened" feed) */
function traceFacts(st, prev) {
  const f = [];
  const top = st.stack[st.stack.length - 1];
  const ptop = prev && prev.stack[prev.stack.length - 1];
  if (st.stack.length > (prev ? prev.stack.length : 0) && top)
    f.push(["call", "→ " + top.fn + top.args]);
  if (prev && st.stack.length < prev.stack.length && ptop)
    f.push(["call", "← return from " + ptop.fn]);
  if (prev && top && ptop && top.fid === ptop.fid
      && st.line != null && prev.line != null && st.line < prev.line)
    f.push(["loop", "↻ next iteration"]);
  for (const op of st.ops) {
    if (op.op === "compare")
      f.push(["cmp", `${op.a_repr} ${op.sym} ${op.b_repr} → ${op.result}`]);
    else if (op.op === "value_set")
      f.push(["mut", `${op.old} → ${op.new}`]);
    else if (op.op === "edge_flip")
      f.push(["mut", `${nodeLabel(op.src)} ${op.slot} ⇄ ${nodeLabel(op.dst)}`]);
    else if (op.op === "edge_set")
      f.push(["mut", `${nodeLabel(op.src)}.${op.slot} → ${nodeLabel(op.dst)}`]);
    else if (op.op === "edge_unset")
      f.push(["mut", `${nodeLabel(op.src)}.${op.slot} → ∅`]);
    else if (op.op === "node_add")
      f.push(["mut", `+ ${op.label}`]);
    else if (op.op === "node_remove")
      f.push(["mut", `− ${nodeLabel(op.id)}`]);
    else if (op.op === "state_set" && op.state !== "default")
      f.push(["state", `${nodeLabel(op.id)} → ${op.state}`]);
    else if (op.op === "badge_set")
      f.push(["mut", `${op.slot} → ${op.dst ? nodeLabel(op.dst) : "∅"}`]);
    else if (op.op === "note" && op.text)
      f.push(["note", op.text]);
  }
  for (const name of st.chg || []) {
    const v = st.vars.find(x => x.name === name);
    if (v) f.push(["var", `${name} = ${v.repr}`]);
  }
  return f;
}

/* the left pane: the function source, line numbers, current line highlighted */
function buildCode() {
  const code = (DATA.meta && DATA.meta.code) || [];
  const host = $("code");
  if (!code.length) { host.innerHTML = '<div class="cline dim">source unavailable</div>'; return; }
  host.innerHTML = code.map(([ln, text]) =>
    `<div class="cline" id="L${ln}"><span class="ln">${ln}</span><span class="lt">${esc(text) || " "}</span></div>`
  ).join("");
}
let litLines = [];
function highlightStep(st) {
  for (const e of litLines) e.classList.remove("active", "via");
  litLines = [];
  for (const v of st.via || []) {
    const e = $("L" + v);
    if (e) { e.classList.add("via"); litLines.push(e); }
  }
  const cur = st.line != null ? $("L" + st.line) : null;
  if (cur) {
    cur.classList.add("active"); litLines.push(cur);
    cur.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function updatePanel(st) {
  $("counter").textContent = `${st.i + 1} / ${DATA.steps.length}`;
  $("steplabel").textContent =
    (st.label ? st.label + " · " : "") + (st.line ? "line " + st.line : "");
  $("scrub").value = st.i;

  highlightStep(st);
  const facts = traceFacts(st, st.i ? DATA.steps[st.i - 1] : null);
  $("changes").innerHTML = facts.length
    ? facts.map(([cls, text]) => `<div class="fact ${cls}">${esc(text)}</div>`).join("")
    : '<div class="fact dim">no change</div>';

  if (!DATA.meta.debug) return;

  const vars = st.vars || [];
  const refs = vars.filter(v => v.kind !== "index");
  const iters = vars.filter(v => v.kind === "index");
  $("vars").innerHTML = refs.map(v =>
    `<tr class="k-${v.kind}"><td class="vn">${esc(v.name)}</td><td class="vv">${esc(v.repr)}</td></tr>`).join("")
    || '<tr><td class="dim">—</td></tr>';
  $("iters").innerHTML = iters.map(v =>
    `<div class="iter">${esc(v.name)} = ${esc(v.repr)}</div>`).join("")
    || '<div class="iter dim">—</div>';

  const live = STATES[st.i].nodes;
  const states = [];
  for (const [id, n] of live) if (n.state && n.state !== "default") states.push([n.label, n.state]);
  $("states").innerHTML = states.length
    ? states.map(([label, s]) => `<div class="nstate s-${s}"><span class="dot"></span>${esc(label)} <span class="sn">${s}</span></div>`).join("")
    : '<div class="nstate dim">—</div>';

  $("stack").innerHTML = [...st.stack].reverse().map((f, i) =>
    `<div class="frame${i === 0 ? " top" : ""}">${esc(f.fn)}${esc(f.args)}</div>`).join("")
    || '<div class="frame dim">—</div>';
}

/* ---------- step engine ---------- */
let idx = -1, playing = false, token = 0;

async function animateStep(i) {
  const st = DATA.steps[i];
  idx = i;
  updatePanel(st);
  await moveToKf(st.kf, true);
  await Promise.all(st.ops.map(op => (PRIM[op.op] || (async () => {}))(op, st)));
  updateVarBadges(st.vars, true);
  updateTitles();
}

function renderState(i) {
  idx = i;
  const s = STATES[i], st = DATA.steps[i];
  gNodes.innerHTML = ""; gEdges.innerHTML = ""; gOver.innerHTML = "";
  nodeEls.clear(); edgeEls.clear(); badgeEls.clear(); curPos.clear(); titleEls.clear();
  shownKf = s.kf;
  for (const [id, n] of s.nodes) makeNode(id, kfPos(s.kf, id), n.label, n.state);
  for (const [key, e] of s.edges) makeEdge(key, e.src, e.dst, e.slot, e.w);
  for (const [slot, dst] of s.badges) placeStructBadge(slot, dst, false);
  setCaption(s.note);
  updateVarBadges(st.vars, false);
  updateTitles();
  updatePanel(st);
}

async function play() {
  if (playing) { playing = false; return; }
  playing = true;
  setPlay(true);
  const my = ++token;
  if (idx >= DATA.steps.length - 1) renderState(0);
  while (playing && token === my && idx < DATA.steps.length - 1) {
    await animateStep(idx + 1);
    await sleep(D(140));
  }
  if (token === my) { playing = false; setPlay(false); }
}
function pause() { playing = false; token++; setPlay(false); }

function bind() {
  $("fitbtn").innerHTML =
    '<svg viewBox="0 0 24 24"><path d="M4 9V4h5v2H6v3H4zm16 0h-2V6h-3V4h5v5zM4 15h2v3h3v2H4v-5zm14 3v-3h2v5h-5v-2h3z"/></svg>';
  $("fitbtn").onclick = fit;
  $("prevbtn").innerHTML = IC.prev;
  $("nextbtn").innerHTML = IC.next;
  setPlay(false);
  $("playbtn").onclick = play;
  $("nextbtn").onclick = async () => { pause(); if (idx < DATA.steps.length - 1) await animateStep(idx + 1); };
  $("prevbtn").onclick = () => { pause(); if (idx > 0) renderState(idx - 1); };
  $("scrub").max = DATA.steps.length - 1;
  $("scrub").oninput = e => { pause(); renderState(+e.target.value); };
  $("speed").onchange = e => { speed = +e.target.value; try { localStorage.setItem("granim-speed", speed); } catch (_) {} };
  try {
    const s = localStorage.getItem("granim-speed");
    if (s) { speed = +s; $("speed").value = s; }
  } catch (_) {}
  document.addEventListener("keydown", e => {
    if (e.key === " ") { e.preventDefault(); play(); }
    else if (e.key === "ArrowRight") $("nextbtn").onclick();
    else if (e.key === "ArrowLeft") $("prevbtn").onclick();
    else if (e.key === "f") fit();
    else if (e.key === "r") { manualPos.clear(); renderState(idx); }  // release all dragged nodes
    else if (e.key === "Home") { pause(); renderState(0); }
    else if (e.key === "End") { pause(); renderState(DATA.steps.length - 1); }
  });
}

bind();
buildCode();
if (!DATA.meta.debug) document.body.classList.add("nodebug");
if (DATA.meta.error) $("steplabel").classList.add("err");
renderState(0);
