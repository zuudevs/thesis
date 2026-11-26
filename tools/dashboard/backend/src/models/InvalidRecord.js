const { Schema, model } = require('mongoose');

/**
 * InvalidRecord — record yang GAGAL validasi schema saat scan.
 * Ditampilkan di halaman Import agar operator bisa memperbaiki sumbernya.
 */
const InvalidRecordSchema = new Schema(
	{
		file_name: { type: String, required: true },
		file_path: String,
		scanned_at: { type: Date, required: true },
		reason: { type: String },
		validation_errors: { type: Schema.Types.Mixed },
	},
	{ minimize: false }
);

InvalidRecordSchema.index({ file_name: 1, scanned_at: 1 });

module.exports = model('InvalidRecord', InvalidRecordSchema);