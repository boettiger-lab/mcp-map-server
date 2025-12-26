import { defineConfig } from 'vite';

export default defineConfig({
    server: {
        port: 8082,
        open: true
    },
    build: {
        outDir: 'dist',
        sourcemap: true
    },
    resolve: {
        alias: {
            // Map Node.js 'eventsource' to browser's built-in EventSource
            'eventsource': '/src/eventsource-shim.js'
        }
    },
    optimizeDeps: {
        esbuildOptions: {
            // Fix for Ajv default export issue
            define: {
                global: 'globalThis'
            }
        },
        exclude: ['@modelcontextprotocol/sdk']
    }
});
