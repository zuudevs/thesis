/**
 * nd6_bench.mjs — matriks benchmark 4 fase A–D (Stage 6, TASKS ND-6).
 *
 * Protokol: docs/measurement/nd6-benchmark-plan.md (disetujui pemilik).
 * Kontrol eksperimen: warmup untimed, ronde independen, alternating
 * (urutan jalur dirotasi per ronde), TANPA buang outlier — semua ronde
 * dilaporkan; agregat mean/median/P95/stddev. Satu run_id per fase;
 * perbandingan baseline↔ze hanya dalam satu run_id (AGENTS §4).
 *
 * Output per eksekusi:
 *   out/raw/<run_id>/nd6_phase_<X>.json        — exhibit mentah (semua ronde)
 *   out/raw/<run_id>/metadata.json             — sidecar host/tool/config
 *   out/measurements/<run_id>-nd6-<x>-...record.json — record schema v1.0.0
 *
 * Record wajib PASS scripts/measurement-schema/validate.py sebelum dipakai.
 *
 * Definisi instrumentasi (extras):
 *   - binding_calls  = jumlah panggilan EKSPOR ABI yang dibuat sisi JS
 *     harness (open/parse/project/lazy-iter/get/type/asString/close/
 *     resetHeap). Internal C++ tidak terlihat dari JS. Untuk jalur fase D
 *     yang melewati lapisan repositori (readCount() internal), nilainya
 *     null (tidak diukur di level ini) — jujur, bukan nol palsu.
 *   - index_count    = jumlah operasi akses struktural yang dibuat harness
 *     (get/count/item-step/kind). Null untuk fase D (alasan sama).
 *   - consumed/skipped_fields = statis dari referensi V8 (definisi di
 *     consumedFields) — bukan counter runtime.
 *
 * @cite 10.1002_spe.3313 on-demand JSON — selective consumption pays only
 *       for visited fields; phases B/C isolate the mechanism (L2 project
 *       vs L1 frame traversal) against the identical V8 consumer.
 * @cite 10.14778_3115404.3115416 Mison — structural index supports
 *       counting without full materialization; phase D counts only.
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
const PHASE = (arg('phase') || '').toUpperCase();
const ROUNDS = Number(arg('rounds', 15));
const WARMUP = Number(arg('warmup', 3));
const SITE = arg('site', 'dev_device');
const CORPUS_DIR = path.resolve(arg('corpus',
    path.join(ROOT, 'corpus', 'benchmarks', 'saq_payload_v1')));
const OUT_DIR = process.env.OUT_DIR || path.join(ROOT, 'out');

const VALID_PHASES = new Set(['A', 'B', 'C', 'D']);
if (!VALID_PHASES.has(PHASE)) {
    console.error('usage: node scripts/bench/nd6_bench.mjs --phase A|B|C|D '
        + '[--rounds 15] [--warmup 3] [--site dev_device] [--corpus <dir>] '
        + '[--allow-dirty]');
    process.exit(2);
}

// Binding ze_json (wasm64 C-ABI v3) ----------------------------------------
const BINDING_PATH = process.env.ZE_JSON_BINDING_PATH
    || path.join(ROOT, 'ze_json', 'bindings', 'js', 'ze_json.mjs');
const bindingMod = await import(pathToFileURL(BINDING_PATH).href);
const binding = bindingMod.ZeJson.load();
const ZeParser = bindingMod.ZeParser;
const closeParser = (parser, cnt) => {
    parser.close();
    cnt.bindingCalls += 2; // close + resetHeap (ekspor ABI)
    binding.resetHeap(); // bump-heap rewind antar iterasi (kontrak batch)
};

// Repositori saq-report (fase D — read-only, file store korpus) ------------
const JsonRepository = require(
    path.join(ROOT, 'saq-report', 'repositories', 'JsonRepository.js'));
const MongoJsonRepository = require(
    path.join(ROOT, 'saq-report', 'repositories', 'MongoJsonRepository.js'));

/** Definisi 6 store — mirror repositories/index.js. */
const REPO_DEFS = [
    { name: 'courses',      file: 'courses.json',        rootKey: 'courses',    defaultValue: [] },
    { name: 'assistants',   file: 'config_asisten.json', rootKey: 'assistants', defaultValue: [] },
    { name: 'lecturers',    file: 'lecturers.json',      rootKey: 'lecturers',  defaultValue: [] },
    { name: 'schedules',    file: 'schedules.json',      rootKey: 'schedules',  defaultValue: [] },
    { name: 'reports',      file: 'reports.json',        rootKey: null,         defaultValue: [] },
    { name: 'globalConfig', file: 'config_global.json',  rootKey: null,         defaultValue: {} },
];
/** Route /rekap memakai 4 repo ini (parity gate ND-5). */
const D_REPOS = ['courses', 'assistants', 'schedules', 'reports'];

// Korpus -------------------------------------------------------------------
const MANIFEST = JSON.parse(
    fs.readFileSync(path.join(CORPUS_DIR, 'MANIFEST.json'), 'utf8'));
const DOCS = REPO_DEFS.map((def) => {
    const file = path.join(CORPUS_DIR, def.file);
    const bytes = fs.readFileSync(file);
    return {
        ...def,
        file,
        bytes,
        text: bytes.toString('utf8'),
        v8: JSON.parse(bytes), // referensi semantik (parity gate ND-5)
    };
});
const BYTES_TOTAL = DOCS.reduce((s, d) => s + d.bytes.length, 0);
const manifestSha256 = require('node:crypto')
    .createHash('sha256')
    .update(fs.readFileSync(path.join(CORPUS_DIR, 'MANIFEST.json')))
    .digest('hex');

// GC observer (dilaporkan, bukan disembunyikan) ----------------------------
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

// Field counters (extras consumed/skipped — statis dari referensi V8) ------
const totalFields = (v) => {
    if (Array.isArray(v)) return v.reduce((s, e) => s + totalFields(e), 0);
    if (v !== null && typeof v === 'object') {
        return Object.keys(v).length
            + Object.values(v).reduce((s, e) => s + totalFields(e), 0);
    }
    return 0;
};
const isArrayOfObjectsWithId = (v) => Array.isArray(v) && v.length > 0
    && v.every((e) => e !== null && typeof e === 'object' && !Array.isArray(e))
    && v.some((e) => Object.prototype.hasOwnProperty.call(e, 'id'));
const consumedFields = (pathName, v) => {
    if (['v8-parse', 'v8-clone', 'ze-parse'].includes(pathName)) {
        return totalFields(v); // jalur ini membayar seluruh dokumen
    }
    if (['v8-selective', 'ze-project-selective', 'ze-l1-traversal']
        .includes(pathName)) {
        if (isArrayOfObjectsWithId(v)) return v.length; // 1 field `id` per item
        if (Array.isArray(v)) return 0;                 // {$count:true} — 0 field
        if (v !== null && typeof v === 'object') {
            return Object.values(v).reduce((s, e) => {
                if (isArrayOfObjectsWithId(e)) return s + e.length;
                if (Array.isArray(e) || (e !== null && typeof e === 'object')) {
                    return s; // {$count:true}
                }
                return s + 1; // scalar level-atas diambil (shape=true)
            }, 0);
        }
        return 1;
    }
    return totalFields(v);
};

// Jalur ze fase A–C — analog probe lazy_probe.mjs (teruji lazy.mjs T1–T6) --
const openZe = (bytes, cnt) => {
    cnt.bindingCalls += 1; // ZeParser.open (ekspor ABI)
    return ZeParser.open(binding, bytes);
};

const selectiveShape = (v) => {
    if (isArrayOfObjectsWithId(v)) return { $array: { id: true } };
    if (Array.isArray(v)) return { $count: true };
    if (v !== null && typeof v === 'object') {
        const shape = Object.create(null);
        for (const [key, item] of Object.entries(v)) {
            shape[key] = isArrayOfObjectsWithId(item) ? { $array: { id: true } }
                : (Array.isArray(item) || (item !== null && typeof item === 'object'))
                    ? { $count: true }
                    : true;
        }
        return shape;
    }
    return true;
};

const l1Phase = (parser, v8Value, cnt) => {
    if (Array.isArray(v8Value)) {
        let ids = 0;
        cnt.bindingCalls += 1; // lazy() + items() iterator
        for (const item of parser.lazy().items()) {
            cnt.indexCalls += 1; // langkah iterasi struktural
            if (item.type() !== 'object') continue;
            cnt.bindingCalls += 2; // type() + get()
            const id = item.get('id');
            if (id !== undefined) {
                cnt.bindingCalls += 1; // asString()
                ids += id.asString().length;
            }
        }
        return ids;
    }
    if (v8Value !== null && typeof v8Value === 'object') {
        let touched = 0;
        cnt.indexCalls += 1; // baca rootTs
        for (const key of Object.keys(v8Value)) {
            cnt.bindingCalls += 1; // get()
            const f = parser.get(key, parser.rootTs, 0);
            if (f !== undefined) {
                cnt.indexCalls += 1; // kind()
                cnt.bindingCalls += 1;
                touched += parser.kind(f.ts);
            }
        }
        return touched;
    }
    return 0;
};

// Jalur per fase (fn(cnt) mengembalikan nilai sink — anti dead-code elim). --
function phasePaths(doc, phase) {
    const A = [
        { name: 'v8-parse', engine: 'v8', fn: () => JSON.parse(doc.text) },
        {
            name: 'v8-clone', engine: 'v8',
            // Semantik MongoJsonRepository.read() (klon H1).
            fn: () => JSON.parse(JSON.stringify(doc.v8)),
        },
        {
            name: 'ze-parse', engine: 'wasm64_cabi',
            fn: (cnt) => {
                const parser = openZe(doc.bytes, cnt);
                try { cnt.bindingCalls += 1; return parser.parse(); }
                finally { closeParser(parser, cnt); }
            },
        },
    ];
    const v8Selective = {
        name: 'v8-selective', engine: 'v8',
        fn: () => {
            const v = JSON.parse(doc.text);
            if (isArrayOfObjectsWithId(v)) {
                return v.map((e) => e.id); // subset `id` — konsumen fase B/C
            }
            if (Array.isArray(v)) return v.length; // {$count:true}
            if (v !== null && typeof v === 'object') {
                const out = {};
                for (const [key, item] of Object.entries(v)) {
                    if (isArrayOfObjectsWithId(item)) {
                        out[key] = item.map((e) => e.id);
                    } else if (Array.isArray(item)
                        || (item !== null && typeof item === 'object')) {
                        out[key] = item.length ?? Object.keys(item).length;
                    } else {
                        out[key] = item;
                    }
                }
                return out;
            }
            return v;
        },
    };
    const B = [
        v8Selective,
        {
            name: 'ze-project-selective', engine: 'wasm64_cabi',
            fn: (cnt) => {
                const parser = openZe(doc.bytes, cnt);
                try {
                    cnt.bindingCalls += 1;
                    return parser.project(selectiveShape(doc.v8));
                } finally { closeParser(parser, cnt); }
            },
        },
    ];
    const C = [
        v8Selective,
        {
            name: 'ze-l1-traversal', engine: 'wasm64_cabi',
            fn: (cnt) => {
                const parser = openZe(doc.bytes, cnt);
                try { return l1Phase(parser, doc.v8, cnt); }
                finally { closeParser(parser, cnt); }
            },
        },
    ];
    if (phase === 'A') return A;
    if (phase === 'B') return B;
    return C;
}

// Fase D — repositori aplikasi nyata (read-only) ---------------------------
function phaseDPaths() {
    const fileRepos = [];
    const mongoRepos = [];
    for (const doc of DOCS) {
        if (!D_REPOS.includes(doc.name)) continue;
        fileRepos.push(new JsonRepository(doc.file, doc.rootKey, doc.defaultValue));
        const mr = new MongoJsonRepository(
            doc.file, doc.rootKey, doc.defaultValue, `bench-${doc.name}`);
        mr._cache = doc.rootKey ? (doc.v8[doc.rootKey] ?? doc.defaultValue) : doc.v8;
        mr._cacheLoaded = true; // replikasi state pasca-init() — tanpa MongoDB
        mongoRepos.push(mr);
    }
    return [
        {
            name: 'D-file-store-v8', engine: 'v8',
            fn: () => {
                const out = {};
                for (const r of fileRepos) out[r.filePath] = r.read().length;
                return out;
            },
        },
        {
            name: 'D-file-store-ze', engine: 'wasm64_cabi',
            fn: () => {
                const out = {};
                for (const r of fileRepos) out[r.filePath] = r.readCount();
                return out;
            },
        },
        {
            name: 'D-mongo-cache-v8', engine: 'v8',
            fn: () => {
                const out = {};
                for (const r of mongoRepos) out[r.storeKey] = r.read().length;
                return out;
            },
        },
        {
            name: 'D-mongo-cache-ze', engine: 'wasm64_cabi',
            fn: () => {
                const out = {};
                for (const r of mongoRepos) out[r.storeKey] = r.readCount();
                return out;
            },
        },
    ];
}

// Rationale per jalur (sinkron @cite di header) ----------------------------
const RATIONALE = {
    'v8-parse': 'Baseline V8 JSON.parse penuh — batas atas jalur materialisasi.',
    'v8-clone': 'Baseline klon JSON.parse(JSON.stringify()) — semantik MongoJsonRepository.read() (H1) yang ditanggung server per request.',
    'ze-parse': 'ze_json full materialize via binding — pembanding bawah jalur lazy (probe §13: 14–25x di bawah V8).',
    'v8-selective': 'Baseline V8: JSON.parse penuh lalu akses subset field yang sama dengan jalur ze — mengisolasi untung lazy pada konsumen selektif.',
    'ze-project-selective': 'L2 project(shape) C++-side — membayar hanya field shape; konsumen identik v8-selective (isolasi mekanisme L2 vs L1).',
    'ze-l1-traversal': 'L1 traversal frame manual (get/count + decode minimal, early-exit) — konsumen identik v8-selective; biaya per-panggilan ABI terlihat.',
    'D-file-store-v8': 'Workload SAQ asli: satu iterasi = request GET /rekap (4 repo) jalur baseline repo.read().length (file store).',
    'D-file-store-ze': 'Workload SAQ asli: request GET /rekap jalur ze opt-in repo.readCount() (file store) — acceptance T_baseline/T_ze >= 1.5x.',
    'D-mongo-cache-v8': 'Workload SAQ asli mode cache Mongo (state pasca-init disimulasikan tanpa MongoDB): repo.read() klon + .length.',
    'D-mongo-cache-ze': 'Workload SAQ asli mode cache Mongo: repo.readCount() stringify + structural count (acceptance).',
};

// EKSEKUSI pengukuran ------------------------------------------------------
const targetReps = (perIterationBytes) =>
    Math.max(1, Math.min(30, Math.floor(200_000 / perIterationBytes)));

const rawRounds = []; // exhibit mentah: {doc, path, reps, rounds_ms, ...}
const results = [];
const gcAtStart = { ...gcCounts };
let SINK; // sink anti dead-code elimination

function runPathRound(p, reps) {
    const cnt = { bindingCalls: 0, indexCalls: 0 };
    const t0 = performance.now();
    for (let i = 0; i < reps; i += 1) SINK = p.fn(cnt);
    return { dt: (performance.now() - t0) / reps, cnt }; // ms per op
}

function measureBlock(label, paths, reps) {
    const acc = new Map(paths.map((p) => [p.name, { p, rounds: [], cnt: { bindingCalls: 0, indexCalls: 0 } }]));
    for (let w = 0; w < WARMUP; w += 1) {
        for (const p of paths) SINK = p.fn(acc.get(p.name).cnt); // warmup untimed
    }
    for (let r = 0; r < ROUNDS; r += 1) {
        // Alternating: rotasi urutan jalur per ronde (round-robin offset).
        const off = r % paths.length;
        const order = paths.slice(off).concat(paths.slice(0, off));
        for (const p of order) {
            const { dt, cnt } = runPathRound(p, reps);
            const cell = acc.get(p.name);
            cell.rounds.push(dt);
            cell.cnt.bindingCalls += cnt.bindingCalls;
            cell.cnt.indexCalls += cnt.indexCalls;
        }
    }
    if (SINK === undefined) throw new Error(`path produced undefined (${label})`);
    for (const [, cell] of acc) {
        rawRounds.push({
            doc: label,
            path: cell.p.name,
            reps,
            rounds_ms: cell.rounds.map((x) => Number(x.toPrecision(9))),
            binding_calls: cell.cnt.bindingCalls,
            index_calls: cell.cnt.indexCalls,
        });
    }
    return acc;
}

function pushResult(prefix, doc, p, cell, reps, refValue, instrumented) {
    const roundsMs = cell.rounds;
    const perOpS = mean(roundsMs) / 1000;
    const bytes = doc ? doc.bytes.length : BYTES_TOTAL;
    const isD = refValue && refValue.__totalFields !== undefined;
    const refTotal = isD ? refValue.__totalFields : totalFields(refValue);
    const consumed = isD
        ? (p.engine === 'v8' ? refTotal : 0)
        : consumedFields(p.name, refValue);
    results.push({
        name: `${prefix}/${p.name}`,
        engine: p.engine,
        status: 'ok',
        rationale: {
            purpose: RATIONALE[p.name],
            basis_papers: ['10.1002_spe.3313', '10.14778_3115404.3115416'],
        },
        metrics: {
            seconds_mean: Number(perOpS.toPrecision(9)),
            seconds_stddev: Number((stddev(roundsMs) / 1000).toPrecision(6)),
            bytes_per_second: Number((bytes / perOpS).toPrecision(9)),
            documents_per_second: Number(((doc ? 1 : D_REPOS.length) / perOpS)
                .toPrecision(9)),
        },
        extras: {
            path: p.name,
            seconds_median: Number((median(roundsMs) / 1000).toPrecision(9)),
            seconds_p95: Number((percentile(roundsMs, 95) / 1000).toPrecision(9)),
            rounds: ROUNDS,
            reps_per_round: reps,
            gc_minor: gcCounts.minor - gcAtStart.minor, // kumulatif sejak start fase
            gc_major: gcCounts.major - gcAtStart.major,
            binding_calls: instrumented ? cell.cnt.bindingCalls : null,
            index_count: instrumented ? cell.cnt.indexCalls : null,
            consumed_fields: consumed,
            skipped_fields: refTotal - consumed,
            total_fields: refTotal,
            doc_bytes: bytes,
        },
    });
}

function runPhaseABC(phase) {
    for (const doc of DOCS) {
        const paths = phasePaths(doc, phase);
        const reps = targetReps(doc.bytes.length);
        const acc = measureBlock(doc.name, paths, reps);
        for (const p of paths) {
            pushResult(`${phase}/${doc.name}`, doc, p, acc.get(p.name), reps,
                doc.v8, true);
        }
        if (global.gc) global.gc();
    }
}

function runPhaseD() {
    const paths = phaseDPaths();
    const reps = targetReps(BYTES_TOTAL); // 1 iterasi ~= seluruh 4 store
    const refFields = D_REPOS.reduce((s, name) => {
        const doc = DOCS.find((d) => d.name === name);
        return s + totalFields(doc.v8);
    }, 0);
    const acc = measureBlock('D-rekap-request', paths, reps);
    for (const p of paths) {
        // instrumented=false: jalur melewati lapisan repositori — panggilan
        // ABI internal readCount() tidak terlihat di level harness.
        pushResult('D', null, p, acc.get(p.name), reps,
            { __totalFields: refFields }, false);
    }
}

// Metadata host/git --------------------------------------------------------
// Definisi dirty: modifikasi file TRACKED (+ mismatch pointer submodule).
// File untracked milik pemilik (mis. utils/typ/*, ze_json README.md) tidak
// memengaruhi kode yang diukur — dicatat transparan, tidak menodai hash
// (rencana ND-6 §3.9).
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
// Acceptance gate (audit ND-6 / protocol §3.9): acceptance runs MUST execute
// from a clean tree (root + both submodules; tracked changes only — untracked
// owner files do not affect the measured code). Refuse otherwise; --allow-dirty
// produces an exploratory run labeled in the record (never acceptance evidence).
const GATE = gateDecision({
    rootDirty: DIRTY, zeDirty, saqDirty,
    allowDirty: argv.includes('--allow-dirty'),
});
if (!GATE.ok) {
    console.error(`[nd6] REFUSED: tracked changes in ${GATE.dirtyRepos.join(', ')} `
        + '— acceptance runs require a clean tree (protocol §3.9).');
    console.error('[nd6] For an exploratory run add --allow-dirty '
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
const RUN_ID = `${HOSTNAME}-${tsNow()}-${ROOT_HASH}`; // schema: tanpa suffix;
// status dirty dilaporkan lewat git_commit.dirty + git_commit.hash '-dirty'.
const RAW_DIR = path.join(OUT_DIR, 'raw', RUN_ID);
const MEAS_DIR = path.join(OUT_DIR, 'measurements');
fs.mkdirSync(RAW_DIR, { recursive: true });
fs.mkdirSync(MEAS_DIR, { recursive: true });

/**
 * Version registry (R5-13): bindings/js/package.json is REGENERATED from
 * cmake/templates/package.json.in at configure time — version =
 * ZE_JSON_JS_VERSION (independent js semver), coreVersion =
 * ZE_JSON_CORE_VERSION_NUMBER (= ze_abi_version()), coreSemver = project
 * VERSION. Every measurement record carries all three, standard.
 */
const zePkg = (() => {
    try {
        return require(path.join(ROOT, 'ze_json', 'bindings', 'js',
            'package.json'));
    } catch {
        return { version: '0.0.0-unknown', coreVersion: null,
            coreSemver: '0.0.0-unknown' };
    }
})();

// Identity of the actually-loaded wasm artifact (cross-site byte-identity check).
const WASM_PATH = path.join(path.dirname(BINDING_PATH), 'ze_json.wasm');
const WASM_SHA256 = wasmSha256(WASM_PATH);

const metadata = {
    run_id: RUN_ID,
    phase: PHASE,
    site: SITE,
    generator: 'node_harness',
    cmd: `node scripts/bench/nd6_bench.mjs --phase ${PHASE} `
        + `--rounds ${ROUNDS} --warmup ${WARMUP} --site ${SITE}`,
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
        alternating: true,
        outlier_trimming: false,
        gc_exposed: Boolean(global.gc),
    },
    gc_at_start: { ...gcAtStart },
    date_utc: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
};
fs.writeFileSync(path.join(RAW_DIR, 'metadata.json'),
    JSON.stringify(metadata, null, 2));

// Jalankan fase ------------------------------------------------------------
console.log(`[nd6] phase ${PHASE} | rounds=${ROUNDS} warmup=${WARMUP} site=${SITE}`);
console.log(`[nd6] run_id=${RUN_ID}`);
console.log(`[nd6] corpus=${CORPUS_DIR} (${MANIFEST.document_count} docs, `
    + `${BYTES_TOTAL} B total)`);

if (PHASE === 'D') runPhaseD();
else runPhaseABC(PHASE);

fs.writeFileSync(path.join(RAW_DIR, `nd6_phase_${PHASE}.json`),
    JSON.stringify({ metadata, raw_rounds: rawRounds }, null, 2));

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
        iterations: Math.max(...rawRounds.map((r) => r.reps)),
        warmup_runs: WARMUP,
        repeats: ROUNDS,
        cpu_pinning: false,
        threads: 1,
        exploratory: GATE.exploratory,
        notes: `ND-6 phase ${PHASE}; alternating rounds; no outlier trimming; `
            + `gc_exposed=${Boolean(global.gc)}; gc(minor=${gcCounts.minor - gcAtStart.minor}, `
            + `major=${gcCounts.major - gcAtStart.major}); raw: out/raw/${RUN_ID}/; `
            + `per-result detail in extras (seconds_median/p95, binding_calls, `
            + `index_count, consumed/skipped — kumulatif GC sejak start fase). `
            + `Baseline=V8 (engine=v8), candidate=ze_json wasm64_cabi — same run_id; `
            + `phase D measures through the saq-report repository layer (binding `
            + `calls not observable there: extras.binding_calls=null).`
            + (GATE.exploratory
                ? ` EXPLORATORY run (tracked changes: ${GATE.dirtyRepos.join(', ')}; `
                  + `--allow-dirty) — NOT acceptance evidence.`
                : ''),
    },
    results,
};
const recordFile = path.join(MEAS_DIR,
    recordFilename(RUN_ID, PHASE, SITE));
fs.writeFileSync(recordFile, JSON.stringify(record, null, 2));

// Ringkasan ---------------------------------------------------------------
console.log(`[nd6] results=${results.length} | raw -> out/raw/${RUN_ID}/`);
for (const r of results) {
    console.log(`  ${r.name.padEnd(34)} `
        + `median ${(r.extras.seconds_median * 1000).toFixed(3).padStart(10)} ms/op `
        + `p95 ${(r.extras.seconds_p95 * 1000).toFixed(3).padStart(10)} ms/op`);
}
console.log(`[nd6] record -> ${recordFile}`);
console.log(`[nd6] VALIDATE: python scripts/measurement-schema/validate.py ${recordFile}`);
if (gcObserver) gcObserver.disconnect();
