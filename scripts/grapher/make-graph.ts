import fs from 'node:fs';
import path from 'node:path';
import { render } from 'pele';

const inputFile = process.argv[2];

if (!inputFile) {
  console.error("Error: Filename required!");
  console.error("Usage: npm make <filename.mmd>");
  process.exit(1);
}

const outputFile = path.basename(inputFile, path.extname(inputFile)) + '.svg';

try {
  const mermaidCode = fs.readFileSync(inputFile, 'utf-8');

  const { svg } = render(mermaidCode);
  fs.writeFileSync(outputFile, svg);
  
  console.log(`Successfully! generate SVG: ${outputFile}`);
} catch (error) {
  console.error("Failed generate SVG:", error.message);
}