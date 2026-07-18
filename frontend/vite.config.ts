/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    sourcemap: true,
    target: 'es2020',
  },
  test: {
    environment: 'node',
  },
})
