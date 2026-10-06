/**
 * VP4 — 내보내기 · 제안서로(`/vp/:id/export`): 보낼 제안서 · 유형 3열(시트 맞춤) · 옵션 3 · 파일 · 공유 · 다른 기능으로 이어가기.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Modal, Skeleton, ErrorState, Icon, Button, toast } from '@/ui';
import { api, unwrap } from '@/api/client';
import {
  ApiError, copyText, createHandoff, errText, getExport, isJob, patchVp, postMessage, startExport, usePackages, useRefresh, useVp,
  type Question,
} from '../api';
import { Agent, Btn, CardHead, Dock, Page, PIcon, ICONS, Spinner, useJobDone, useVpShell } from '../parts';

type PType = 'standard' | 'quickwin' | 'solution';
const TYPE_LABEL: Record<PType, string> = { standard: '표준', quickwin: '퀵윈', solution: 'Solution형' };

export function ExportPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 3, { complete: true });
  const refresh = useRefresh(id);
  const [ptype, setPtype] = useState<PType | ''>('');
  const [opts, setOpts] = useState({ estimates_as_notes: true, sync_storyboard: true, ask_before_overwrite_pinned: true });
  const pk = usePackages(id, ptype || undefined, opts.estimates_as_notes);
  const [propOpen, setPropOpen] = useState(false);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [exp, setExp] = useState<{ job: string; vex: string; format: string } | null>(null);
  const [file, setFile] = useState<{ file_id: string; filename: string } | null>(null);
  const [ask, setAsk] = useState<Question | null>(null);
  const [hoJob, setHoJob] = useState<string | null>(null);
  const [msgJob, setMsgJob] = useState<string | null>(null);

  useEffect(() => { if (doc && !ptype) setPtype(((doc.target_proposal?.type) as PType) || 'standard'); }, [doc, ptype]);
  const props = useQuery({
    queryKey: ['vp', 'proposals', doc?.customer_name ?? ''],
    queryFn: async () => unwrap(await api.proposal.GET('/v1/proposals', { params: { query: { tab: 'draft,review', limit: 20, q: (doc?.customer_name || '').split(' ').slice(0, 2).join(' ') || undefined } } })),
    enabled: !!doc, retry: 0,
  });
  const ej = useJobDone(exp?.job, async (snap) => {
    if (snap.status === 'succeeded') {
      const rec = await getExport(id, exp!.vex).catch(() => null);
      const fid = (snap.result?.file_id as string) || rec?.file_id;
      if (fid) setFile({ file_id: fid, filename: (snap.result?.filename as string) || rec?.filename || '파일' });
    } else setErr(snap.error?.message || '파일을 만들지 못했어요');
    setExp(null);
  });
  const hj = useJobDone(hoJob, async (snap) => {
    setHoJob(null);
    const h = snap.result?.handoff as { open_route?: string } | undefined;
    if (h?.open_route) nav(h.open_route); else setErr(snap.error?.message || '보내지 못했어요');
  });
  useJobDone(msgJob, async () => { setMsgJob(null); await refresh(); });

  const sel = useMemo(() => pk.data?.types.find((t) => t.proposal_type === (ptype || pk.data?.selected)), [pk.data, ptype]);
  if (!doc || pk.isLoading) return <Page><Skeleton h={360} /></Page>;
  if (pk.isError || !pk.data) return <Page><ErrorState message={errText(pk.error)} onRetry={() => pk.refetch()} /></Page>;
  const tp = doc.target_proposal;
  const n = sel?.counts.send ?? 0;
  const models = Array.from(new Set((doc.sheets ?? []).flatMap((s) => (s.content?.pillars ?? []).flatMap((p) => p.product_refs ?? [])).filter((r) => r.kind === 'model').map((r) => r.name)));
  const sbSource = (doc.sources ?? []).find((s) => s.kind === 'storyboard' && s.connected);

  const pickProposal = async (p: { id: string; title: string; type?: string | null } | null) => {
    setPropOpen(false);
    const t = ((p?.type as PType) || ptype || 'standard') as PType;
    await patchVp(id, { target_proposal: p ? { proposal_id: p.id, title: p.title, type: t, section_label: 'Value Props' } : { proposal_id: null, title: '', type: t, section_label: 'Value Props' } });
    setPtype(t);
    await refresh();
  };
  const send = async (confirmed?: boolean, toNew = false) => {
    setBusy(toNew ? 'new' : 'send');
    setErr('');
    try {
      const r = await createHandoff(id, {
        proposal_id: toNew ? null : (tp?.proposal_id ?? null), proposal_type: (ptype || 'standard') as PType, proposal_title: toNew ? undefined : tp?.title || undefined,
        options: opts, interview_numbers_confirmed: confirmed,
      });
      if (isJob(r.data)) setHoJob(r.data.job_id);
      else nav(r.data.open_route);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'QUESTION_REQUIRED' && (e.details as { question?: Question }).question) setAsk((e.details as { question: Question }).question);
      else setErr(errText(e));
    } finally { setBusy(''); }
  };
  const makeFile = async (format: 'pptx' | 'pdf_summary') => {
    setErr(''); setFile(null);
    try { const r = await startExport(id, format, ptype || undefined); setExp({ job: r.job_id, vex: (r.ref?.id as string) || '', format }); } catch (e) { setErr(errText(e)); }
  };
  const copy = async () => {
    try { const t = await copyText(id); await navigator.clipboard.writeText(t); toast('메시지를 복사했어요'); } catch (e) { setErr(errText(e)); }
  };
  const share = async () => {
    try {
      const b = unwrap(await api.workspace.POST('/v1/share-links', { body: { target: `vp:${id}`, route: `/vp/${id}/result`, title: doc.title, expires_days: 30 } }));
      const url = b.url.startsWith('http') ? b.url : `${location.origin}${b.url}`;
      await navigator.clipboard.writeText(url).catch(() => undefined);
      toast('공유 링크를 복사했어요');
    } catch (e) { setErr(errText(e)); }
  };
  const msg = async (text: string) => {
    try { const r = await postMessage(id, { text, context: 'export' }); setMsgJob(r.job_id); } catch (e) { setErr(errText(e)); }
  };

  return (
    <Page dock={
      <Dock title="결과 활용" meta={pk.data.dock} headRight={pk.data.estimates_note ? <span className="vp-card__sub">{pk.data.estimates_note}</span> : undefined}
        input={{ placeholder: '보내기 전 요청 (예: 퀵윈 버전도 함께 만들어 둬)', label: '보내기 전 요청', onSend: msg, busy: !!msgJob }}
        actions={<>
          {err && <span className="vp-err">{err}</span>}
          <Link to={`/vp/${id}/result`} className="vp-btn">이전</Link>
          {hoJob ? <Spinner label={`퀵윈 1장을 만드는 중 · ${hj.progress}%`} /> : <Btn primary onClick={() => send()} busy={busy === 'send'}>제안서에 {n}시트 보내기</Btn>}
        </>} />
    }>
      <Agent text="어디에 쓸지 골라 주세요. 보낼 제안서의 유형을 보고 시트 수와 레이아웃을 맞춰서 보냅니다.">
        <div className="vp-card" data-testid="vp-export">
          <CardHead plain title={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ color: 'var(--wm-brand)', display: 'inline-flex' }}><PIcon d={ICONS.monitor} size={16} /></span>제안서 Value Props로</span>} right={
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>보낼 제안서</span>
              <span className="vp-prop">
                <button type="button" className="vp-prop__btn" aria-haspopup="listbox" aria-expanded={propOpen} onClick={() => setPropOpen((x) => !x)}>
                  <span>{tp?.title ? <><b>{tp.title}</b> · {TYPE_LABEL[(tp.type as PType) || 'standard']}</> : '연결 안 됨'}</span><Icon name="chevronDown" size={14} />
                </button>
                {propOpen && (
                  <div className="vp-prop__list" role="listbox" aria-label="보낼 제안서">
                    {props.isLoading && <Skeleton h={30} />}
                    {(props.data?.items ?? []).map((p) => (
                      <div key={p.id} role="option" aria-selected={tp?.proposal_id === p.id} className="vp-prop__opt" onClick={() => pickProposal(p)}>
                        <b>{p.title}</b> · {p.type_label || TYPE_LABEL[(p.type as PType) || 'standard']}
                      </div>
                    ))}
                    {!props.isLoading && !(props.data?.items ?? []).length && <div className="vp-prop__opt" aria-disabled="true">같은 고객사의 작성 중 제안서가 없어요</div>}
                    {tp?.title && <div role="option" aria-selected={false} className="vp-prop__opt" onClick={() => pickProposal(null)}>연결 풀기</div>}
                  </div>
                )}
              </span>
              <button type="button" className="vp-card__link" onClick={() => send(undefined, true)} disabled={busy === 'new'}>새 제안서로</button>
            </span>} />
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '10px 16px 0 16px', fontSize: 12.5 }}>
            <span style={{ fontWeight: 600 }}>제안서 유형마다 시트 구성이 달라져요 <span style={{ color: 'var(--wm-text-muted)', fontWeight: 500 }}>· 고른 제안서는 {TYPE_LABEL[(tp?.type as PType) || 'standard']}</span></span>
            <span style={{ color: 'var(--wm-text-muted)' }}>다른 유형으로 보내면 에이전트가 자동으로 줄이거나 빼요</span>
          </div>
          <div className="vp-types" role="radiogroup" aria-label="제안서 유형">
            {pk.data.types.map((t) => {
              const on = t.proposal_type === (ptype || pk.data!.selected);
              return (
                <button key={t.proposal_type} type="button" role="radio" aria-checked={on} className={on ? 'vp-type vp-type--on' : 'vp-type'} onClick={() => setPtype(t.proposal_type as PType)}>
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                    <span className="vp-type__name">{t.type_label}</span>
                    <span className="vp-type__badge">{on ? '보낼 곳' : '다른 유형'}</span>
                  </span>
                  <span className="vp-type__path">{t.path_label}</span>
                  {t.rows.map((r, i) => (
                    <span key={i} className="vp-type__row">
                      <span className={r.code === '—' ? 'vp-type__code vp-type__code--none' : 'vp-type__code'}>{r.code}</span>
                      <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                        <span className={r.code === '—' ? 'vp-type__sheet vp-type__sheet--none' : 'vp-type__sheet'}>{r.sheet_label}</span>
                        <span className="vp-type__st">{r.treatment}</span>
                      </span>
                    </span>
                  ))}
                </button>
              );
            })}
          </div>
          <div className="vp-opts3">
            <label><input type="checkbox" checked={opts.estimates_as_notes} onChange={(e) => setOpts({ ...opts, estimates_as_notes: e.target.checked })} />[추정] 값은 노트로 남기기</label>
            <label><input type="checkbox" checked={opts.sync_storyboard} onChange={(e) => setOpts({ ...opts, sync_storyboard: e.target.checked })} />다듬은 Key Message를 Storyboard에도 반영</label>
            <label><input type="checkbox" checked={opts.ask_before_overwrite_pinned} onChange={(e) => setOpts({ ...opts, ask_before_overwrite_pinned: e.target.checked })} />고정한 시트는 덮어쓰기 전에 묻기</label>
          </div>
        </div>
        <div className="vp-card">
          <div className="vp-more">
            <div className="vp-more__col">
              <span className="vp-more__k">파일 · 공유</span>
              <div className="vp-files4">
                {[
                  { k: 'pptx', icon: ICONS.pptx, t: `PPTX ${n}장`, s: '고른 레이아웃 그대로', on: () => makeFile('pptx'), dis: !!exp },
                  { k: 'pdf', icon: ICONS.pdf, t: 'PDF 한 장 요약', s: '경영진 보고용 · VP-G', on: () => makeFile('pdf_summary'), dis: !!exp },
                  { k: 'copy', icon: ICONS.copy, t: '메시지 복사', s: '기둥 · 근거 문장', on: copy, dis: false },
                  { k: 'share', icon: ICONS.link, t: '링크 공유', s: '팀원 보기 · 코멘트', on: share, dis: false },
                ].map((x) => (
                  <button key={x.k} type="button" className="vp-filebtn" onClick={x.on} disabled={x.dis}>
                    <span className="vp-filebtn__icon"><PIcon d={x.icon} size={15} /></span>
                    <span className="vp-filebtn__txt"><span className="vp-filebtn__t">{x.t}</span><span className="vp-filebtn__s">{x.s}</span></span>
                  </button>
                ))}
              </div>
            </div>
            <div className="vp-more__div" />
            <div className="vp-more__col">
              <span className="vp-more__k">다른 기능으로 이어가기</span>
              <div className="vp-handoffs">
                {[
                  { k: 'sb', icon: ICONS.sb, tool: 'Storyboard', what: 'Key Message를 다듬은 문장으로', to: sbSource ? `/storyboard/${sbSource.ref_id}` : '/storyboard' },
                  { k: 'sc', icon: ICONS.scene, tool: '공간 시나리오', what: '가치 기둥을 장면으로', to: `/scenario/new?from=vp:${id}` },
                  { k: 'spec', icon: ICONS.rq, tool: 'Spec 시트', what: models.length ? `기둥에 나온 ${models.slice(0, 2).join(' · ')} 스펙` : '기둥에 나온 제품 스펙', to: `/spec/new?${models.length ? `models=${encodeURIComponent(models.join(','))}&` : ''}from=vp:${id}` },
                ].map((h) => (
                  <Link key={h.k} className="vp-handoff" to={h.to}>
                    <span className="vp-handoff__icon"><PIcon d={h.icon} size={15} /></span>
                    <b>{h.tool}</b><span className="vp-handoff__what">{h.what}</span>
                    <span className="vp-handoff__go"><Icon name="arrowRight" size={13} /></span>
                  </Link>
                ))}
              </div>
            </div>
            {(exp || file) && (
              <div className="vp-more__file" data-testid="vp-export-file">
                {exp ? <Spinner label={`${exp.format === 'pptx' ? 'PPTX' : 'PDF'} 만드는 중 · ${ej.progress}%`} />
                  : file && <a href={`/api/files/v1/files/${file.file_id}/content`} download={file.filename} style={{ fontWeight: 600, display: 'inline-flex', gap: 6, alignItems: 'center' }}><Icon name="download" size={13} />{file.filename} 받기</a>}
              </div>
            )}
          </div>
        </div>
      </Agent>
      <Modal open={!!ask} onClose={() => setAsk(null)} title={ask?.title ?? ''} width={560} ariaLabel="고객 내부 인터뷰 수치"
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
          <Button h={38} onClick={() => { setAsk(null); void send(true); }}>그대로 쓰기</Button>
          <Button h={38} variant="primary" onClick={() => { setAsk(null); void send(false); }}>[00]으로 바꾸고 노트에 남기기</Button>
        </div>}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
          <span style={{ color: 'var(--wm-text-muted)' }}>{ask?.aside}</span>
          <span>{ask?.context_text}</span>
          <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>답이 없으면 그 수치를 [00]으로 바꾸고 발표자 노트에 [확인 필요]로 남겨요.</span>
        </div>
      </Modal>
    </Page>
  );
}
