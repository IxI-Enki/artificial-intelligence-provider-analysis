import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const destDir = join(root, 'src', 'lib', 'data');
mkdirSync(destDir, { recursive: true });

for (const file of ['providers.json', 'manifest.json']) {
  copyFileSync(join(root, 'data', file), join(destDir, file));
}

console.log('[OK] Synced data/*.json to src/lib/data/');
