const path = require('path');

require('dotenv').config({
	path: path.resolve(__dirname, '../../.env')
});

const app = require('./app');
const connectDatabase = require('./config/database');

const PORT = Number(process.env.BACKEND_PORT) || 3000;

async function startServer() {
	try {
		await connectDatabase();

		const server = app.listen(PORT, () => {
			console.log(`Backend running at http://localhost:${PORT}`);
		});

		server.on('error', (error) => {
			console.error(`HTTP server error: ${error.message}`);
			process.exit(1);
		});
	} catch (error) {
		console.error(`Failed to start backend: ${error}`);
		process.exit(1);
	}
}

startServer();