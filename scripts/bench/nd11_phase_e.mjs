#!/usr/bin/env node
/**
 * nd11_phase_e.mjs — Phase E (ND-11): HTTP GET /rekap end-to-end benchmark.
 *
 * Boundary yang diukur (desain docs/measurement/nd11-phase-e-http.md):
 *   request HTTP penuh pada aplikasi Express saq-report: middleware chain
 *   (express.json, static) -> routing -> handler rekapRoutes.js L25-47
 *   (4 repo call: readCount()/read().length) -> render EJS
 *   (views/rekap-pilihan) -> serialisasi respons.
 * Bagian yang TIDAK termasuk: MongoDB (store lokal), browser, jaringan
 * antar-mesin (load generator di mesin yang sama, localhost).
 *
 * Dua instance aplikasi di localhost, kode + data store identik, hanya
 * engine yang berbeda (SAQ_JSON_ENGINE=ze vs baseline V8 default):
 *   instance v8 -> PORT v8-port (default 3000)
 *   instance ze -> PORT ze-port (default 3001)
 * Boot WhatsApp/cron dimatikan di kedua instance (SAQ_DISABLE_WHATSAPP=1,
 * saq-report PR #5) supaya puppeteer headless tidak menodai latensi —
 * handler/route/template aplikasi tidak diubah.
 *
 * Protokol: warmup untimed per jalur (default 3 request), lalu ronde
 * berulang (default 15 ronde x 20 request per engine), urutan engine
 * ALTERNATING per-request (offset rotasi per ronde agar bias urutan merata),
 * tanpa trimming — semua request dilaporkan di exhibit mentah.
 * Latensi di-sampling sisi generator: performance.now() di sekitar fetch.
 *
 * PARITY GATE: setiap body respons harus byte-identik (satu hash unik untuk
 * SELURUH request, kedua engine). Mismatch = run void, tidak ada record
 * ditulis.
 *
 * Satu run_id untuk pasangan v8<->ze (rasio hanya sah dalam satu run_id —
 * AGENTS §4). Record schema v1.0.0; tidak boleh dibandingkan lintas
 * mesin/hash/korpus/store.
 *
 * @cite 10.1002_spe_3313 — on-demand JSON: pertanyaan risetnya adalah pada
 *       kondisi apa manfaat lazy parsing muncul/hilang di boundary aplikasi
 *       penuh (bukan hanya lapisan repository seperti fase D ND-6).
 *       rationale dicerminkan oleh field rationale tiap result di record.
 *
 * COEXISTENCE GUARDS (audit 2026-11-17, laporan reports/nd11-coexistence-audit.md):
 * saat SAQ Production berjalan di host yang sama, harness wajib:
 *   1. preflight port — kedua port benchmark WAJIB kosong sebelum spawn
 *      (health-check tidak lagi memercayai "siapa pun yang listen di port");
 *   2. health = HTTP 200 + boot marker di stdout CHILD KITA
 *      ("Server berjalan di http://localhost:<port>") — identitas instance
 *      terikat ke proses, bukan ke port;
 *   3. child exit saat warmup/ukur = abort void instan;
 *   4. mode koeksistensi (--coexist-prod-port): preflight count json_store
 *      (benchmark tidak boleh memicu seed ke DB produksi —
 *      MongoJsonRepository.init() melakukan upsert bila storeKey kosong)
 *      + boot-log seed guard (abort void bila child menyebut seed);
 *   5. kedua child bind 127.0.0.1 via SAQ_BIND_HOST (saq-report boot knob;
 *      env absen = perilaku produksi eksisting, tidak berubah).
 */
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { execSync, spawn } from 'node:child_process';
import { recordFilename, gateDecision } from './nd6_protocol.mjs';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..', '..');
const SAQ_DIR = path.join(ROOT, 'saq-report');
const OUT_DIR = process.env.OUT_DIR || path.join(ROOT, 'out');
const CORPUS_DIR = process.env.CORPUS_DIR || path.join(ROOT, 'corpus');
const BINDING_PATH = path.join(ROOT, 'ze_json', 'bindings', 'js', 'ze_json.mjs');

// ─── CLI ──────────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const argValue = (flag, dflt) => {
    const i = argv.indexOf(flag);
    return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : dflt;
};
const ROUNDS = Number(argValue('--rounds', 15));
const PER_ROUND = Number(argValue('--per-round', 20));
const WARMUP = Number(argValue('--warmup', 3));
const SITE = argValue('--site', 'dev_device');
const V8_PORT = Number(argValue('--v8-port', 3000));
const ZE_PORT = Number(argValue('--ze-port', 3001));
const allowDirty = argv.includes('--allow-dirty');
// Coexistence mode (audit ND-11, 2026-11-17): --coexist-prod-port menyatakan
// SAQ Production berjalan di host yang sama (tidak disentuh). Mengaktifkan
// write-to-production guards (preflight counts + seed guard) dan mencatat
// provenance koeksistensi di config.coexistence record.
const PROD_PORT = Number(argValue('--coexist-prod-port', 0));
const COEXISTENCE = {
    production_same_host: PROD_PORT > 0,
    production_port: PROD_PORT > 0 ? PROD_PORT : null,
    production_untouched: PROD_PORT > 0,
    wa_production: PROD_PORT > 0 ? 'active (untouched)' : null,
    cron_production: PROD_PORT > 0 ? 'active (untouched)' : null,
    benchmark_bind_host: '127.0.0.1',
    benchmark_whatsapp: 'SAQ_DISABLE_WHATSAPP=1 (both benchmark instances)',
    write_guard: PROD_PORT > 0
        ? 'preflight json_store counts + refuse on boot seed marker'
        : 'off (dev throwaway DB)',
};
let PREFLIGHT_COUNTS = null;

const STORE_FILES = ['config_asisten.json', 'config_global.json', 'courses.json',
    'lecturers.json', 'reports.json', 'schedules.json'];

// ─── git identity + clean-tree gate (tracked only; owner untracked ignored) ──
const git = (cmd) => String(execSync(cmd, { cwd: ROOT })).trim();
const dirtyTracked = (dir) => git(`git -C ${dir} status --porcelain `
    + '--untracked-files=no').length > 0;
const ROOT_HASH = git('git rev-parse --short HEAD');
const zeHash = git('git -C ze_json rev-parse --short HEAD');
const saqHash = git('git -C saq-report rev-parse --short HEAD');
const GATE = gateDecision({
    rootDirty: dirtyTracked('.'), zeDirty: dirtyTracked('ze_json'),
    saqDirty: dirtyTracked('saq-report'), allowDirty,
});
if (!GATE.ok) {
    console.error(`[nd11] REFUSED: tracked changes in ${GATE.dirtyRepos.join(', ')} `
        + '— acceptance runs require a clean tree (protocol §3.9).');
    process.exit(3);
}
const HOSTNAME = os.hostname().replace(/[^A-Za-z0-9._-]/g, '-');
const tsNow = () => {
    const d = new Date();
    const p = (n, w = 2) => String(n).padStart(w, '0');
    return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}`
        + `${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}`;
};
const RUN_ID = `${HOSTNAME}-${tsNow()}-${ROOT_HASH}`;
const RAW_DIR = path.join(OUT_DIR, 'raw', RUN_ID);
const MEAS_DIR = path.join(OUT_DIR, 'measurements');
fs.mkdirSync(RAW_DIR, { recursive: true });
fs.mkdirSync(MEAS_DIR, { recursive: true });

// Version registry (R5-13) + artifact identity — pola nd6_bench.
const zePkg = (() => {
    try {
        return require(path.join(ROOT, 'ze_json', 'bindings', 'js', 'package.json'));
    } catch {
        return { version: '0.0.0-unknown', coreVersion: null, coreSemver: '0.0.0-unknown' };
    }
})();
const wasmSha256 = (p) => (fs.existsSync(p)
    ? crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex') : null);
const WASM_SHA = wasmSha256(path.join(path.dirname(BINDING_PATH), 'ze_json.wasm'));
const manifestSha256 = (p) => crypto.createHash('sha256')
    .update(fs.readFileSync(p)).digest('hex');
const CORPUS_MANIFEST = path.join(CORPUS_DIR, 'benchmarks', 'saq_payload_v1',
    'MANIFEST.json');
const MANIFEST = JSON.parse(fs.readFileSync(CORPUS_MANIFEST, 'utf8'));
const storeSha = {};
for (const f of STORE_FILES) {
    const p = path.join(SAQ_DIR, f);
    if (!fs.existsSync(p)) {
        console.error(`[nd11] store file missing: ${p} — seed dulu `
            + '(langkah 1 rencana: copy corpus store ke saq-report/).');
        process.exit(2);
    }
    storeSha[f] = storeSha256(p);
}
function storeSha256(p) {
    return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}

// ─── app instances ────────────────────────────────────────────────────────────
const children = [];
function killChildren() {
    for (const c of children) {
        try { c.kill(); } catch (_) { /* already dead */ }
    }
}
process.on('exit', killChildren);
process.on('SIGINT', () => { killChildren(); process.exit(130); });

const bootLog = {};
let childDied = null; // audit ND-11 R6: kematian child = abort void instan
function spawnInstance(engine, port) {
    const env = {
        ...process.env, PORT: String(port), SAQ_DISABLE_WHATSAPP: '1',
        SAQ_JSON_ENGINE: engine === 'ze' ? 'ze' : '',
        // Bind loopback only — instance benchmark tidak boleh reachable dari
        // jaringan (audit ND-11 R3: endpoint mutasi + static ROOT + lazy-init
        // WA). Produksi tidak mewarisi env ini (child-only harness).
        SAQ_BIND_HOST: '127.0.0.1',
    };
    const child = spawn(process.execPath, ['server.js'], {
        cwd: SAQ_DIR, env, stdio: ['ignore', 'pipe', 'pipe'],
    });
    const lines = [];
    child.stdout.on('data', (d) => lines.push(String(d)));
    child.stderr.on('data', (d) => lines.push(String(d)));
    child.on('exit', (code, signal) => {
        lines.push(`[exit code=${code} signal=${signal}]`);
        if (!childDied) childDied = { engine, code, signal };
    });
    children.push(child);
    bootLog[engine] = lines;
    return child;
}

/**
 * Preflight port (audit ND-11 R1/R2): kedua port benchmark WAJIB kosong
 * SEBELUM spawn. Mencegah (a) EADDRINUSE di child, dan (b) skenario
 * "mengukur SAQ Production" ketika port yang dipilih kebetulan dipakai
 * produksi — health-check lama menerima respons HTTP apa pun.
 * Timeout connect dihitung BUSY (konservatif; port terfilter).
 */
function probeBusy(port) {
    return new Promise((resolve) => {
        const s = net.connect({ port, host: '127.0.0.1' });
        let settled = false;
        const fin = (busy) => {
            if (!settled) { settled = true; s.destroy(); resolve(busy); }
        };
        s.on('connect', () => fin(true));
        s.on('error', () => fin(false));
        s.setTimeout(2000, () => fin(true));
    });
}

/**
 * Abort void: tulis exhibit (best-effort), bunuh HANYA child benchmark,
 * keluar 2 — tanpa record. Dipakai parity mismatch, child exit, seed guard.
 */
function failVoid(reason, requests, bodyHashes, bootV8, bootZe) {
    console.error(`[nd11] VOID: ${reason} — run dibatalkan, tidak ada record.`);
    try {
        writeRaw(null, requests, bodyHashes, bootV8, bootZe, reason);
    } catch (_) { /* exhibit best-effort */ }
    killChildren();
    process.exit(2);
}

/**
 * Health (audit ND-11 R1): instance dianggap siap HANYA bila
 * (a) GET /rekap balas 200 dan (b) marker boot milik CHILD KITA
 * ("Server berjalan di http://localhost:<port>") terlihat di stdout yang
 * di-capture harness — bukan sekadar "ada yang menjawab di port".
 */
async function waitHealthy(engine, port, timeoutMs = 120000) {
    const t0 = performance.now();
    const marker = `Server berjalan di http://localhost:${port}`;
    for (;;) {
        if (childDied) {
            throw new Error(`instance ${engine} exited before healthy `
                + `(code=${childDied.code} signal=${childDied.signal})`);
        }
        try {
            const res = await fetch(`http://127.0.0.1:${port}/rekap`);
            const status = res.status;
            await res.text(); // drain body agar socket bebas
            const logText = (bootLog[engine] || []).join('');
            if (status === 200 && logText.includes(marker)) {
                return (performance.now() - t0) / 1000;
            }
        } catch (_) { /* not up yet */ }
        if (performance.now() - t0 > timeoutMs) {
            const markerSeen = (bootLog[engine] || []).join('').includes(marker);
            throw new Error(`instance ${engine} port ${port} not healthy `
                + `within ${timeoutMs} ms (boot-marker=${markerSeen})`);
        }
        await new Promise((r) => setTimeout(r, 250));
    }
}

/**
 * Preflight Mongo (coexistence only, audit ND-11 R4): bila SAQ Production
 * berjalan di host yang sama, benchmark instance membaca DB produksi yang
 * sama (LIVE store). MongoJsonRepository.init() melakukan SEED + upsert ke
 * json_store bila storeKey kosong — artinya benchmark bisa MENULIS ke DB
 * produksi bila ada koleksi kosong. Guard ini memverifikasi SEMUA storeKey
 * sudah terisi SEBELUM spawn (script berjalan dengan node_modules + .env
 * milik saq-report; URI tidak dicetak). Script disimpan ke RAW_DIR sebagai
 * bagian exhibit provenance.
 */
function preflightMongoCounts() {
    const scriptPath = path.join(RAW_DIR, 'preflight_json_store_counts.cjs');
    fs.writeFileSync(scriptPath, `'use strict';
// ND-11 coexistence preflight (read-only): hitung doc per storeKey di
// json_store DB produksi; exit 3 bila ada yang kosong (seed-to-prod guard).
const path = require('path');
// Resolusi modul dari node_modules APP (cwd = dir saq-report), bukan dari
// lokasi file script ini (out/raw/... — tanpa node_modules sendiri).
const { createRequire } = require('module');
const requireFromApp = createRequire(path.join(process.cwd(), 'package.json'));
requireFromApp('dotenv').config({ path: path.join(process.cwd(), '.env') });
const { MongoClient } = requireFromApp('mongodb');
const KEYS = ['assistants', 'courses', 'lecturers', 'schedules', 'reports',
    'globalConfig'];
(async () => {
    const uri = process.env.MONGO_URL || process.env.MONGO_PUBLIC_URL;
    if (!uri) { console.error('no Mongo URI in env'); process.exit(3); }
    const mc = new MongoClient(uri, { serverSelectionTimeoutMS: 8000 });
    await mc.connect();
    const col = mc.db().collection('json_store');
    const counts = {};
    for (const k of KEYS) counts[k] = await col.countDocuments({ key: k });
    await mc.close();
    console.log('COUNTS_JSON=' + JSON.stringify(counts));
    const empty = KEYS.filter((k) => counts[k] === 0);
    if (empty.length) {
        console.error('EMPTY_KEYS=' + empty.join(','));
        process.exit(3);
    }
})().catch((e) => { console.error(String((e && e.message) || e)); process.exit(3); });
`);
    const out = String(execSync(`"${process.execPath}" "${scriptPath}"`, {
        cwd: SAQ_DIR, encoding: 'utf8', windowsHide: true,
    })).trim();
    const jsonLine = out.split('\n')
        .map((l) => l.trim())
        .find((l) => l.startsWith('COUNTS_JSON='));
    if (!jsonLine) throw new Error(`no COUNTS_JSON in preflight output: ${out}`);
    return JSON.parse(jsonLine.slice('COUNTS_JSON='.length));
}

async function requestOnce(port) {
    const t0 = performance.now();
    const res = await fetch(`http://127.0.0.1:${port}/rekap`);
    const body = await res.text();
    const t1 = performance.now();
    if (res.status !== 200) throw new Error(`GET /rekap status=${res.status}`);
    return {
        seconds: (t1 - t0) / 1000,
        bodyBytes: Buffer.byteLength(body),
        bodySha: crypto.createHash('sha256').update(body).digest('hex'),
    };
}

// ─── statistics ───────────────────────────────────────────────────────────────
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
const stddev = (xs) => {
    const m = mean(xs);
    return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length);
};
const median = (xs) => {
    const s = [...xs].sort((a, b) => a - b);
    const n = s.length;
    return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
};
const p95 = (xs) => {
    const s = [...xs].sort((a, b) => a - b);
    if (s.length === 1) return s[0];
    const pos = 0.95 * (s.length - 1);
    const lo = Math.floor(pos), hi = Math.ceil(pos);
    return s[lo] + (s[hi] - s[lo]) * (pos - lo);
};

// ─── main ─────────────────────────────────────────────────────────────────────
async function main() {
    console.log(`[nd11] phase E | rounds=${ROUNDS} per_round=${PER_ROUND} `
        + `warmup=${WARMUP} site=${SITE} ports v8=${V8_PORT} ze=${ZE_PORT}`);
    console.log(`[nd11] run_id=${RUN_ID}`);

    // PREFLIGHT PORT (audit ND-11 R1/R2) — sebelum spawn apa pun.
    const busyPorts = [];
    for (const p of [V8_PORT, ZE_PORT]) {
        if (await probeBusy(p)) busyPorts.push(p);
    }
    if (busyPorts.length) {
        console.error(`[nd11] REFUSED: port sudah terpakai: `
            + `${busyPorts.join(', ')} — pilih port lain (--v8-port/--ze-port); `
            + `pemilik port: powershell "Get-NetTCPConnection -State Listen `
            + `-LocalPort ${busyPorts.join(',')}"`);
        process.exit(2);
    }
    console.log(`[nd11] port preflight OK (v8 ${V8_PORT}, ze ${ZE_PORT} free)`);

    // PREFLIGHT MONGO (coexistence only, audit ND-11 R4) — sebelum spawn:
    // semua storeKey json_store di DB produksi wajib terisi agar init()
    // benchmark tidak pernah menulis seed ke produksi.
    if (PROD_PORT > 0) {
        try {
            PREFLIGHT_COUNTS = preflightMongoCounts();
        } catch (err) {
            console.error(`[nd11] REFUSED: preflight json_store gagal — `
                + `${String(err.message).split('\n').filter(Boolean).pop()}`);
            process.exit(2);
        }
        console.log(`[nd11] json_store counts: ${JSON.stringify(PREFLIGHT_COUNTS)}`);
    }

    spawnInstance('v8', V8_PORT);
    spawnInstance('ze', ZE_PORT);
    const bootV8 = await waitHealthy('v8', V8_PORT);
    const bootZe = await waitHealthy('ze', ZE_PORT);
    console.log(`[nd11] instances healthy (v8 ${bootV8.toFixed(2)}s, `
        + `ze ${bootZe.toFixed(2)}s)`);

    // SEED GUARD layer kedua (coexistence only) — menutup race window antara
    // preflight counts dan init(): bila CHILD KITA menyebut seed, berarti
    // koleksi produksi kosong saat init → benchmark menulis ke produksi =
    // run void. (Log format app: "[MongoDB] Seed '<key>' from JSON file.")
    if (PROD_PORT > 0) {
        const seeded = ['v8', 'ze'].filter((k) =>
            (bootLog[k] || []).join('').includes("[MongoDB] Seed '"));
        if (seeded.length) {
            failVoid(`benchmark instance(s) [${seeded.join(', ')}] would seed `
                + `an empty production collection (write-to-prod guard)`,
                { v8: [], ze: [] }, new Set(), bootV8, bootZe);
        }
    }

    const requests = { v8: [], ze: [] };
    const bodyHashes = new Set();

    // warmup untimed per jalur (JIT + EJS compile + pool koneksi)
    for (let i = 0; i < WARMUP; i++) {
        for (const [engine, port] of [['v8', V8_PORT], ['ze', ZE_PORT]]) {
            if (childDied) {
                failVoid(`instance ${childDied.engine} exited (code=`
                    + `${childDied.code}) during warmup`,
                    requests, bodyHashes, bootV8, bootZe);
            }
            await requestOnce(port);
        }
    }

    // ronde terukur: alternation v8<->ze PER-REQUEST, start offset per ronde
    for (let r = 1; r <= ROUNDS; r++) {
        for (let k = 0; k < PER_ROUND; k++) {
            if (childDied) {
                failVoid(`instance ${childDied.engine} exited (code=`
                    + `${childDied.code}) during measurement round ${r}`,
                    requests, bodyHashes, bootV8, bootZe);
            }
            const engine = (r + k) % 2 === 0 ? 'v8' : 'ze';
            const port = engine === 'v8' ? V8_PORT : ZE_PORT;
            const rec = await requestOnce(port);
            rec.round = r;
            rec.engine = engine;
            requests[engine].push(rec);
            bodyHashes.add(rec.bodySha);
        }
    }
    console.log(`[nd11] requests done: v8=${requests.v8.length} `
        + `ze=${requests.ze.length}`);

    // PARITY GATE — satu hash unik untuk seluruh request (byte-identical HTML)
    if (bodyHashes.size !== 1) {
        const uniq = [...bodyHashes];
        failVoid(`parity: ${uniq.length} respons berbeda `
            + `(${uniq.slice(0, 4).join(', ')}…)`,
            requests, bodyHashes, bootV8, bootZe);
    }
    const BODY_SHA = [...bodyHashes][0];
    console.log(`[nd11] parity OK: seluruh respons byte-identik (sha ${BODY_SHA.slice(0, 12)}…)`);

    const results = {};
    for (const engine of ['v8', 'ze']) {
        const xs = requests[engine].map((x) => x.seconds);
        const secMean = mean(xs);
        const bytes = requests[engine][0].bodyBytes;
        results[engine] = {
            name: `phase-e/rekap/${engine}`,
            engine: engine === 'v8' ? 'v8' : 'wasm64_cabi',
            status: 'ok',
            rationale: {
                purpose: 'Latensi request HTTP GET /rekap end-to-end (middleware → handler 4 repo → render EJS → respons) pada aplikasi Express saq-report.',
                basis_papers: ['10.1002_spe.3313'],
            },
            metrics: {
                seconds_mean: secMean,
                seconds_stddev: stddev(xs),
                bytes_per_second: bytes / secMean,
                documents_per_second: 1 / secMean,
            },
            extras: {
                path: `E-rekap-${engine}`,
                seconds_median: median(xs),
                seconds_p95: p95(xs),
                rounds: ROUNDS,
                reps_per_round: PER_ROUND,
                request_count: xs.length,
                response_bytes: bytes,
                response_sha256: BODY_SHA,
                port: engine === 'v8' ? V8_PORT : ZE_PORT,
                saq_json_engine: engine === 'v8' ? 'v8-baseline' : 'ze',
                gc_minor: 0,
                gc_major: 0,
                binding_calls: null,  // tidak terlihat di level harness (jalan lewat repo layer)
                index_count: null,
                store_sha256: storeSha,
                doc_bytes: MANIFEST.total_bytes,
            },
        };
    }

    const speedup = results.v8.extras.seconds_median
        / results.ze.extras.seconds_median;
    const p95v8 = results.v8.extras.seconds_p95;
    const p95ze = results.ze.extras.seconds_p95;
    console.log(`[nd11] E/rekap/v8  median ${(results.v8.extras.seconds_median * 1000).toFixed(3)} ms `
        + `p95 ${(p95v8 * 1000).toFixed(3)} ms`);
    console.log(`[nd11] E/rekap/ze  median ${(results.ze.extras.seconds_median * 1000).toFixed(3)} ms `
        + `p95 ${(p95ze * 1000).toFixed(3)} ms`);
    console.log(`[nd11] speedup (in-run) v8/ze = ${speedup.toFixed(2)}x`);
    console.log(`[nd11] VALIDATE: python scripts/measurement-schema/validate.py `
        + `${path.join(MEAS_DIR, recordFilename(RUN_ID, 'phase-e', SITE, 'nd11'))}`);

    await writeRaw(speedup, requests, bodyHashes, bootV8, bootZe);

    const record = {
        schema_version: '1.0.0',
        kind: 'benchmark',
        run_id: RUN_ID,
        site: SITE,
        generator: 'node_harness',
        library: {
            name: 'ze_json',
            version: `${zePkg.coreSemver} (ze_json@${zeHash}, saq-report@${saqHash})`,
            language_runtime: `node ${process.version} (v8 ${process.versions.v8}) + wasm64 C-ABI`,
            js_version: zePkg.version,
            core_version: zePkg.coreSemver,
            abi_version: zePkg.coreVersion,
            artifact_sha256: WASM_SHA,
        },
        git_commit: { hash: ROOT_HASH, dirty: GATE.exploratory, repo: 'v5' },
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
        corpus: {
            name: 'saq_payload_v1-live-store',
            document_count: MANIFEST.document_count,
            total_bytes: MANIFEST.total_bytes,
            max_document_bytes: MANIFEST.max_document_bytes,
            sha256: manifestSha256(CORPUS_MANIFEST),
        },
        config: {
            date_utc: new Date().toISOString(),
            iterations: PER_ROUND,
            warmup_runs: WARMUP,
            repeats: ROUNDS,
            cpu_pinning: false,
            threads: 1,
            exploratory: GATE.exploratory,
            notes: `ND-11 phase E (HTTP GET /rekap end-to-end); alternating `
                + `v8<->ze per-request, no outlier trimming; load generator on `
                + `the same machine (localhost); boot WhatsApp/cron gated `
                + `(SAQ_DISABLE_WHATSAPP=1, saq-report PR #5) — byte-identical `
                + `apps, engine toggle only; store dev = anonymized corpus `
                + `mirror (sha per file di extras.store_sha256; server run = `
                + `LIVE store, jangan bandingkan lintas site); gc not `
                + `applicable across processes (recorded only); `
                + `raw: out/raw/${RUN_ID}/; git ze_json=${zeHash} `
                + `saq-report=${saqHash}; dirty=${GATE.exploratory}`,
            coexistence: COEXISTENCE,
        },
        results: [results.v8, results.ze],
    };
    fs.writeFileSync(path.join(MEAS_DIR, recordFilename(RUN_ID, 'phase-e', SITE, 'nd11')),
        JSON.stringify(record, null, 2));
    killChildren();
}

async function writeRaw(speedup, requests, bodyHashes, bootV8, bootZe,
    voidReason = null) {
    const exhibit = {
        run_id: RUN_ID,
        site: SITE,
        protocol: {
            rounds: ROUNDS, per_round: PER_ROUND, warmup: WARMUP,
            order: 'alternating per-request (round-robin offset per round)',
            trimming: 'none — every request reported',
        },
        void_reason: voidReason,
        coexistence: COEXISTENCE,
        mongo_json_store_counts: PREFLIGHT_COUNTS,
        boot: {
            v8_seconds: bootV8, ze_seconds: bootZe,
            v8_log: (bootLog.v8 || []).join('\n').split('\n').slice(0, 20),
            ze_log: (bootLog.ze || []).join('\n').split('\n').slice(0, 20),
        },
        parity: {
            unique_response_hashes: bodyHashes.size === 1 ? 1 : bodyHashes.size,
            void: bodyHashes.size !== 1,
        },
        speedup_in_run: speedup,
        requests: {
            v8: requests.v8.map(({ seconds, round, bodySha, bodyBytes }) =>
                ({ round, seconds, body_bytes: bodyBytes, body_sha256: bodySha })),
            ze: requests.ze.map(({ seconds, round, bodySha, bodyBytes }) =>
                ({ round, seconds, body_bytes: bodyBytes, body_sha256: bodySha })),
        },
        store_sha256: storeSha,
    };
    fs.writeFileSync(path.join(RAW_DIR, 'nd11_phase_e.json'),
        JSON.stringify(exhibit, null, 2));
}

main().catch((err) => {
    console.error('[nd11] FAILED:', err.message);
    killChildren();
    process.exit(1);
});