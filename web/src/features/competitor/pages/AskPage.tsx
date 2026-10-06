/** CA2Q — 되묻기 · 고객사 · 장소(§4.11). find 잡 awaiting_input{kind:"slots"} 에 답한다. */
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { answerJob, cancelJob } from '@/api/jobs';
import { Button, PathIcon } from '@/ui';
import { patchAnalysis, qk, useAnalysis } from '../api';
import { useCaShell } from '../hooks';
import { Band, BigButton, CaPage, ErrorCol, FootBar, GUIDE, Head, InfoLine, LoadingCol, SlotStrip } from '../parts';

export function AskPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useAnalysis(aid, { poll: 5000 });
  const a = q.data;
  useCaShell({ aid, title: a?.title || '새 분석', current: 1, added: a?.added_refs });
  const [customer, setCustomer] = useState('');
  const [place, setPlace] = useState('');
  const [busy, setBusy] = useState<'answer' | 'skip' | 'back' | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const fresh = q.isFetchedAfterMount;
  useEffect(() => {
    if (!a || busy || !fresh) return;
    if (a.status === 'finding') nav(`/competitor/${aid}/finding`, { replace: true });
    else if (a.status === 'confirming') nav(`/competitor/${aid}/candidates`, { replace: true });
    else if (a.status === 'draft' || a.status === 'failed') nav(`/competitor/${aid}/input`, { replace: true });
    else if (a.status !== 'ask') nav(a.route, { replace: true });
  }, [a, aid, nav, busy, fresh]);

  if (q.isLoading) return <LoadingCol />;
  if (q.isError || !a) return <ErrorCol message="작업을 찾지 못했어요" onRetry={() => q.refetch()} />;
  const jobId = a.current_job_id;
  const ask = a.ask;

  async function send(answer: Record<string, unknown>, kind: 'answer' | 'skip') {
    if (!jobId) return;
    setBusy(kind);
    setErr(null);
    try {
      await answerJob(jobId, answer);
      await qc.invalidateQueries({ queryKey: qk.analysis(aid) });
      nav(`/competitor/${aid}/finding`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '답을 보내지 못했어요');
      setBusy(null);
    }
  }

  async function back() {
    setBusy('back');
    try {
      if (jobId) await cancelJob(jobId);
      await patchAnalysis(aid, { last_screen: 'input' }).catch(() => undefined);
      await qc.invalidateQueries({ queryKey: qk.analysis(aid) });
    } finally {
      nav(`/competitor/${aid}/input`);
    }
  }

  const can = !!(customer.trim() || place.trim());
  return (
    <CaPage>
      <Head kicker="질문 1 / 1" title={ask?.title || '어느 고객사, 어느 지역인가요?'}
        desc={ask?.desc || '입력에서 고객사와 장소를 읽지 못했어요. 알려 주면 지역 경쟁사까지 찾아요.'} />
      <SlotStrip label="입력에서 읽은 것" slots={a.slots} count={a.found_count} order="found-first" />
      <div className="ca-askcard">
        <div className="ca-field">
          <label htmlFor="ca-cust">고객사</label>
          <div className="ca-field__box"><input id="ca-cust" placeholder="예) A 커피 프랜차이즈" value={customer} maxLength={60} autoFocus
            onChange={(e) => setCustomer(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && can) void send({ customer: customer.trim(), place: place.trim() }, 'answer'); }} /></div>
        </div>
        <div className="ca-field">
          <label htmlFor="ca-place">지역 · 장소</label>
          <div className="ca-field__box"><input id="ca-place" placeholder="예) 수도권 직영점 · 전국 320개 매장" value={place} maxLength={40}
            onChange={(e) => setPlace(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && can) void send({ customer: customer.trim(), place: place.trim() }, 'answer'); }} /></div>
        </div>
      </div>
      <InfoLine>{GUIDE}</InfoLine>
      {!jobId && <Band tone="warn">찾기가 이미 끝났거나 멈췄어요 · 입력 화면에서 다시 찾아 주세요</Band>}
      {err && <Band tone="danger">{err}</Band>}
      <FootBar back={{ onClick: back }}>
        <div className="ca-row">
          <Button h={44} className="ca-big2" onClick={() => send({ skip: true }, 'skip')} loading={busy === 'skip'} disabled={!jobId || !!busy}
            icon={<PathIcon d="M5 6l7 6-7 6 M13 6l7 6-7 6" size={14} color="var(--wm-text-muted)" strokeWidth={2.2} />}>건너뛰기 — 업종 기준으로 찾기</Button>
          <span className="ca-hint" style={{ padding: 0 }}>후보가 넓어져요</span>
        </div>
        <span className="ca-grow" />
        <BigButton onClick={() => send({ customer: customer.trim(), place: place.trim() }, 'answer')} disabled={!can || !jobId || !!busy && busy !== 'answer'}
          loading={busy === 'answer'} disabledReason="고객사나 지역 · 장소 중 하나는 적어 주세요">답하고 찾기</BigButton>
      </FootBar>
    </CaPage>
  );
}

export default AskPage;
