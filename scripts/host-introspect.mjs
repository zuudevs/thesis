#!/usr/bin/env node
/**
 * host-introspect.mjs — host metadata collector for measurement records (AGENTS.md §4).
 *
 * Emits the `host` object of the measurement schema v1 (schemas/measurement.schema.json)
 * so dev_device and saq_server runs carry identical, comparable metadata.
 *
 * Usage:
 *   node scripts/host-introspect.mjs                # pretty JSON to stdout
 *   node scripts/host-introspect.mjs --save .temp/host.json
 *
 * As a module: `import { collectHost } from './host-introspect.mjs'` — used by
 * scripts/node-benchmark/harness.mjs (P2) so every record carries identical
 * host metadata on both sites.
 */
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const nodeMajor = Number(process.versions.node.split('.')[0]);
if (nodeMajor < 24) {
  console.error(`[warn] node ${process.versions.node} < 24 (project contract requires >= 24)`);
}

function archLabel(raw) {
  if (raw === 'x64') return 'x86_64';
  if (raw === 'arm64') return 'aarch64';
  return raw;
}

function ghz(mhz) {
  if (!mhz || mhz <= 0) return null;
  return `${(mhz / 1000).toFixed(2)} GHz`;
}

export function collectHost() {
  const cpus = os.cpus();
  const speeds = cpus.map((c) => c.speed).filter((s) => s > 0);
  let cpu_freq;
  if (speeds.length > 0) {
    const min = Math.min(...speeds);
    const max = Math.max(...speeds);
    const minG = ghz(min);
    const maxG = ghz(max);
    cpu_freq = minG === maxG ? minG : `${minG} - ${maxG}`;
  }

  return {
    hostname: os.hostname(),
    os: os.type(),
    os_version: typeof os.version === 'function' && os.version()
      ? `${os.release()} (${os.version()})`
      : os.release(),
    arch: archLabel(os.arch()),
    cpu_model: (cpus[0]?.model ?? '').trim(),
    cpu_cores: cpus.length,
    ...(cpu_freq ? { cpu_freq } : {}),
    ram_gb: Number((os.totalmem() / 2 ** 30).toFixed(1)),
    toolchain: `node ${process.versions.node} (v8 ${process.versions.v8})`,
  };
}

function main(argv) {
  const host = collectHost();
  const saveIndex = argv.indexOf('--save');
  if (saveIndex !== -1) {
    const target = argv[saveIndex + 1];
    if (!target) {
      console.error('usage: node scripts/host-introspect.mjs [--save <path>]');
      process.exit(1);
    }
    fs.mkdirSync(path.dirname(path.resolve(target)), { recursive: true });
    fs.writeFileSync(path.resolve(target), `${JSON.stringify(host, null, 2)}\n`, 'utf8');
    console.error(`[+] host metadata saved to ${path.resolve(target)}`);
  }
  process.stdout.write(`${JSON.stringify(host, null, 2)}\n`);
}

// CLI guard: run main() only when executed directly, never when imported.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2));
}
