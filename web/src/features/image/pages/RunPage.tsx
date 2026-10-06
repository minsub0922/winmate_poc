/**
 * /image/w/:workId/run/:runId — run 이 queued · running 이면 IMG3G(생성 중, §4.6), awaiting_input 이면 IMG3X(보류 · 대안, §4.8).
 * 진행은 jobs SSE + 2초 폴링(useLiveRun). 끝나도 자동으로 옮기지 않고 주 버튼을 「결과 보기」로 바꾼다.
 */
import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Button, cx, ErrorState, Icon, Img, searchProducts } from '@/ui';
import { useOpenPopover } from '@/shell';
import { errMessage, img, type Answer, type PolicyIssue, type RunDetail, type Work } from '../api';
import { AskInput, Echo, Ico, Loading, PATH, Pill, Screen, ShotCard, SwitchRow, useImgShell, WSay } from '../components';
import { isActive, useInvalidate, useLiveRun, useQueue, useWork } from '../hooks';
import { josa, pct, route } from '../lib';

export function resultRoute(run: RunDetail): string {
  if (run.kind === 'variants' && run.base_image_id) return route.variants(run.work_id, run.base_image_id);
  const first = run.shots.find((s) => s.state === 'done');
  return route.result(run.work_id, first?.image_id ?? null, run.kind === 'renditions' ? run.id : null);
}
const conditionsRoute = (w: Work | undefined, run: RunDetail) => (run.kind === 'composite' || w?.kind === 'composite' ? route.composite(run.work_id) : route.conditions(run.work_id));

export default function RunPage() {
  const { workId = '', runId = '' } = useParams();
  const wq = useWork(workId);
  const rq = useLiveRun(runId);
  const run = rq.data;
  useImgShell({ title: wq.data?.title ?? '이미지 생성', step: 3 });
  if (rq.isLoading) return <Loading />;
  if (!run) return <div className="img-center"><ErrorState message="생성 기록을 불러오지 못했어요" onRetry={() => rq.refetch()} /></div>;
  return run.status === 'awaiting_input' ? <HeldView run={run} work={wq.data} /> : <ProgressView run={run} work={wq.data} />;
}

// ── IMG3G ───────────────────────────────────────────
function ProgressView({ run, work }: { run: RunDetail; work?: Work }) {
  const nav = useNavigate();
  const inv = useInvalidate();
  const active = isActive(run.status);
  const queue = useQueue(active);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const total = run.total;
  const live = run.shots.filter((s) => s.state !== 'canceled' && s.state !== 'held');
  const overall = live.length ? live.reduce((a, s) => a + (s.state === 'done' ? 100 : s.state === 'failed' ? 100 : s.progress), 0) / live.length : 0;
  const what = run.kind === 'variants' ? `변형 ${total}장` : run.kind === 'renditions' ? `${total}개 비율` : `${total}장`;
  const failed = run.status === 'failed';
  const finished = run.status === 'succeeded' || run.status === 'canceled';
  const others = (queue.data?.items ?? []).filter((q) => q.run_id !== run.id);

  const cancelAll = async () => {
    setBusy('cancel'); setErr(null);
    try { await img.cancelRun(run.id); void inv.gallery(); void inv.work(run.work_id); nav(conditionsRoute(work, run)); } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const retry = async () => {
    setBusy('retry'); setErr(null);
    try {
      const p = run.params as Record<string, unknown>;
      const acc = run.kind === 'variants' && run.base_image_id
        ? await img.variants(run.base_image_id, { count: Math.min(4, Math.max(1, total)), axis: (p.axis as 'any' | 'lighting' | 'people') ?? 'any' })
        : run.kind === 'renditions' && run.base_image_id
          ? await img.renditions(run.base_image_id, { aspects: (p.aspects as Array<'16:9' | '4:3' | '1:1' | '9:16'>) ?? [], fit: (p.fit as 'recompose' | 'crop' | 'outpaint') ?? 'recompose', upscale: (p.upscale as '1x' | '2x' | '4x') ?? '2x' })
          : await img.startRun(run.work_id, { kind: run.kind === 'composite' ? 'composite' : 'initial' });
      nav(route.run(run.work_id, acc.run_id), { replace: true });
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const cancelShot = async (imageId: string) => {
    try { await img.cancelShot(run.id, imageId); await inv.run(run.id); } catch (e) { setErr(errMessage(e)); }
  };
  const cancelQueued = async (rid: string) => {
    try { await img.cancelRun(rid); await queue.refetch(); void inv.gallery(); } catch (e) { setErr(errMessage(e)); }
  };
  const setNotify = async (v: boolean) => {
    try { await img.setNotify(run.id, v); await inv.run(run.id); } catch (e) { setErr(errMessage(e)); }
  };
  const done = run.done;
  const reason = (run.error as { message?: string } | null)?.message ?? '이미지 모델이 응답하지 않아요';
  const zoomTo = (imageId: string) => nav(run.kind === 'variants' && run.base_image_id ? route.variants(run.work_id, run.base_image_id) : route.result(run.work_id, imageId, run.kind === 'renditions' ? run.id : null));
  const wText = failed
    ? `이미지를 만들지 못했어요. ${reason}`
    : run.status === 'succeeded'
      ? `${what}${josa(what, '을', '를')} 모두 만들었어요. 「결과 보기」에서 마음에 드는 이미지를 골라 주세요.`
      : run.status === 'canceled'
        ? '생성을 취소했어요. 끝난 시안은 갤러리에 남겨 두었어요.'
        : `${what}${josa(what, '을', '를')} 만들고 있어요. 제품 외형과 비율을 먼저 맞춘 뒤 장면을 그립니다. 완료되면 알려드릴 테니 다른 작업을 하셔도 됩니다.`;
  return (
    <Screen testid="img3g" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span data-testid="img3g-head">{run.head}<small> · 3 / 3</small></span>
            {active && <SwitchRow label="완료되면 알림" checked={run.notify} onChange={(v) => void setNotify(v)} icon={<Ico d={PATH.bell} size={14} color="var(--wm-text-muted)" />} />}
          </div>
          <div style={{ padding: '10px 18px 0 18px' }} className="img-row">
            <span className="img-progressbar" role="progressbar" aria-label="전체 진행" aria-valuenow={Math.round(overall)} aria-valuemin={0} aria-valuemax={100}>
              <span style={{ width: pct(finished ? 100 : overall) }} />
            </span>
            <span className="img-hint img-hint--sm" style={{ whiteSpace: 'nowrap' }}>{active ? run.eta_label : failed ? '멈춤' : '완료'}</span>
          </div>
          {others.length > 0 && (
            <div style={{ padding: '12px 18px 0 18px' }}>
              <div className="img-queue" data-testid="img3g-queue">
                <div className="img-row" style={{ justifyContent: 'space-between', height: 18 }}>
                  <span style={{ fontSize: 12, fontWeight: 700 }}>내 대기열 <span className="wm-num">{others.length}</span>건</span>
                  <span className="img-hint" style={{ fontSize: 11.5 }}>이 작업이 끝나면 순서대로 이어서 생성돼요</span>
                </div>
                {others.map((q) => (
                  <div key={q.run_id} className="img-queue__row">
                    <span className="img-queue__num">{q.position}</span>
                    <Link to={route.run(q.work_id, q.run_id)} className="wm-ellipsis" style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--wm-text)' }}>{q.title}</Link>
                    <span className="img-hint img-hint--sm" style={{ whiteSpace: 'nowrap', flexShrink: 0 }}>{q.meta}</span>
                    <span style={{ flex: 1 }} />
                    {q.note && q.note_route && (
                      <Link to={q.note_route} className="img-row" style={{ gap: 4, fontSize: 12, fontWeight: 600, color: 'var(--wm-text)', whiteSpace: 'nowrap' }}>
                        <Icon name="info" size={12} />{q.note}
                      </Link>
                    )}
                    <span style={{ fontSize: 12, fontWeight: q.position === 1 ? 600 : 500, color: q.position === 1 ? 'var(--wm-brand)' : 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>{q.state_label}</span>
                    <button type="button" className="img-mini" onClick={() => void cancelQueued(q.run_id)} aria-label={`${q.title} 취소`}>취소</button>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="wm-composer__foot" style={{ justifyContent: 'space-between' }}>
            <div className="img-row">
              {failed ? (
                <>
                  <Button h={44} loading={busy === 'retry'} onClick={() => void retry()} icon={<Icon name="refresh" size={14} />}>다시 시도</Button>
                  <Button h={44} onClick={() => nav(conditionsRoute(work, run))}>조건 수정</Button>
                </>
              ) : (
                <>
                  <Button h={44} disabled={!active} loading={busy === 'cancel'} onClick={() => void cancelAll()} icon={<Icon name="x" size={14} />}
                    disabledReason="진행 중인 생성이 없어요">전체 취소 · 조건 수정</Button>
                  <Button h={44} onClick={() => nav(route.list())}>목록에서 기다리기</Button>
                </>
              )}
              {err && <span className="img-err" role="alert">{err}</span>}
            </div>
            <Button h={44} variant="primary" disabled={done < 1} disabledReason="아직 완료된 이미지가 없어요" onClick={() => nav(resultRoute(run))}
              iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>
              {finished && done > 0 ? '결과 보기' : `완료된 ${done}장 먼저 보기`}
            </Button>
          </div>
        </div>
      </div>
    }>
      <WSay text={wText}>
        <div className="img-stages" aria-label="생성 단계">
          {run.stages.map((s, i) => (
            <span key={s.key} className="img-row" style={{ gap: 8 }}>
              {i > 0 && <span className={cx('img-stage__line', s.state !== 'todo' && 'img-stage__line--on')} />}
              <span className={cx('img-stage', `img-stage--${s.state}`)} data-state={s.state}>
                <span className="img-stage__dot">
                  {s.state === 'done' && <Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} />}
                  {s.state === 'now' && <Icon name="clock" size={11} color="var(--wm-brand)" strokeWidth={2.6} />}
                </span>
                {s.label}
              </span>
            </span>
          ))}
          <span style={{ flex: 1 }} />
          {run.summary_line && <span className="img-hint img-hint--sm" style={{ whiteSpace: 'nowrap' }}>{run.summary_line}</span>}
        </div>
        <div className={cx('img-shots', run.shots.length === 1 && 'img-shots--one')} data-testid="img3g-shots">
          {run.shots.map((s) => (
            <ShotCard key={s.image_id} shot={s} onZoom={s.state === 'done' ? () => zoomTo(s.image_id) : undefined}
              onCancel={active ? () => void cancelShot(s.image_id) : undefined} />
          ))}
        </div>
      </WSay>
    </Screen>
  );
}

// ── IMG3X ───────────────────────────────────────────
const ISSUE_ICON: Record<string, string> = { product_unrecognized: PATH.scan, competitor_brand: PATH.ban, real_person: PATH.personX, unsafe: PATH.ban };
type Sel = { option?: string; custom_text?: string; product?: { model_code?: string | null; family_id?: string | null; name: string; short: string } };

function HeldView({ run, work }: { run: RunDetail; work?: Work }) {
  const nav = useNavigate();
  const inv = useInvalidate();
  const openPop = useOpenPopover();
  const [sels, setSels] = useState<Record<string, Sel>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<{ text: string; ok: boolean } | null>(null);
  const [policyOpen, setPolicyOpen] = useState(false);
  const [pickFor, setPickFor] = useState<string | null>(null);
  const issues = run.issues ?? [];
  const selOf = (it: PolicyIssue): Sel | null => sels[it.id] ?? (it.selected ? (it.selected === 'custom' ? { custom_text: it.custom_text ?? '' } : { option: it.selected }) : null);
  const chosen = issues.filter((it) => selOf(it)).length;
  const k = issues.length;
  const g = run.done;
  const h = run.held;
  const N = run.total;

  const productFromRef = async (ref: string): Promise<Sel['product'] | null> => {
    const [, kind, id] = ref.split(':');
    if (kind === 'model') {
      const code = id.replace(/^mdl_/, '');
      const hit = (await searchProducts(code, { limit: 5 })).find((x) => x.model_code === code);
      return hit ? { model_code: hit.model_code, family_id: (hit as { family_id?: string | null }).family_id ?? null, name: hit.label || hit.display_name, short: hit.display_name } : null;
    }
    if (kind === 'family') {
      const r = await fetch(`/api/kb/v1/models?family_id=${encodeURIComponent(id)}&limit=1`, { credentials: 'same-origin' }).then((x) => (x.ok ? x.json() : null));
      const fam = r?.items?.[0]?.family;
      if (!fam?.name) return null;
      const m = /^(.+?) Series$/.exec(fam.series_label ?? '');
      return { model_code: null, family_id: id, name: fam.name, short: m ? m[1] : fam.name };
    }
    return null;
  };
  useImgShell({
    title: work?.title ?? '이미지 생성', step: 3, addable: ['product'],
    onAdd: pickFor ? async (_t, refs) => {
      const p = await productFromRef(refs[0]);
      if (!p) return { added: [] };
      setSels((s) => ({ ...s, [pickFor]: { product: p } }));
      setPickFor(null);
      return { added: [refs[0]] };
    } : undefined,
  });

  const allRecommended = () => {
    const next: Record<string, Sel> = {};
    for (const it of issues) { const rec = it.options.find((o) => o.recommended) ?? it.options.find((o) => o.default); if (rec) next[it.id] = { option: rec.id }; }
    setSels(next);
  };
  const submit = async (opts: { skip?: boolean; then?: string } = {}) => {
    setBusy(opts.skip ? 'skip' : 'go'); setNote(null);
    try {
      const answers: Answer[] = Object.entries(sels).map(([issue_id, s]) => ({ issue_id, option: s.option ?? null, custom_text: s.custom_text ?? null, product: s.product ?? null }));
      await img.answer(run.id, opts.skip ? { answers: [], skip_held: true } : { answers });
      await inv.run(run.id);
      if (opts.then) nav(opts.then);
    } catch (e) { setNote({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const sendCustom = async (text: string) => {
    setBusy('alt'); setNote(null);
    try {
      const r = await img.alternative(run.id, text);
      setNote({ text: r.message, ok: r.accepted });
      if (r.accepted && r.issue_id) setSels((s) => ({ ...s, [r.issue_id!]: { custom_text: text } }));
      await inv.run(run.id);
    } catch (e) { setNote({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };

  const doneShots = run.shots.filter((s) => s.state === 'done');
  const heldShots = run.shots.filter((s) => s.state === 'held');
  const refsTail = (work?.references?.length ?? 0) > 0 ? ' + 참조 사진' : '';
  const firstDone = doneShots[0]?.image_id ?? null;
  const wText = `${N}장 중 ${g}장을 만들고 ${h}장은 보류했어요. 요청에 그대로 만들 수 없는 부분이 ${k}가지 있습니다. 항목마다 대안을 고르면 보류한 ${h}장을 이어서 만듭니다.`;
  const labelFor = useMemo(() => (it: PolicyIssue, optId: string) => {
    const s = sels[it.id];
    if (optId === 'cand_1' && s?.product) return `${s.product.short} · 가장 비슷`;
    return it.options.find((o) => o.id === optId)?.label ?? optId;
  }, [sels]);

  return (
    <Screen testid="img3x" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span data-testid="img3x-foot-head">대안 선택<small> · {k}개 중 {chosen}개 선택됨</small></span>
            <span className="img-quick">
              <Pill onClick={allRecommended}>모두 추천 대안으로</Pill>
              <Pill onClick={() => void submit({ skip: true })} disabled={busy === 'skip'}>보류 {h}장 건너뛰기</Pill>
            </span>
          </div>
          {note && <div className={cx('img-askline', !note.ok && 'img-err')} role="status" data-testid="img3x-note">{note.ok ? <Icon name="check" size={13} /> : <Icon name="info" size={13} />}{note.text}</div>}
          <div className="wm-composer__foot">
            <AskInput label="다른 대안 입력" placeholder="다른 방법 (예: 경쟁사 화면은 회색 박스로)" busy={busy === 'alt'} onSend={sendCustom} testid="img3x-custom" />
            <Button h={44} onClick={() => void submit({ skip: true, then: work?.kind === 'composite' ? route.composite(run.work_id) : route.conditions(run.work_id) })}>조건 다시 입력</Button>
            <Button h={44} variant="primary" loading={busy === 'go'} onClick={() => void submit()} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>대안으로 {h}장 이어서 생성</Button>
          </div>
        </div>
      </div>
    }>
      <Echo head={work?.kind_label} text={work ? `${work.description}${refsTail}` : null} />
      <WSay text={wText}>
        <div className="img-strip" data-testid="img3x-strip">
          {doneShots.map((s) => <span key={s.image_id} className="img-strip__shot"><Img src={s.thumb_url} alt={`완성된 ${s.label}`} /><span>{s.label}</span></span>)}
          {heldShots.map((s) => <span key={s.image_id} className="img-strip__held"><Ico d={PATH.pause} size={14} />{s.label} · 보류</span>)}
          <span style={{ display: 'flex', flexDirection: 'column', gap: 3, paddingLeft: 8, minWidth: 0 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600 }}>완성 {g}장</span>
            {run.applied_note && <span className="img-hint img-hint--sm">{run.applied_note}</span>}
            {firstDone && <Link to={route.result(run.work_id, firstDone)} className="img-row" style={{ gap: 3, fontSize: 12, fontWeight: 600 }}>완성본 보기<Icon name="chevronRight" size={12} strokeWidth={2.4} /></Link>}
          </span>
        </div>
        <div className="img-card" style={{ position: 'relative' }}>
          <div className="img-card__bar" style={{ minHeight: 40, padding: '0 16px', justifyContent: 'space-between' }}>
            <span className="img-card__title" data-testid="img3x-head">보류 사유 {k}<small> · 대안 {chosen}개 선택됨</small></span>
            <button type="button" className="img-pill img-pill--h26" style={{ border: 'none', background: 'transparent', color: 'var(--wm-text-muted)' }} aria-expanded={policyOpen}
              onClick={() => setPolicyOpen(!policyOpen)}><Ico d={PATH.doc} size={13} />생성 이미지 사용 기준</button>
          </div>
          {policyOpen && (
            <div className="img-popover" style={{ right: 12, top: 44 }} role="dialog" aria-label="생성 이미지 사용 기준">
              <b style={{ color: 'var(--wm-text)' }}>생성 이미지 사용 기준</b>
              <ol>
                <li>다른 회사의 로고·상표·고유 디자인(제품 외형 포함)은 그리지 않아요. 비교는 Why Samsung 비교표 시트로.</li>
                <li>실존 인물(연예인·공인·특정 개인)의 얼굴·이름을 쓴 이미지는 만들지 않아요. 사람은 가상 인물·뒷모습·손만.</li>
                <li>참조·현장 사진 속 사람 얼굴과 다른 회사 로고는 흐리게 처리하거나 글로만 참고해요.</li>
                <li>고객 현장 사진은 고객 자료로 다뤄요(기밀 표시, 대외 사용 전 고객 확인).</li>
                <li>생성 이미지는 「AI 생성 이미지」 표기를 권장하고, 제품 수치·인증 마크·가격을 이미지에 그리지 않아요.</li>
              </ol>
              <div className="img-row" style={{ justifyContent: 'flex-end', marginTop: 8 }}><button type="button" className="img-mini" onClick={() => setPolicyOpen(false)}>닫기</button></div>
            </div>
          )}
          {issues.map((it) => {
            const s = selOf(it);
            const st = s ? 'auto' : 'need';
            const data = it.data as { thumb_url?: string | null; box?: number[] | null; thumb_label?: string; link_label?: string; link_route?: string };
            return (
              <div key={it.id} className="img-issue" data-testid="img3x-issue" data-type={it.type}>
                <span className="img-issue__icon"><Ico d={ISSUE_ICON[it.type] ?? PATH.ban} size={16} /></span>
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div className="img-row" style={{ minHeight: 20 }}>
                    <span className="img-issue__title">{it.title}</span>
                    <span className={cx('img-issue__state', `img-issue__state--${st}`)} data-testid="img3x-state">
                      <Icon name={st === 'auto' ? 'check' : 'info'} size={11} strokeWidth={2.6} />{st === 'auto' ? '대안 선택됨' : '선택 필요'}
                    </span>
                  </div>
                  <div className="img-issue__desc">{it.description}</div>
                  <div className="img-issue__opts" role="group" aria-label={`${it.title} 대안`}>
                    {it.options.map((o) => {
                      const on = s?.option === o.id || (o.id === 'cand_1' && !!s?.product);
                      const isDefault = !s && o.default && it.status === 'needs_choice';
                      return (
                        <Pill key={o.id} h={28} on={on} def={isDefault} onClick={() => {
                          if (o.action === 'pick_product') { setPickFor(it.id); openPop('product'); return; }
                          setSels((x) => ({ ...x, [it.id]: { option: o.id } }));
                        }}>
                          {on && <Icon name="check" size={12} strokeWidth={2.6} />}{labelFor(it, o.id)}
                        </Pill>
                      );
                    })}
                    {s?.custom_text && <Pill h={28} on><Icon name="check" size={12} strokeWidth={2.6} />{s.custom_text}</Pill>}
                    {it.type === 'competitor_brand' && data.link_route && (
                      <Link to={data.link_route} className="img-pill img-pill--h28 img-pill--brand">{data.link_label ?? 'Why Samsung 비교표로 보내기'}<Icon name="arrowRight" size={12} strokeWidth={2.4} /></Link>
                    )}
                  </div>
                  {pickFor === it.id && <span className="img-hint img-hint--sm">상단 제품 탐색에서 고른 제품을 「현재 작업에 추가」하면 후보 1 자리에 들어가요</span>}
                </div>
                {it.type === 'product_unrecognized' && (
                  <div className="img-issue__ref">
                    <span className="img-issue__refimg">
                      <Img src={data.thumb_url ?? null} alt={data.thumb_label ?? '올린 참조 사진'} />
                      {data.box && data.box.length === 4 && (
                        <span className="img-issue__box" style={{ left: `${data.box[0] * 100}%`, top: `${data.box[1] * 100}%`, width: `${(data.box[2] - data.box[0]) * 100}%`, height: `${(data.box[3] - data.box[1]) * 100}%` }} />
                      )}
                      <span className="img-issue__q" style={{ right: 4, top: 24 }}>?</span>
                    </span>
                    <span className="img-hint" style={{ fontSize: 11, textAlign: 'center', color: 'var(--wm-text-subtle)' }}>{data.thumb_label ?? '올린 참조 사진'}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </WSay>
    </Screen>
  );
}
