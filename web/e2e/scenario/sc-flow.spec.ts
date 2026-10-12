/**
 * 공간 시나리오 상세 한 장(웹앱 ① v63 보드 SC0 · SC1 · SC2 · SC_Draft · SC2_AI · SC2_Pick · SC2_Empty · SC2_Edit · SC_View · 본문 SCBody) — Storyboard 허브 연동.
 * API 로 Storyboard(요구사항 + DSS)를 만들고 목록 → 「새 공간 시나리오 만들기」→ 목록 위 Storyboard 고르기 팝업 → 상세(새로 · DSS 공간 · 제품만)
 * → 시나리오 추가 · 장면 · 쓰인 제품 · 항목 → AI 3안(점선 카드) 수락 → 공간 제품 고르기 팝업 → 저장 → 그 자리에서 저장됨(토스트)
 * → 한 칸 고치기 → 「고친 곳 1」(고친 칸 강조) → 되돌리기 → 다시 고쳐 저장 · v2 → 허브 stages.sc.
 * 보드 고정 칸(공간 220 · 카드 2열)과 본문 열(1180 · 패딩 40)을 숫자로 재고 `__screens__/<보드>.png` 를 `_rendered` 와 나란히 본다.
 * 실제 스택(mock 모델 — 로비 AI 3안은 mocks/ai-tools/sc.space_candidates.v1.json 고정 응답).
 */
import { expect, test, type Locator, type Page } from '@playwright/test';
import { makeStoryboard, tag } from '../shell/flowkit';
import { shot } from './helpers';

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const box = async (l: Locator) => { const b = (await l.boundingBox())!; return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
/** 캡처 전 — 마우스를 치우고 앞 단계 토스트가 사라질 때까지(보드에는 토스트가 없다) */
const still = async (page: Page) => { await page.mouse.move(0, 0); await expect(page.locator('.wm-toast')).toHaveCount(0, { timeout: 8_000 }); await page.waitForTimeout(300); };
const card = (page: Page, title: string) => page.locator(`.ss-card[data-title="${title.replace(/"/g, '\\"')}"]`);
/** 칸을 고치고 떠난다(InlineInput 은 떠날 때 저장) */
const type = async (l: Locator, v: string) => { await l.fill(v); await l.press('Enter'); };
const doc = async (page: Page, id: string) => (await page.request.get(`/api/scenario/v1/space-sets/${id}`)).json();

test('SC v63 — 목록 → 팝업 → 상세(새로) → 바로 입력 · AI 3안 · 제품 고르기 → 저장 → 고친 곳 1 → 되돌리기 → v2', async ({ page, request }) => {
  test.setTimeout(300_000);
  const sb = await makeStoryboard(request, { dss: true, name: `용산 AI Ready 오피스 ${tag()}` });
  const flow0 = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  const dssRef: string = flow0.stages.dss.ref;
  await page.setViewportSize({ width: 1440, height: 900 });

  // ── SC0 목록 → 「새 공간 시나리오 만들기」 = 목록 위 팝업(SC1) ──
  await page.goto('/scenario');
  await expect(page.getByRole('heading', { name: '공간 시나리오 생성', level: 1 })).toBeVisible();
  await page.locator('.fl-hero').click();
  await expect(page).toHaveURL(/\/scenario\/new$/);
  const gate = page.getByRole('dialog', { name: '새 공간 시나리오 만들기 · Storyboard 고르기' });
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const row = gate.getByRole('radio', { name: new RegExp(esc(sb.name)) });
  await row.click();
  await expect(row).toHaveAttribute('aria-checked', 'true');
  await expect(gate.getByText('고르면 바로 공간 시나리오 화면으로 넘어가요')).toBeVisible();
  await still(page);
  await shot(page, 'SC1');
  await gate.getByRole('button', { name: /이 Storyboard로 시작/ }).click();
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/]+$/, { timeout: 20_000 });
  const setId = page.url().split('/').pop()!;

  // ── SC2 새로 만들기 — DSS 공간 · 공간 제품만, 시나리오 없음 ──
  const head = page.locator('.cd-head');
  await expect(head.locator('.cd-ref')).toHaveText('새로 만들기');
  await expect(head.locator('.cd-meta')).toHaveText(`새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · 저장하면 ${sb.id}에 연결돼요`);
  await expect(head.getByRole('button', { name: '저장', exact: true })).toBeVisible();
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);
  await expect(page.locator('.ss-spaces__h')).toHaveText(`공간 · ${dssRef}`);
  await expect(page.locator('.ss-sp')).toHaveText([/로비시나리오 없음 · 제품 4/, /회의실시나리오 없음 · 제품 2/, /주차장시나리오 없음 · 제품 1/]);
  await expect(page.locator('.ss-spaces__foot')).toHaveText('공간마다 제품 · 솔루션이 하나 이상 있어야 저장돼요');
  await expect(page.locator('.ss-head__name')).toHaveText('로비');
  await expect(page.locator('.ss-head__n')).toHaveText('시나리오 0');
  await expect(page.locator('.ss-pchip')).toHaveText([/제품The Wall IAB 146"/, /제품Smart Signage QM55C/, /제품삼성 키오스크/, /솔루션MagicINFO/]);
  await expect(page.locator('.ss-empty')).toContainText('이 공간은 시나리오가 없어요');
  await expect(page.getByRole('button', { name: '+ 시나리오 추가' })).toBeVisible();
  // 보드 폭: 본문 열 1180 · 패딩 40 → 1100 = 공간 220 | 14 | 866 · 카드 2열((866 - 2 - 32 - 12) / 2 = 410)
  expect((await box(page.locator('.cd'))).w).toBe(1180);
  expect((await box(page.locator('.ss-grid'))).w).toBe(1100);
  expect((await box(page.locator('.ss-spaces'))).w).toBe(220);
  expect((await box(page.locator('.ss-main'))).w).toBe(866);
  expect((await box(page.locator('.ss-sp').first())).h).toBe(52);
  expect((await box(page.locator('.ss-addcard'))).w).toBe(410);
  // 본문 높이(보드 682): 900 − 64 − 52 − 20 − 46 − 14 − 22 = 682
  expect((await box(page.locator('.ss-grid'))).h).toBe(682);
  await still(page);
  await shot(page, 'SC2');

  // SC2_Empty — 시나리오 없는 공간(주차장)
  await page.locator('.ss-sp', { hasText: '주차장' }).click();
  await expect(page.locator('.ss-head__name')).toHaveText('주차장');
  await expect(page.locator('.ss-pchip')).toHaveText([/제품옥외형 사이니지 OHC55/]);
  await expect(page.locator('.ss-empty')).toContainText('아래 「+ 시나리오 추가」로 바로 쓰거나 「AI 시나리오 3안」으로 후보를 받아요 · 없어도 저장돼요');
  await still(page);
  await shot(page, 'SC2_Empty');

  // 공간 제품을 모두 빼면 주황 · 저장 막힘(이유 토스트) → 다시 넣기
  await page.getByRole('button', { name: '빼기 · 옥외형 사이니지 OHC55' }).click();
  await expect(page.locator('.ss-warnpill')).toHaveText('하나 이상 골라야 저장돼요');
  await expect(page.locator('.ss-sp', { hasText: '주차장' })).toContainText('제품 없음 · 저장 안 됨');
  await expect(page.getByRole('button', { name: /AI 시나리오 3안/ })).toBeDisabled();
  const saveBtn = head.getByRole('button', { name: '저장', exact: true });
  await expect(saveBtn).toHaveAttribute('aria-disabled', 'true');
  await saveBtn.click({ force: true });                                                  // aria-disabled — 누르면 이유를 알려 준다
  await expect(page.locator('.wm-toast').filter({ hasText: '주차장에 제품 · 솔루션이 없어요 · 공간마다 하나 이상 있어야 저장돼요' })).toBeVisible();
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  let dlg = page.getByRole('dialog', { name: '주차장 · 공간 제품 · 솔루션 고르기' });
  await expect(dlg.getByText('하나 이상 골라야 해요')).toBeVisible();
  await dlg.getByRole('checkbox', { name: /옥외형 사이니지 OHC55/ }).click();
  await expect(dlg.getByText('1개 골랐어요')).toBeVisible();
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(saveBtn).not.toHaveAttribute('aria-disabled', 'true');

  // ── 로비: 직접 시나리오(제품 토글 · 장면 · 쓰인 제품 · 항목) ──
  await page.locator('.ss-sp', { hasText: '로비' }).click();
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  let c = page.locator('.ss-card').last();
  await expect(c.getByRole('textbox', { name: '시나리오 이름' })).toBeFocused();
  await type(c.getByRole('textbox', { name: '시나리오 이름' }), '출근 혼잡 시간의 로비');
  c = card(page, '출근 혼잡 시간의 로비');
  await expect(c.locator('.ss-tag')).toHaveText('직접');
  await type(c.getByRole('textbox', { name: '사용자' }), '오전 9시 전후 임직원');
  await c.getByRole('button', { name: 'The Wall IAB 146"', exact: true }).click();     // 이 시나리오에서 빼기(점선)
  await c.getByRole('button', { name: '삼성 키오스크', exact: true }).click();
  await expect(c.locator('.ss-tchip--on')).toHaveText(['Smart Signage QM55C', 'MagicINFO']);
  await type(c.getByRole('textbox', { name: '장면 1' }), '출근 인원이 몰려 게이트 앞이 혼잡해짐');
  await c.getByRole('button', { name: '+ 단계' }).click();
  await type(c.getByRole('textbox', { name: '장면 2' }), '층별 엘리베이터 대기 안내가 뜸');
  await c.getByRole('button', { name: '+ 단계' }).click();
  await type(c.getByRole('textbox', { name: '장면 3' }), '혼잡이 풀리면 사이니지가 공지로 돌아감');
  await expect(c.locator('.ss-pbtn')).toHaveText(['+ 쓰인 제품', '+ 쓰인 제품', '+ 쓰인 제품']);
  await c.locator('.ss-pbtn').nth(1).click();
  await expect(c.getByRole('listbox', { name: '장면 2 쓰인 제품' }).getByRole('option')).toHaveText(['Smart Signage QM55C', 'MagicINFO']);
  await c.getByRole('option', { name: 'Smart Signage QM55C' }).click();
  await c.locator('.ss-pbtn').nth(2).click();
  await c.getByRole('option', { name: 'MagicINFO' }).click();
  await expect(c.locator('.ss-pbtn')).toHaveText(['+ 쓰인 제품', 'Smart Signage QM55C', 'MagicINFO']);
  await expect(c.locator('.ss-more .ss-fchip')).toHaveText(['+ 시간대', '+ 기대 효과', '+ 연결 요구', '+ 페인 포인트']);
  await expect(page.locator('.ss-head__n')).toHaveText('시나리오 1');
  await expect(page.locator('.ss-sp', { hasText: '로비' })).toContainText('시나리오 1 · 제품 4');
  // 무언가 썼으니 「작성 중」
  await expect(head.locator('.cd-ref')).toHaveText('작성 중');
  await expect.poll(async () => (await doc(page, setId)).counts.scenarios, { timeout: 10_000 }).toBe(1);

  // ── SC2_Pick — 로비 공간 제품 · 솔루션 고르기(DSS 묶음 · 있던 공간) ──
  await page.getByRole('button', { name: '+ 추가 · 변경' }).click();
  dlg = page.getByRole('dialog', { name: '로비 · 공간 제품 · 솔루션 고르기' });
  await expect(dlg.getByText('공간에 쓸 제품 · 솔루션을 고르세요. 하나 이상 있어야 하고, 고른 것 중에서 시나리오마다 다시 골라요.')).toBeVisible();
  await expect(dlg.getByText(`${dssRef} · 제품`, { exact: true })).toBeVisible();
  await expect(dlg.getByText(`${dssRef} · 솔루션`, { exact: true })).toBeVisible();
  await expect(dlg.getByRole('checkbox', { name: /Flip Pro WA75D/ })).toContainText(`${dssRef} · 회의실`);
  await expect(dlg.getByText('4개 골랐어요')).toBeVisible();
  expect((await box(dlg)).w).toBe(760);
  await still(page);
  await shot(page, 'SC2_Pick');
  await dlg.getByRole('checkbox', { name: /SmartThings Pro/ }).click();               // 솔루션 하나 더하기 → 칩 5
  await expect(dlg.getByText('5개 골랐어요')).toBeVisible();
  await dlg.getByRole('button', { name: '완료' }).click();
  await expect(page.locator('.ss-pchip')).toHaveCount(5);
  await expect(c.locator('.ss-tchip')).toHaveCount(5);
  await expect(c.locator('.ss-tchip', { hasText: 'SmartThings Pro' })).not.toHaveClass(/ss-tchip--on/);   // 새 공간 제품은 시나리오에 자동으로 넣지 않는다
  await page.getByRole('button', { name: '빼기 · SmartThings Pro' }).click();
  await expect(page.locator('.ss-pchip')).toHaveCount(4);

  // ── SC2_AI — AI 시나리오 3안(점선 카드 · 수락 · ×) ──
  await page.getByRole('button', { name: /AI 시나리오 3안/ }).click();
  await expect(page.locator('.ss-card.cd-pend')).toHaveCount(3, { timeout: 30_000 });
  const ca = card(page, '미등록 방문객 응대');
  await expect(ca.locator('.ss-tag')).toHaveText('AI A안');
  await expect(card(page, '사내 행사 날 로비').locator('.ss-tag')).toHaveText('AI B안');
  await expect(page.locator('.ss-head__n')).toHaveText('시나리오 1');                  // 후보는 시나리오 수에 들지 않는다
  await type(ca.getByRole('textbox', { name: '사용자' }), '예약 없이 온 외부 방문객');   // 수락 전 편집
  await expect.poll(async () => (await doc(page, setId)).spaces[0].candidates[0].user, { timeout: 10_000 }).toBe('예약 없이 온 외부 방문객');
  // 보드 SC2_AI 와 같은 화면: 직접 시나리오 1 + 수락 1 이 위에, 점선 후보 B · C 가 아래에
  await ca.getByRole('button', { name: '수락' }).click();
  await expect(page.locator('.ss-card.cd-pend')).toHaveCount(2);
  await expect(card(page, '미등록 방문객 응대').locator('.ss-tag')).toHaveText('AI A안 · 수락');
  await expect(page.locator('.ss-head__n')).toHaveText('시나리오 2');
  await expect(card(page, '미등록 방문객 응대').getByRole('textbox', { name: '사용자' })).toHaveValue('예약 없이 온 외부 방문객');
  await expect(card(page, '미등록 방문객 응대').getByRole('textbox', { name: '기대 효과' })).toHaveValue('대기 시간 단축');
  await page.locator('.ss-scroll').evaluate((el) => el.scrollTo(0, 0));
  await still(page);
  await shot(page, 'SC2_AI');
  for (const t of ['사내 행사 날 로비', '퇴근 후 보안 모드']) {
    await card(page, t).getByRole('button', { name: `후보 지우기 · ${t}` }).click();
    await expect(card(page, t)).toHaveCount(0);
  }
  await expect(page.locator('.ss-card')).toHaveCount(2);

  // 시간대 항목 · 회의실 직접 시나리오 하나(제품 고르지 않으면 저장 막힘)
  c = card(page, '출근 혼잡 시간의 로비');
  await c.getByRole('button', { name: '+ 시간대' }).click();
  await type(c.getByRole('textbox', { name: '시간대' }), '오전 9시 전후');
  await page.locator('.ss-sp', { hasText: '회의실' }).click();
  await page.getByRole('button', { name: '+ 시나리오 추가' }).click();
  const cm = page.locator('.ss-card').last();
  await type(cm.getByRole('textbox', { name: '시나리오 이름' }), '하이브리드 회의');
  for (const n of ['Flip Pro WA75D', 'Smart Signage QB55C']) await cm.getByRole('button', { name: n, exact: true }).click();
  await expect(cm.locator('.ss-tchip--on')).toHaveCount(0);
  await expect(saveBtn).toHaveAttribute('aria-disabled', 'true');
  await saveBtn.click({ force: true });
  await expect(page.locator('.wm-toast').filter({ hasText: '회의실 · 하이브리드 회의에 쓰는 제품 · 솔루션을 하나 이상 골라 주세요' })).toBeVisible();
  await cm.getByRole('button', { name: 'Flip Pro WA75D', exact: true }).click();
  await type(cm.getByRole('textbox', { name: '장면 1' }), '[확인 필요]');
  await expect(cm.getByRole('textbox', { name: '장면 1' })).toHaveClass(/cd-in--warn/);

  // SC_Draft — 다시 열었을 때(작성 중 · 공간 3 · 시나리오 3 · 자동 저장)
  await page.waitForTimeout(800);
  await page.reload();
  await expect(head.locator('.cd-ref')).toHaveText('작성 중');
  await expect(head.locator('.cd-meta')).toHaveText(new RegExp(`^작성 중 · 공간 3 · 시나리오 3 · 오늘 \\d\\d:\\d\\d 자동 저장 · 저장하면 ${sb.id}에 연결돼요$`));
  await expect(page.locator('.ss-sp')).toHaveText([/로비시나리오 2 · 제품 4/, /회의실시나리오 1 · 제품 2/, /주차장시나리오 없음 · 제품 1/]);
  await expect(page.locator('.ss-card')).toHaveCount(2);
  await expect(card(page, '출근 혼잡 시간의 로비').locator('.ss-pbtn')).toHaveText(['+ 쓰인 제품', 'Smart Signage QM55C', 'MagicINFO']);
  // 카드 2열(보드 SC_Draft)
  const [b0, b1] = [await box(page.locator('.ss-card').nth(0)), await box(page.locator('.ss-card').nth(1))];
  expect(b0.w).toBe(410);
  expect(b1.w).toBe(410);
  expect(b1.x - b0.x).toBe(422);
  expect(b1.y).toBe(b0.y);
  await still(page);
  await shot(page, 'SC_Draft');

  // ── 저장 → 그 자리에서 저장됨(SC_View · 토스트 · 완료 화면 없음) ──
  await saveBtn.click();
  await expect(page.locator('.wm-toast').filter({ hasText: new RegExp(`^SC-\\d+ v1 저장 · ${sb.id}에 반영했어요`) })).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/scenario/spaces/${setId}$`));
  const set1 = await doc(page, setId);
  await expect(head.locator('.cd-ref')).toHaveText(`${set1.code} v1`);
  await expect(head.locator('.cd-meta')).toHaveText(/^오늘 \d\d:\d\d 저장 · 공간 3 · 시나리오 3 · 시나리오 없는 공간 1$/);
  await expect(head.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await expect(head.getByRole('button', { name: /flow\.json/ })).toBeVisible();
  await expect(head.getByRole('button', { name: '저장', exact: true })).toHaveCount(0);
  await expect(page.locator('.cd-next')).toHaveCount(0);                                  // 공간 시나리오는 후속 작업이 없다
  expect(set1.ver).toBe(1);
  expect(set1.changes).toBe(0);
  await page.locator('.ss-sp', { hasText: '로비' }).click();
  await still(page);
  await shot(page, 'SC_View');
  // flow.json 팝업(이 콘텐츠 줄 강조)
  await head.getByRole('button', { name: /flow\.json/ }).click();
  const json = page.getByRole('dialog').filter({ hasText: `${sb.id}/flow.json` });
  await expect(json).toBeVisible();
  await expect(json.getByText('초록 줄이 이 콘텐츠(stages.sc)예요')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(json).toHaveCount(0);

  // 허브 flow.json stages.sc · 진행 칸 · 팝업 카드
  let flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  let sc = flow.stages.sc;
  expect(sc.ref).toBe(set1.code);
  expect(sc.ver).toBe(1);
  expect(sc.from).toBe(dssRef);
  expect(sc.spaces.map((s: { name: string }) => s.name)).toEqual(['로비', '회의실', '주차장']);
  const lobby = sc.spaces[0];
  expect(lobby.scenarios.map((x: { title: string; by: string }) => [x.title, x.by])).toEqual([['출근 혼잡 시간의 로비', 'manual'], ['미등록 방문객 응대', 'ai-candidate-A']]);
  expect(lobby.scenarios[0].products).toEqual(['Smart Signage QM55C', 'MagicINFO']);
  expect(lobby.scenarios[0].steps[1]).toEqual({ text: '층별 엘리베이터 대기 안내가 뜸', product: 'Smart Signage QM55C' });
  expect(lobby.scenarios[0].fields).toEqual([{ k: '시간대', v: '오전 9시 전후' }]);
  expect(lobby.scenarios[1].user).toBe('예약 없이 온 외부 방문객');
  expect(sc.counts).toEqual({ spaces: 3, scenarios: 3, spacesWithoutScenario: 1 });
  const cell = flow.cells.find((x: { key: string }) => x.key === 'sc');
  expect(cell.state).toBe('done');
  expect(cell.route).toBe(`/scenario/spaces/${setId}`);
  expect(flow.cards.sc.facts).toEqual([['공간', '3'], ['시나리오', '3'], ['시나리오 없는 공간', '1']]);

  // ── 한 칸 고치기 → 「고친 곳 1」 · 고친 칸 강조(SC2_Edit) ──
  c = card(page, '출근 혼잡 시간의 로비');
  await type(c.getByRole('textbox', { name: '사용자' }), '오전 9시 전후 임직원 · 방문객');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1', { timeout: 10_000 });
  await expect(head.locator('.cd-ref')).toHaveText(`${set1.code} v1 · 고치는 중`);
  await expect(head.locator('.cd-meta')).toHaveText(`${set1.code} v1 고치는 중 · 저장하면 v2 · ${sb.id}에 반영돼요`);
  await expect(head.getByRole('button', { name: '저장 · v2' })).toBeVisible();
  await expect(c.getByRole('textbox', { name: '사용자' })).toHaveClass(/cd-in--chg/);
  await expect(page.locator('.cd-in--chg')).toHaveCount(1);
  // 되돌리기 → 저장한 값 · 고친 곳 없음
  await head.getByRole('button', { name: '되돌리기' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${set1.code} v1로 되돌렸어요` })).toBeVisible();
  await expect(head.getByText('눌러서 바로 고쳐요')).toBeVisible();
  await expect(head.locator('.cd-chg')).toHaveCount(0);
  await expect(card(page, '출근 혼잡 시간의 로비').getByRole('textbox', { name: '사용자' })).toHaveValue('오전 9시 전후 임직원');
  await expect(page.locator('.cd-in--chg')).toHaveCount(0);
  expect((await doc(page, setId)).changes).toBe(0);

  // 다시 고치기(SC2_Edit: 사용자 · 장면 2 · 장면 4 더하기 = 고친 곳 3) → 화면 캡처 → 저장 · v2
  c = card(page, '출근 혼잡 시간의 로비');
  await type(c.getByRole('textbox', { name: '사용자' }), '오전 9시 전후 임직원 · 방문객');
  await type(c.getByRole('textbox', { name: '장면 2' }), '층별 엘리베이터 대기 시간이 실시간으로 뜸');
  await c.getByRole('button', { name: '+ 단계' }).click();
  await type(c.getByRole('textbox', { name: '장면 4' }), '방문객은 키오스크로 따로 안내');
  await c.locator('.ss-pbtn').nth(3).click();
  await c.getByRole('option', { name: 'Smart Signage QM55C' }).click();
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 3', { timeout: 10_000 });
  await expect(page.locator('.cd-in--chg')).toHaveCount(3);
  await expect(page.locator('.ss-sp', { hasText: '로비' })).toContainText('시나리오 2 · 제품 4');
  await still(page);
  await shot(page, 'SC2_Edit');
  await head.getByRole('button', { name: '저장 · v2' }).click();
  await expect(page.locator('.wm-toast').filter({ hasText: `${set1.code} v2 저장 · ${sb.id}에 반영했어요` })).toBeVisible({ timeout: 20_000 });
  await expect(head.locator('.cd-ref')).toHaveText(`${set1.code} v2`);
  await expect(page.locator('.cd-in--chg')).toHaveCount(0);
  flow = await (await request.get(`/api/storyboard/v1/flows/${sb.id}`)).json();
  sc = flow.stages.sc;
  expect(sc.ver).toBe(2);
  expect(sc.spaces[0].scenarios[0].user).toBe('오전 9시 전후 임직원 · 방문객');
  expect(sc.spaces[0].scenarios[0].steps.map((s: { text: string }) => s.text)).toEqual(['출근 인원이 몰려 게이트 앞이 혼잡해짐', '층별 엘리베이터 대기 시간이 실시간으로 뜸', '혼잡이 풀리면 사이니지가 공지로 돌아감', '방문객은 키오스크로 따로 안내']);
  expect(sc.spaces[0].scenarios[0].steps[3].product).toBe('Smart Signage QM55C');

  // 고치다 다른 화면으로 가면 묻는다(셸 ContentDetail)
  await type(card(page, '출근 혼잡 시간의 로비').getByRole('textbox', { name: '시간대' }), '오전 8시 30분 ~ 9시 30분');
  await expect(head.locator('.cd-chg')).toHaveText('고친 곳 1', { timeout: 10_000 });
  await page.locator('.sh-group__link').filter({ hasText: '공간 시나리오 생성' }).first().click();
  const leave = page.getByRole('dialog', { name: '저장하지 않은 고친 곳' });
  await expect(leave).toContainText('고친 곳 1개를 아직 저장하지 않았어요');
  await leave.getByRole('button', { name: '계속 고치기' }).click();
  await head.getByRole('button', { name: '되돌리기' }).click();
  await expect(head.locator('.cd-chg')).toHaveCount(0);

  // 목록 — 저장된 공간 시나리오 카드 · 연결된 Storyboard 칩
  await page.goto('/scenario');
  const listRow = page.locator('.fl-card', { hasText: `${set1.code} v2` });
  await expect(listRow).toContainText(sb.name);
  await expect(listRow.locator('.fl-cardtitle')).toHaveAttribute('href', `/scenario/spaces/${setId}`);

  // 팝업 — 이미 SC 가 있는 Storyboard 는 「열어 고치기」 / 복제본
  await page.goto(`/scenario/new?sb=${sb.id}`);
  await expect(page.getByText(`이 Storyboard에는 공간 시나리오 ${set1.code} v2가 이미 있어요`)).toBeVisible();
  await expect(page.getByRole('button', { name: `${set1.code} 열어 고치기` })).toBeVisible();
});

test('SC v63 — Storyboard 화면의 「만들기」(?sb=&auto=1)는 팝업을 건너뛴다 · 옛 주소 · 이전 흐름', async ({ page, request }) => {
  test.setTimeout(120_000);
  const sb = await makeStoryboard(request, { dss: true, name: `판교 스타트업 단지 ${tag()}` });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/scenario/new?sb=${sb.id}&auto=1`);
  await expect(page).toHaveURL(/\/scenario\/spaces\/scs_[^/]+$/, { timeout: 20_000 });
  await expect(page.locator('.ss-sp', { hasText: '로비' })).toBeVisible();
  await expect(page.locator('.cd-head .cd-ref')).toHaveText('새로 만들기');
  await expect(page.locator('.wm-sbbar__chip')).toContainText(sb.name);
  // 예전 완료 · 단계 주소로 와도 상세가 뜬다
  await page.goto(`${page.url()}?step=done`);
  await expect(page.locator('.ss-sp', { hasText: '로비' })).toBeVisible();

  // DSS 전 Storyboard 는 팝업에서 고를 수 없다(「DSS 먼저」)
  const pre = await makeStoryboard(request, { name: `동탄 시니어 복합단지 ${tag()}` });
  await page.goto(`/scenario/new?sb=${pre.id}&auto=1`);
  const gate = page.getByRole('dialog', { name: '새 공간 시나리오 만들기 · Storyboard 고르기' });
  await expect(gate.getByRole('heading', { name: '어느 Storyboard로 만들까요?' })).toBeVisible();
  const off = gate.getByRole('radio', { name: new RegExp(esc(pre.name)) });
  await expect(off).toHaveAttribute('aria-disabled', 'true');
  await expect(off).toContainText('DSS 먼저');
  const r = await request.post('/api/scenario/v1/space-sets', { data: { sb_id: pre.id } });
  expect(r.status()).toBe(422);
  expect((await r.json()).error.code).toBe('PREREQUISITE_MISSING');
  // 팝업을 닫으면 목록
  await gate.getByRole('button', { name: '닫기' }).first().click();
  await expect(page).toHaveURL(/\/scenario$/);
  // 저장 전 되돌리기는 409 NOT_SAVED
  const made = await (await request.post('/api/scenario/v1/space-sets', { data: { sb_id: sb.id } })).json();
  const rv = await request.post(`/api/scenario/v1/space-sets/${made.id}:revert`);
  expect(rv.status()).toBe(409);
  expect((await rv.json()).error.code).toBe('NOT_SAVED');

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
  await page.goto('/scenario/spaces/new');
  await expect(page).toHaveURL(/\/scenario\/new$/);
  await expect(page.getByRole('dialog', { name: '새 공간 시나리오 만들기 · Storyboard 고르기' })).toBeVisible();
});
