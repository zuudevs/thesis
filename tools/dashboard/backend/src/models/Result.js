const { Schema, model } = require('mongoose');

/**
 * Result — satu dokumen per entri results[] (flatten untuk search/filter/agregasi).
 * Menyimpan seluruh metrik + extras apa adanya; rationale (purpose + basis_papers)
 * disimpan terpisah agar bisa dicari dan ditampilkan (AGENTS.md §4: record tanpa
 * rationale tidak boleh dipakai analisis).
 */
const ResultSchema = new Schema(
	{
		run_ref: { type: Schema.Types.ObjectId, ref: 'Run', index: true },
		run_id: { type: String, required: true },
		corpus_key: { type: String, required: true },
		name: { type: String, required: true },
		family: String,
		action: String,
		subject: String,
		mode: String,
		engine: { type: String },
		status: { type: String },
		purpose: String,
		basis_papers: [String],
		metrics: {
			type: new Schema(
				{
					bytes_per_second: Number,
					seconds_mean: Number,
					seconds_stddev: Number,
					cpu_seconds: Number,
					documents_per_second: Number,
					items_per_second: Number,
					peak_rss_bytes: Number,
				},
				{ _id: false, strict: false, minimize: false }
			),
		},
		extras: { type: Schema.Types.Mixed },
		site: String,
		kind: String,
		generator: String,
		library_name: String,
		library_runtime: String,
		git_hash: String,
		dirty: Boolean,
		exploratory: Boolean,
		scanner_mode: String,
		corpus_name: String,
		date_utc: Date,
		hostname: String,
		toolchain: String,
		cpu_model: String,
	},
	{ minimize: false }
);

ResultSchema.index({ run_id: 1, corpus_key: 1, name: 1 }, { unique: true });
ResultSchema.index({ site: 1, kind: 1, corpus_name: 1, engine: 1 });
ResultSchema.index({ name: 1 });
ResultSchema.index({ 'metrics.bytes_per_second': -1 });
ResultSchema.index({ 'metrics.seconds_mean': 1 });
ResultSchema.index({ purpose: 1 });

module.exports = model('Result', ResultSchema);