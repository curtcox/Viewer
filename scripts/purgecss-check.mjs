#!/usr/bin/env node
import { PurgeCSS } from 'purgecss';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

async function main() {
  const currentFile = fileURLToPath(import.meta.url);
  const currentDir = path.dirname(currentFile);
  const projectRoot = path.resolve(currentDir, '..');

  const purgeCSS = new PurgeCSS();
  const results = await purgeCSS.purge({
    css: [path.join(projectRoot, 'static/**/*.css')],
    content: [
      path.join(projectRoot, 'templates/**/*.html'),
      path.join(projectRoot, 'templates/**/*.j2'),
      path.join(projectRoot, 'static/js/**/*.js'),
    ],
  });

  const warnings = results.flatMap((entry) => entry.warnings ?? []);

  if (warnings.length > 0) {
    console.error('PurgeCSS warnings detected:');
    for (const warning of warnings) {
      console.error(`- ${warning}`);
    }
    process.exit(1);
  }

  console.log('PurgeCSS completed without warnings.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
