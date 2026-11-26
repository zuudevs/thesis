const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');

const app = express();

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Routes
app.use('/api/runs', require('./routes/runs.routes'));
app.use('/api/results', require('./routes/results.routes'));
app.use('/api/charts', require('./routes/charts.routes'));
app.use('/api/compare', require('./routes/compare.routes'));
app.use('/api/imports', require('./routes/imports.routes'));
app.use('/api/stats', require('./routes/stats.routes'));

app.get('/api/health', (req, res) => {
	const isConnected = mongoose.connection.readyState === 1;

	res.status(isConnected ? 200 : 503).json({
		status: isConnected ? 'ok' : 'error',
		message: isConnected
			? 'Backend berjalan dan koneksi database sehat.'
			: 'Backend berjalan, tetapi koneksi database tidak tersedia.',
		database: {
			status: isConnected ? 'connected' : 'disconnected',
		},
	});
});

// 404 untuk API tidak dikenal.
app.use('/api', (req, res) => {
	res.status(404).json({ message: `Endpoint tidak ditemukan: ${req.method} ${req.originalUrl}` });
});

// Error handler terpusat.
app.use((err, req, res, next) => {
	const status = err.status || 500;
	console.error(`[api] ${status} ${err.message}`);
	res.status(status).json({ message: err.message, ...(status === 400 && err.errors ? { errors: err.errors } : {}) });
});

module.exports = app;