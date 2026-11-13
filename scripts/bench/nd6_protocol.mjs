/**
 * nd6_protocol.mjs — pure protocol helpers for the ND-6 harness.
 *
 * No side effects: importable from unit tests and from nd6_bench.mjs.
 *
 * recordFilename(): site-aware measurement record filename. AUD-1: the
 *   previous implementation hardcoded the `-dev_device` suffix regardless of
 *   --site, so saq_server records were written with a dev_device filename
 *   while the `site` field inside the record was correct. The suffix must be
 *   derived from the actual site value. `prefix` defaults to `nd6` (the ND-6
 *   phase records); ND-9 passes `nd9` to keep its record names distinct.
 * gateDecision(): clean-tree acceptance gate. Audit directive + protocol
 *   §3.9: acceptance runs MUST execute from a clean tree (root + submodules).
 *   "Dirty" counts tracked modifications only — untracked owner-owned files
 *   do not change the measured code and are reported transparently without
 *   polluting the hash. A tracked change anywhere in root/ze_json/sa-report
 *   refuses the run unless --allow-dirty is given, in which case the record
 *   is labeled exploratory and must not be promoted as acceptance evidence.
 * wasmSha256(): identity of the actually-loaded wasm artifact — required in
 *   metadata so cross-site comparisons can verify byte-identical artifacts.
 *
 * @cite 10.1002_spe.3313 — in-run speedup ratios are only interpretable when
 *       code, artifact, and corpus identity are pinned per run.
 */
import fs from 'node:fs';
import crypto from 'node:crypto';

export const recordFilename = (runId, phase, site, prefix = 'nd6') =>
    `${runId}-${prefix}-${phase.toLowerCase()}-${site}.record.json`;

export const gateDecision = ({ rootDirty, zeDirty, saqDirty, allowDirty }) => {
    const dirtyRepos = [];
    if (rootDirty) dirtyRepos.push('v5(root)');
    if (zeDirty) dirtyRepos.push('ze_json');
    if (saqDirty) dirtyRepos.push('saq-report');
    if (dirtyRepos.length === 0) {
        return { ok: true, exploratory: false, dirtyRepos };
    }
    if (allowDirty) {
        return { ok: true, exploratory: true, dirtyRepos };
    }
    return { ok: false, exploratory: false, dirtyRepos };
};

export const wasmSha256 = (wasmPath) => {
    if (!fs.existsSync(wasmPath)) return null;
    return crypto.createHash('sha256')
        .update(fs.readFileSync(wasmPath))
        .digest('hex');
};
