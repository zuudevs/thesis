/**
 * Unit tests for nd6_protocol.mjs (audit ND-6, task AUD-1).
 *
 * Run: node --test scripts/bench/tests/
 *
 * @cite 10.1002_spe.3313 — provenance discipline: the record filename must
 *       carry the actual site, and the clean-tree gate must separate
 *       acceptance runs from exploratory ones.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { recordFilename, gateDecision, wasmSha256 } from '../nd6_protocol.mjs';

test('record filename derives the suffix from the actual site', () => {
    assert.equal(
        recordFilename('zuu-20261112064001-0dcb418', 'D', 'dev_device'),
        'zuu-20261112064001-0dcb418-nd6-d-dev_device.record.json');
    assert.equal(
        recordFilename('server-lanjut-20261113004520-714cbb9', 'D', 'saq_server'),
        'server-lanjut-20261113004520-714cbb9-nd6-d-saq_server.record.json');
    assert.equal(
        recordFilename('x-20260101000000-abcdef0', 'A', 'saq_server'),
        'x-20260101000000-abcdef0-nd6-a-saq_server.record.json');
});

test('gate: clean tree passes without the exploratory label', () => {
    assert.deepEqual(
        gateDecision({ rootDirty: false, zeDirty: false, saqDirty: false, allowDirty: false }),
        { ok: true, exploratory: false, dirtyRepos: [] });
});

test('gate: tracked changes refuse the run (fail-fast)', () => {
    const g = gateDecision({ rootDirty: true, zeDirty: false, saqDirty: false, allowDirty: false });
    assert.equal(g.ok, false);
    assert.deepEqual(g.dirtyRepos, ['v5(root)']);
});

test('gate: --allow-dirty forces an exploratory run, never acceptance', () => {
    const g = gateDecision({ rootDirty: true, zeDirty: true, saqDirty: false, allowDirty: true });
    assert.equal(g.ok, true);
    assert.equal(g.exploratory, true);
    assert.deepEqual(g.dirtyRepos, ['v5(root)', 'ze_json']);
});

test('wasmSha256: 64-hex for the real artifact when present, null when absent', () => {
    const wasm = path.resolve(path.dirname(fileURLToPath(import.meta.url)),
        '..', '..', '..', 'ze_json', 'bindings', 'js', 'ze_json.wasm');
    const sha = wasmSha256(wasm);
    assert.ok(sha === null || /^[a-f0-9]{64}$/.test(sha), `unexpected sha: ${sha}`);
    assert.equal(wasmSha256(path.join(wasm, '..', 'does-not-exist.wasm')), null);
});
