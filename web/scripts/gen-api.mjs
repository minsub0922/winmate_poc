// contracts/<서비스>.json → src/api/gen/<서비스>.ts (openapi-typescript)
//   node scripts/gen-api.mjs            # 전부
//   node scripts/gen-api.mjs kb mi      # 일부
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import openapiTS, { astToString } from 'openapi-typescript';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const contracts = path.join(root, 'contracts');
const outDir = path.resolve(here, '..', 'src', 'api', 'gen');
fs.mkdirSync(outDir, { recursive: true });

const want = process.argv.slice(2);
const files = fs.readdirSync(contracts).filter((f) => f.endsWith('.json')).filter((f) => !want.length || want.includes(f.replace(/\.json$/, '')));
for (const f of files) {
  const name = f.replace(/\.json$/, '');
  const schema = JSON.parse(fs.readFileSync(path.join(contracts, f), 'utf8'));
  const ast = await openapiTS(schema, { alphabetize: true });
  const header = `// 자동 생성 — 직접 고치지 말 것. 원본: contracts/${f} (make contracts)\n`;
  fs.writeFileSync(path.join(outDir, `${name}.ts`), header + astToString(ast));
  console.log(`✓ src/api/gen/${name}.ts`);
}
