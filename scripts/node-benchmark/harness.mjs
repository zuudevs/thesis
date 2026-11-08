#!/usr/bin/env node
/**
 * node-benchmark harness — V8 (and future ze-wasm64) baselines as measurement
 * records v1 (TASKS P2-1 .. P2-5).
 *
 * Rationale: the thesis compares JSON parsing pathways against the V8 baseline
 * actually used by the SAQ server. The three measured contexts mirror the real
 * JSON workloads of saq-report (PLANS.md section 5, P2-2):
 *
 *   body-parse        JSON.parse(utf8)                 — express.json() body parsing
 *   store-read        JSON.parse + rootKey unwrap      — JsonRepository.read() hot path
 *                     (disk I/O excluded on purpose: identical for every engine,
 *                      page-cache noise would drown the parsing signal)
 *   export-stringify  JSON.stringify(data, null, 2)    — exportService / JsonRepository.write
 *
 * The engine label in every result mirrors the `@cite` map below; the same
 * purpose text is written into each record's `rationale` field (AGENTS.md §4).
 *
 * @cite 10.48550_arXiv.1902.08318 simdjson: staging/parse throughput is the
 *       bound for on-demand parsing; V8 numbers are the comparison baseline.
 * @cite 10.1002_spe.3313 On-demand JSON: defines the access pattern the V8
 *       baseline is compared against.
 * @cite 10.1145_2807591.2807644 scientific benchmarking: warmup, repeats,
 *       in-situ comparisons; never compare across machines/presets/corpora.
 *
 * Usage:
 *   node scripts/node-benchmark/harness.mjs [--corpus <name>|all] [--context <name>|all]
 *       [--engine v8] [--site dev_device|saq_server] [--repeats 5]
 *       [--min-time-ms 200] [--warmup-ms 300] [--repo saq_report] [--out-root out]
 *
 * Outputs per corpus:
 *   out/raw/<run_id>/node_harness_<corpus>.json       — raw exhibit (per-repeat data)
 *   out/measurements/<run_id>_<corpus>_record.json    — record v1 (validate with
 *                                                       scripts/measurement-schema/validate.py)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { collectHost } from '../host-introspect.mjs';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const CORPUS_ROOT = path.join(ROOT, 'corpus', 'benchmarks');

// --------------------------------------------------------------- CLI parsing

function parseArgs(argv) {
  const opts = {
    corpus: 'all',
    context: 'all',
    engine: 'v8',
    site: 'dev_device',
    repeats: 5,
    minTimeMs: 200,
    warmupMs: 300,
    repo: 'saq_report',
    outRoot: 'out',
  };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i]?.replace(/^--/, '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    if (!(key in opts) || argv[i + 1] === undefined) {
      console.error(`usage: node harness.mjs ${Object.keys(opts).map((k) => `--${k} <v>`).join(' ')}`);
      process.exit(1);
    }
    opts[key] = (key === 'repeats' || key === 'minTimeMs' || key === 'warmupMs')
      ? Number(argv[i + 1])
      : argv[i + 1];
  }
  return opts;
}

// -------------------------------------------------------------- git metadata

function gitMeta(repo) {
  // schema repo enum (underscore) -> working directory (hyphen where needed)
  const repoDirs = { v5: '.', ze_json: 'ze_json', saq_report: 'saq-report' };
  const cwd = path.join(ROOT, repoDirs[repo] ?? repo);
  const run = (args) => spawnSync('git', args, { cwd, encoding: 'utf8' });
  const hash = run(['rev-parse', '--short', 'HEAD']).stdout?.trim() ?? '';
  const dirty = (run(['status', '--porcelain']).stdout ?? '').trim().length > 0;
  if (!hash) {
    throw new Error(`git rev-parse failed for repo '${repo}' (cwd=${cwd})`);
  }
  return { hash, dirty };
}

// ------------------------------------------------------------- corpus loading

/** rootKey per store file, mirroring saq-report repositories/index.js (P2-2). */
const STORE_ROOT_KEYS = {
  'config_asisten.json': 'assistants',
  'courses.json': 'courses',
  'lecturers.json': 'lecturers',
  'schedules.json': 'schedules',
  'reports.json': null,
  'config_global.json': null,
};

function loadCorpus(name) {
  const dir = path.join(CORPUS_ROOT, name);
  const manifestPath = path.join(dir, 'MANIFEST.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`corpus manifest not found: ${manifestPath}`);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const docs = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith('.json') || entry.name === 'MANIFEST.json') {
      continue;
    }
    docs.push({
      name: entry.name,
      rootKey: STORE_ROOT_KEYS[entry.name] ?? null,
      utf8: fs.readFileSync(path.join(dir, entry.name), 'utf8'),
      bytes: fs.statSync(path.join(dir, entry.name)).size,
    });
  }
  docs.sort((a, b) => a.name.localeCompare(b.name));
  const totalBytes = docs.reduce((sum, d) => sum + d.bytes, 0);
  if (totalBytes !== manifest.total_bytes) {
    throw new Error(`corpus ${name}: bytes on disk (${totalBytes}) != manifest (${manifest.total_bytes})`);
  }
  return { name, dir, manifest, docs, totalBytes };
}

// ------------------------------------------------------------- v8 contexts
// One `run(doc-states)` call = one benchmark operation (batch semantics for
// multi-document corpora, matching the C++ benchmarks of P1-5/P1-6).

const CONTEXTS = {
  'body-parse': {
    purpose: 'v8 baseline (P2): JSON.parse over the corpus documents as delivered by express.json() body parsing',
    basisPapers: ['10.48550_arXiv.1902.08318', '10.1145_2807591.2807644'],
    prepare(docs) {
      return docs.map((doc) => ({ utf8: doc.utf8, bytes: doc.bytes }));
    },
    run(states) {
      let sink = 0;
      for (const state of states) {
        const parsed = JSON.parse(state.utf8);
        sink += typeof parsed === 'object' && parsed !== null ? 1 : 0;
      }
      return sink; // keep the parse alive across iterations
    },
    bytesPerOp(states) {
      return states.reduce((sum, s) => sum + s.bytes, 0);
    },
  },
  'store-read': {
    purpose: 'v8 baseline (P2): JSON.parse plus rootKey unwrap shaped like saq-report JsonRepository.read() (disk I/O excluded — identical across engines)',
    basisPapers: ['10.48550_arXiv.1902.08318', '10.1145_2807591.2807644'],
    prepare(docs) {
      return docs.map((doc) => ({ utf8: doc.utf8, bytes: doc.bytes, rootKey: doc.rootKey }));
    },
    run(states) {
      let sink = 0;
      for (const state of states) {
        const json = JSON.parse(state.utf8);
        const unwrapped = state.rootKey ? (json[state.rootKey] ?? []) : json;
        sink += Array.isArray(unwrapped) ? unwrapped.length : 1;
      }
      return sink;
    },
    bytesPerOp(states) {
      return states.reduce((sum, s) => sum + s.bytes, 0);
    },
  },
  'export-stringify': {
    purpose: 'v8 baseline (P2): JSON.stringify(data, null, 2) over parsed corpus documents, shaped like saq-report exportService/JsonRepository.write',
    basisPapers: ['10.48550_arXiv.1902.08318', '10.1145_2807591.2807644'],
    prepare(docs) {
      return docs.map((doc) => {
        const object = JSON.parse(doc.utf8);
        return { object, bytes: doc.bytes };
      });
    },
    run(states) {
      let sink = 0;
      for (const state of states) {
        const out = JSON.stringify(state.object, null, 2);
        sink += out.length;
      }
      return sink;
    },
    // bytes accounted for stringify = produced output bytes (measured once)
    bytesPerOp(states) {
      return states.reduce((sum, s) => {
        const out = JSON.stringify(s.object, null, 2);
        return sum + Buffer.byteLength(out, 'utf8');
      }, 0);
    },
  },
};

// ------------------------------------------------------------- measurement

function timedRepeat(run, states, minTimeMs) {
  const start = process.hrtime.bigint();
  const startCpu = process.cpuUsage();
  let ops = 0;
  let elapsedNs = 0;
  do {
    run(states);
    ops += 1;
    elapsedNs = Number(process.hrtime.bigint() - start) / 1e6; // ms
  } while (elapsedNs < minTimeMs);
  const cpu = process.cpuUsage(startCpu);
  return { ops, elapsedMs: elapsedNs, cpuMs: (cpu.user + cpu.system) / 1e3 };
}

function measureContext(context, states, opts) {
  const { repeats, minTimeMs, warmupMs } = opts;
  // Warmup: run the op in a loop for warmupMs so V8 tiers up before timing.
  const warmStart = process.hrtime.bigint();
  do {
    context.run(states);
  } while (Number(process.hrtime.bigint() - warmStart) / 1e6 < warmupMs);

  const repeatsData = [];
  for (let r = 0; r < repeats; r += 1) {
    if (typeof globalThis.gc === 'function') {
      globalThis.gc(); // node --expose-gc: reduce GC noise between repeats
    }
    repeatsData.push(timedRepeat(context.run, states, minTimeMs));
  }

  const bytesPerOp = context.bytesPerOp(states);
  const throughputs = repeatsData.map((d) => (bytesPerOp * d.ops) / (d.elapsedMs / 1e3));
  const opsPerSec = repeatsData.map((d) => d.ops / (d.elapsedMs / 1e3));
  const secondsPerOp = repeatsData.map((d) => d.elapsedMs / 1e3 / d.ops);
  const sorted = (arr) => [...arr].sort((a, b) => a - b);
  const median = (arr) => sorted(arr)[Math.floor(arr.length / 2)];
  const mean = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length;
  const stdev = (arr) => (arr.length > 1
    ? Math.sqrt(mean(arr.map((v) => (v - mean(arr)) ** 2)) * (arr.length / (arr.length - 1)))
    : 0);

  return {
    bytesPerOp,
    secondsMean: median(secondsPerOp),
    secondsStddev: stdev(secondsPerOp),
    bytesPerSecond: median(throughputs),
    documentsPerSecond: median(opsPerSec) * states.length,
    cpuSecondsMean: mean(repeatsData.map((d) => d.cpuMs / 1e3)) / mean(repeatsData.map((d) => d.ops)),
    iterationsMedian: median(repeatsData.map((d) => d.ops)),
    repeatsRaw: repeatsData,
  };
}

// ----------------------------------------------------------------- assembly

function buildRecord(opts, meta, corpus, results) {
  const notes = [
    'generator=node_harness',
    `min_time_ms=${opts.minTimeMs}`,
    `warmup_ms=${opts.warmupMs}`,
    `gc_between_repeats=${typeof globalThis.gc === 'function'}`,
    `repo=${opts.repo}`,
  ].join('; ');

  return {
    schema_version: '1.0.0',
    kind: 'benchmark',
    run_id: meta.runId,
    site: opts.site,
    generator: 'node_harness',
    library: {
      name: 'saq_baseline',
      version: process.versions.node,
      language_runtime: `node ${process.versions.node} (v8 ${process.versions.v8})`,
    },
    git_commit: { hash: meta.hash, dirty: meta.dirty, repo: opts.repo },
    host: meta.host,
    corpus: {
      name: corpus.name,
      document_count: corpus.manifest.document_count,
      total_bytes: corpus.manifest.total_bytes,
      ...(corpus.manifest.max_document_bytes
        ? { max_document_bytes: corpus.manifest.max_document_bytes } : {}),
      sha256: meta.corpusSha256,
    },
    config: {
      date_utc: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
      iterations: Math.max(1, Math.round(Math.max(...results.map((r) => r.extras.iterations_median)))),
      warmup_runs: 1,
      repeats: opts.repeats,
      cpu_pinning: false,
      threads: 1,
      notes,
    },
    results,
  };
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  const engineName = opts.engine;
  if (engineName !== 'v8') {
    console.error(`FAIL engine '${engineName}' not registered yet (P2 ships v8; ze-wasm64 lands in P3)`);
    process.exit(1);
  }

  const corpusNames = opts.corpus === 'all'
    ? ['synthetic_1k', 'synthetic_10k', 'synthetic_100k', 'synthetic_1mb', 'saq_payload_v1', 'checker_batch']
    : [opts.corpus];
  const contextNames = opts.context === 'all'
    ? Object.keys(CONTEXTS)
    : [opts.context];

  const git = gitMeta(opts.repo);
  const host = collectHost();
  const now = new Date();
  const runId = `${host.hostname}-${now.toISOString().replace(/[-:T]/g, '').slice(0, 14)}-${git.hash}`;
  const rawDir = path.join(ROOT, opts.outRoot, 'raw', runId);
  const measDir = path.join(ROOT, opts.outRoot, 'measurements');
  fs.mkdirSync(rawDir, { recursive: true });
  fs.mkdirSync(measDir, { recursive: true });

  console.log(`run_id     : ${runId}`);
  console.log(`git        : ${git.hash}${git.dirty ? ' (dirty)' : ''} / repo=${opts.repo}`);
  console.log(`engine     : ${engineName} | site: ${opts.site}`);
  console.log(`repeats    : ${opts.repeats} x >= ${opts.minTimeMs}ms (warmup ${opts.warmupMs}ms)`);
  console.log(`gc support : ${typeof globalThis.gc === 'function' ? 'yes (--expose-gc)' : 'no (run node --expose-gc for cleaner repeats)'}\n`);

  for (const corpusName of corpusNames) {
    const corpus = loadCorpus(corpusName);
    const manifestSha = createHash('sha256')
      .update(fs.readFileSync(path.join(corpus.dir, 'MANIFEST.json')))
      .digest('hex');
    const meta = { runId, hash: git.hash, dirty: git.dirty, host, corpusSha256: manifestSha };

    const results = [];
    const rawContexts = {};
    for (const contextName of contextNames) {
      const context = CONTEXTS[contextName];
      if (!context) {
        console.error(`FAIL unknown context '${contextName}'`);
        process.exit(1);
      }
      const states = context.prepare(corpus.docs);
      const sample = context.run(states); // one untimed call: fail fast + prime caches
      if (sample === undefined) {
        throw new Error(`context ${contextName} returned undefined on ${corpusName}`);
      }
      const stats = measureContext(context, states, opts);
      rawContexts[contextName] = stats.repeatsRaw;

      results.push({
        name: `${engineName}/${contextName}/${corpus.name}`,
        engine: engineName,
        status: 'ok',
        rationale: {
          purpose: context.purpose,
          basis_papers: context.basisPapers,
        },
        metrics: {
          seconds_mean: stats.secondsMean,
          seconds_stddev: stats.secondsStddev,
          bytes_per_second: stats.bytesPerSecond,
          documents_per_second: stats.documentsPerSecond,
          cpu_seconds: stats.cpuSecondsMean,
        },
        extras: {
          bytes_per_op: stats.bytesPerOp,
          iterations_median: stats.iterationsMedian,
          rss_bytes_snapshot: process.memoryUsage().rss,
        },
      });
      console.log(`[${corpus.name}] ${contextName.padEnd(16)} `
        + `${(stats.bytesPerSecond / 1e6).toFixed(1).padStart(9)} MB/s `
        + `cv=${((stats.secondsStddev / stats.secondsMean) * 100).toFixed(1)}%`);
    }

    // Raw exhibit first (never lose raw data because a later step failed).
    const exhibitPath = path.join(rawDir, `node_harness_${corpus.name}.json`);
    fs.writeFileSync(exhibitPath, `${JSON.stringify({
      run_id: runId,
      corpus: { name: corpus.name, manifest: corpus.manifest },
      engine: engineName,
      site: opts.site,
      repeats: opts.repeats,
      min_time_ms: opts.minTimeMs,
      warmup_ms: opts.warmupMs,
      contexts: rawContexts,
    }, null, 2)}\n`, 'utf8');

    const record = buildRecord(opts, meta, corpus, results);
    const recordPath = path.join(measDir, `${runId}_${corpus.name}_record.json`);
    fs.writeFileSync(recordPath, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
    console.log(`[+] exhibit -> ${path.relative(ROOT, exhibitPath)}`);
    console.log(`[+] record  -> ${path.relative(ROOT, recordPath)} (validate with scripts/measurement-schema/validate.py)\n`);
  }
}

main();
