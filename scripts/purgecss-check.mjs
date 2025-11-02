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
  const unusedSelectors = results.flatMap((entry) =>
    entry.rejected?.map((selector) => ({
      selector,
      file: entry.file ?? 'unknown file',
    })) ?? [],
  );

  if (warnings.length > 0) {
    console.error('PurgeCSS warnings detected:');
    for (const warning of warnings) {
      console.error(`- ${warning}`);
    }
    process.exit(1);
  }

  if (unusedSelectors.length > 0) {
    console.error('Unused CSS selectors detected:');
    for (const { file, selector } of unusedSelectors) {
      console.error(`- ${selector} (${file})`);
    }
    process.exit(1);
  }

  console.log('PurgeCSS completed without warnings or unused selectors.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
