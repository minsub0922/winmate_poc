/**
 * 공간 시나리오 새 흐름(보드 webapp1 v62 — SC0 · 최종본 View content=sc(SC_View · SC_Draft) + 단계 팝업 SC1 · SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC2_Edit) — Storyboard 허브 연동.
 * API 로 Storyboard(요구사항 + DSS)를 만들고 목록 → 새로 만들기(빈 최종본 + ① Gate 팝업) → ② 공간 · 시나리오 팝업(DSS 공간 미리 채움 · AI 3안 · 수락 · 직접 시나리오 ·
 * 제품 고르기(팝업 위 팝업) · 제품 없는 공간 막기) → 저장하면 팝업이 닫히고 같은 주소의 최종본(허브 stages.sc 확인) → 단계 칩으로 고치기 팝업(저장 · v2 · 닫기 물음).
 * 상세에는 페이지 이동이 없다(같은 주소 · `?step=`). 팝업은 1440×900 에서 (130, 50) 1180×800 — 칸 좌표는 팝업 기준(예전 page 좌표에서 x −130 · y −50).
 * 실제 스택(mock 모델 — 로비 AI 3안은 mocks/ai-tools/sc.space_candidates.v1.json 고정 응답).
 * 실행: cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=scenario WM_E2E_DEV=1 WM_E2E_PORT=5209 npx playwright test e2e/scenario/sc-flow.spec.ts --workers=1
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
const width = async (page: Page, sel: string) => Math.round((await page.locator(sel).first().boundingBox())!.width);
const height = async (page: Page, sel: string) => Math.round((await page.locator(sel).first().boundingBox())!.height);
const still = async (page: Page) => { await page.mouse.move(10, 890); await page.waitForTimeout(300); };

test('SC 새 흐름 — 목록 → 새로 만들기(① 팝업) → ② 공간 · 시나리오 팝업 → 저장 → 최종본 · 허브 stages.sc → 고치기 v2', async ({ page, request }) => {
  test.setTimeout(300_000);
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  const flow0 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const dssRef: string = flow0.stages.dss.ref;
  await page.setViewportSize({ width: 1440, height: 900 });

  // ── SC0 목록(보드 List content=sc) ──
  await page.goto('/scenario');
  await expect(page.getByRole('heading', { name: '공간 시나리오 생성', level: 1 })).toBeVisible();
  await expect(page.getByText('Storyboard의 공간마다 사용자 시나리오를 만들어요.')).toBeVisible();
  await expect(page.getByText('사전 작업 · 최소 DSS까지 된 Storyboard')).toBeVisible();
  await still(page);
  await shot(page, 'SC0-new');
  await page.locator('.fl-hero').click();
  await expect(page).toHaveURL(/\/scenario\/new$/);

  // ── SC1 — 빈 최종본(새로 만들기 · ② 자리표시) 위 ① Storyboard 팝업(보드 Gate content=sc) ──
  const gateDlg = page.getByRole('dialog', { name: '새 공간 시나리오 · Storyboard' });
  await expect(gateDlg).toBeVisible();
  expect(await box(gateDlg)).toMatchObject({ x: 130, y: 50, w: 1180, h: 800 });
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-detail [data-slot="2"]')).toBeVisible();
  await expect(gateDlg.locator('.fl-shead__pos')).toHaveText('단계 1/2');
  await expect(gateDlg.locator('.fl-sstep__t')).toHaveText(['Storyboard', '공간 · 시나리오']);   // 보드 v62 CONTENT.sc.steps
  await expect(gateDlg.locator('.fl-shead__note')).toHaveText('Storyboard를 고르면 공간 시나리오가 그 Storyboard에 연결돼요 · 고르기 전에 닫으면 목록으로');
  await expect(gateDlg.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  await expect(gateDlg.getByRole('link', { name: '목록' })).toHaveCount(0);                     // 팝업 안 Gate 는 「목록」 링크가 없다(× 로 닫으면 목록)
  const row = gateDlg.getByRole('radio', { name: new RegExp(esc(sb.name)) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  await expect(gateDlg.getByText(`${sb.name}에 공간 시나리오가 연결돼요`)).toBeVisible();
  await still(page);
  await shot(page, 'SC1-new');
  await gateDlg.getByRole('button', { name: /이 Storyboard로 시작/ }).click();

  // ── SC2 — 같은 최종본 위 ② 공간 · 시나리오 팝업(주소는 ?step=spaces) · DSS 공간 · 공간별 제품 미리 채움 ──
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/?]+\?step=spaces$/, { timeout: 20_000 });
  const setId = page.url().split('/').pop()!.split('?')[0];
  const stepDlg = page.locator('.fl-stepdlg');
  await expect(stepDlg.getByRole('heading', { name: '공간마다 시나리오를 여러 개 써요' })).toBeVisible();
  await expect(stepDlg.locator('.fl-shead__sb')).toContainText(sb.name);
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText('Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨');
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(stepDlg.locator('.fl-shead__pos')).toHaveText('단계 2/2');
  await expect(stepDlg.locator('.wm-sbbar')).toHaveCount(0);                                   // 팝업 안에는 Storyboard 바가 없다(머리 칩)
  await expect(stepDlg.locator('.wm-flow__back')).toHaveCount(0);                              // 보드 SC2: 이전 단계 링크 없음
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'new');
  await expect(page.locator('.ss-spaces__h')).toHaveText(`공간 · ${dssRef}`);
  await expect(page.getByRole('tab')).toHaveText([/로비/, /회의실/, /주차장/]);
  await expect(page.getByRole('tab', { name: /로비/ })).toContainText('시나리오 0 · 제품 4');   // DSS 제품 3 + MagicINFO(links → 로비)
  await expect(page.locator('.ss-pchip')).toHaveText([/제품The Wall IAB 146"/, /제품Smart Signage QM55C/, /제품삼성 키오스크/, /솔루션MagicINFO/]);
  // 보드 SC2(팝업 1180 × 800 · 본문 728 · 패딩 16 32): 공간 196 | 12 | (헤더 908 · 시나리오 236 | 10 | 편집 662) · 저장 48(y 786)
  expect(await width(page, '.fl-sbody .wm-flow')).toBe(1180);
  expect(await height(page, '.fl-sbody .wm-flow__section')).toBe(728);
  expect(await box(page.locator('.ss-spaces'))).toMatchObject({ x: 162, w: 196 });
  expect(await box(page.locator('.ss-sphead'))).toMatchObject({ x: 370, w: 908 });
  expect(await box(page.locator('.ss-lpanel'))).toMatchObject({ x: 370, w: 236 });
  expect(await box(page.locator('.ss-ed'))).toMatchObject({ x: 616, w: 662 });
  expect(await height(page, '.ss-sp')).toBe(52);
  expect(await box(stepDlg.getByRole('button', { name: '저장', exact: true }))).toMatchObject({ y: 786, h: 48 });
  const sp0 = await box(page.locator('.ss-spaces'));
  expect(sp0.y + sp0.h).toBe(774);                                                              // 그리드 바닥 = 850 − 16 − 48 − 12

  // SC2_Empty — 시나리오 없는 공간(주차장)
  await page.getByRole('tab', { name: /주차장/ }).click();
  await expect(page.getByText('주차장 시나리오를 시작해요')).toBeVisible();
  await expect(page.getByText('아직 시나리오가 없어요. 직접 추가하거나 AI 3안을 받아 보세요.')).toBeVisible();
  await still(page);
  await shot(page, 'SC2_Empty-new');

  // 제품 · 솔루션을 모두 빼면 주황 경고 · 저장 막힘 → 고르기(팝업 위 팝업)로 다시 넣기
  await page.getByRole('button', { name: '옥외형 사이니지 OHC55 빼기' }).click();
  await expect(page.getByText('공간마다 제품 · 솔루션이 하나 이상 있어야 해요')).toBeVisible();
  await expect(page.getByRole('tab', { name: /주차장/ })).toContainText('제품 · 솔루션 없음');
  await expect(page.locator('.wm-flow__summary')).toHaveText('공간 3 · 시나리오 0 · 제품 · 솔루션 없는 공간 1');
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: /AI 시나리오 3안/ })).toBeDisabled();
  await still(page);
  await shot(page, 'SC2_NoProduct-new');
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  let dlg = page.getByRole('dialog', { name: '주차장 · 제품 · 솔루션 고르기' });
  await expect(dlg.getByText(`${dssRef} · 제품`, { exact: true })).toBeVisible();
  await dlg.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).click();
  await expect(dlg.getByText('1개 골랐어요')).toBeVisible();
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(dlg).toHaveCount(0);
  await expect(stepDlg).toBeVisible();
  await expect(page.getByRole('button', { name: '저장', exact: true })).toBeEnabled();

  // SC2_Pick — 로비 고르기(DSS 제품 · 솔루션 묶음, 있던 공간 표시) · Esc 는 고르기만 닫는다(단계 팝업은 그대로)
  await page.getByRole('tab', { name: /로비/ }).click();
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  dlg = page.getByRole('dialog', { name: '로비 · 제품 · 솔루션 고르기' });
  await expect(dlg.getByText(`${dssRef} · 솔루션`, { exact: true })).toBeVisible();
  await expect(dlg.getByRole('checkbox', { name: /SmartThings Pro/ })).toHaveAttribute('aria-checked', 'false');
  await expect(dlg.getByRole('checkbox', { name: /Flip Pro WA75D/ })).toContainText(`${dssRef} · 회의실`);
  await expect(dlg.getByText('4개 골랐어요')).toBeVisible();
  expect(await box(dlg)).toMatchObject({ x: 340, w: 760 });
  await still(page);
  await shot(page, 'SC2_Pick-new');
  await page.keyboard.press('Escape');
  await expect(dlg).toHaveCount(0);
  await expect(stepDlg).toBeVisible();
  await expect(page).toHaveURL(/step=spaces/);

  // SC2_AI — 로비 AI 3안(점선 A/B/C · 수락 전에도 고칠 수 있음)
  await page.getByRole('button', { name: /AI 시나리오 3안/ }).click();
  await expect(page.locator('.ss-sc--cand')).toHaveCount(3, { timeout: 30_000 });
  await expect(page.getByText('점선은 AI 후보')).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'AI 후보 A안이에요 · 수락해야 시나리오로 들어가요' })).toBeVisible();
  await expect(page.locator('#ss-title')).toHaveValue('미등록 방문객 응대');
  await expect(page.locator('.ss-ed')).toHaveClass(/wm-flow__panel--dashed/);
  await still(page);
  await shot(page, 'SC2_AI-new');
  await page.locator('#ss-who').fill('예약 없이 온 외부 방문객');                 // 수락 전 편집
  await page.waitForTimeout(900);
  await page.getByRole('status').getByRole('button', { name: '수락' }).click();
  await expect(page.locator('.ss-sc--cand')).toHaveCount(2);
  await expect(page.getByRole('tab', { name: /로비/ })).toContainText('시나리오 1 · 제품 4');
  // B · C 빼기
  for (const t of ['사내 행사 날 로비', '퇴근 후 보안 모드']) {
    await page.locator('.ss-sc', { hasText: t }).click();
    await page.getByRole('status').getByRole('button', { name: '빼기' }).click();
    await expect(page.locator('.ss-sc', { hasText: t })).toHaveCount(0);
  }

  // 직접 시나리오(단계 · 쓰인 제품 · 자유 항목)
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  await page.locator('#ss-title').fill('출근 혼잡 시간의 로비');
  await page.locator('#ss-who').fill('오전 9시 전후 임직원');
  await page.getByRole('checkbox', { name: 'The Wall IAB 146"' }).click();      // 이 시나리오에서 빼기
  await page.getByRole('checkbox', { name: '삼성 키오스크' }).click();
  await page.locator('#ss-step-0').fill('출근 인원이 몰려 게이트 앞이 혼잡해짐');
  await page.getByRole('button', { name: '+ 단계 추가' }).click();
  await page.locator('#ss-step-1').fill('층별 엘리베이터 대기 안내가 뜸');
  await page.locator('.ss-ptag').nth(1).click();                                  // 쓰인 제품 → 첫 시나리오 제품
  await expect(page.locator('.ss-ptag').nth(1)).toHaveText('Smart Signage QM55C');
  await page.getByRole('button', { name: '+ 시간대' }).click();
  await page.locator('#ss-f-0').fill('오전 9시 전후');
  await expect(page.locator('.ss-sc', { hasText: '출근 혼잡 시간의 로비' })).toContainText('제품 2 · 단계 2');
  await page.waitForTimeout(1200);                                                // 자동 저장(600ms)
  await page.locator('.ss-sc', { hasText: '미등록 방문객 응대' }).click();
  await expect(page.locator('.ss-sc', { hasText: '미등록 방문객 응대' })).toContainText('AI A안 · 수락');
  await expect(page.locator('#ss-who')).toHaveValue('예약 없이 온 외부 방문객');
  await expect(page.locator('.wm-flow__summary')).toHaveText('공간 3 · 시나리오 2');
  await still(page);
  await shot(page, 'SC2-new');

  // ── 저장 → 팝업이 닫히고 같은 주소의 최종본(보드 SC_View · 완료 안내 화면 없음) ──
  await stepDlg.getByRole('button', { name: '저장', exact: true }).click();
  await expect(stepDlg).toHaveCount(0, { timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`));
  const set = await (await request.get(`/api/scenario/v1/space-sets/${setId}`)).json();
  const code: string = set.code;
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'saved');
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v1`);
  await expect(view.locator('.fl-dhead__meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 공간 3 · 시나리오 2 · 시나리오 없는 공간 2$/);
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계별 고치기');
  await expect(view.locator('.fl-dstep__t')).toHaveText(['Storyboard', '공간 · 시나리오']);
  await expect(page.getByRole('heading', { name: '공간 시나리오를 저장했어요' })).toHaveCount(0);
  await expect(view.locator('.fl-dfollow')).toHaveCount(0);                                  // 후속 작업 없음
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(code);                           // 상단바 제목 = 코드(보드 View refId)
  // 공간 목록(236): 「공간 · DSS」 · 이름 + 시나리오 n · 제품 n / 시나리오 없음 · 제품 n · 처음 고른 공간 = 시나리오가 있는 첫 공간(#eaeefb)
  await expect(view.locator('.scv-spaces__h')).toHaveText(`공간 · ${dssRef}`);
  const vsp = view.locator('.scv-sp');
  await expect(vsp).toHaveText([/^로비시나리오 2 · 제품 4$/, /^회의실시나리오 없음 · 제품 2$/, /^주차장시나리오 없음 · 제품 1$/]);
  await expect(view.locator('[data-vspace="로비"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(view.locator('[data-vspace="로비"]')).toHaveCSS('background-color', 'rgb(234, 238, 251)');
  await expect(view.locator('[data-vspace="회의실"] .scv-sp__sub')).toHaveCSS('color', 'rgb(138, 145, 160)');
  // 고른 공간: 이름 18/700 · 시나리오 n · 제품 · 솔루션 칩(종류)
  await expect(view.locator('.scv-head__name')).toHaveText('로비');
  await expect(view.locator('.scv-head__n')).toHaveText('시나리오 2');
  await expect(view.locator('.scv-prod')).toHaveText(['제품The Wall IAB 146"', '제품Smart Signage QM55C', '제품삼성 키오스크', '솔루션MagicINFO']);
  await expect(view.locator('.scv-prod__k--sol')).toHaveText('솔루션');
  // 시나리오 카드 2열: 이름 15/700 · 출처 태그 · 사용자 · 제품 · 번호 장면(쓰인 제품) · 자유 항목
  const cards = view.locator('.scv-card');
  await expect(cards).toHaveCount(2);
  const ai = view.locator('[data-vscenario="미등록 방문객 응대"]');
  await expect(ai.locator('.fl-vtag')).toHaveText('AI A안 · 수락');
  await expect(ai.locator('.fl-vtag')).toHaveClass(/fl-vtag--ai/);
  await expect(ai).toContainText('사용자예약 없이 온 외부 방문객');
  const man = view.locator('[data-vscenario="출근 혼잡 시간의 로비"]');
  await expect(man.locator('.fl-vtag')).toHaveText('직접');
  await expect(man.locator('.scv-pill')).toHaveText(['Smart Signage QM55C', 'MagicINFO']);
  await expect(man.locator('.scv-step')).toHaveText(['1출근 인원이 몰려 게이트 앞이 혼잡해짐', '2층별 엘리베이터 대기 안내가 뜸Smart Signage QM55C']);
  await expect(man.locator('.scv-step__p')).toHaveText('Smart Signage QM55C');
  await expect(man.locator('.scv-kv').last()).toHaveText('시간대오전 9시 전후');
  // 보드 View(content=sc): 본문 1100 · 공간 236 | 14 | 850 · 공간 버튼 52 · 카드 2열(본문 816 − 12) · 머리 아래 본문 y209
  expect(await box(view.locator('.scv'))).toMatchObject({ x: 300, w: 1100 });
  expect(await box(view.locator('.scv-spaces'))).toMatchObject({ x: 300, w: 236 });
  expect(await box(view.locator('.scv-main'))).toMatchObject({ x: 550, w: 850 });
  const scv = await box(view.locator('.scv'));
  expect(scv.y + scv.h).toBe(876);                                                                // 본문 바닥 = 900 − 24
  expect(await height(page, '.scv-sp')).toBe(52);
  expect(await box(cards.first())).toMatchObject({ x: 567, w: 402 });
  expect(await box(cards.nth(1))).toMatchObject({ x: 981, w: 402 });
  expect(await height(page, '.scv-prod')).toBe(26);
  await still(page);
  await shot(page, 'SC_View-new');
  // 시나리오 없는 공간 — 점선 칸(보드 · 문구는 팝업 모델로)
  await view.locator('[data-vspace="회의실"]').click();
  await expect(view.locator('.scv-empty')).toHaveText('이 공간은 시나리오가 없어요단계 칩 「공간 · 시나리오」에서 시나리오를 더할 수 있어요');
  await expect(view.locator('.scv-head__n')).toHaveText('시나리오 0');
  await still(page);
  await shot(page, 'SC_View-empty-new');
  await view.locator('[data-vspace="로비"]').click();
  // flow.json(stages.sc 강조)
  await view.getByRole('button', { name: 'flow.json' }).click();
  const json = page.getByRole('dialog', { name: /flow\.json/ });
  await expect(json).toBeVisible();
  await expect(json.getByText('"sc": {').first()).toBeVisible();
  await expect(json.locator('.wm-jsonline--add').first()).toBeVisible();
  await shot(page, 'SC_ViewJson-new');
  await json.getByRole('button', { name: '닫기' }).last().click();

  // 허브 flow.json stages.sc · 진행 칸 · 팝업 카드
  const flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const sc = flow.stages.sc;
  expect(sc.ref).toBe(code);
  expect(sc.ver).toBe(1);
  expect(sc.from).toBe(dssRef);
  expect(sc.spaces.map((s: { name: string }) => s.name)).toEqual(['로비', '회의실', '주차장']);
  const lobby = sc.spaces[0];
  expect(lobby.scenarios.map((x: { title: string; by: string }) => [x.title, x.by])).toEqual([['미등록 방문객 응대', 'ai-candidate-A'], ['출근 혼잡 시간의 로비', 'manual']]);
  expect(lobby.scenarios[0].user).toBe('예약 없이 온 외부 방문객');
  expect(lobby.scenarios[1].products).toEqual(['Smart Signage QM55C', 'MagicINFO']);
  expect(lobby.scenarios[1].steps[1]).toEqual({ text: '층별 엘리베이터 대기 안내가 뜸', product: 'Smart Signage QM55C' });
  expect(lobby.scenarios[1].fields).toEqual([{ k: '시간대', v: '오전 9시 전후' }]);
  expect(sc.counts).toEqual({ spaces: 3, scenarios: 2, spacesWithoutScenario: 2 });
  const cell = flow.cells.find((c: { key: string }) => c.key === 'sc');
  expect(cell.state).toBe('done');
  expect(cell.route).toBe(`/scenario/spaces/${setId}`);
  expect(flow.cards.sc.facts).toEqual([['공간', '3'], ['시나리오', '2'], ['시나리오 없는 공간', '2']]);

  // ── 단계 칩 「공간 · 시나리오」 → 고치기 팝업(SC2_Edit: SC-nn v1 고치기 · 저장 · v2 · 이전 단계 링크 없음) — 고치지 않고 닫으면 묻지 않는다 ──
  await view.getByRole('button', { name: /^공간 · 시나리오 · / }).click();
  await expect(page).toHaveURL(/step=spaces/);
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${code} v1 고치기`);
  await expect(stepDlg.locator('.fl-shead__note')).toHaveText(`저장하면 ${code} v2 · ${sb.id}에 반영돼요`);
  await expect(stepDlg.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(stepDlg.locator('.wm-flow__back')).toHaveCount(0);
  await expect(page.getByRole('tab', { name: /로비/ })).toContainText('시나리오 2 · 제품 4');
  await still(page);
  await shot(page, 'SC2_Edit-new');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  await expect(page.getByRole('dialog', { name: '고친 내용을 저장할까요?' })).toHaveCount(0);
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v1`);

  // 고친 뒤(자동 저장을 기다리지 않고) 닫으면 저장할지 한 번 묻는다 → 「저장 · v2」 → 최종본 v2
  await view.getByRole('button', { name: /^공간 · 시나리오 · / }).click();
  await page.locator('.ss-sc', { hasText: '출근 혼잡 시간의 로비' }).click();
  await page.locator('#ss-who').fill('오전 8시 반 ~ 9시 반 임직원');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  const ask = page.getByRole('dialog', { name: '고친 내용을 저장할까요?' });
  await expect(ask).toBeVisible();
  await expect(ask).toContainText(`저장하면 ${code} v2로 연결된 Storyboard에 반영돼요.`);
  await shot(page, 'SC2_EditAsk-new');
  await ask.getByRole('button', { name: '저장 · v2' }).click();
  await expect(stepDlg).toHaveCount(0, { timeout: 20_000 });
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v2`);
  await expect(man).toContainText('사용자오전 8시 반 ~ 9시 반 임직원');
  await expect(page.getByTestId('scv-unsaved')).toHaveCount(0);
  expect((await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json()).stages.sc.ver).toBe(2);

  // 「저장하지 않고 닫기」 → 고친 내용은 이 묶음에만(머리 아래 안내 줄 · 보드에 없음) → 줄의 「저장 · v3」
  await view.getByRole('button', { name: /^공간 · 시나리오 · / }).click();
  await page.getByRole('tab', { name: /주차장/ }).click();
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  await page.locator('#ss-title').fill('야간 주차 안내');
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await ask.getByRole('button', { name: '저장하지 않고 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  const unsaved = page.getByTestId('scv-unsaved');
  await expect(unsaved).toContainText(`고친 내용이 아직 Storyboard에 반영되지 않았어요 · 저장하면 ${code} v3`);
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v2`);
  await expect(view.locator('[data-vspace="주차장"]')).toContainText('시나리오 1 · 제품 1');
  await still(page);
  await shot(page, 'SC_View-unsaved-new');
  await unsaved.getByRole('button', { name: '저장 · v3' }).click();
  await expect(view.locator('.fl-dver')).toHaveText(`${code} v3`, { timeout: 20_000 });
  await expect(unsaved).toHaveCount(0);
  await expect(view.locator('.fl-dhead__meta')).toContainText('공간 3 · 시나리오 3 · 시나리오 없는 공간 1');

  // 목록 — 저장된 공간 시나리오 줄 · 연결된 Storyboard 칩
  await page.goto('/scenario');
  const listRow = page.locator('.fl-card', { hasText: `${code} v3` });
  await expect(listRow).toContainText(sb.name);
  await expect(listRow.locator('.fl-cardtitle')).toHaveAttribute('href', `/scenario/spaces/${setId}`);
  await still(page);
  await shot(page, 'SC0-list-new');
  await listRow.locator('.fl-cardtitle').click();
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`));
  await expect(page.locator('.fl-detail')).toHaveAttribute('data-status', 'saved');
  await expect(stepDlg).toHaveCount(0);                                                       // 저장된 것은 최종본만

  // Gate — 이미 SC 가 있는 Storyboard 는 수정 / 복제본 → 「수정하기」는 최종본 위 ② 고치기 팝업
  await page.goto(`/scenario/new?sb=${sb.id}`);
  await expect(page.getByText(`이 Storyboard에는 공간 시나리오 ${code} v3이 이미 있어요`)).toBeVisible();
  await page.getByRole('button', { name: `${code} 수정하기` }).click();
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}\\?step=spaces$`));
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText(`${code} v3 고치기`);
});

test('SC 새 흐름 — 「만들기」(?sb=&auto=1)는 Gate 를 건너뛰고 바로 ② 팝업 · 닫으면 작성 중 최종본 · 옛 주소는 이전 흐름으로', async ({ page, request }) => {
  test.setTimeout(150_000);
  const sb = await makeStoryboard(request, { dss: true, name: `판교 스타트업 단지 ${tag()}` });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/scenario/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/?]+\?step=spaces$/, { timeout: 20_000 });
  const setId = page.url().split('/').pop()!.split('?')[0];
  const stepDlg = page.locator('.fl-stepdlg');
  await expect(page.getByRole('tab', { name: /로비/ })).toBeVisible();
  await expect(stepDlg.locator('.fl-shead__sb')).toContainText(sb.name);
  await expect(stepDlg.locator('.fl-shead__mode')).toHaveText('새로 만들기');
  await expect(page.locator('.fl-detail .fl-dver')).toHaveText('새로 만들기');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText('새로 만들기');
  // 1920 × 1080: 팝업은 가운데 1180 × 800 그대로 · 칸 폭 그대로
  await page.setViewportSize({ width: 1920, height: 1080 });
  expect(await box(stepDlg)).toMatchObject({ x: 370, y: 140, w: 1180, h: 800 });
  expect(await box(page.locator('.ss-spaces'))).toMatchObject({ x: 402, w: 196 });
  expect(await box(page.locator('.ss-ed'))).toMatchObject({ w: 662 });
  await page.setViewportSize({ width: 1440, height: 900 });

  // 닫으면 작성 중(보드 SC_Draft) — 채운 칸 없음 → ② 자리표시에 「이어서 · 공간 · 시나리오」
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await expect(stepDlg).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`));
  const view = page.locator('.fl-detail');
  await expect(view).toHaveAttribute('data-status', 'draft');
  await expect(view.locator('.fl-dver')).toHaveText('작성 중 1/2');
  await expect(view.locator('.fl-dhead__meta')).toHaveText(new RegExp(`^작성 중 · 2단계 중 1단계 마침 · 오늘 \\d\\d:\\d\\d · 저장하면 ${sb.id}에 연결돼요$`));
  await expect(view.locator('.fl-dnav__label')).toHaveText('단계 1/2');
  await expect(view.locator('.wm-sbbar')).toContainText('저장하면 이 Storyboard에 연결돼요');
  await expect(page.locator('.sh-crumbs__cur')).toHaveText(sb.name);                         // 작성 중 = 이름
  const slot = view.locator('[data-slot="2"]');
  await expect(slot).toContainText('공간 · 시나리오 단계');
  await expect(slot).toContainText('공간 → 시나리오 → 장면 — 이 단계를 마치면 여기에 채워져요');
  await expect(slot).toHaveClass(/fl-slot--next/);
  // 보드 SC_Draft: 자리표시가 본문을 채운다(300, 209 · 1100 × 667)
  expect(await box(slot)).toMatchObject({ x: 300, w: 1100 });
  const sb0 = await box(slot);
  expect(sb0.y + sb0.h).toBe(876);
  await still(page);
  await shot(page, 'SC_Draft-new');
  await slot.getByRole('button', { name: '이어서 · 공간 · 시나리오' }).click();
  await expect(page).toHaveURL(/step=spaces/);
  await expect(stepDlg).toBeVisible();
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  // 작성 중을 다시 열면(목록 · 작업 내역 · 새로 고침) ② 팝업이 열린 채로
  await page.goto(`/scenario/spaces/${setId}`);
  await expect(page).toHaveURL(/step=spaces/);
  await expect(stepDlg.getByRole('heading', { name: '공간마다 시나리오를 여러 개 써요' })).toBeVisible();
  // 단계 칩(머리) — 작성 중에는 「단계 n/N」 · ② 를 누르면 팝업
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();
  await view.getByRole('button', { name: /^공간 · 시나리오 · / }).click();
  await expect(page).toHaveURL(/step=spaces/);
  await stepDlg.getByRole('button', { name: '팝업 닫기' }).click();

  // 새로 만들기 팝업을 고르기 전에 닫으면 목록
  await page.goto('/scenario/new');
  await page.getByRole('dialog', { name: '새 공간 시나리오 · Storyboard' }).getByRole('button', { name: '팝업 닫기' }).click();
  await expect(page).toHaveURL(/\/scenario$/);

  // DSS 전 Storyboard 는 Gate 에서 고를 수 없다(「DSS 먼저」)
  const pre = await makeStoryboard(request, { name: `동탄 시니어 복합단지 ${tag()}` });
  await page.goto(`/scenario/new?sb=${pre.id}&auto=1`);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const off = page.getByRole('radio', { name: new RegExp(esc(pre.name)) });
  await expect(off).toHaveAttribute('aria-disabled', 'true');
  await expect(off).toContainText('DSS 먼저');
  const r = await request.post('/api/scenario/v1/space-sets', { data: { sb_id: pre.id } });
  expect(r.status()).toBe(422);
  expect((await r.json()).error.code).toBe('PREREQUISITE_MISSING');

  // 이전 흐름은 /scenario/legacy 아래 · 다른 기능 · 서버 handoff 가 만드는 옛 주소는 주소 그대로 이전 화면
  await page.goto('/scenario/legacy');
  await expect(page.getByTestId('sc0-new')).toHaveAttribute('href', '/scenario/legacy/new');
  await page.getByTestId('sc0-new').click();
  await expect(page).toHaveURL(/\/scenario\/legacy\/new$/);
  await expect(page.getByTestId('sc1-with')).toBeVisible();
  await page.goto('/scenario/new?sb=sb_01HZZZZZZZZZZZZZZZZZZZZZZZ');               // 이전 Storyboard SB4 handoff
  await expect(page.getByTestId('sc1-with')).toBeVisible();
  await page.goto('/scenario/new?from=vp:vp_x');                                // VP4 재료
  await expect(page.getByTestId('sc1-with')).toBeVisible();
  await expect(page).toHaveURL(/\/scenario\/new\?from=vp:vp_x$/);
  await page.goto('/scenario/new/template');                                     // UC_SC · 다른 기능 링크
  await expect(page.getByTestId('sc1t-tile')).toHaveCount(16);
  await page.goto('/scenario/legacy/new/template');
  await expect(page.getByTestId('sc1t-tile')).toHaveCount(16);
  await page.goto('/scenario/spaces/new');
  await expect(page).toHaveURL(/\/scenario\/new$/);
  await expect(page.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
});
