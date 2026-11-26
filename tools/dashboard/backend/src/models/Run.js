const { Schema, model } = require('mongoose');

/**
 * Run — satu dokumen per FILE record di out/measurements.
 * Kunci unik: (run_id, corpus_key). run_id TIDAK unik per file:
 * satu run mengukur beberapa korpus (hingga 6 file per run_id).
 */
const ResultsBriefSchema = new Schema(
	{
		name: String,
		engine: String,
		status: String,
		family: String,
		action: String,
		subject: String,
		mode: String,
		seconds_mean: Number,
		bytes_per_second: Number,
	},
	{ _id: false, strict: false, minimize: false }
);

const RunSchema = new Schema(
	{
		run_id: { type: String, required: true },
		corpus_key: { type: String, required: true },
		file_name: { type: String, required: true },
		file_sha256: { type: String, required: true },
		imported_at: { type: Date, required: true },
		schema_version: { type: String },
		kind: { type: String, enum: ['benchmark', 'test'] },
		generator: { type: String },
		site: { type: String },
		library: { type: Schema.Types.Mixed },
		git_commit: { type: Schema.Types.Mixed },
		host: { type: Schema.Types.Mixed },
		corpus: { type: Schema.Types.Mixed },
		config: { type: Schema.Types.Mixed },
		record: { type: Schema.Types.Mixed, required: true },
		results_brief: [ResultsBriefSchema],
		derived: {
			n_results: Number,
			engines: [String],
			families: [String],
			modes: [String],
			statuses: [String],
			dirty: Boolean,
			exploratory: Boolean,
			scanner_mode: String,
			date_utc: Date,
			corpus_name: String,
			host_label: String,
			runtime_label: String,
			toolchain: String,
			names_text: String,
		},
	},
	{ minimize: false }
);

RunSchema.index({ run_id: 1, corpus_key: 1 }, { unique: true });
RunSchema.index({ 'derived.date_utc': -1 });
RunSchema.index({ site: 1, kind: 1, generator: 1 });
RunSchema.index({ 'derived.corpus_name': 1 });
RunSchema.index({ 'derived.names_text': 1 });

module.exports = model('Run', RunSchema);