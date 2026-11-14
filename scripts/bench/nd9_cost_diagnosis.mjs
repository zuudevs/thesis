/**
 * nd9_cost_diagnosis.mjs — component-bound cost diagnosis of the ze_json
 * wasm64 on-demand count path (ND-9; design:
 * docs/measurement/nd9-parser-cost-diagnosis.md).
 *
 * DIAGNOSIS, NOT optimization. No core/scanner/ABI code is touched; every
 * stage is measured through exports that already exist. Stacked stages are
 * reported as bounds, never force-subtracted: s2-open inseparably contains
 * the arena carve + structural scan + bracket match (one pass), so "open"
 * time is an upper bound for each of those components.
 *
 * One full cycle per document (order fixed by data dependency):
 *   s1-copy  alloc(src) + writeBytes + alloc(dst)      [binding JS->wasm input]
 *   s2-open  openParser(src, len)                      [arena + scan + match]
 *   s3-count parserRoot(slot) + countElements(slot,ts) [traversal count]
 *   s4-close closeParser(slot) + resetHeap()           [slot + bump rewind]
 * s5-boundary (per round, not per document): micro-loop abiVersion() x N —
 *   the JS/BigInt boxing floor per plain ABI call, 0 arguments.
 *
 * Protocol (mirrors nd6_bench): warmup untimed, 15 independent rounds,
 * document order rotated per round (stage order cannot rotate — data
 * dependency), NO outlier trimming, GC observer counts reported,
 * mean/median/P95/stddev over rounds. CYCLES bracket-samples averaged per
 * round reduce per-stage bracket noise for the microsecond stages.
 *
 * Differential correctness guard: countElements(root) must equal the root
 * child count derived from the V8 reference (array length / object key
 * count) for every document, every cycle — a mismatch voids the run.
 *
 * Record: schema v1.0.0, one results[] entry per (stage, document) plus one
 * for s5. Raw exhibit: out/raw/<run_id>/nd9_stages.json. Filename:
 * <run_id>-nd9-cost-<site>.record.json.
 *
 * @cite 10.1002_spe.3313 — on-demand JSON: component costs are only
 *       interpretable when code, artifact, and corpus identity are pinned
 *       per run (artifact_sha256 + clean-tree gate; AGENTS section 4).
 * @cite 10.14778_3115404.3115416 — Mison: a structural index supports
 *       counting without full materialization; s3 measures what that index
 *       walk actually costs through the C-ABI surface.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { recordFilename, gateDecision, wasmSha256 } from './nd6_protocol.mjs';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

// CLI ----------------------------------------------------------------------
const argv = process.argv.slice(2);
const arg = (name, fallback = undefined) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROUNDS = Number(arg('rounds', 15));
const WARMUP = Number(arg('warmup', 3));
const CYCLES = Number(arg('cycles', 4)); // bracket samples averaged per round
const ABI_CALLS = Number(arg('abi-calls', 4096)); // s5 micro-loop length
const SITE = arg('site', 'dev_device');
const CORPUS_DIR = path.resolve(arg('corpus',
    path.join(ROOT, 'corpus', 'benchmarks', 'saq_payload_v1')));
const OUT_DIR = process.env.OUT_DIR || path.join(ROOT, 'out');

// Binding ze_json (wasm64 C-ABI v3) ----------------------------------------
const BINDING_PATH = process.env.ZE_JSON_BINDING_PATH
    || path.join(ROOT, 'ze_json', 'bindings', 'js', 'ze_json.mjs');
const bindingMod = await import(pathToFileURL(BINDING_PATH).href);
const binding = bindingMod.ZeJson.load();

// Korpus (identik nd6 — tidak diganti) --------------------------------------
const MANIFEST = JSON.parse(
    fs.readFileSync(path.join(CORPUS_DIR, 'MANIFEST.json'), 'utf8'));
const REPO_DEFS = [
    { name: 'courses',      file: 'courses.json',        rootKey: 'courses' },
    { name: 'assistants',   file: 'config_asisten.json', rootKey: 'assistants' },
    { name: 'lecturers',    file: 'lecturers.json',      rootKey: 'lecturers' },
    { name: 'schedules',    file: 'schedules.json',      rootKey: 'schedules' },
    { name: 'reports',      file: 'reports.json',        rootKey: null },
    { name: 'globalConfig', file: 'config_global.json',  rootKey: null },
];
const DOCS = REPO_DEFS.map((def) => {
    const file = path.join(CORPUS_DIR, def.file);
    const bytes = fs.readFileSync(file);
    const v8 = JSON.parse(bytes); // referensi semantik (guard parity)
    const rootChildren = Array.isArray(v8) ? v8.length : Object.keys(v8).length;
    return { ...def, file, bytes, v8, rootChildren };
});
const BYTES_TOTAL = DOCS.reduce((s, d) => s + d.bytes.length, 0);
const manifestSha256 = require('node:crypto')
    .createHash('sha256')
    .update(fs.readFileSync(path.join(CORPUS_DIR, 'MANIFEST.json')))
    .digest('hex');

// GC observer (dilaporkan, bukan disembunyikan) — pola nd6 -----------------
const gcCounts = { minor: 0, major: 0, other: 0 };
let gcObserver = null;
if (global.gc) {
    const { PerformanceObserver } = await import('node:perf_hooks');
    gcObserver = new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
            const k = e.detail && e.detail.kind;
            if (k === 1) gcCounts.minor += 1;
            else if (k === 2) gcCounts.major += 1;
            else gcCounts.other += 1;
        }
    });
    gcObserver.observe({ entryTypes: ['gc'], buffered: false });
}

// Statistik ----------------------------------------------------------------
const mean = (xs) => xs.reduce((s, x) => s + x, 0) / xs.length;
const stddev = (xs) => {
    const m = mean(xs);
    return Math.sqrt(xs.reduce((s, x) => s + (x - m) ** 2, 0) / xs.length);
};
const median = (xs) => {
    const s = [...xs].sort((a, b) => a - b);
    return s.length % 2 ? s[(s.length - 1) / 2]
        : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};
const percentile = (xs, p) => { // interpolasi linier (tanpa trimming)
    const s = [...xs].sort((a, b) => a - b);
    const idx = (p / 100) * (s.length - 1);
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    return s[lo] + (idx - lo) * (s[hi] - s[lo]);
};

// Rationale per stage (sinkron @cite di header) -----------------------------
const RATIONALE = {
    's1-copy': 'Stage 1: input alloc + copy JS->wasm (ze_alloc x2 + Uint8Array.set; binding L159-169/L371-372) — the fixed input side of every count call.',
    's2-open': 'Stage 2: ze_parser_open — arena carve (3x len*8 upper bound) + Document::open (structural scan + bracket match in ONE pass; document.cpp L234-259). Inseparable: reported as a bound, never decomposed.',
    's3-count': 'Stage 3: parserRoot + ze_count_elements — index-walk traversal count through the C-ABI surface (cost per direct child + framing; NOT assumed O(1) per ABI call).',
    's4-close': 'Stage 4: ze_parser_close + ze_reset_heap — slot release + bump rewind (cabi.cpp L118-123/L461-462; no individual free).',
    's5-boundary': 'Stage 5: JS/BigInt boxing floor per plain ABI call (abiVersion x 4096 micro-loop, 0 args) — the cross-boundary cost every parser call pays.',
};

// EKSEKUSI ------------------------------------------------------------------
const rawRounds = []; // exhibit mentah
const results = [];
const gcAtStart = { ...gcCounts };
let SINK; // anti dead-code elimination
let parityChecks = 0;

const STAGES = ['s1-copy', 's2-open', 's3-count', 's4-close'];

/** One timed stage bracket; returns {dt: ms, out: stage value}. */
const bracket = (fn) => {
    const t0 = performance.now();
    const out = fn();
    return { dt: performance.now() - t0, out };
};

/**
 * runCycle(doc, sums) — one full s1..s4 cycle for `doc`; each stage time is
 * added to `sums` (ms). Returns the countElements verdict for the parity
 * guard. The cycle IS the unit of accounting: after s4 the bump heap is
 * rewound, so the next cycle starts from a clean heap.
 */
function runCycle(doc, sums) {
    // s1: input alloc + copy (2 alloc + direct memory write)
    let srcPtr;
    let dstPtr;
    sums['s1-copy'] += bracket(() => {
        srcPtr = binding.alloc(doc.bytes.length);
        binding.writeBytes(srcPtr, doc.bytes);
        dstPtr = binding.alloc(doc.bytes.length * 8);
    }).dt;

    // s2: open (arena + scan + match, inseparable)
    let slot;
    sums['s2-open'] += bracket(() => {
        slot = binding.openParser(srcPtr, doc.bytes.length);
        if (!slot.ok) throw new Error(`open failed: ${slot.error}`);
    }).dt;

    // s3: root frame + traversal count (2 ABI calls)
    let count;
    sums['s3-count'] += bracket(() => {
        const root = binding.parserRoot(slot.slot);
        if (!root.ok) throw new Error(`root failed: ${root.error}`);
        const c = binding.countElements(slot.slot, root.ts);
        if (!c.ok) throw new Error(`count failed: ${c.error}`);
        count = c.value;
    }).dt;

    // s4: close slot + bump rewind (2 ABI calls)
    sums['s4-close'] += bracket(() => {
        binding.closeParser(slot.slot);
        binding.resetHeap();
    }).dt;

    return count;
}

/**
 * measureRounds() — warmup untimed, then ROUNDS independent rounds. Per
 * round: CYCLES full cycles per document (rotated order), each stage's
 * bracket times SUMMED then averaged; one s5 boundary micro-loop sample.
 * Parity guard runs on every cycle (parity_checks counted).
 */
function measureRounds() {
    const cellOf = new Map(DOCS.map((d) => [d.name, {
        's1-copy': [], 's2-open': [], 's3-count': [], 's4-close': [], counts: [],
    }]));
    const boundarySamples = [];

    const warmSums = new Map(DOCS.map((d) => [d.name,
        { 's1-copy': 0, 's2-open': 0, 's3-count': 0, 's4-close': 0 }]));
    for (let w = 0; w < WARMUP; w += 1) { // warmup untimed (pola nd6)
        for (const doc of DOCS) runCycle(doc, warmSums.get(doc.name));
        SINK = binding.abiVersion();
    }

    for (let r = 0; r < ROUNDS; r += 1) {
        // Alternating pada dimensi yang sah: urutan DOKUMEN dirotasi per
        // ronde. Urutan stage tidak bisa dirotasi (data dependency
        // s1->s4); dinyatakan di notes record.
        const off = r % DOCS.length;
        const order = DOCS.slice(off).concat(DOCS.slice(0, off));
        for (const doc of order) {
            const cell = cellOf.get(doc.name);
            const sums = { 's1-copy': 0, 's2-open': 0, 's3-count': 0, 's4-close': 0 };
            for (let c = 0; c < CYCLES; c += 1) {
                const count = runCycle(doc, sums);
                if (count !== doc.rootChildren) {
                    throw new Error(`parity guard FAILED: ${doc.name} `
                        + `ze count=${count} v8 root children=${doc.rootChildren}`);
                }
                cell.counts.push(count);
                parityChecks += 1;
            }
            for (const stage of STAGES) {
                cell[stage].push(Number((sums[stage] / CYCLES).toPrecision(9)));
            }
        }
        // s5: per-call ABI boundary floor (micro-loop, 0 args)
        const { dt } = bracket(() => {
            let v = 0;
            for (let i = 0; i < ABI_CALLS; i += 1) v += binding.abiVersion();
            return v;
        });
        boundarySamples.push(Number((dt / ABI_CALLS).toPrecision(9))); // ms/call
    }
    if (SINK === undefined) throw new Error('undefined sink');

    for (const doc of DOCS) {
        const cell = cellOf.get(doc.name);
        for (const stage of STAGES) {
            rawRounds.push({
                doc: doc.name,
                stage,
                cycles_per_round: CYCLES,
                rounds_ms: cell[stage],
            });
        }
    }
    rawRounds.push({
        doc: null,
        stage: 's5-boundary',
        abi_calls_per_sample: ABI_CALLS,
        rounds_ms: boundarySamples,
    });
    return { cellOf, boundarySamples };
}

const STAGE_ABI = {
    's1-copy': { abi_calls: 2, note: 'alloc x2 + Uint8Array.set (direct write, not an ABI export)' },
    's2-open': { abi_calls: 1, note: 'inseparable arena+scan+match bound' },
    's3-count': { abi_calls: 2, note: 'parserRoot + countElements' },
    's4-close': { abi_calls: 2, note: 'closeParser + resetHeap' },
    's5-boundary': { abi_calls: ABI_CALLS, note: `micro-loop x${ABI_CALLS}, 0 args` },
};

function pushStageResult(doc, stage, roundsMs) {
    const perOpS = mean(roundsMs) / 1000;
    const bytes = doc ? doc.bytes.length : 0;
    const isBoundary = stage === 's5-boundary';
    results.push({
        name: isBoundary ? `nd9/${stage}` : `nd9/${stage}/${doc.name}`,
        engine: 'wasm64_cabi',
        status: 'ok',
        rationale: {
            purpose: RATIONALE[stage],
            basis_papers: ['10.1002_spe.3313', '10.14778_3115404.3115416'],
        },
        metrics: {
            seconds_mean: Number(perOpS.toPrecision(9)),
            ...(isBoundary ? {} : {
                seconds_stddev: Number((stddev(roundsMs) / 1000).toPrecision(6)),
                bytes_per_second: Number((bytes / perOpS).toPrecision(9)),
                documents_per_second: Number((1 / perOpS).toPrecision(9)),
            }),
        },
        extras: {
            stage,
            doc: doc ? doc.name : null,
            doc_bytes: bytes,
            seconds_median: Number((median(roundsMs) / 1000).toPrecision(9)),
            seconds_p95: Number((percentile(roundsMs, 95) / 1000).toPrecision(9)),
            rounds: ROUNDS,
            cycles_per_round: isBoundary ? 1 : CYCLES,
            gc_minor: gcCounts.minor - gcAtStart.minor, // kumulatif sejak start
            gc_major: gcCounts.major - gcAtStart.major,
            parity_checks: isBoundary ? null : parityChecks,
            ...STAGE_ABI[stage],
        },
    });
}

// Metadata host/git ---------------------------------------------------------
// Definisi dirty: modifikasi file TRACKED (+ mismatch pointer submodule).
// File untracked milik pemilik tidak memengaruhi kode yang diukur —
// dicatat transparan, tidak menodai hash (rencana ND-6 §3.9).
const git = (cmd) => String(execSync(cmd, { cwd: ROOT })).trim();
const dirtyTracked = (dir) => git(`git -C ${dir} status --porcelain `
    + '--untracked-files=no').length > 0;
const untrackedOwnerFiles = git('git status --porcelain')
    .split('\n').filter((l) => l.startsWith('??'))
    .map((l) => l.slice(3).trim()).filter(Boolean);
const ROOT_HASH = git('git rev-parse --short HEAD');
const DIRTY = dirtyTracked('.');
const zeHash = git('git -C ze_json rev-parse --short HEAD');
const saqHash = git('git -C saq-report rev-parse --short HEAD');
const zeDirty = dirtyTracked('ze_json');
const saqDirty = dirtyTracked('saq-report');
// Acceptance gate (protocol §3.9): acceptance runs MUST execute from a clean
// tree (root + both submodules; tracked changes only). Refuse otherwise;
// --allow-dirty produces an exploratory run labeled in the record (never
// acceptance evidence).
const GATE = gateDecision({
    rootDirty: DIRTY, zeDirty, saqDirty,
    allowDirty: argv.includes('--allow-dirty'),
});
if (!GATE.ok) {
    console.error(`[nd9] REFUSED: tracked changes in ${GATE.dirtyRepos.join(', ')} `
        + '— acceptance runs require a clean tree (protocol §3.9).');
    console.error('[nd9] For an exploratory run add --allow-dirty '
        + '(record config.exploratory=true; NOT acceptance evidence).');
    process.exit(3);
}
const HOSTNAME = os.hostname().replace(/[^A-Za-z0-9._-]/g, '-');
const tsNow = () => {
    const d = new Date();
    const p = (n, w = 2) => String(n).padStart(w, '0');
    return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}`
        + `${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}`;
};
const RUN_ID = `${HOSTNAME}-${tsNow()}-${ROOT_HASH}`; // schema: tanpa suffix
const RAW_DIR = path.join(OUT_DIR, 'raw', RUN_ID);
const MEAS_DIR = path.join(OUT_DIR, 'measurements');
fs.mkdirSync(RAW_DIR, { recursive: true });
fs.mkdirSync(MEAS_DIR, { recursive: true });

const zePkg = (() => {
    try {
        return require(path.join(ROOT, 'ze_json', 'bindings', 'js',
            'package.json'));
    }
    catch { return { version: '0.0.0-unknown', coreVersion: null,
        coreSemver: '0.0.0-unknown' }; }
})();

// Identity of the actually-loaded wasm artifact (cross-site byte-identity).
const WASM_PATH = path.join(path.dirname(BINDING_PATH), 'ze_json.wasm');
const WASM_SHA256 = wasmSha256(WASM_PATH);

const metadata = {
    run_id: RUN_ID,
    experiment: 'ND-9 cost diagnosis',
    site: SITE,
    generator: 'node_harness',
    cmd: `node scripts/bench/nd9_cost_diagnosis.mjs --rounds ${ROUNDS} `
        + `--warmup ${WARMUP} --cycles ${CYCLES} --abi-calls ${ABI_CALLS} `
        + `--site ${SITE}`,
    host: {
        hostname: HOSTNAME,
        os: `${os.type()} ${os.release()}`,
        arch: os.arch(),
        cpu_model: os.cpus()[0].model,
        cpu_cores: os.cpus().length,
        ram_gb: Number((os.totalmem() / 2 ** 30).toFixed(1)),
        toolchain: `node ${process.version} (v8 ${process.versions.v8}) `
            + `+ ze_json wasm64 (ABI ${zePkg.coreVersion})`,
    },
    git: {
        root: { hash: ROOT_HASH, dirty: DIRTY },
        ze_json: { hash: zeHash, dirty: zeDirty },
        saq_report: { hash: saqHash, dirty: saqDirty },
        untracked_owner_files_ignored: untrackedOwnerFiles,
    },
    corpus: {
        dir: CORPUS_DIR,
        manifest_sha256: manifestSha256,
        document_count: MANIFEST.document_count,
        total_bytes: MANIFEST.total_bytes,
    },
    artifact: {
        wasm_path: WASM_PATH,
        wasm_sha256: WASM_SHA256, // null when the artifact was not found
    },
    gate: {
        clean: GATE.dirtyRepos.length === 0,
        dirty_repos: GATE.dirtyRepos,
        exploratory: GATE.exploratory,
    },
    protocol: {
        rounds: ROUNDS,
        warmup: WARMUP,
        cycles_per_round: CYCLES,
        stage_order: 'fixed by data dependency (s1->s4); document order rotated per round',
        alternating: true,
        outlier_trimming: false,
        gc_exposed: Boolean(global.gc),
        abi_calls_per_boundary_sample: ABI_CALLS,
    },
    gc_at_start: { ...gcAtStart },
    date_utc: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
};
fs.writeFileSync(path.join(RAW_DIR, 'metadata.json'),
    JSON.stringify(metadata, null, 2));

// Jalankan eksperimen -------------------------------------------------------
console.log(`[nd9] cost diagnosis | rounds=${ROUNDS} warmup=${WARMUP} `
    + `cycles=${CYCLES} abi_calls=${ABI_CALLS} site=${SITE}`);
console.log(`[nd9] run_id=${RUN_ID}`);
console.log(`[nd9] corpus=${CORPUS_DIR} (${MANIFEST.document_count} docs, `
    + `${BYTES_TOTAL} B total)`);

const { cellOf, boundarySamples } = measureRounds();

for (const doc of DOCS) {
    const cell = cellOf.get(doc.name);
    for (const stage of STAGES) pushStageResult(doc, stage, cell[stage]);
}
pushStageResult(null, 's5-boundary', boundarySamples);

fs.writeFileSync(path.join(RAW_DIR, 'nd9_stages.json'),
    JSON.stringify({
        metadata,
        raw_rounds: rawRounds,
        parity_checks: parityChecks,
    }, null, 2));

const record = {
    schema_version: '1.0.0',
    kind: 'benchmark',
    run_id: RUN_ID,
    site: SITE,
    generator: 'node_harness',
    library: {
        name: 'ze_json',
        version: `${zePkg.version} (ze_json@${zeHash}${zeDirty ? '-dirty' : ''}, `
            + `saq-report@${saqHash}${saqDirty ? '-dirty' : ''})`,
        language_runtime: `node ${process.version} (v8 ${process.versions.v8}) `
            + `+ wasm64 C-ABI`,
        js_version: zePkg.version,
        core_version: zePkg.coreSemver,
        abi_version: zePkg.coreVersion,
        ...(WASM_SHA256 ? { artifact_sha256: WASM_SHA256 } : {}),
    },
    git_commit: {
        hash: ROOT_HASH + (DIRTY ? '-dirty' : ''),
        dirty: DIRTY,
        repo: 'v5',
    },
    host: metadata.host,
    corpus: {
        name: MANIFEST.corpus_name,
        document_count: MANIFEST.document_count,
        total_bytes: MANIFEST.total_bytes,
        max_document_bytes: MANIFEST.max_document_bytes,
        sha256: manifestSha256,
    },
    config: {
        date_utc: metadata.date_utc,
        iterations: CYCLES,
        warmup_runs: WARMUP,
        repeats: ROUNDS,
        cpu_pinning: false,
        threads: 1,
        exploratory: GATE.exploratory,
        notes: `ND-9 cost diagnosis (5 stages, ${parityChecks} parity checks); `
            + `stage order fixed by data dependency s1->s4, document order `
            + `rotated per round; no outlier trimming; bracket gaps excluded `
            + `(stage times = per-stage averages over ${CYCLES} cycles/round; `
            + `s2-open is an INSEPARABLE bound over arena carve + scan + match); `
            + `s5-boundary = per-call floor over a ${ABI_CALLS}-call micro-loop. `
            + `gc_exposed=${Boolean(global.gc)}; gc(minor=${gcCounts.minor - gcAtStart.minor}, `
            + `major=${gcCounts.major - gcAtStart.major}); raw: out/raw/${RUN_ID}/.`
            + (GATE.exploratory
                ? ` EXPLORATORY run (tracked changes: ${GATE.dirtyRepos.join(', ')}; `
                  + `--allow-dirty) — NOT acceptance evidence.`
                : ''),
    },
    results,
};
const recordFile = path.join(MEAS_DIR,
    recordFilename(RUN_ID, 'cost', SITE, 'nd9'));
fs.writeFileSync(recordFile, JSON.stringify(record, null, 2));

// Ringkasan -----------------------------------------------------------------
console.log(`[nd9] results=${results.length} | parity_checks=${parityChecks} `
    + `| raw -> out/raw/${RUN_ID}/`);
const byStage = new Map();
for (const r of results) {
    const st = r.extras.stage;
    if (!byStage.has(st)) byStage.set(st, []);
    byStage.get(st).push(r.extras.seconds_median);
}
for (const [st, vals] of byStage) {
    const total = vals.reduce((s, x) => s + x, 0);
    console.log(`  ${st.padEnd(12)} Σmedian ${(total * 1000).toFixed(4).padStart(10)} ms/op `
        + `(${vals.length} entries)`);
}
console.log(`[nd9] record -> ${recordFile}`);
console.log(`[nd9] VALIDATE: python scripts/measurement-schema/validate.py ${recordFile}`);
if (gcObserver) gcObserver.disconnect();
