/**
 * VP 새 흐름(보드 webapp1 v62 — VP0 · 최종본 View content=vp + 단계 팝업 VP1 · VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP2_Edit · VP_Draft)
 * — 실제 스택(MODEL_MODE=mock · mocks/ai-tools/vp.need_infer.v1 · KB 실데이터).
 * Storyboard(요구사항 + DSS)를 API 로 만들고 → 새로 만들기(빈 최종본 + ① Gate 팝업) → ② 가치 · 고객의 니즈 팝업(직접 · AI 니즈 추론 · AI 가치 매칭 · 고르기 · 연결된 가치)
 * → 저장하면 팝업이 닫히고 같은 주소의 최종본(허브 stages.vp 확인 · 완료 화면 없음) → 단계 칩으로 고치기 팝업(저장 · v2 · 닫기 물음).
 * 팝업은 1440×900 에서 (130, 50) 1180×800 — 칸 좌표는 팝업 기준(예전 page 좌표 x −130 · y −50).
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=vp WM_E2E_DEV=1 WM_E2E_PORT=5205 npx playwright test e2e/vp/values.spec.ts --workers=1
 */
import { test, type Locator } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { expect, shot } from './helpers';

const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };

test('VP 새 흐름 — Gate 팝업 · 가치 · 고객의 니즈 팝업(직접 · AI · 고르기 · 연결된 가치) · 저장 → 최종본 · 고치기 v2', async ({ page, request }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 AI Ready 오피스 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  const dssRef = (await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.dss.ref as string;

  // VP1 — 빈 최종본(새로 만들기 · ② 자리표시) 위 ① Storyboard 팝업(보드 Gate content=vp)
  await page.goto('/vp/new');
  const gate = page.getByRole('dialog', { name: '새 VP · Storyboard' });
  await expect(gate).toBeVisible();
  expect(await box(gate)).toMatchObject({ x: 130, y: 50, w: 1180, h: 800 });
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-detail [data-slot="2"]')).toBeVisible();
  await expect(gate.locator('.fl-shead__pos')).toHaveText('단계 1/2');
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(gate.locator('.wm-flow__back')).toHaveCount(0);
  const row = gate.getByRole('radio', { name: new RegExp(name) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  await page.mouse.move(10, 890);
  await shot(page, 'VP1-new');
  await gate.getByRole('button', { name: '이 Storyboard로 시작' }).click();

  // VP2 — ② 가치 · 고객의 니즈 팝업(같은 최종본 위 · 주소는 ?step=values)
  await expect(page).toHaveURL(/\/vp\/values\/vmap_[0-9A-Za-z]+\?step=values$/, { timeout: 30_000 });
  const mapId = page.url().split('/').pop()!.split('?')[0];
  const dlg = page.locator('.fl-stepdlg');
  await expect(dlg.getByRole('heading', { name: '제품 · 솔루션마다 가치와 고객의 니즈를 적어요' })).toBeVisible();
  await expect(dlg.locator('.fl-shead__sb')).toContainText(name);
  await expect(dlg.locator('.fl-shead__note')).toHaveText('Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨');
  await expect(dlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(dlg.locator('.fl-shead__pos')).toHaveText('단계 2/2');
  await expect(dlg.locator('.wm-sbbar')).toHaveCount(0);
  await expect(dlg.locator('.wm-flow__back')).toHaveCount(0);
  await expect(dlg.getByRole('button', { name: /제품 · 솔루션 고르기 · 8/ })).toBeVisible();          // DSS 제품 6 + 솔루션 2
  // 가치가 없으면 저장이 막힌다(주황 안내)
  await expect(dlg.getByRole('button', { name: '저장', exact: true })).toBeDisabled();
  await expect(dlg.getByText('가치를 하나 이상 적어야 저장할 수 있어요')).toBeVisible();

  // 직접 적은 가치 둘(API) → 다시 읽기(새로 고침해도 같은 팝업)
  const doc0 = await (await request.get(`/api/vp/v1/value-maps/${mapId}`)).json();
  const wall = doc0.items.find((i: { name: string }) => i.name === 'The Wall IAB 146"').key as string;
  await request.post(`/api/vp/v1/value-maps/${mapId}/items/${wall}/values`, { data: { space: '로비', message: '들어서는 순간 회사의 AI 비전을 보여 줌', need: '방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요', req: 'RQ-01 최초 AI Ready' } });
  await request.post(`/api/vp/v1/value-maps/${mapId}/items/${wall}/values`, { data: { space: '로비', message: '사내 행사 때 로비를 무대로 바꿈', req: 'RQ-01 업무환경 플랫폼' } });
  await page.reload();
  await expect(page).toHaveURL(/step=values/);
  await expect(dlg.getByRole('button', { name: /The Wall IAB 146"/ })).toContainText('가치 2 · 니즈 1/2');
  // 보드 VP2(팝업 1180 × 800): 본문 1180 · 왼쪽 280 | 오른쪽 806 · 아래 저장 h48 (y784)
  expect(Math.round((await dlg.locator('.fl-sbody .wm-flow').boundingBox())!.width)).toBe(1180);
  const left = dlg.locator('.wm-flow__grid > .wm-flow__panel').first();
  const left0 = await box(left);
  expect(left0).toMatchObject({ x: 170, w: 280 });
  expect(await box(dlg.locator('.wm-flow__grid > .wm-flow__panel').nth(1))).toMatchObject({ x: 464, w: 806 });
  expect(await box(dlg.getByRole('button', { name: '저장', exact: true }))).toMatchObject({ y: 784, h: 48 });
  await page.mouse.move(10, 890);
  await shot(page, 'VP2-new');

  // AI 니즈 추론(mock: '행사' → 고정 문장) → 점선 → 수락
  await dlg.getByRole('button', { name: 'AI 니즈 추론' }).click();
  await expect(dlg.getByText('“행사 때마다 외부 장소를 빌리지 않았으면 해요”')).toBeVisible();
  await dlg.locator('.vv-need').getByRole('button', { name: '수락' }).click();
  await expect(dlg.getByRole('button', { name: /The Wall IAB 146"/ })).toContainText('가치 2 · 니즈 2/2');

  // AI 가치 매칭 추천(mock 은 LLM 없이 KB 원문 메시지 → 점선 후보)
  await dlg.getByRole('button', { name: /AI 가치 매칭 추천/ }).click();
  const aiBar = dlg.getByRole('status').filter({ hasText: '점선은 수락해야 들어가요' });
  await expect(aiBar).toBeVisible({ timeout: 30_000 });
  await dlg.getByRole('button', { name: /MagicINFO/ }).first().click();
  await expect(dlg.locator('.vv-card--pend').first()).toBeVisible();
  // 보드 VP2_AI: 안내 줄 1100 × 38 · 그리드가 50 아래로
  expect(await box(aiBar)).toMatchObject({ x: 170, w: 1100, h: 38 });
  expect(await box(left)).toMatchObject({ x: 170, w: 280, y: left0.y + 50, h: left0.h - 50 });
  await page.mouse.move(10, 890);
  await shot(page, 'VP2_AI-new');

  // VP2_Pick — 제품 · 솔루션 고르기(팝업 위에 겹침) · 옥외형 사이니지 빼기
  await dlg.getByRole('button', { name: /제품 · 솔루션 고르기 · 8/ }).click();
  const pick = page.getByRole('dialog', { name: 'VP에 넣을 제품 · 솔루션 고르기' });
  await expect(pick).toBeVisible();
  expect(await box(pick)).toMatchObject({ w: 760, h: 640 });
  await pick.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).click();
  await expect(pick.getByText('7개 골랐어요')).toBeVisible();
  await shot(page, 'VP2_Pick-new');
  await page.keyboard.press('Escape');                                     // 고르기만 닫힌다(단계 팝업은 그대로)
  await expect(pick).toHaveCount(0);
  await expect(dlg).toBeVisible();
  await expect(dlg.getByRole('button', { name: /제품 · 솔루션 고르기 · 7/ })).toBeVisible();

  // VP2_Detail — 연결된 가치 전체 보기(KB 공식 메시지)
  await dlg.getByRole('button', { name: /연결된 가치 전체 보기/ }).click();
  const det = page.getByRole('dialog', { name: /MagicINFO.*연결된 가치/ });
  await expect(det.getByText('삼성 공식 메시지')).toBeVisible();
  expect(await box(det)).toMatchObject({ w: 900, h: 720 });
  await shot(page, 'VP2_Detail-new');
  await det.getByRole('button', { name: '닫기' }).last().click();
  await expect(det).toHaveCount(0);
  await expect(dlg).toBeVisible();

  // 모두 수락 → 저장 → 팝업이 닫히고 같은 주소의 최종본(보드 VP_View · 완료 안내 화면 없음)
  await dlg.getByRole('button', { name: '모두 수락' }).click();
  await expect(aiBar).toHaveCount(0);
  await dlg.getByRole('button', { name: '저장', exact: true }).click();
  await expect(dlg).toHaveCount(0, { timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/vp/values/${mapId}$`));
  await expect(page.getByRole('heading', { name: '가치 제안을 저장했어요' })).toHaveCount(0);
  const doc = await (await request.get(`/api/vp/v1/value-maps/${mapId}`)).json();
  const c = doc.counts as { items: number; values: number; needs: number };
  const ref = doc.code as string;
  expect(doc).toMatchObject({ status: 'done', ver: 1 });
  expect(c.items).toBe(7);
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(view.locator('.fl-dver')).toHaveText(`${ref} v1`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(new RegExp(` 저장 · 제품 · 솔루션 7 · 가치 ${c.values} · 고객의 니즈 ${c.needs}/${c.values}$`));
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계별 고치기');
  await expect(view.locator('.vpv-bar__from')).toHaveText(`${dssRef}에서 7개를 골랐어요`);
  await expect(view.locator('.vpv-bar__out')).toHaveText('· 고르지 않은 1 — 옥외형 사이니지 OHC55');
  await expect(view.locator('.vpv-item')).toHaveCount(7);
  const wallRow = view.locator('[data-vitem="The Wall IAB 146\\""]');
  await expect(wallRow.locator('.vpv-item__n')).toHaveText('가치 2 · 니즈 2/2');
  await expect(wallRow.locator('.vpv-item__sp')).toHaveText('로비');
  await expect(wallRow.locator('.fl-vtag').first()).toHaveText('제품');
  await expect(wallRow.locator('.vpv-msg')).toHaveText(['들어서는 순간 회사의 AI 비전을 보여 줌', '사내 행사 때 로비를 무대로 바꿈']);
  await expect(wallRow.locator('.vpv-req').first()).toHaveText('RQ-01 최초 AI Ready');
  await expect(wallRow.locator('.vpv-need__t')).toHaveText(['“방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요”', '“행사 때마다 외부 장소를 빌리지 않았으면 해요”']);
  await expect(wallRow.locator('.vpv-need .fl-vtag')).toHaveText(['직접', 'AI 추론 · 수락']);
  await expect(view.locator('[data-vitem="MagicINFO"] .fl-vtag').first()).toHaveText('솔루션');
  // KB 원문 메시지로 넣은 가치(니즈 비움) → 주황 점선 「비어 있어요」
  if (c.needs < c.values) {
    await expect(view.locator('.vpv-need--empty').first()).toContainText('비어 있어요 · 고치기에서 적거나 AI 니즈 추론으로 채워요');
    expect(await box(view.locator('.vpv-need--empty').first())).toMatchObject({ h: 36 });
  }
  // 보드 View(content=vp): 본문 1100 · 줄 칸 h44 · 줄 210 | 1fr(사이 18 · 안쪽 20) · 니즈 줄 h36
  expect(await box(view.locator('.vpv-bar'))).toMatchObject({ x: 300, w: 1100, h: 44 });
  expect(await box(view.locator('.vpv-panel'))).toMatchObject({ x: 300, w: 1100 });
  expect(await box(view.locator('.vpv-item__l').first())).toMatchObject({ x: 321, w: 210 });
  expect(await box(view.locator('.vpv-vals').first())).toMatchObject({ x: 549, w: 830 });
  expect(await box(wallRow.locator('.vpv-need').first())).toMatchObject({ h: 36 });
  await expect(view.locator('.fl-dfollow')).toHaveCount(0);                // 후속 작업 없음

  // 허브 flow.json stages.vp(점선 대기 값은 빠진다) · 칸 경로
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const st = flow.stages.vp;
  expect(st).toMatchObject({ ref, selection: { fromDss: 7, excluded: ['옥외형 사이니지 OHC55'] } });
  expect(st.counts).toMatchObject({ items: 7, values: c.values, needs: c.needs });
  expect(flow.cells.find((x: { key: string }) => x.key === 'vp')).toMatchObject({ state: 'done', ref, route: `/vp/values/${mapId}` });
  await page.mouse.move(10, 890);
  await shot(page, 'VP_View-new');
  await view.getByRole('button', { name: 'flow.json' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json.getByText('"vp": {').first()).toBeVisible();
  await shot(page, 'VP_ViewJson-new');
  await json.getByRole('button', { name: '닫기' }).last().click();

  // 단계 칩 「가치 · 고객의 니즈」 → 고치기 팝업(VP2_Edit: VP-nn v1 고치기 · 저장 · v2 · 이전 단계 링크 없음) — 고치지 않고 닫으면 묻지 않는다
  await view.getByRole('button', { name: /^가치 · 고객의 니즈 · / }).click();
  await expect(page).toHaveURL(/step=values/);
  await expect(dlg.locator('.fl-shead__mode')).toHaveText(`${ref} v1 고치기`);
  await expect(dlg.locator('.fl-shead__note')).toHaveText(`저장하면 ${ref} v2 · ${sb.id}에 반영돼요`);
  await expect(dlg.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(dlg.locator('.wm-flow__back')).toHaveCount(0);
  await page.mouse.move(10, 890);
  await shot(page, 'VP2_Edit-new');
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(dlg).toHaveCount(0);
  await expect(page.getByRole('dialog', { name: '고친 내용을 저장할까요?' })).toHaveCount(0);
  // 고친 뒤(가치 하나 더) 닫으면 저장할지 묻는다 → 「저장 · v2」 → 최종본 v2
  await view.getByRole('button', { name: /^가치 · 고객의 니즈 · / }).click();
  await dlg.getByRole('button', { name: /The Wall IAB 146"/ }).click();
  await dlg.getByRole('button', { name: /가치 추가/ }).click();
  await dlg.locator('[data-add-value]').getByLabel('가치 메시지').fill('베젤 없는 큰 화면으로 콘텐츠에 몰입');
  await dlg.locator('[data-add-value]').getByRole('button', { name: '추가' }).click();
  await expect(dlg.getByRole('button', { name: /The Wall IAB 146"/ })).toContainText('가치 3 · 니즈 2/3');
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  const ask = page.getByRole('dialog', { name: '고친 내용을 저장할까요?' });
  await expect(ask).toBeVisible();
  await ask.getByRole('button', { name: '저장 · v2' }).click();
  await expect(dlg).toHaveCount(0, { timeout: 20_000 });
  await expect(view.locator('.fl-dver')).toHaveText(`${ref} v2`);
  await expect(wallRow.locator('.vpv-item__n')).toHaveText('가치 3 · 니즈 2/3');
  await expect(wallRow.locator('.vpv-need--empty')).toHaveCount(1);
  expect((await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.vp).toMatchObject({ ref });
  await page.goto('/vp');
  const listRow = page.locator('.fl-card').filter({ hasText: name });
  await expect(listRow).toContainText(`${ref} v2`);
});

test('VP — Storyboard 「만들기」(?sb=&auto=1)는 Gate 를 건너뛰고 바로 ② 팝업 · 닫으면 작성 중 최종본 · 예전 주소 /vp/values/new', async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const name = `용산 바로 만들기 ${tag()}`;
  const sb = await makeStoryboard(request, { dss: true, name });
  await page.goto(`/vp/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/vp\/values\/vmap_[0-9A-Za-z]+\?step=values$/, { timeout: 30_000 });
  const mapId = page.url().split('/').pop()!.split('?')[0];
  const dlg = page.locator('.fl-stepdlg');
  await expect(dlg.getByRole('heading', { name: '제품 · 솔루션마다 가치와 고객의 니즈를 적어요' })).toBeVisible();
  await expect(dlg.locator('.fl-shead__sb')).toContainText(name);
  // 1920 × 1080: 팝업은 가운데 1180 × 800 그대로
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await box(dlg)).toMatchObject({ x: 370, y: 140, w: 1180, h: 800 });
  await page.setViewportSize({ width: 1440, height: 900 });
  // 빈 최종본(뒤) — 새로 만들기 · ② 자리표시
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'new');
  // 닫으면 작성 중 최종본(채운 칸 없음 → ② 자리표시에 「이어서 · 가치 · 고객의 니즈」)
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(dlg).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/vp/values/${mapId}$`));
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'draft');
  await expect(view.locator('.fl-dver')).toHaveText('작성 중 1/2');
  await expect(view.locator('.fl-dhead__meta')).toHaveText(`작성 중 · 2단계 중 1단계 마침 · 저장하면 ${sb.id}에 연결돼요`);
  const slot = view.locator('[data-slot="2"]');
  await expect(slot).toContainText('가치 · 고객의 니즈 단계');
  await expect(slot).toContainText('제품 · 솔루션별 가치 · 고객의 니즈 — 이 단계를 마치면 여기에 채워져요');
  expect(await box(slot)).toMatchObject({ x: 300, w: 1100 });
  await page.mouse.move(10, 890);
  await shot(page, 'VP_Draft-new');
  await slot.getByRole('button', { name: '이어서 · 가치 · 고객의 니즈' }).click();
  await expect(page).toHaveURL(/step=values/);
  await expect(dlg).toBeVisible();
  // 목록 · 작업 내역에서 작성 중을 열면(주소에 step 없음) ② 팝업이 열린 채로
  await page.goto(`/vp/values/${mapId}`);
  await expect(page).toHaveURL(/step=values/);
  await expect(dlg.getByRole('heading', { name: '제품 · 솔루션마다 가치와 고객의 니즈를 적어요' })).toBeVisible();

  // 예전 주소 — /vp/values/new(요구 문장 없음) → /vp/new(Gate 팝업) · ?text= → Storyboard 없이 맵을 만들어 ② 팝업
  await page.goto('/vp/values/new');
  await expect(page).toHaveURL(/\/vp\/new$/);
  await expect(page.getByRole('dialog', { name: '새 VP · Storyboard' })).toBeVisible();
  await page.goto(`/vp/values/new?title=${encodeURIComponent(`요구로 시작 ${tag()}`)}&text=${encodeURIComponent('로비 미디어월과 회의실 전자칠판')}`);
  await expect(page).toHaveURL(/\/vp\/values\/vmap_[0-9A-Za-z]+\?step=values$/, { timeout: 30_000 });
  const freeId = page.url().split('/').pop()!.split('?')[0];
  await expect(dlg.locator('.fl-shead__note')).toHaveText('요구 문장으로 시작했어요 · 연결된 Storyboard가 없어요');
  await expect(dlg.locator('.fl-shead__sb')).toHaveCount(0);
  await dlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(page.locator('.fl-detail .wm-sbbar')).toContainText('연결된 Storyboard가 없어요 · 요구 문장으로 시작했어요');
  // 정리 — 저장 전 초안 지우기
  for (const id of [mapId, freeId]) expect((await request.delete(`/api/vp/v1/value-maps/${id}`)).status()).toBe(204);
});
