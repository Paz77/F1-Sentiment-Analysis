import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  root: 'front end',
  publicDir: resolve(__dirname, 'front end/public'), 
  build: {
    outDir: 'dist',
    emptyOutDir: true
  },
  server: { port: 5173 },
  preview: { port: 4173 }
})