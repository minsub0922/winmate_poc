/**
 * DSS 상세 → 셸 「현재 작업에 추가」(셸 제품 · 솔루션 상세 시트와 팝오버): 제품은 첫 공간에, 솔루션은 고른 솔루션에 더한다.
 */
import { kb, type DragType } from '@/shell';
import { toast } from '@/ui';
import type { DSAddProduct, DSDoc, DsActions } from './api';
import { addBodyOf, modelCodeOf } from './parts';

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
    else if (refs.length) toast('KB 에서 그 제품을 찾지 못했어요. 공간 카드의 「+ 제품」으로 넣어 주세요.');
    return { added };
  };
}
