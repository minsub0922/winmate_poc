/** BE4 — 배치 · 인테리어 컨펌 4/5(`/birdseye/:id/layout`, §4.7): 2D 배치안 · 인테리어 톤 3 · 시점 2 · 배치 수정 요청 · 이 배치로 3D 생성. */
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/ui';
import { useJob } from '@/api/jobs';
import { be, errText, qk, useBe, useCatalog, useLayout } from '../api';
import { PlanCanvas } from '../PlanCanvas';
import { Agent, BePage, Dock, FieldLabel, Loading, MainButton, Pill, PromptBar, SubButton, useBeShell } from '../ui';

export const TONES = [
  { value: 'warm_wood', label: '웜 우드', swatch: '#d9c3a5' },
  { value: 'modern_white', label: '모던 화이트', swatch: '#eeeeee' },
  { value: 'dark_metal', label: '다크 메탈', swatch: '#2b2f36' },
] as const;

export default function LayoutPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const lq = useLayout(id);
  const cat = useCatalog();
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const refresh = () => Promise.all([qc.invalidateQueries({ queryKey: qk.layout(id) }), qc.invalidateQueries({ queryKey: qk.one(id) })]);
  useJob(job ?? (lq.data?.running ? lq.data.job_id : null), { onDone: () => { setJob(null); void refresh(); } });
  useBeShell(bq.data, 4);
  if (bq.isLoading || lq.isLoading) return <Loading />;
  const b = bq.data!;
  const lv = lq.data;
  const lay = lv?.layout;
  const tones = cat.data?.tones?.length
    ? cat.data.tones.map((t) => ({ value: String(t.code), label: String(t.label), swatch: String(t.swatch ?? t.floor ?? '') }))
    : TONES.map((t) => ({ ...t }));
  const setTone = async (tone: string) => { try { await be.patch(id, { tone: tone as never }); await refresh(); } catch (e) { toast(errText(e)); } };
  const setView = async (v: 'aerial45' | 'entrance') => { try { await be.patch(id, { default_view: v }); await refresh(); } catch (e) { toast(errText(e)); } };
  const make = async () => {
    setBusy(true);
    try {
      const acc = await be.createCuts(id, { views: [{ preset: b.default_view }], lights: ['day'], primary: true, auto_extra: true, tone: b.tone, before: false });
      void qc.invalidateQueries({ queryKey: qk.cuts(id) });     // 기다리지 않는다 — BE5G 가 다시 읽는다
      if (acc.route) nav(acc.route);
      else nav(`/birdseye/${id}/result`);
    } catch (e) { toast(errText(e)); setBusy(false); }
  };
  const openW = lv?.open_warnings ?? 0;

  return (
    <BePage testId="be4" dock={(
      <Dock title="배치 · 인테리어 컨펌" meta="4 / 5"
        foot={(
          <>
            <PromptBar label="배치 수정 요청" placeholder="배치 수정 요청 (예: 관람 벤치를 2열로 줄이고 The Wall 쪽으로 붙여줘)" busy={!!job} disabled={!lay} testId="be4-nl"
              onSend={async (t) => { try { const r = await be.layoutNlEdit(id, t); setJob(r.job_id); } catch (e) { toast(errText(e)); return false; } }} />
            <SubButton to={`/birdseye/${id}/furniture`}>이전</SubButton>
            <MainButton onClick={make} busy={busy} disabled={!lay || lv?.running} testId="be4-render">이 배치로 3D 생성</MainButton>
          </>
        )}>
        <div className="be-row">
          <FieldLabel>인테리어 톤</FieldLabel>
          {tones.map((t) => <Pill key={t.value} on={b.tone === t.value} swatch={t.swatch} onClick={() => void setTone(t.value)} testId={`be4-tone-${t.value}`}>{t.label}</Pill>)}
          <span className="be-sep" />
          <FieldLabel>시점</FieldLabel>
          <Pill on={b.default_view === 'aerial45'} onClick={() => void setView('aerial45')} testId="be4-view-aerial45">조감 (45°)</Pill>
          <Pill on={b.default_view === 'entrance'} onClick={() => void setView('entrance')} testId="be4-view-entrance">입구 시점</Pill>
        </div>
      </Dock>
    )}>
      <Agent text={lv?.w_message} busy={lv?.running || !!job}>
        {lv?.plan && (
          <PlanCanvas plan={lv.plan} items={lay?.items} groups={lay?.groups} width={760} height={300} testId="be4-canvas"
            onDragStart={() => undefined}
            onMove={(target, dx, dy) => nav(`/birdseye/${id}/layout/edit?move=${encodeURIComponent(`${target}:${dx}:${dy}`)}`)} />
        )}
        {openW > 0 && <Link className="be-link" to={`/birdseye/${id}/layout/edit`} data-testid="be4-warn-link">경고 {openW} · 직접 수정에서 보기</Link>}
      </Agent>
    </BePage>
  );
}
