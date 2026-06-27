import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const indexPath = join(root, 'dist', 'index.html');

if (!existsSync(indexPath)) {
  console.error('[ERROR] dist/index.html not found — run npm run build first');
  process.exit(1);
}

const html = readFileSync(indexPath, 'utf-8');
const forbidden = ['openrouter.ai', 'huggingface.co', 'cdn.jsdelivr.net'];
const hits = forbidden.filter((token) => html.includes(token));

if (hits.length) {
  console.error('[ERROR] Forbidden runtime URLs in built HTML:', hits.join(', '));
  process.exit(1);
}

console.log('[OK] Static build has no forbidden third-party fetch URLs');
