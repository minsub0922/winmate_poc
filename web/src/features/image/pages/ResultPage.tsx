/**
 * IMG3 · 생성 결과(3/3, §4.7) — 2×2 시안(선택 · 확대 · 다운로드), 빠른 수정 칩, 수정 요청(LLM 분류 R6), 내 이미지에 저장, 제안서에 넣기.
 * 보여 줄 run: `?run=` → `?image=` 의 run → 작업의 최근 생성 run(initial · composite · alternatives).
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Button, cx, ErrorState, Icon, Spinner } from '@/ui';
import { useJob } from '@/api/jobs';
import { errMessage, img, type Shot } from '../api';
import { AskInput, Loading, Pill, Screen, ShotCard, useImgShell, WSay, ZoomView } from '../components';
import { qk, useImage, useInvalidate, useLiveRun, useWork } from '../hooks';
import { route, STYLE_SHORT, withDownload } from '../lib';

const GEN = new Set(['initial', 'composite', 'alternatives']);

export default function ResultPage() {
  const { workId = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const wq = useWork(workId);
  const w = wq.data;
  const imageParam = sp.get('image');
  const runParam = sp.get('run');
  const imgQ = useImage(imageParam && !runParam ? imageParam : null);
  const runsQ = useQuery({ queryKey: qk.runs(workId), queryFn: () => img.runs(workId), enabled: !!workId && !runParam, staleTime: 2_000 });
  const runId = runParam ?? imgQ.data?.run_id ?? runsQ.data?.items.find((r) => GEN.has(r.kind))?.id ?? null;
  const rq = useLiveRun(runId);
  const run = rq.data;
  const shots = run?.shots ?? [];
  const selectedId = imageParam ?? w?.selected_image_id ?? shots.find((s) => s.state === 'done')?.image_id ?? shots[0]?.image_id ?? null;
  const sel = shots.find((s) => s.image_id === selectedId) ?? shots[0];
  const [zoom, setZoom] = useState<Shot | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ text: string; ok?: boolean; spin?: boolean } | null>(null);
  const [showChanges, setShowChanges] = useState(false);
  const [editJob, setEditJob] = useState<string | null>(null);

  useEffect(() => { if (w && sel && w.selected_image_id !== sel.image_id && sel.state === 'done') void img.patchWork(w.id, { selected_image_id: sel.image_id }).then(inv.setWork).catch(() => undefined); },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sel?.image_id]);
  useJob(editJob, { onDone: (j) => {
    setEditJob(null);
    if (j.status === 'succeeded') setMsg({ text: '수정한 새 버전을 만들었어요 · 부분 수정에서 전/후를 비교할 수 있어요', ok: true });
    else setMsg({ text: j.error?.message ?? '수정하지 못했어요', ok: false });
    void inv.run(runId); if (sel) void inv.image(sel.image_id);
  } });

  useImgShell({ title: w?.title ?? '생성 결과', step: 3 });
  const n = shots.filter((s) => s.state === 'done').length;
  const pick = (s: Shot) => { const p = new URLSearchParams(sp); p.set('image', s.image_id); setSp(p, { replace: true }); };
  const download = (s: Shot) => {
    const url = s.url ? withDownload(s.url) : null;
    if (url) window.location.assign(url);
  };
  const variants = async () => {
    if (!sel) return;
    setBusy('variants'); setMsg(null);
    try { await img.variants(sel.image_id, { count: 4, axis: 'any' }); nav(route.variants(workId, sel.image_id), { state: { echo: `${sel.label}로 변형 4장` } }); }
    catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const brighten = async () => {
    if (!sel) return;
    setBusy('bright'); setMsg(null);
    try {
      const v = await img.adjust(sel.image_id, { preset: 'brighten' });
      setMsg({ text: `밝기를 올린 ${v.label} 버전을 만들었어요`, ok: true });
      await inv.run(runId); void inv.image(sel.image_id); void inv.gallery();
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const ask = async (text: string) => {
    if (!sel) return;
    setBusy('ask'); setMsg(null);
    try {
      const r = await img.interpret(sel.image_id, { text, screen: 'result' });
      if (r.action === 'region_edit') {
        const reg = r.region as { rect?: number[]; label?: string } | null;
        if (reg?.rect?.length === 4) await img.addRegion(sel.image_id, { shape: 'rect', rect: reg.rect, instruction: r.instruction, label: reg.label ?? undefined });
        nav(route.edit(workId, sel.image_id), { state: { echo: text } });
      } else if (r.action === 'global_edit') {
        const acc = await img.edit(sel.image_id, { mode: 'global', instruction: r.instruction || text });
        setEditJob(acc.job_id);
        setMsg({ text: '이미지 전체를 고치는 중이에요', spin: true });
      } else if (r.action === 'variants') {
        await img.variants(sel.image_id, { count: 4, axis: 'any', instruction: r.instruction || text });
        nav(route.variants(workId, sel.image_id), { state: { echo: text } });
      } else setMsg({ text: r.question ?? '어떻게 바꿀지 조금 더 알려 주세요', ok: false });
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const save = async () => {
    if (!sel) return;
    setBusy('save');
    try { await img.save(sel.image_id); void inv.gallery(); void inv.works(); nav(route.list()); } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const issues = run?.issues ?? [];
  const changeRows = useMemo(() => issues.map((it) => ({ title: it.title, alt: it.options.find((o) => o.id === (it.selected ?? (it.options.find((x) => x.default)?.id)))?.label ?? it.custom_text ?? '' })), [issues]);

  if (wq.isLoading || (runId && rq.isLoading) || (!runParam && (runsQ.isLoading || (imageParam && imgQ.isLoading)))) return <Loading />;
  if (!w) return <div className="img-center"><ErrorState message="작업을 불러오지 못했어요" onRetry={() => wq.refetch()} /></div>;
  if (!run) return <div className="img-center"><ErrorState message="아직 만든 이미지가 없어요" onRetry={() => nav(route.conditions(workId))} /></div>;
  const selDone = sel?.state === 'done';
  const style = STYLE_SHORT[(run.params as { style?: string }).style ?? w.conditions.style] ?? '실사';
  const selIndex = sel?.label ?? '시안';
  return (
    <Screen testid="img3" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span data-testid="img3-head">{selIndex} 선택됨<small> · 3 / 3</small></span>
            <span className="img-quick">
              <Pill disabled={!selDone || !!busy} onClick={() => void variants()}>이 시안으로 변형 4장</Pill>
              <Pill disabled={!selDone || !!busy} onClick={() => void brighten()}>밝기 올리기</Pill>
              <Pill disabled={!selDone} onClick={() => sel && nav(`${route.edit(workId, sel.image_id)}?preset=erase_people`, { state: { echo: `${sel.label}에서 사람 제거` } })}>사람 제거</Pill>
            </span>
          </div>
          {msg && (
            <div className={cx('img-askline', msg.ok === false && 'img-err')} role="status" data-testid="img3-msg">
              {msg.spin ? <Spinner /> : <Icon name={msg.ok ? 'check' : 'info'} size={13} />}{msg.text}
            </div>
          )}
          <div className="wm-composer__foot">
            <AskInput label="수정 요청" placeholder="수정 요청 (예: 메뉴보드 화면에 실제 메뉴 이미지 넣어줘)" busy={busy === 'ask' || !!editJob} disabled={!selDone} onSend={ask} testid="img3-ask" />
            <Button h={44} loading={busy === 'save'} disabled={!selDone} onClick={() => void save()}>내 이미지에 저장</Button>
            <Button h={44} variant="primary" disabled={!selDone} onClick={() => sel && nav(route.exportTo(workId, sel.image_id))} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>제안서에 넣기</Button>
          </div>
        </div>
      </div>
    }>
      <WSay text={`${n}장을 생성했습니다. 마음에 드는 이미지를 선택해 저장하거나, 한 장을 기준으로 변형을 더 만들 수 있습니다.`}>
        {run.change_note && (
          <div className="img-banner" data-testid="img3-change">
            <Icon name="info" size={14} />
            <span>{run.change_note} · <button type="button" className="img-pill img-pill--h26" style={{ border: 'none', background: 'transparent', color: 'var(--wm-brand)', padding: 0 }}
              aria-expanded={showChanges} onClick={() => setShowChanges(!showChanges)}>자세히</button></span>
          </div>
        )}
        {showChanges && (
          <ul className="img-hint" style={{ margin: 0, paddingLeft: 18 }}>
            {changeRows.map((c) => <li key={c.title}>{c.title}{c.alt ? ` → ${c.alt}` : ''}</li>)}
          </ul>
        )}
        <div className={cx('img-shots', shots.length === 1 && 'img-shots--one')} data-testid="img3-shots">
          {shots.map((s) => (
            <ShotCard key={s.image_id} shot={s} tall showSelectedBadge selected={s.image_id === sel?.image_id}
              tagExtra={`${s.aspect} · ${style}`} onSelect={() => pick(s)}
              onZoom={s.state === 'done' ? () => setZoom(s) : undefined} onDownload={s.state === 'done' ? () => download(s) : undefined}
              heldTo={route.run(workId, run.id)} />
          ))}
        </div>
      </WSay>
      <ZoomView src={zoom?.url} alt={`${zoom?.label ?? ''} 크게 보기`} caption={zoom ? `${zoom.label} · ${zoom.width ?? ''}×${zoom.height ?? ''}` : undefined} onClose={() => setZoom(null)} />
    </Screen>
  );
}
