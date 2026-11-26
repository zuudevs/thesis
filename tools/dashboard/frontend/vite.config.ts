import { fileURLToPath } from 'node:url';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const dashboardRoot = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, dashboardRoot, '');

	return {
		envDir: dashboardRoot,
		plugins: [react()],
		server: {
			port: Number(env.FRONTEND_PORT) || 5173,
			proxy: {
				'/api': {
					target: `http://127.0.0.1:${env.BACKEND_PORT || 3000}`,
					changeOrigin: true,
				},
			},
		},
		build: {
			outDir: 'dist',
			sourcemap: false,
		},
	};
});
