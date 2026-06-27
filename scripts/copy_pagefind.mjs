import { cpSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'dist', 'pagefind');
const dest = join(root, 'public', 'pagefind');

if (!existsSync(src)) {
  console.warn('[WARN] dist/pagefind not found — skip copy to public/pagefind');
  process.exit(0);
}

mkdirSync(join(root, 'public'), { recursive: true });
cpSync(src, dest, { recursive: true });
console.log('[OK] copied dist/pagefind -> public/pagefind');
