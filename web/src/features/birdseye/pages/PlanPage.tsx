/** BE1D — 도면 인식 확인(`/birdseye/:id/space/plan` · 새로 `/birdseye/new/plan`, §4.3): 인식 결과 · 요소 5종 · 되묻기 · 치수 보정 · 말로 고치기. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Dropzone, Icon, Toggle, toast } from '@/ui';
import { useJob } from '@/api/jobs';
import { be, errText, qk, uploadAll, useBe, usePlans, type PlanView, type Question } from '../api';
import { PlanCanvas, type Highlight } from '../PlanCanvas';
import { Agent, BePage, Dock, DockLink, Loading, MainButton, PromptBar, SubButton, useBeShell } from '../ui';

export default function PlanPage() {
  const { id } = useParams();
  if (!id) return <NewPlan />;
  return <PlanReview id={id} />;
}

/** 「도면 올려서 시작」 — 올리면 작업을 만들고 인식 → BE1D */
function NewPlan() {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  useBeShell(null, 1);
  const onFiles = async (files: File[]) => {
    if (!files.length) return;
    setBusy(true);
    try {
      const work = await be.create({});
      const up = await uploadAll(files.slice(0, 1));
      const acc = await be.addPlan(work.id, up[0].id);
      nav(`/birdseye/${work.id}/space/plan?plan=${acc.plan_id}`, { replace: true });
    } catch (e) { toast(errText(e)); setBusy(false); }
  };
  return (
    <BePage testId="be1d-new" dock={<Dock title="공간 인식 확인" meta="1 / 5" foot={<SubButton to="/birdseye/new">이전</SubButton>} />}>
      <Agent text="도면 파일을 올려 주세요. 벽 · 창 · 문 · 기둥을 읽어 공간 구조를 만들어 드릴게요." busy={busy} />
      <Dropzone onFiles={onFiles} accept=".pdf,.png,.jpg,.jpeg,.heic,application/pdf,image/png,image/jpeg,image/heic" multiple={false}
        title="도면 끌어 놓기" hint="PDF · PNG · JPG · HEIC" disabled={busy} />
    </BePage>
  );
}

function PlanReview({ id }: { id: string }) {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const pq = usePlans(id);
  const plans = pq.data?.items ?? [];
  const plan = plans.find((p) => p.id === sp.get('plan')) ?? plans[plans.length - 1];
  const [overlay, setOverlay] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [hl, setHl] = useState<Highlight>(null);
  const [openQ, setOpenQ] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editJob, setEditJob] = useState<string | null>(null);
  const [manual, setManual] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: qk.plans(id) });
  useJob(editJob, { onDone: () => { setEditJob(null); void refresh(); } });
  useJob(plan?.status === 'recognizing' ? plan.job_id : null, { onDone: () => void refresh() });
  useBeShell(bq.data, 1);
  const questions = plan?.questions ?? [];
  const open = questions.filter((q) => !q.answered);
  useEffect(() => { if (!openQ && open.length) setOpenQ(open.find((q) => q.kind === 'door')?.id ?? open[0].id); }, [open.length]); // eslint-disable-line react-hooks/exhaustive-deps
  const geo = usePlanGeo(plan);

  const answer = async (body: Parameters<typeof be.answer>[1]) => {
    if (!plan) return;
    try { await be.answer(id, body, plan.id); await refresh(); } catch (e) { toast(errText(e)); }
  };
  const again = async (page?: number) => {
    if (!plan) return;
    try { await be.recognize(id, plan.id, page); await refresh(); } catch (e) { toast(errText(e)); }
  };
  const another = async (files: FileList | null) => {
    if (!files?.length) return;
    try {
      const up = await uploadAll([files[0]]);
      const acc = await be.addPlan(id, up[0].id);
      setSp({ plan: acc.plan_id });
      await refresh();
    } catch (e) { toast(errText(e)); }
  };
  const proceed = async () => {
    setBusy(true);
    try {
      await be.analyze(id);
      await qc.invalidateQueries({ queryKey: qk.one(id) });
      const photos = await be.photos(id);
      nav(photos.counts.total > 0 && photos.basis_count === 0 ? `/birdseye/${id}/space/photos` : `/birdseye/${id}/products`);
    } catch (e) { toast(errText(e)); setBusy(false); }
  };

  if (pq.isLoading || bq.isLoading) return <Loading />;
  if (!plan) {
    return (
      <BePage dock={<Dock title="공간 인식 확인" meta="1 / 5" foot={<SubButton to={`/birdseye/${id}/space`}>이전</SubButton>} />}>
        <Agent text="아직 올린 도면이 없어요. 도면 파일을 올려 주세요." />
        <Dropzone onFiles={(f) => void another(f as unknown as FileList)} accept=".pdf,.png,.jpg,.jpeg,.heic" multiple={false} title="도면 끌어 놓기" hint="PDF · PNG · JPG · HEIC" />
      </BePage>
    );
  }
  const recognizing = plan.status === 'recognizing';
  const dimQ = questions.filter((q) => q.kind === 'dim');
  const doorQ = questions.filter((q) => q.kind === 'door');

  return (
    <BePage testId="be1d" dock={(
      <Dock title="공간 인식 확인" meta={open.length ? <>확인 필요 {open.length} · 1 / 5</> : '1 / 5'}
        right={(
          <>
            <DockLink onClick={() => void again()} icon={<Icon name="refresh" size={13} />} disabled={recognizing}>다시 인식</DockLink>
            <DockLink onClick={() => fileRef.current?.click()} icon={<Icon name="upload" size={13} />}>다른 도면 올리기</DockLink>
            <DockLink to={`/birdseye/${id}/space/photos`} icon={<Icon name="image" size={13} />}>현장 사진 더하기</DockLink>
            <input ref={fileRef} type="file" hidden accept=".pdf,.png,.jpg,.jpeg,.heic" onChange={(e) => { void another(e.target.files); e.target.value = ''; }} />
          </>
        )}
        foot={(
          <>
            <PromptBar label="말로 고치기" placeholder="말로 고치기 (예: 오른쪽 기둥은 철거됐어, 창은 끝까지 유리야)" busy={!!editJob} disabled={recognizing}
              onSend={async (t) => { try { const r = await be.spaceNlEdit(id, t); setEditJob(r.job_id); } catch (e) { toast(errText(e)); return false; } }} testId="be1d-nl" />
            <SubButton to={`/birdseye/${id}/space`}>이전</SubButton>
            <MainButton onClick={proceed} busy={busy} disabled={recognizing || plan.status === 'failed'} testId="be1d-next">이 구조로 계속</MainButton>
          </>
        )} />
    )}>
      <div className="be-echo">
        <div className="be-row">
          <span className="be-file-chip" style={{ height: 34, padding: '0 12px' }} data-testid="be1d-file">
            <Icon name="file" size={14} /><b style={{ color: 'var(--wm-text)' }}>{plan.file_name}</b><span>{plan.file_meta}</span>
          </span>
          {plan.pages > 1 && (
            <select aria-label="쪽 선택" value={plan.page} onChange={(e) => void again(Number(e.target.value))} className="be-pill">
              {Array.from({ length: plan.pages }, (_, i) => <option key={i} value={i + 1}>{i + 1}쪽</option>)}
            </select>
          )}
          {plans.length > 1 && (
            <select aria-label="도면 고르기" value={plan.id} onChange={(e) => setSp({ plan: e.target.value })} className="be-pill">
              {plans.map((p) => <option key={p.id} value={p.id}>{p.file_name}</option>)}
            </select>
          )}
        </div>
      </div>
      <Agent text={plan.w_message} busy={recognizing}>
        {(plan.notices ?? []).map((n) => <div key={n} className="be-notice" role="status" data-testid="be1d-notice"><Icon name="info" size={14} />{n}</div>)}
        {plan.status === 'failed' && <div className="be-notice">{plan.error || '도면을 읽지 못했어요'}</div>}
        <div className="be-plan" style={{ width: 760, height: 440, display: 'flex', flexDirection: 'column' }}>
          <div className="be-canvas-head" style={{ height: 42, padding: '0 12px 0 16px', borderBottom: '1px solid var(--wm-line)' }}>
            <div className="be-row"><b>인식 결과</b><span className="be-muted" data-testid="be1d-scale">{plan.scale_label}</span></div>
            <div className="be-row">
              <Toggle checked={overlay} onChange={setOverlay}>원본 겹쳐 보기</Toggle>
              <span className="be-zoom">
                <button type="button" aria-label="축소" onClick={() => setZoom((z) => Math.max(0.5, Math.round((z - 0.25) * 100) / 100))}>−</button>
                <span>{Math.round(zoom * 100)}%</span>
                <button type="button" aria-label="확대" onClick={() => setZoom((z) => Math.min(3, Math.round((z + 0.25) * 100) / 100))}>+</button>
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
            <div style={{ width: 467, height: 396, flexShrink: 0, overflow: 'auto' }}>
              {geo ? (
                <PlanCanvas plan={geo} width={467} height={396} legend="plan" highlight={hl} zoom={zoom} testId="be1d-canvas" ariaLabel="도면 인식 결과"
                  pageImage={{ url: plan.page_image_url ?? '', box: plan.page_box }} showImage={overlay} />
              ) : <Loading />}
            </div>
            <div style={{ flex: 1, minWidth: 0, borderLeft: '1px solid var(--wm-line)', padding: '14px 16px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div className="be-canvas-head"><b>인식한 요소</b><span className="be-muted" data-testid="be1d-head">{plan.head}</span></div>
              <div className="be-elems" data-testid="be1d-elements">
                {(plan.elements ?? []).map((el) => {
                  const q = el.key === 'door' ? doorQ.find((x) => !x.answered) ?? doorQ[0] : undefined;
                  return (
                    <div key={el.key}>
                      <button type="button" className={hl === el.key ? 'be-elem be-elem--on' : 'be-elem'} aria-expanded={q ? openQ === q.id : undefined}
                        onClick={() => { setHl(hl === el.key ? null : (el.key as Highlight)); if (q) setOpenQ(openQ === q.id ? null : q.id); }}>
                        <b>{el.label}</b><span>{el.summary}</span>
                        {q ? <span className={q.answered ? 'be-badge-n be-badge-n--ok' : 'be-badge-n'}>{q.answered ? '✓' : q.n}</span>
                          : <span className="be-badge-n be-badge-n--ok" aria-hidden="true">✓</span>}
                      </button>
                      {q && openQ === q.id && <DoorQuestion q={q} onAnswer={(opt) => answer({ question_id: q.id, option: opt as never })} />}
                    </div>
                  );
                })}
              </div>
              {dimQ.map((q) => (
                <DimQuestion key={q.id} q={q} manual={manual} setManual={setManual}
                  onChoose={(choice, m) => answer({ dim_id: q.ref, choice: choice as never, manual_m: m ?? null })} />
              ))}
              {doorQ.filter(() => !(plan.elements ?? []).some((e) => e.key === 'door')).map((q) => (
                <DoorQuestion key={q.id} q={q} onAnswer={(opt) => answer({ question_id: q.id, option: opt as never })} />
              ))}
            </div>
          </div>
        </div>
      </Agent>
    </BePage>
  );
}

function usePlanGeo(plan: PlanView | undefined) {
  return useMemo(() => {
    const m = plan?.model;
    if (!m) return null;
    const rooms = m.rooms ?? [];
    const xs = rooms.flatMap((r) => r.outline.map((p) => p[0]));
    const ys = rooms.flatMap((r) => r.outline.map((p) => p[1]));
    return {
      width_m: xs.length ? Math.max(...xs) - Math.min(...xs) : 10, height_m: ys.length ? Math.max(...ys) - Math.min(...ys) : 8,
      rooms, walls: m.walls ?? [], openings: m.openings ?? [], columns: m.columns ?? [], cores: m.cores ?? [], power_points: m.power_points ?? [], area_label: '', window_label: null,
    };
  }, [plan]);
}

function DoorQuestion({ q, onAnswer }: { q: Question; onAnswer: (opt: string) => void }) {
  return (
    <div className={q.answered ? 'be-q be-q--ok' : 'be-q'} data-testid={`be1d-q-${q.n}`}>
      <div className="be-q__title"><span className={q.answered ? 'be-badge-n be-badge-n--ok' : 'be-badge-n'}>{q.n}</span>{q.title}</div>
      <div className="be-row">
        {(q.options ?? []).map((o) => (
          <button key={o.value} type="button" className={q.answer === o.value ? 'be-pill be-pill--on' : 'be-pill'} aria-pressed={q.answer === o.value}
            onClick={() => onAnswer(o.value)}>{o.label}</button>
        ))}
      </div>
    </div>
  );
}

function DimQuestion({ q, manual, setManual, onChoose }: { q: Question; manual: string; setManual: (v: string) => void;
  onChoose: (choice: string, manual?: number) => void }) {
  const cur = q.answer ?? 'annotated';
  return (
    <div className={q.answered ? 'be-q be-q--ok' : 'be-q'} data-testid={`be1d-q-${q.n}`}>
      <div className="be-q__title"><span className={q.answered ? 'be-badge-n be-badge-n--ok' : 'be-badge-n'}>{q.n}</span>{q.title}</div>
      {q.sub && <div className="be-q__sub">{q.sub}</div>}
      <div className="be-row" role="radiogroup" aria-label={q.title}>
        {(q.options ?? []).map((o) => (
          o.value === 'manual' ? (
            <span key={o.value} className="be-row">
              <button type="button" role="radio" aria-checked={cur === 'manual'} className={cur === 'manual' ? 'be-pill be-pill--on' : 'be-pill'}
                onClick={() => { const v = Number(manual || q.manual_m || 0); if (v > 0) onChoose('manual', v); else document.getElementById(`be-man-${q.id}`)?.focus(); }}>
                {o.label}
              </button>
              <span className="be-unit" style={{ height: 30, width: 96 }}>
                <input id={`be-man-${q.id}`} aria-label="직접 입력 (m)" inputMode="decimal" value={manual || (q.manual_m ? String(q.manual_m) : '')}
                  onChange={(e) => setManual(e.target.value.replace(/[^0-9.]/g, ''))}
                  onKeyDown={(e) => { if (e.key === 'Enter' && Number(manual) > 0) onChoose('manual', Number(manual)); }} />
                <span>m</span>
              </span>
            </span>
          ) : (
            <button key={o.value} type="button" role="radio" aria-checked={cur === o.value} className={cur === o.value ? 'be-pill be-pill--on' : 'be-pill'}
              onClick={() => onChoose(o.value)}>{o.label}</button>
          )
        ))}
      </div>
    </div>
  );
}
