#!/usr/bin/env node
// ============================================================================
//  benchmark_ze_json_js.mjs — ze_json WASM (bindings/js) vs JSON.parse di Node
// ============================================================================
//  Perbandingan INTI skripsi: parser yang sama (korpus terpadu $SAMPLE,
//  join per fixture sha256), runtime yang sama (Node.js), dua implementasi:
//
//    json-parse            JSON.parse(str)                  — baseline V8
//    wasm-parse            ze.openDocument(str)             — end-to-end dari
//                            string JS: TextEncoder.encodeInto ke memori
//                            wasm + resetArena + scan penuh (biaya integrasi
//                            jujur, dilaporkan apa adanya)
//    wasm-parse-preloaded  payload byte sudah tertanam di memori wasm;
//                            per operasi: resetArena + create_session saja
//                            (parse-only ceiling, tanpa biaya encode)
//
//  Metodologi & skema report mengikuti saq-report/benchmark/benchmark-json.js
//  (schema 1.1.0: warmup + kalibrasi operasi per sampel + stats latency/
//  throughput + CI95) supaya research/analyze_benchmarks.py bisa menggabung
//  ketiga paket (ze_json C++, ze_json_js, saq-report) per fixture sha256.
//
//  Report SELF-CONTAINED (tanpa sidecar) di $RAW/benchmark/ze_json_js/
//  <RUN_ID>.json — kontrak audit sama dengan paket saq-report.
//
//  Butuh Node.js >= 24 (WASM memory64 aktif default); versi lebih tua:
//    node --experimental-wasm-memory64 benchmark_ze_json_js.mjs
//
//  Pemakaian:
//    $env:SAMPLE=...; $env:RAW=...
//    node research/benchmark_ze_json_js.mjs
//    node research/benchmark_ze_json_js.mjs --samples=10 --warmup=50
// ============================================================================
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { performance, PerformanceObserver } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { ZeJson } from "../ze_json/bindings/js/ze_json.mjs";

const WORKSPACE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ZE_REPO = path.join(WORKSPACE, "ze_json");
const MANIFEST_PATH = path.join(process.env.RAW ?? "", "ze_json", "manifest.json");

// Guard memori: fixture di atas batas ini di-skip untuk mode wasm (tape
// 8 byte/entri x size/2 menumpuk cepat). Korpus terpadu saat ini tidak
// punya fixture di atas 256 MB, jadi guard ini hanya pengaman.
const WASM_MAX_BYTES = 256 * 1024 * 1024;

const MODES = ["json-parse", "wasm-parse", "wasm-parse-preloaded"];
const MODE_LABEL = {
  "json-parse": "JSON.parse (V8, proses sama)",
  "wasm-parse": "ze_json WASM end-to-end (encode + scan)",
  "wasm-parse-preloaded": "ze_json WASM parse-only (payload pra-tanam)",
};

const DEFAULTS = {
  input: process.env.SAMPLE ?? "",
  out: path.join(process.env.RAW ?? "", "benchmark", "ze_json_js"),
  samples: 100,
  warmupMs: 100,
  sampleTargetMs: 20,
  maxOperationsPerSample: 1_000_000,
  deviceLabel: os.hostname(),
  wasm: null,
  modes: [...MODES],
};

function parseArgs(argv) {
  const options = { ...DEFAULTS, modes: [...DEFAULTS.modes] };
  for (const arg of argv) {
    if (arg === "--help" || arg === "-h") { options.help = true; continue; }
    const [rawKey, ...valueParts] = arg.replace(/^--/, "").split("=");
    const value = valueParts.join("=");
    if (!valueParts.length) throw new Error(`Expected --key=value, got: ${arg}`);
    switch (rawKey) {
      case "input": options.input = value; break;
      case "out": options.out = value; break;
      case "samples": options.samples = positiveInteger(value, rawKey); break;
      case "warmup": options.warmupMs = nonNegativeNumber(value, rawKey); break;
      case "sample-target-ms": options.sampleTargetMs = positiveNumber(value, rawKey); break;
      case "max-operations-per-sample": options.maxOperationsPerSample = positiveInteger(value, rawKey); break;
      case "device-label":
        if (!value) throw new Error("--device-label must be a non-empty label");
        options.deviceLabel = value; break;
      case "wasm": options.wasm = value || null; break;
      case "modes": {
        const allowed = new Set(MODES);
        options.modes = value.split(",").map((item) => item.trim()).filter(Boolean);
        if (!options.modes.length || options.modes.some((mode) => !allowed.has(mode))) {
          throw new Error(`--modes must be a comma-separated subset of: ${[...allowed].join(", ")}`);
        }
        break;
      }
      default: throw new Error(`Unknown option: --${rawKey}`);
    }
  }
  if (!options.samples) throw new Error("--samples must be greater than zero");
  return options;
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) throw new Error(`--${name} must be a positive integer`);
  return parsed;
}
function positiveNumber(value, name) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) throw new Error(`--${name} must be greater than zero`);
  return parsed;
}
function nonNegativeNumber(value, name) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) throw new Error(`--${name} must be zero or greater`);
  return parsed;
}

function printHelp() {
  console.log(`ze_json JS binding (WASM) vs JSON.parse benchmark

Usage:
  node research/benchmark_ze_json_js.mjs [options]

Options:
  --input=$SAMPLE              Directory scanned recursively for .json files
  --out=$RAW/benchmark/ze_json_js  Output directory, or a .json file path
  --samples=100                Number of measured batches per mode and fixture
  --warmup=100                 Warm-up duration per mode and fixture (ms)
  --sample-target-ms=20        Target duration for each measured batch (ms)
  --max-operations-per-sample=1000000  Safety cap for operations in one batch
  --modes=json-parse,wasm-parse,wasm-parse-preloaded  Subset of modes
  --device-label=LABEL         Device/site tag (default: hostname); run-id prefix
  --wasm=PATH                  Custom ze_json_core.wasm (default: bindings/js)
  --help                       Show this help

Requires Node.js >= 24 (WASM memory64). Older runtimes:
  node --experimental-wasm-memory64 research/benchmark_ze_json_js.mjs
`);
}

function walkJsonFiles(directory) {
  if (!fs.existsSync(directory)) throw new Error(`Input directory does not exist: ${directory}`);
  const found = [];
  const walk = (current) => {
    const entries = fs.readdirSync(current, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) walk(absolute);
      else if (entry.isFile() && entry.name.toLowerCase().endsWith(".json")) found.push(absolute);
    }
  };
  walk(directory);
  return found.sort((a, b) => path.relative(directory, a).split(path.sep).join("/").localeCompare(
    path.relative(directory, b).split(path.sep).join("/")
  ));
}

// Manifest korpus terpadu ($RAW/ze_json/manifest.json) = jangkar join
// lintas-paket: path relatif ke akar $SAMPLE + sha256 + size_bytes.
function loadCorpusManifest() {
  if (!fs.existsSync(MANIFEST_PATH)) return new Map();
  const parsed = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));
  const entries = Array.isArray(parsed.files) ? parsed.files : [];
  const map = new Map();
  for (const entry of entries) {
    if (!entry.path) continue;
    map.set(path.resolve(process.env.SAMPLE ?? "", entry.path), entry);
  }
  return map;
}

function rootType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function memorySnapshot() {
  const usage = process.memoryUsage();
  return {
    heap_used: usage.heapUsed,
    heap_total: usage.heapTotal,
    rss: usage.rss,
    external: usage.external,
    array_buffers: usage.arrayBuffers
  };
}

function machineSnapshot() {
  const cpus = os.cpus();
  const speeds = cpus.map((cpu) => cpu.speed).filter(Boolean);
  const snapshot = {
    cpu_model: cpus[0]?.model || null,
    cpu_speed_mhz_min: speeds.length ? Math.min(...speeds) : null,
    cpu_speed_mhz_max: speeds.length ? Math.max(...speeds) : null,
    logical_cores: cpus.length,
    total_memory_bytes: os.totalmem(),
    free_memory_bytes: os.freemem(),
    loadavg: os.loadavg()
  };
  if (process.platform === "linux") {
    try {
      const governorPath = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor";
      if (fs.existsSync(governorPath)) {
        snapshot.cpu_governor = fs.readFileSync(governorPath, "utf8").trim();
      }
      const cpuinfo = fs.readFileSync("/proc/cpuinfo", "utf8");
      const currentMhz = Array.from(cpuinfo.matchAll(/cpu MHz\s*:\s*([\d.]+)/g))
        .map((match) => Number(match[1]))
        .filter((value) => Number.isFinite(value));
      if (currentMhz.length) {
        snapshot.cpu_current_freq_mhz_min = Math.min(...currentMhz);
        snapshot.cpu_current_freq_mhz_max = Math.max(...currentMhz);
        snapshot.cpu_current_freq_mhz_mean =
          currentMhz.reduce((sum, value) => sum + value, 0) / currentMhz.length;
      }
    } catch {
      // Detail Linux tidak tersedia — field tetap null, bukan error.
    }
  }
  return snapshot;
}

function createGcTracker() {
  try {
    const state = { events: 0, total_pause_ms: 0 };
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        state.events += 1;
        state.total_pause_ms += entry.duration;
      }
    });
    observer.observe({ entryTypes: ["gc"] });
    return {
      snapshot() {
        return {
          events: state.events,
          total_pause_ms: Number(state.total_pause_ms.toFixed(3))
        };
      },
      dispose() {
        try { observer.disconnect(); } catch { /* noop */ }
      }
    };
  } catch {
    return null;
  }
}

function tCritical975(df) {
  if (df < 1) return null;
  const chiSquare = df *
    Math.pow(1 - 2 / (9 * df) + 1.959963984540054 * Math.sqrt(2 / (9 * df)), 3);
  return 1.959963984540054 * Math.sqrt(df / chiSquare);
}

function confidenceInterval95(values, mean) {
  const count = values.length;
  if (count < 2) return null;
  const sampleVariance =
    values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / (count - 1);
  const standardError = Math.sqrt(sampleVariance / count);
  const t = tCritical975(count - 1);
  if (!t) return null;
  const halfWidth = t * standardError;
  return {
    low_ns: mean - halfWidth,
    high_ns: mean + halfWidth,
    half_width_ns: halfWidth,
    confidence_level: 0.95,
    method: "mean ± t(0.975, n-1) * SE; sample variance; t via Wilson–Hilferty"
  };
}

function elapsedNs(start) {
  return Number(process.hrtime.bigint() - start);
}

// Loop ukur khusus per mode — tanpa dispatch callback di hot loop.
let blackhole;
function runBatch(mode, operations, context) {
  let last;
  const started = process.hrtime.bigint();

  if (mode === "json-parse") {
    for (let i = 0; i < operations; i += 1) last = JSON.parse(context.raw);
  } else if (mode === "wasm-parse") {
    // End-to-end: encode string ke memori wasm + resetArena + scan penuh.
    for (let i = 0; i < operations; i += 1) last = context.ze.openDocument(context.raw);
  } else if (mode === "wasm-parse-preloaded") {
    // Payload byte sudah tertanam; per operasi hanya resetArena + scan.
    const { src, srcSize, tapeBase, tapeEntries } = context.preloaded;
    const arena = context.ze.arena;
    const errRef = context.ze.errRef;
    const createSession = context.ze.ex.create_session;
    for (let i = 0; i < operations; i += 1) {
      context.ze.resetArena();
      last = createSession(src, srcSize, tapeBase, tapeEntries, arena, errRef);
      if (last === 0n) throw new Error("create_session gagal pada payload pra-tanam");
    }
  } else {
    throw new Error(`Unsupported mode: ${mode}`);
  }

  const durationNs = elapsedNs(started);
  blackhole = last;
  return { operations, elapsed_ns: durationNs, ns_per_operation: durationNs / operations };
}

function calibrateOperations(mode, context, targetNs, maxOperations) {
  let operations = 1;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const result = runBatch(mode, operations, context);
    if (result.elapsed_ns >= targetNs || operations >= maxOperations) return operations;
    const estimated = Math.ceil((targetNs / Math.max(result.elapsed_ns, 1)) * operations * 0.85);
    operations = Math.min(maxOperations, Math.max(operations + 1, estimated));
  }
  return operations;
}

function runWarmup(mode, operations, context, warmupMs) {
  if (warmupMs <= 0) return;
  const deadline = performance.now() + warmupMs;
  do {
    runBatch(mode, operations, context);
  } while (performance.now() < deadline);
}

function percentile(sortedValues, percentileValue) {
  if (!sortedValues.length) return null;
  const rank = Math.max(1, Math.ceil(percentileValue * sortedValues.length));
  return sortedValues[Math.min(rank - 1, sortedValues.length - 1)];
}

function calculateStats(samples, payloadBytes) {
  const values = samples.map((sample) => sample.ns_per_operation).sort((a, b) => a - b);
  const count = values.length;
  const mean = values.reduce((sum, value) => sum + value, 0) / count;
  const variance = values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / count;
  const totalOperations = samples.reduce((sum, sample) => sum + sample.operations, 0);
  const totalElapsedNs = samples.reduce((sum, sample) => sum + sample.elapsed_ns, 0);
  const totalBytes = payloadBytes * totalOperations;
  const seconds = totalElapsedNs / 1e9;
  return {
    total_operations: totalOperations,
    total_elapsed_ns: totalElapsedNs,
    latency: {
      min_ns: values[0],
      max_ns: values[count - 1],
      mean_ns: mean,
      mean_ci95_ns: confidenceInterval95(values, mean),
      median_ns: percentile(values, 0.50),
      p95_ns: percentile(values, 0.95),
      p99_ns: percentile(values, 0.99),
      stddev_ns: Math.sqrt(variance)
    },
    throughput: {
      operations_per_second: seconds > 0 ? totalOperations / seconds : null,
      mib_per_second: seconds > 0 ? (totalBytes / (1024 * 1024)) / seconds : null,
      data_processed_bytes: totalBytes
    },
    samples
  };
}

function measureMode(mode, context, options, payloadBytes) {
  const targetNs = options.sampleTargetMs * 1e6;
  const operationsPerSample = calibrateOperations(
    mode, context, targetNs, options.maxOperationsPerSample
  );
  runWarmup(mode, operationsPerSample, context, options.warmupMs);

  const samples = [];
  const modeStartedAtMs = performance.now();
  for (let index = 0; index < options.samples; index += 1) {
    const sampleStartedDeltaMs = performance.now() - modeStartedAtMs;
    const result = runBatch(mode, operationsPerSample, context);
    const seconds = result.elapsed_ns / 1e9;
    const bytes = payloadBytes * result.operations;
    samples.push({
      sample: index + 1,
      started_at_delta_ms: Number(sampleStartedDeltaMs.toFixed(3)),
      operations: result.operations,
      elapsed_ns: result.elapsed_ns,
      ns_per_operation: result.ns_per_operation,
      operations_per_second: seconds > 0 ? result.operations / seconds : null,
      mib_per_second: seconds > 0 ? (bytes / (1024 * 1024)) / seconds : null
    });
  }
  const stats = calculateStats(samples, payloadBytes);
  return {
    operations_per_sample: operationsPerSample,
    warmup_ms: options.warmupMs,
    target_sample_ms: options.sampleTargetMs,
    ...stats
  };
}

function getZeJsonCommit() {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], { cwd: ZE_REPO, stdio: ["ignore", "pipe", "ignore"] })
      .toString("utf8").trim();
  } catch {
    return null;
  }
}

function aggregateMode(results, mode) {
  let totalOperations = 0;
  let totalElapsedNs = 0;
  let totalBytes = 0;
  for (const result of results) {
    const measurement = result.measurements?.[mode];
    if (!measurement || measurement.skipped) continue;
    totalOperations += measurement.total_operations;
    totalElapsedNs += measurement.total_elapsed_ns;
    totalBytes += measurement.throughput.data_processed_bytes;
  }
  const seconds = totalElapsedNs / 1e9;
  return {
    total_operations: totalOperations,
    total_elapsed_ns: totalElapsedNs,
    data_processed_bytes: totalBytes,
    aggregate_operations_per_second: seconds > 0 ? totalOperations / seconds : null,
    aggregate_mib_per_second: seconds > 0 ? (totalBytes / (1024 * 1024)) / seconds : null
  };
}

function aggregateByGroup(results, modes) {
  const groups = {};
  for (const result of results) {
    const group = result.group || "unclassified";
    if (!groups[group]) groups[group] = {};
  }
  for (const group of Object.keys(groups)) {
    const groupResults = results.filter((result) => (result.group || "unclassified") === group);
    for (const mode of modes) groups[group][mode] = aggregateMode(groupResults, mode);
  }
  return groups;
}

// Kapasitas region per fixture — meniru metodologi corpus_benchmark:
// tape = size/2 + 64 entri; arena dibesarkan mengikuti dokumen agar
// Session + string unescape tidak pernah jadi batasan.
function regionSizes(sizeBytes) {
  const payloadCap = sizeBytes + 64;
  const tapeEntries = Math.floor(sizeBytes / 2) + 64;
  const arenaCap = Math.min(Math.max(sizeBytes / 8, 1024 * 1024), 64 * 1024 * 1024);
  return { payloadCap, tapeEntries, arenaCap: Math.ceil(arenaCap) };
}

async function run() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) return printHelp();

  if (!process.env.SAMPLE || !process.env.RAW) {
    throw new Error(
      "Set SAMPLE and RAW environment variables first. Example (PowerShell): " +
      "$env:SAMPLE=<dir>; $env:RAW=<dir>; node research/benchmark_ze_json_js.mjs"
    );
  }

  // Muat wasm SEKALI di luar loop untuk validasi runtime (memory64).
  let wasmBinary;
  try {
    wasmBinary = fs.readFileSync(options.wasm || path.join(ZE_REPO, "bindings", "js", "ze_json_core.wasm"));
  } catch {
    wasmBinary = null; // biarkan ZeJson.load mencoba kandidat default-nya
  }
  const probe = await ZeJson.load({ binary: wasmBinary ?? undefined });
  const zeVersion = probe.versionNumber ? String(probe.versionNumber) : null;
  console.log(`ze_json wasm version: ${zeVersion ?? "pra-v0.1.0"}`);
  probe.close();

  const inputDirectory = path.resolve(options.input);
  const files = walkJsonFiles(inputDirectory);
  if (!files.length) throw new Error(`No .json files found under ${inputDirectory}`);
  const corpusManifest = loadCorpusManifest();
  const gcTracker = createGcTracker();

  const startedAt = new Date();
  const startedMemory = memorySnapshot();
  const machineStarted = machineSnapshot();
  const errors = [];
  const results = [];
  let validFixtures = 0;
  let totalPayloadBytes = 0;

  console.log(`Found ${files.length} JSON fixture(s) in ${inputDirectory}.`);
  console.log(`Device: ${options.deviceLabel} | Modes: ${options.modes.join(", ")} | samples: ${options.samples} | target: ${options.sampleTargetMs} ms`);

  for (const filePath of files) {
    const relativePath = path.relative(inputDirectory, filePath).split(path.sep).join("/");
    const manifestEntry = corpusManifest.get(filePath);
    const fixture = manifestEntry ? {
      fixture_id: manifestEntry.fixture_id
        ?? relativePath.replace(/\.json$/i, "").replace(/[^a-zA-Z0-9._-]+/g, "."),
      group: manifestEntry.group ?? "unclassified",
      description: manifestEntry.description ?? null,
    } : {
      fixture_id: relativePath.replace(/\.json$/i, "").replace(/[^a-zA-Z0-9._-]+/g, "."),
      group: "unclassified",
      description: "JSON file discovered under input directory; no manifest entry."
    };

    let raw;
    let bytes;
    let parsed;
    let fileStats;
    try {
      bytes = fs.readFileSync(filePath);
      raw = bytes.toString("utf8");
      fileStats = fs.statSync(filePath);
      parsed = JSON.parse(raw);
    } catch (error) {
      // Korpus negatif JSON_checker (fail*.json) MEMANG wajib ditolak parser.
      if (/^JSON_checker\/fail/i.test(relativePath)) {
        results.push({
          fixture_id: fixture.fixture_id,
          group: fixture.group,
          file: relativePath,
          status: "skipped",
          reason: "korpus negatif JSON_checker (fail*) — wajib ditolak parser"
        });
        console.log(`  [SKIP-NEGATIVE] ${relativePath}`);
        continue;
      }
      const entry = {
        fixture_id: fixture.fixture_id,
        file: relativePath,
        stage: "load-or-validate",
        error_name: error.name,
        message: error.message
      };
      errors.push(entry);
      results.push({
        fixture_id: fixture.fixture_id,
        group: fixture.group,
        file: relativePath,
        status: "error",
        error: entry
      });
      console.error(`  [INVALID] ${relativePath}: ${error.message}`);
      continue;
    }

    const sizeBytes = fileStats.size;
    const wasmTooBig = sizeBytes > WASM_MAX_BYTES;
    const sizes = regionSizes(sizeBytes);

    // Instance wasm per fixture dengan region sesuai ukuran dokumen.
    let ze = null;
    try {
      ze = await ZeJson.load({
        binary: wasmBinary ?? undefined,
        payloadCap: sizes.payloadCap,
        tapeEntries: sizes.tapeEntries,
        arenaCap: sizes.arenaCap,
      });
    } catch (error) {
      const entry = {
        fixture_id: fixture.fixture_id,
        file: relativePath,
        stage: "wasm-instance",
        error_name: error.name,
        message: error.message
      };
      errors.push(entry);
      results.push({
        fixture_id: fixture.fixture_id,
        group: fixture.group,
        file: relativePath,
        status: "error",
        error: entry
      });
      console.error(`  [WASM-INSTANCE] ${relativePath}: ${error.message}`);
      continue;
    }

    validFixtures += 1;
    totalPayloadBytes += sizeBytes;
    const context = { raw, ze };
    const measurements = {};

    console.log(`  [RUN] ${relativePath} (${sizeBytes} bytes, tape ${sizes.tapeEntries} entri)`);

    try {
      // Validasi sekali di luar timing: scan ze_json harus sukses (root
      // OBJECT) sebelum mode wasm diukur; JSON.parse sudah lolos di atas.
      if (!wasmTooBig) {
        try {
          const probeDoc = ze.openDocument(raw);
          if (probeDoc.session === 0n) throw new Error("scan gagal");
        } catch (error) {
          for (const mode of options.modes) {
            if (mode !== "json-parse") {
              measurements[mode] = {
                skipped: true,
                reason: `ze_json menolak dokumen: ${error.message}`
              };
            }
          }
          console.warn(`  [SKIP-WASM] ${relativePath}: ${error.message}`);
        }
      }

      for (const mode of options.modes) {
        if (measurements[mode]?.skipped) continue;
        if (mode !== "json-parse" && wasmTooBig) {
          measurements[mode] = {
            skipped: true,
            reason: `fixture ${sizeBytes} bytes > guard ${WASM_MAX_BYTES} bytes — mode wasm di-skip`
          };
          console.warn(`  [SKIP] ${relativePath}: ${mode} dilewati (fixture > 256 MB)`);
          continue;
        }
        if (mode === "wasm-parse-preloaded") {
          // Tanam payload sekali di luar timing; operasi = scan saja.
          const regions = ze.regions;
          const [src, srcSize] = ze.writeRegion(
            regions.payloadBase, regions.payloadCap, bytes);
          context.preloaded = {
            src, srcSize,
            tapeBase: regions.tapeBase,
            tapeEntries: regions.tapeEntries,
          };
        }
        measurements[mode] = measureMode(mode, context, options, sizeBytes);      }

      const memoryAfter = memorySnapshot();
      const gcAfter = gcTracker ? gcTracker.snapshot() : null;
      results.push({
        fixture_id: fixture.fixture_id,
        group: fixture.group,
        description: fixture.description,
        file: relativePath,
        status: "success",
        payload: {
          size_bytes: sizeBytes,
          sha256: crypto.createHash("sha256").update(raw, "utf8").digest("hex"),
          root_type: rootType(parsed)
        },
        wasm: {
          payload_cap_bytes: Number(sizes.payloadCap),
          tape_entries: sizes.tapeEntries,
          arena_cap_bytes: sizes.arenaCap,
          version: zeVersion
        },
        measurements,
        gc: gcAfter,
        memory: { rss_after: memoryAfter.rss, heap_used_after: memoryAfter.heap_used }
      });
    } catch (error) {
      const entry = {
        fixture_id: fixture.fixture_id,
        file: relativePath,
        stage: "measurement",
        error_name: error.name,
        message: error.message
      };
      errors.push(entry);
      results.push({
        fixture_id: fixture.fixture_id,
        group: fixture.group,
        file: relativePath,
        status: "error",
        error: entry,
        measurements
      });
      console.error(`  [ERROR] ${relativePath}: ${error.message}`);
    } finally {
      ze.close();
    }
  }

  const finishedAt = new Date();
  const finishedMemory = memorySnapshot();
  const machineFinished = machineSnapshot();
  const successful = results.filter((result) => result.status === "success");
  const skippedNegative = results.filter((result) => result.status === "skipped").length;
  const gitCommit = getZeJsonCommit();
  const labelSafe = String(options.deviceLabel).trim().replace(/[^a-zA-Z0-9._-]+/g, "-") || "device";
  const startedStamp = startedAt.toISOString().replace(/[-:.TZ]/g, "").slice(0, 17);
  const runId = `${labelSafe}-${startedStamp}-${(gitCommit || "nogit").slice(0, 8)}`;
  const summary = {
    total_fixtures: files.length,
    successful_fixtures: successful.length,
    skipped_negative_fixtures: skippedNegative,
    failed_fixtures: results.filter((result) => result.status === "error").length,
    modes: Object.fromEntries(options.modes.map((mode) => [mode, aggregateMode(successful, mode)])),
    by_group: aggregateByGroup(successful, options.modes)
  };
  const report = {
    schema_version: "1.1.0",
    metadata: {
      benchmark_name: "ze-json-js-binding",
      benchmark_version: "1.0.0",
      run_id: runId,
      started_at: startedAt.toISOString(),
      finished_at: finishedAt.toISOString(),
      duration_ms: Number(finishedAt - startedAt),
      source: {
        repository: "ze_json (bindings/js)",
        git_commit: gitCommit
      },
      runtime: {
        runtime: "Node.js",
        node_version: process.version,
        v8_version: process.versions.v8,
        platform: process.platform,
        architecture: process.arch,
        cpu_model: os.cpus()[0]?.model || null,
        logical_cores: os.cpus().length,
        total_memory_bytes: os.totalmem(),
        wasm_memory64: true,
        ze_json_wasm_version: zeVersion
      },
      environment: {
        device_label: options.deviceLabel,
        hostname: os.hostname(),
        os_release: os.release(),
        machine_started: machineStarted,
        machine_finished: machineFinished,
        node_flags: process.execArgv,
        node_options_env: process.env.NODE_OPTIONS || null,
        runtime_versions: { ...process.versions }
      },
      parser: {
        name: "ze_json (WASM memory64)",
        implementation: "ze_json_core.wasm via bindings/js/ze_json.mjs",
        baseline: "JSON.parse (V8 native, proses sama)",
        note: "wasm-parse mencakup TextEncoder.encodeInto string->UTF-8 ke memori wasm (biaya integrasi); wasm-parse-preloaded mengukur scan saja tanpa encode"
      },
      configuration: {
        input_directory: inputDirectory,
        modes: options.modes,
        warmup_ms: options.warmupMs,
        samples: options.samples,
        sample_target_ms: options.sampleTargetMs,
        max_operations_per_sample: options.maxOperationsPerSample,
        wasm_max_bytes_guard: WASM_MAX_BYTES,
        region_sizing: "payloadCap=size+64; tapeEntries=size/2+64 (metodologi corpus_benchmark); arenaCap=clamp(size/8, 1MiB, 64MiB)",
        measurement_scope: {
          primary_cross_device: "wasm-parse",
          environment_sensitive: ["json-parse", "wasm-parse-preloaded"],
          comparison_join_keys: ["fixture_id", "mode", "payload.sha256"]
        },
        concurrency: 1,
        execution_mode: "sequential",
        percentile_method: "nearest-rank over batch-normalized ns_per_operation",
        standard_deviation: "population standard deviation over batch-normalized ns_per_operation",
        confidence_interval: "95% CI over batch-normalized ns_per_operation mean (t-distribution)"
      },
      process_memory: {
        heap_used_before: startedMemory.heap_used,
        heap_used_after: finishedMemory.heap_used,
        heap_used_delta: finishedMemory.heap_used - startedMemory.heap_used,
        rss_before: startedMemory.rss,
        rss_after: finishedMemory.rss
      },
      gc: gcTracker ? gcTracker.snapshot() : null
    },
    dataset: {
      directory: inputDirectory,
      files_discovered: files.length,
      files_valid: validFixtures,
      files_invalid: files.length - validFixtures,
      files_skipped_negative: skippedNegative,
      total_size_bytes: totalPayloadBytes
    },
    summary,
    results,
    errors
  };

  const requestedOutput = options.out;
  const outputPath = requestedOutput.toLowerCase().endsWith(".json")
    ? requestedOutput
    : path.join(requestedOutput, `${runId}.json`);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2), "utf8");

  console.log("\nBenchmark finished.");
  console.log(`Successful fixtures: ${successful.length}/${files.length}`);
  for (const mode of options.modes) {
    const aggregate = summary.modes[mode];
    console.log(`  ${mode}: ${aggregate.aggregate_mib_per_second?.toFixed(2) ?? "n/a"} MiB/s (agg)`);
  }
  console.log(`Report: ${outputPath} (schema 1.1.0, device: ${options.deviceLabel})`);
  if (gcTracker) gcTracker.dispose();
  if (errors.length) process.exitCode = 1;
}

try {
  await run();
} catch (error) {
  console.error(`[benchmark-ze-json-js] ${error.message}`);
  process.exitCode = 1;
}
