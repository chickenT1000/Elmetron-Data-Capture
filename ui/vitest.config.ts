import { defineConfig, configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'
import type { PluginOption } from 'vite'

export default defineConfig({
  plugins: [react() as PluginOption],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    css: false,
    exclude: [...configDefaults.exclude, 'playwright/**'],
  },
})

