const mongoose = require('mongoose');

async function connectDatabase() {
	const host = process.env.MONGODB_HOST;
	const port = process.env.MONGODB_PORT;
	const name = process.env.MONGODB_NAME;

	if (!host || !port || !name) {
		throw new Error('Konfigurasi MongoDB tidak lengkap (MONGODB_HOST/PORT/NAME)');
	}

	const uri = process.env.MONGODB_URI || `mongodb://${host}:${port}/${name}`;

	mongoose.connection.on('error', (err) => console.error('[mongoose] error:', err.message));
	await mongoose.connect(uri, { serverSelectionTimeoutMS: 5000 });

	console.log(`MongoDB connected: ${name}`);
}

module.exports = connectDatabase;