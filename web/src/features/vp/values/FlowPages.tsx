/**
 * VP 목록 · 사전 작업 고르기(보드 VP0 = List content=vp · VP1 = Gate content=vp) — 셸 흐름 화면에 VP 자원만 붙인다.
 */
import { Navigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ContentListScreen, GateScreen, type DraftRow } from '@/shell';
import { createValueMap, deleteValueMap, useValueMaps, vmListKey } from './api';

/** VP0 — 저장 전 초안은 줄의 × 로 지운다(보드에 없음 — 셸이 확인을 묻는다) */
export function VpListScreen() {
  const maps = useValueMaps();
  const qc = useQueryClient();
  const drafts: DraftRow[] = (maps.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: `/vp/values/${m.id}`, sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at,
      onDelete: async () => { await deleteValueMap(m.id); void qc.invalidateQueries({ queryKey: vmListKey }); } }));
  return <ContentListScreen content="vp" drafts={drafts} />;
}

export function VpGateScreen() {
  const [sp] = useSearchParams();
  // 이전 흐름 들어오기(이전 Storyboard `sb_…` · MI · 요구사항 · 제안서에서 `/vp/new?…`) → 이전 VP 만들기 화면으로
  const sb = sp.get('sb');
  const maps = useValueMaps();
  const drafts: DraftRow[] = (maps.data?.items ?? []).filter((m) => m.status !== 'done')
    .map((m) => ({ title: m.title, ref: m.code ?? null, to: `/vp/values/${m.id}`, sbIds: m.sb_id ? [m.sb_id] : [], when: m.updated_at }));
  if ((sb && sb.startsWith('sb_')) || sp.has('mi') || sp.has('rq') || sp.has('proposal')) return <Navigate to={`/vp/legacy/new?${sp.toString()}`} replace />;
  return <GateScreen content="vp" initialSb={sp.get('sb')} autoStart={sp.get('auto') === '1'} drafts={drafts}
    onStart={async ({ sbId }) => `/vp/values/${(await createValueMap({ sb_id: sbId, select_all: true })).id}`} />;
}
