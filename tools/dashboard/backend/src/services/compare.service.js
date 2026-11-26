const Result = require('../models/Result');

/**
 * Compare service — membandingkan 2+ result terpilih.
 *
 * Guardrail (AGENTS.md §4): speedup hanya sah dalam satu run_id per site.
 * - BLOCK: beda run_id, site, kind, atau korpus.
 * - WARNING: beda runtime/toolchain/git-hash (narasi riset, bukan bukti),
 *   tree dirty, run exploratory.
 */

function refOf(item) {
	return { run_id: item.run_id, corpus_key: item.corpus_key, name: item.name };
}

/** Evaluasi guardrail murni agar dapat diuji tanpa MongoDB. */
function evaluateGuardrails(docs) {
	const blocks = [];
	const warnings = [];

	const runIds = new Set(docs.map((d) => d.run_id));
	const sites = new Set(docs.map((d) => d.site));
	const kinds = new Set(docs.map((d) => d.kind));
	const corpusKeys = new Set(docs.map((d) => d.corpus_key));
	const corpora = new Set(docs.map((d) => d.corpus_name));

	if (runIds.size > 1) {
		blocks.push({
			code: 'CROSS_RUN',
			message: `Perbandingan lintas run_id dilarang (AGENTS.md §4): ${[...runIds].join(' vs ')}. Bukti speedup hanya sah dalam satu run_id per site.`,
		});
	}
	if (sites.size > 1) {
		blocks.push({
			code: 'CROSS_SITE',
			message: `Perbandingan lintas site dilarang (AGENTS.md §4): ${[...sites].join(' vs ')}. Bukti speedup hanya sah dalam satu site.`,
		});
	}
	if (kinds.size > 1) {
		blocks.push({
			code: 'CROSS_KIND',
			message: `Mencampur kind berbeda: ${[...kinds].join(' vs ')}. Bandingkan benchmark dengan benchmark, test dengan test.`,
		});
	}
	if (corpusKeys.size > 1 || corpora.size > 1) {
		blocks.push({
			code: 'CROSS_CORPUS',
			message: `Mencampur korpus berbeda: ${[...corpora].join(' vs ')}. Pilih satu korpus agar perbandingan bermakna.`,
		});
	}

	const runtimes = new Set(docs.map((d) => d.library_runtime || '(unknown)'));
	if (runtimes.size > 1) {
		warnings.push({
			code: 'CROSS_RUNTIME',
			message: `Runtime berbeda (${[...runtimes].join(' vs ')}) — angka lintas runtime = narasi riset, bukan bukti kausal.`,
		});
	}

	const toolchains = new Set(docs.map((d) => d.toolchain || '(unknown)'));
	if (toolchains.size > 1) {
		warnings.push({
			code: 'CROSS_TOOLCHAIN',
			message: `Toolchain berbeda (${[...toolchains].join(' vs ')}) — angka lintas toolchain = narasi riset, bukan bukti kausal.`,
		});
	}

	const hashes = new Set(docs.map((d) => d.git_hash || '(none)'));
	if (hashes.size > 1) {
		warnings.push({
			code: 'CROSS_COMMIT',
			message: 'Git commit berbeda — pastikan delta yang diukur milik kode, bukan lingkungan.',
		});
	}

	if (docs.some((d) => d.dirty)) {
		warnings.push({
			code: 'DIRTY_TREE',
			message: 'Ada run dari working tree dirty — hash/cocokkan status di laporan (label -dirty).',
		});
	}
	if (docs.some((d) => d.exploratory)) {
		warnings.push({
			code: 'EXPLORATORY',
			message: 'Ada run exploratory (--allow-dirty) — bukti eksplorasi, bukan acceptance.',
		});
	}

	return { blocks, warnings };
}

async function compare(items) {
	if (!Array.isArray(items) || items.length < 2) {
		const err = new Error('Pilih minimal 2 result untuk dibandingkan');
		err.status = 400;
		throw err;
	}

	const docs = [];
	for (const key of items) {
		if (!key || !key.run_id || !key.corpus_key || !key.name) {
			const err = new Error('Setiap item butuh run_id + corpus_key + name');
			err.status = 400;
			throw err;
		}
		const doc = await Result.findOne({
			run_id: key.run_id,
			corpus_key: key.corpus_key,
			name: key.name,
		}).lean();
		if (!doc) {
			const err = new Error(`Result tidak ditemukan: ${key.run_id} / ${key.corpus_key} / ${key.name}`);
			err.status = 404;
			throw err;
		}
		docs.push(doc);
	}

	const unique = new Map();
	for (const doc of docs) unique.set(`${doc.run_id}::${doc.corpus_key}::${doc.name}`, doc);
	const picked = [...unique.values()].slice(0, 8);
	const { blocks, warnings } = evaluateGuardrails(picked);

	// Ratio: referensi = item pertama (default; UI bisa menandai baseline).
	const ref = picked[0];
	const refSeconds = (ref.metrics && ref.metrics.seconds_mean) || null;
	const refBps = (ref.metrics && ref.metrics.bytes_per_second) || null;

	const rows = picked.map((doc) => {
		const seconds = (doc.metrics && doc.metrics.seconds_mean) ?? null;
		const bps = (doc.metrics && doc.metrics.bytes_per_second) ?? null;
		const speedup = refSeconds && seconds ? refSeconds / seconds : null;
		const bpsRatio = refBps && bps ? bps / refBps : null;
		return {
			ref: refOf(doc),
			run_id: doc.run_id,
			corpus_key: doc.corpus_key,
			corpus_name: doc.corpus_name,
			name: doc.name,
			engine: doc.engine,
			site: doc.site,
			dirty: doc.dirty,
			exploratory: doc.exploratory,
			git_hash: doc.git_hash,
			runtime_label: doc.library_runtime,
			toolchain: doc.toolchain,
			date_utc: doc.date_utc,
			seconds_mean: seconds,
			bytes_per_second: bps,
			documents_per_second: (doc.metrics && doc.metrics.documents_per_second) || null,
			speedup_vs_ref: speedup,
			bps_ratio_vs_ref: bpsRatio,
			purpose: doc.purpose,
			basis_papers: doc.basis_papers || [],
		};
	});

	return { reference: refOf(ref), rows, checks: { blocks, warnings }, valid: blocks.length === 0 };
}

module.exports = { compare, evaluateGuardrails };
