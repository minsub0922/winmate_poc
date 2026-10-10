/**
 * DSS 화면 → 셸 맥락(상단바 · 스텝바 · 「현재 작업에 추가」). 화면마다 한 곳에서만 useShellPage 를 부른다.
 * 셸 제품 · 솔루션 상세 시트와 팝오버의 「현재 작업에 추가」: 제품은 지금 고른 공간에, 솔루션은 고른 솔루션에 더한다.
 */
import { CONTENT, kb, type DragType, type ShellPageConfig } from '@/shell';
import { toast } from '@/ui';
import type { DSAddProduct, DSDoc, DsActions } from './api';
import { addBodyOf, modelCodeOf } from './parts';

const M = CONTENT.dss;

export function dsShell(d: DSDoc | undefined, step: 2 | 3, extra: Partial<ShellPageConfig> = {}): ShellPageConfig {
  return {
    section: M.label, title: d?.title ?? M.short, hasTask: true, stepper: { steps: M.steps, current: step },
    taskContext: d ? { products: d.spaces.flatMap((s) => s.products.filter((p) => p.by !== 'ai-pending' && p.ref).map((p) => ({ ref: p.ref!, label: p.name }))) } : undefined,
    ...extra,
  };
}

/** 이미 이 DSS 에 있는 참조(팝오버 「✓ 추가됨」) — 제품 ref · `kb:solution:<카탈로그 id>` */
export function addedRefs(d: DSDoc): string[] {
  return [...d.spaces.flatMap((s) => s.products.filter((p) => p.by !== 'ai-pending' && p.ref).map((p) => p.ref!)), ...d.solutions.map((s) => `kb:solution:${s.id}`)];
}

/** KB 참조 → 제품 넣기 본문(검색 결과의 이름 · 분류 그대로). 찾지 못하면 null(지어내지 않는다) */
async function bodyOfRef(r: string): Promise<DSAddProduct | null> {
  const code = modelCodeOf(r);
  try {
    const res = await kb.productSearch(code ?? r.split(':').pop() ?? r, 6, code ? 'model' : 'model,family');
    const hit = res.items.find((h) => `kb:${h.kind}:${h.id}` === r);
    return hit ? addBodyOf(hit) : null;
  } catch { return null; }
}

/** 「현재 작업에 추가」 처리기 — space 가 없으면 제품은 받지 않는다 */
export function dsOnAdd(d: DSDoc, actions: DsActions, space: { key: string; name: string } | null) {
  return async (type: DragType, refs: string[]): Promise<{ added: string[] }> => {
    if (type === 'solution') {
      const have = d.solutions.map((s) => s.id);
      const ids = refs.map((r) => r.replace(/^kb:solution:/, '')).filter((id) => id && !have.includes(id));
      if (!ids.length) return { added: [] };
      try {
        await actions.setSolutions([...have, ...ids]);
        toast(`솔루션 ${ids.length}개를 골랐어요`);
        return { added: ids.map((id) => `kb:solution:${id}`) };
      } catch (e) { toast((e as Error).message || '솔루션을 더하지 못했어요'); return { added: [] }; }
    }
    if (type !== 'product' || !space) return { added: [] };
    const added: string[] = [];
    for (const r of refs) {
      const body = await bodyOfRef(r);
      if (!body) continue;
      try { await actions.addProduct(space.key, body); added.push(r); } catch (e) { toast((e as Error).message || '제품을 넣지 못했어요'); }
    }
    if (added.length) toast(`${space.name}에 제품 ${added.length}개를 넣었어요`);
    else if (refs.length) toast('KB 에서 그 제품을 찾지 못했어요. 아래 검색으로 넣어 주세요.');
    return { added };
  };
}
