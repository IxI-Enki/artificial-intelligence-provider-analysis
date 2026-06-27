import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

export default defineConfig({
  integrations: [svelte()],
  output: 'static',
  base: '/artificial-intelligence-provider-analysis/',
  build: {
    assets: '_assets',
  },
});
