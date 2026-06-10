// Headless timeline validation: extract the embedded JSON from each example's
// HTML and replay the same world simulation the player runs, asserting the
// final state is the algorithmically correct one (no browser needed).
const fs = require("fs");
const path = require("path");

function load(file) {
  const html = fs.readFileSync(file, "utf8");
  const m = html.match(/<script type="application\/json" id="granim-data">([\s\S]*?)<\/script>/);
  if (!m) throw new Error("no granim-data in " + file);
  return JSON.parse(m[1].replace(/<\\\//g, "</"));
}

function simulate(data) {
  const nodes = new Map(), edges = new Map();
  for (const st of data.steps) for (const op of st.ops) {
    if (op.op === "node_add") nodes.set(op.id, { label: op.label, state: "default" });
    else if (op.op === "node_remove") nodes.delete(op.id);
    else if (op.op === "edge_set") edges.set(op.key, op);
    else if (op.op === "edge_unset") edges.delete(op.key);
    else if (op.op === "edge_flip") { edges.delete(op.from_key); edges.set(op.key, op); }
    else if (op.op === "value_set") nodes.get(op.id).label = op.new;
    else if (op.op === "state_set") nodes.get(op.id).state = op.state;
  }
  return { nodes, edges };
}

function check(name, cond) {
  if (!cond) { console.error("FAIL  " + name); process.exitCode = 1; }
  else console.log("ok    " + name);
}

const dir = path.join(__dirname, "..", "examples");

// every alive node must have a position in some keyframe
for (const f of fs.readdirSync(dir).filter(f => f.endsWith(".html"))) {
  const data = load(path.join(dir, f));
  const { nodes, edges } = simulate(data);
  const positioned = new Set();
  for (const kf of data.keyframes) for (const id of Object.keys(kf.pos)) positioned.add(id);
  check(f + ": all nodes positioned", [...nodes.keys()].every(id => positioned.has(id)));
  for (const [k, e] of edges) {
    check(f + ": edge endpoints alive (" + k + ")", nodes.has(e.src) && nodes.has(e.dst));
    if (!nodes.has(e.src) || !nodes.has(e.dst)) break;
  }
}

// reversal: final next-edges must run 5->4->3->2->1, with >=1 flip on screen
for (const f of ["reverse_recursive.html", "reverse_iterative.html"]) {
  const data = load(path.join(dir, f));
  const { nodes, edges } = simulate(data);
  const next = {};
  for (const e of edges.values()) if (e.slot === "next") next[nodes.get(e.src).label] = nodes.get(e.dst).label;
  const chain = ["5"]; let cur = "5";
  while (next[cur]) { cur = next[cur]; chain.push(cur); }
  check(f + ": final chain 5->1", chain.join("") === "54321");
  const flips = data.steps.flatMap(s => s.ops).filter(o => o.op === "edge_flip").length;
  check(f + ": " + flips + " flips", flips === 4);
}

// bfs: all nodes end 'done', at least one parallel frontier step
{
  const data = load(path.join(dir, "bfs.html"));
  const { nodes } = simulate(data);
  check("bfs: all done", [...nodes.values()].every(n => n.state === "done"));
  const parallel = data.steps.some(s => s.ops.filter(o => o.op === "state_set" && o.state === "frontier").length >= 2);
  check("bfs: parallel frontier step", parallel);
}

// bst: 9 nodes, 8 child edges
{
  const data = load(path.join(dir, "build_bst.html"));
  const { nodes, edges } = simulate(data);
  check("bst: 9 nodes", nodes.size === 9);
  check("bst: 8 edges", [...edges.values()].filter(e => e.slot.startsWith("child")).length === 8);
}

console.log(process.exitCode ? "\nFAILURES" : "\nall timeline checks passed");
