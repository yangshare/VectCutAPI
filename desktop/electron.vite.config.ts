import { defineConfig } from 'electron-vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  main: {
    build: {
      rollupOptions: {
        input: resolve('electron/main.ts'),
        output: { entryFileNames: 'index.js' },
      },
    },
  },
  preload: {
    build: {
      rollupOptions: {
        input: resolve('electron/preload.ts'),
        output: { entryFileNames: 'index.js' },
      },
    },
  },
  renderer: {
    plugins: [react()],
    root: 'src',
    build: { rollupOptions: { input: resolve('src/index.html') } },
  },
});
