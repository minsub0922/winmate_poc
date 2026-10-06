// 타입 검사 — 기능 세션은 자기 폴더 오류만 본다(다른 세션이 작업 중인 파일 오류에 막히지 않게).
//   node scripts/typecheck.mjs                # 전부(오류 있으면 실패)
//   node scripts/typecheck.mjs requirements   # src/features/requirements/ 오류만 실패로, 나머지는 개수만 알림
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const feature = process.argv[2];
const r = spawnSync('npx', ['tsc', '-p', 'tsconfig.json', '--noEmit', '--pretty', 'false'], { cwd: web, encoding: 'utf8' });
const lines = (r.stdout + r.stderr).split('\n').filter((l) => /\(\d+,\d+\): error TS/.test(l));
const mine = feature ? lines.filter((l) => l.startsWith(`src/features/${feature}/`)) : lines;
const others = feature ? lines.length - mine.length : 0;
for (const l of mine) console.log(l);
if (others) console.log(`(다른 폴더 오류 ${others}개 — 이 기능 검사에는 넣지 않음)`);
console.log(mine.length ? `✗ 타입 오류 ${mine.length}개` : `✓ 타입 오류 없음${feature ? ` (src/features/${feature})` : ''}`);
process.exit(mine.length ? 1 : 0);
