#!/usr/bin/env node
/*
 * 아티팩트 보드를 오프라인으로 그려 JPG · 글자로 남긴다(사내망에서 claude.ai 아티팩트를 열 수 없어도 디자인을 볼 수 있게).
 *
 *   node docs/screens/_runtime/render.mjs                 # 저장소 루트에서. 화면 보드 + PPT 템플릿 보드 전부
 *   node docs/screens/_runtime/render.mjs screens         # 화면 보드만(docs/screens/webapp*)
 *   node docs/screens/_runtime/render.mjs templates       # PPT 템플릿만(docs/templates/source/*)
 *   node docs/screens/_runtime/render.mjs screens CA4 PR7 # 일부 보드만
 *
 * 이미지: 보드의 /_blob/<id> 는 docs/_blob/<id>(아티팩트 에셋 사본, 확장자 없음)로 열린다.
 *
 * 산출물
 *   docs/screens/_rendered/<webapp>/<보드>.jpg · .txt          화면(1440×900 등 보드의 $preview 크기)
 *   docs/templates/_rendered/<묶음>/<레이아웃>.jpg · .txt       PPT 레이아웃(1280×720)
 *   각 _rendered/MANIFEST.json                                 보드 · 크기 · 오류
 *
 * 하는 일: support.js(이 폴더, 아티팩트 런타임 대체)를 보드 폴더마다 복사하고 부모 폴더에 dc-dirs.json 을 쓴 뒤,
 * docs/ 를 5098 포트 정적 서버로 열어 Chromium(web/node_modules 의 playwright)으로 찍는다. 외부 요청(Google Fonts 등)은 보내지 않는다.
 */
import { createRequire } from 'node:module';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';

const ROOT = process.cwd();
const DOCS = path.join(ROOT, 'docs');
const RUNTIME = path.join(DOCS, 'screens', '_runtime', 'support.js');
const require = createRequire(path.join(ROOT, 'web', 'package.json'));
const { chromium } = require('playwright');
const PORT = Number(process.env.SCREENS_PORT || 5098);

const SETS = {
  screens: { base: path.join(DOCS, 'screens'), out: path.join(DOCS, 'screens', '_rendered') },
  templates: { base: path.join(DOCS, 'templates', 'source'), out: path.join(DOCS, 'templates', '_rendered') },
};
const args = process.argv.slice(2);
const pick = args.filter((a) => a in SETS);
const only = new Set(args.filter((a) => !(a in SETS)));
const sets = pick.length ? pick : Object.keys(SETS);

const dirsOf = (base) => fs.readdirSync(base).filter((d) => !d.startsWith('_') && fs.statSync(path.join(base, d)).isDirectory()
  && fs.readdirSync(path.join(base, d)).some((f) => f.endsWith('.dc.html'))).sort();

for (const s of sets) {
  const { base } = SETS[s];
  const dirs = dirsOf(base);
  fs.writeFileSync(path.join(base, 'dc-dirs.json'), JSON.stringify(dirs) + '\n');
  for (const d of dirs) fs.copyFileSync(RUNTIME, path.join(base, d, 'support.js'));
}

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp' };
const server = http.createServer((req, res) => {
  const p = path.normalize(path.join(DOCS, decodeURIComponent(req.url.split('?')[0])));
  if (!p.startsWith(DOCS) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  let type = TYPES[path.extname(p)];
  if (!type) {                                   // docs/_blob/<id> — 아티팩트 이미지(확장자 없음): 머리 바이트로 판단
    const head = Buffer.alloc(4);
    const fd = fs.openSync(p, 'r'); fs.readSync(fd, head, 0, 4, 0); fs.closeSync(fd);
    type = head[0] === 0xff && head[1] === 0xd8 ? 'image/jpeg' : head.toString('latin1', 1, 4) === 'PNG' ? 'image/png' : 'application/octet-stream';
  }
  res.writeHead(200, { 'content-type': type });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(PORT, '127.0.0.1', r));

const launch = fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {};
const browser = await chromium.launch(launch);
const noise = /fonts\.g|support\.js|Failed to load resource|\{\{/;
let total = 0;
let failed = 0;
for (const s of sets) {
  const { base, out } = SETS[s];
  const manifest = [];
  for (const d of dirsOf(base)) {
    fs.mkdirSync(path.join(out, d), { recursive: true });
    for (const f of fs.readdirSync(path.join(base, d)).filter((x) => x.endsWith('.dc.html')).sort()) {
      const name = f.replace(/\.dc\.html$/, '');
      if (only.size && !only.has(name)) continue;
      const html = fs.readFileSync(path.join(base, d, f), 'utf8');
      const m = html.match(/"\$preview":\{"width":(\d+),"height":(\d+)\}/);
      const [w, h] = m ? [Number(m[1]), Number(m[2])] : [1440, 900];
      const page = await browser.newPage({ viewport: { width: w, height: h } });
      const errors = [];
      page.on('pageerror', (e) => { if (!noise.test(e.message)) errors.push(String(e.message).slice(0, 200)); });
      page.on('console', (msg) => { if (msg.type() === 'error' && !noise.test(msg.text())) errors.push(msg.text().slice(0, 200)); });
      await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
      try {
        await page.goto(`http://127.0.0.1:${PORT}/${path.relative(DOCS, path.join(base, d, f)).split(path.sep).join('/')}`, { waitUntil: 'load' });
        await page.waitForFunction(() => window.__dcReady === true, null, { timeout: 15000 });
        await page.waitForTimeout(150);
        await page.screenshot({ path: path.join(out, d, name + '.jpg'), type: 'jpeg', quality: 82 });
        const text = await page.evaluate(() => document.body.innerText);
        fs.writeFileSync(path.join(out, d, name + '.txt'), text.replace(/\n{3,}/g, '\n\n').trim() + '\n');
        const left = (text.match(/\{\{[^}]+\}\}/g) || []).length;
        if (left) errors.push(`남은 템플릿 ${left}개`);
      } catch (e) {
        errors.push(String(e.message).split('\n')[0].slice(0, 200));
      }
      await page.close();
      manifest.push({ dir: d, board: name, width: w, height: h, errors });
      process.stdout.write(errors.length ? 'x' : '.');
    }
  }
  if (!only.size) fs.writeFileSync(path.join(out, 'MANIFEST.json'), JSON.stringify(manifest, null, 1) + '\n');
  const bad = manifest.filter((x) => x.errors.length);
  total += manifest.length;
  failed += bad.length;
  console.log(`\n${s}: ${manifest.length} 보드, 오류 ${bad.length}`);
  for (const b of bad.slice(0, 20)) console.log(' ', b.dir, b.board, b.errors.join(' | '));
}
await browser.close();
server.close();
process.exit(failed ? 1 : 0);
