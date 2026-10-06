/** BE5G — 생성 중(`/birdseye/:id/render/:jobId`, §4.9): 단계 5 · 진행률 · 초안 미리보기 · 컷 대기열 · 확인 필요 · 진행 중 요청 · 중지. */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import { useJob } from '@/api/jobs';
import { Icon, toast } from '@/ui';
import { be, errText, fileUrl, qk, useBe, useCuts, useLayout, useSpace, type Cut } from '../api';
import { Agent, BePage, Dock, Echo, Loading, PromptBar, SubButton, jo, useBeShell } from '../ui';
import { TONES } from './LayoutPage';

const ACTION: Record<string, string> = {
  structure: '공간 구조를 잡는', products: '제품을 배치하는', furniture: '가구와 마감재를 입히는', render: '조명을 맞춰 렌더링하는', qc: '품질을 확인하는',
};
const BAND: Record<string, string> = {
  structure: '공간 구조 잡는 중', products: '제품 배치하는 중', furniture: '가구 · 마감재 입히는 중', render: '조명 · 렌더링 중', qc: '품질 확인 중',
};
const DONE_NAME: Record<string, string> = { structure: '공간 구조', products: '제품 배치', furniture: '가구와 마감재', render: '조명과 렌더링', qc: '품질 확인' };
const ST: Record<string, string> = { done: '완료', run: '진행 중', wait: '대기' };

export function etaLabel(s?: number | null): string {
  if (s == null) return '';
  if (s >= 60) return `약 ${Math.ceil(s / 60)}분 남음`;
  return `약 ${Math.max(10, Math.round(s / 10) * 10)}초 남음`;
}

function joinDone(names: string[]): string {
  if (!names.length) return '';
  if (names.length === 1) return names[0];
  const head = names.slice(0, -1).join(', ');
  return `${jo(head, '과', '와')} ${names[names.length - 1]}`;
}

export function renderW(c: Cut): string {
  const steps = c.steps ?? [];
  const done = steps.filter((s) => s.state === 'done').map((s) => DONE_NAME[s.stage] ?? s.label);
  const run = steps.find((s) => s.state === 'run');
  const head = '배치안을 3D로 만들고 있어요.';
  const tail = '다른 작업을 해도 계속 진행되고, 끝나면 알려드릴게요.';
  if (c.status === 'queued') return `배치안을 3D로 만들 차례를 기다리고 있어요. ${tail}`;
  const now = run ? `지금 ${ACTION[run.stage] ?? run.label} 중입니다.` : '';
  if (!done.length) return [head, now, tail].filter(Boolean).join(' ');
  return [head, `${joinDone(done)}까지 끝났고,`, now || '', tail].filter(Boolean).join(' ');
}

export default function RenderPage() {
  const { id = '', jobId = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const cq = useCuts(id, true);
  const lq = useLayout(id);
  const sq = useSpace(id);
  const [preview, setPreview] = useState<string | null>(null);
  const [memoBusy, setMemoBusy] = useState(false);
  const [sent, setSent] = useState<string[]>([]);
  const cuts = cq.data ?? [];
  const cut = cuts.find((c) => c.job_id === jobId);
  const { job } = useJob(jobId, {
    onEvent: (e) => { if (e.type === 'partial' && e.data?.kind === 'preview' && e.data.draft_file_id) setPreview(String(e.data.draft_file_id)); },
    onDone: () => void qc.invalidateQueries({ queryKey: qk.cuts(id) }),
  });
  useBeShell(bq.data, 5);
  const done = cut && ['done', 'check'].includes(cut.status);
  useEffect(() => {
    if (done) { void qc.invalidateQueries({ queryKey: qk.one(id) }); nav(`/birdseye/${id}/result?cut=${cut!.id}`, { replace: true }); }
  }, [done]); // eslint-disable-line react-hooks/exhaustive-deps
  const assumptions = useMemo(() => {
    const out: Array<{ text: string; action?: string | null }> = [];
    for (const a of lq.data?.layout?.assumptions ?? []) out.push({ text: a.text_ko, action: a.action });
    for (const a of sq.data?.model?.assumptions ?? []) if (['dims_missing', 'door_unknown', 'dim_default'].includes(a.kind)) out.push({ text: a.text_ko, action: a.action });
    return out;
  }, [lq.data, sq.data]);

  if (bq.isLoading || cq.isLoading) return <Loading />;
  if (!cut) {
    if (cq.isFetching) return <Loading />;          // 방금 만든 컷 — 목록을 다시 읽는 중
    return <BePage><Agent text="이 생성 작업을 찾을 수 없어요." /><SubButton to={`/birdseye/${id}/result`}>결과로</SubButton></BePage>;
  }
  const failed = cut.status === 'failed' || job?.status === 'failed';
  const canceled = cut.status === 'canceled' || cut.status === 'draft';
  const tone = TONES.find((t) => t.value === cut.tone)?.label ?? '웜 우드';
  const lay = lq.data?.layout;
  const pKinds = new Set((lay?.groups ?? []).filter((g) => g.kind === 'product').map((g) => g.ref)).size;
  const fKinds = new Set((lay?.groups ?? []).filter((g) => g.kind !== 'product').map((g) => g.ref)).size;
  const queue = cuts.filter((c) => c.status === 'queued' && c.id !== cut.id);
  const draftFid = preview ?? cut.draft_v1_file_id ?? cut.draft_file_id;
  const run = (cut.steps ?? []).find((s) => s.state === 'run');
  const pct = Math.round(cut.progress || job?.progress || 0);

  const stop = async () => {
    try { await be.cancelCut(cut.id); await qc.invalidateQueries({ queryKey: qk.cuts(id) }); nav(`/birdseye/${id}/layout`); } catch (e) { toast(errText(e)); }
  };
  const retry = async () => {
    try {
      const acc = await be.createCuts(id, { views: [{ preset: cut.view.preset, target_item_id: cut.view.target_item_id ?? null, custom_text: cut.view.custom_text ?? null }],
        lights: [cut.light], before: cut.before, tone: cut.tone, primary: cut.is_primary, auto_extra: false });
      if (acc.route) nav(acc.route, { replace: true });
    } catch (e) { toast(errText(e)); }
  };
  const memo = async (text: string) => {
    setMemoBusy(true);
    try {
      unwrap(await api.jobs.POST('/v1/jobs/{job_id}/memos', { params: { path: { job_id: jobId } }, body: { text } as never }));
      setSent((s) => [...s, text]);
    } catch (e) { toast(errText(e)); return false; } finally { setMemoBusy(false); }
  };

  return (
    <BePage testId="be5g" dock={(
      <Dock title="3D 조감도 생성 중" meta="5 / 5 · 다른 작업을 해도 돼요, 끝나면 알려드릴게요"
        foot={(
          <>
            <PromptBar label="진행 중 요청" placeholder="진행 중에도 요청을 남겨주세요 (예: 로비에 사람 실루엣 몇 명 넣어줘)" busy={memoBusy} disabled={failed || canceled}
              onSend={memo} testId="be5g-memo" />
            <SubButton to="/birdseye">작업 목록으로</SubButton>
            <SubButton onClick={() => void stop()} disabled={failed || canceled} testId="be5g-stop">중지</SubButton>
          </>
        )} />
    )}>
      <Echo text={`이 배치로 3D 생성 · ${tone} · ${cut.view.label}`} />
      {failed ? (
        <Agent text={`조감도를 만들지 못했어요. ${cut.error || job?.error?.message || ''}`.trim()}>
          <div className="be-row">
            <button type="button" className="be-btn be-btn--sm" onClick={() => void retry()}>다시 시도</button>
            <Link className="be-btn be-btn--sm" to={`/birdseye/${id}/layout`}>배치로 돌아가기</Link>
          </div>
        </Agent>
      ) : canceled ? (
        <Agent text="생성을 멈췄어요. 끝난 단계까지는 초안으로 저장했어요.">
          <div className="be-row"><Link className="be-btn be-btn--sm" to={`/birdseye/${id}/layout`}>배치로 돌아가기</Link></div>
        </Agent>
      ) : (
        <Agent text={renderW(cut)} busy>
          <div className="be-prog" role="group" aria-label="3D 조감도 생성 중" data-testid="be5g-progress">
            <div className="be-prog__head">
              <b>3D 조감도 생성 중</b>
              <span><span className="be-prog__pct">{pct}%</span>{cut.eta_s != null && <span className="be-muted be-small"> · {etaLabel(cut.eta_s)}</span>}</span>
            </div>
            <div className="be-prog__bar"><i style={{ width: `${pct}%` }} /></div>
            <div className="be-prog__line">{cut.view.label} · {tone} · {cut.resolution} · 제품 {pKinds}종 · 가구 {fKinds}종</div>
            <div className="be-steps" data-testid="be5g-steps">
              {(cut.steps ?? []).map((s) => (
                <div key={s.stage} className={`be-step be-step--${s.state}`}>
                  <span className="be-step__dot">{s.state === 'done' && <Icon name="check" size={11} strokeWidth={3} />}</span>
                  <span className="be-step__name">{s.label}</span>
                  <span className="be-step__note" title={s.note}>{s.note}</span>
                  <span className="be-step__st">{ST[s.state]}</span>
                </div>
              ))}
            </div>
          </div>
          <span className="be-note">중지해도 끝난 단계까지는 초안으로 저장돼요</span>
          {draftFid && (
            <div className="be-sec">
              <div className="be-sec__head"><b>기다리는 동안 미리보기</b><span>마감재 적용 전</span></div>
              <div className="be-preview" data-testid="be5g-preview">
                <img src={fileUrl(draftFid)} alt={`초안 · ${cut.view.label}`} />
                <span className="be-preview__tag">초안 · {cut.view.label}</span>
                {run && <span className="be-preview__band">{BAND[run.stage] ?? run.label}</span>}
              </div>
            </div>
          )}
          {queue.length > 0 && (
            <div className="be-sec" data-testid="be5g-queue">
              <div className="be-sec__head"><b>끝나면 이어서 만들 컷</b><span>· 대기열 {queue.length}</span></div>
              <div className="be-queue">
                {queue.map((c, i) => (
                  <div key={c.id} className="be-queue__row">
                    <span className="n">{i + 1}</span><span className="grow">{c.label}</span><span className="be-muted">대기</span>
                    <button type="button" className="be-btn be-btn--sm" aria-label="대기열에서 빼기"
                      onClick={() => void be.cancelCut(c.id).then(() => qc.invalidateQueries({ queryKey: qk.cuts(id) })).catch((e) => toast(errText(e)))}>
                      <Icon name="x" size={13} />
                    </button>
                  </div>
                ))}
              </div>
              <Link className="be-link" to={`/birdseye/${id}/views`}>시점 · 조명 컷 추가</Link>
            </div>
          )}
          {queue.length === 0 && <Link className="be-link" to={`/birdseye/${id}/views`}>시점 · 조명 컷 추가</Link>}
          {assumptions.map((a, i) => (
            <div key={i} className="be-assume" data-testid="be5g-assume">
              <i>!</i>
              <span style={{ flex: 1 }}><b>확인 필요</b> · {a.text}</span>
              {a.action === 'BE1D' && <Link className="be-link" to={`/birdseye/${id}/space/plan`}>벽 치수 보정</Link>}
              {a.action === 'BE1P' && <Link className="be-link" to={`/birdseye/${id}/space/photos`}>사진 보강</Link>}
            </div>
          ))}
          {sent.length > 0 && <div className="be-note">남긴 요청 · {sent.join(' / ')}</div>}
        </Agent>
      )}
    </BePage>
  );
}

