/**
 * 「조감도 연결」 팝오버 내용(§4.10 · §4.12 — SC1 의 「새로 만들기」 / 「기존 조감도 연결」 선택지 재사용, 보드 밖 결정 Q-6).
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { errMessage, scApi } from '../api';
import { qk } from '../hooks';
import { Note } from '../parts';

export function AerialPicker({ scenarioId, onDone }: { scenarioId: string; onDone: (birdseyeId: string, created: boolean) => void }) {
  const opts = useQuery({ queryKey: qk.beOptions(), queryFn: scApi.birdseyeOptions, staleTime: 30_000, retry: 0 });
  const [mode, setMode] = useState<'new' | 'existing'>('new');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const n = opts.data?.count ?? 0;

  const makeNew = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await scApi.patch(scenarioId, { aerial: { enabled: true, source: 'new', birdseye_id: null, title: null, created: false } });
      if (r.aerial.birdseye_id) onDone(r.aerial.birdseye_id, true);
      else setErr('조감도 초안을 만들지 못했어요 · 조감도 서비스가 켜져 있는지 확인해 주세요');
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(false); }
  };
  const pick = async (beId: string, title: string) => {
    setBusy(true); setErr(null);
    try {
      await scApi.patch(scenarioId, { aerial: { enabled: true, source: 'existing', birdseye_id: beId, title, created: false } });
      onDone(beId, false);
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
        <button type="button" className="sc-opt" aria-pressed={mode === 'new'} onClick={() => setMode('new')} data-testid="aerial-new">
          <b>새로 만들기</b><span>시나리오 공간으로 조감도 생성</span>
        </button>
        <button type="button" className="sc-opt" aria-pressed={mode === 'existing'} onClick={() => setMode('existing')} disabled={n === 0}
          title={n === 0 ? '아직 조감도 작업이 없어요' : undefined} data-testid="aerial-existing">
          <b>기존 조감도 연결</b><span>조감도 작업 {n}개에서 고르기</span>
        </button>
      </div>
      {mode === 'existing' ? (
        <div className="sc-menu" style={{ position: 'static', boxShadow: 'none', maxHeight: 200, overflow: 'auto' }} role="menu">
          {(opts.data?.items ?? []).map((b) => <button key={b.id} type="button" role="menuitem" disabled={busy} onClick={() => void pick(b.id, b.title)}>{b.label}</button>)}
        </div>
      ) : (
        <button type="button" className="sc-btn sc-btn--sm sc-btn--brand" disabled={busy} onClick={() => void makeNew()} data-testid="aerial-make">조감도 초안 만들기</button>
      )}
      {err && <Note tone="err">{err}</Note>}
    </div>
  );
}
