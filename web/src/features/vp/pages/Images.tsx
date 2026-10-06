/**
 * VPI — 이미지 칸 채우기(`/vp/:id/result/images?slot=`): 칸 표(출처 단계 · 이유 · 모드) · 후보 4 + 사진 올리기 · 이미지 정보 시트.
 */
import { useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { Img, Modal, MetaRows, Skeleton, ErrorState, Icon, formatKB } from '@/ui';
import { uploadFile } from '@/api/client';
import {
  addAttachment, addSheet, errText, isJob, postMessage, putSlot, restyle, useRefresh, useSlotCandidates, useSlots, useVp,
  type ImageSlot, type SlotCandidate,
} from '../api';
import { Agent, CardHead, Dock, ModeChip, Page, Spinner, useJobDone, useVpShell } from '../parts';

type Meta = NonNullable<ImageSlot['meta']>;

export function ImagesPage() {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 3);
  const slots = useSlots(id);
  const items = slots.data?.items ?? [];
  const selId = sp.get('slot') || items[0]?.id || '';
  const sel = items.find((s) => s.id === selId);
  const cands = useSlotCandidates(id, selId || undefined);
  const refresh = useRefresh(id);
  const [info, setInfo] = useState<{ title: string; meta: Meta } | null>(null);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [job, setJob] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const j = useJobDone(job, async (snap) => { setJob(null); await refresh(); if (snap.status === 'failed') setErr(snap.error?.message || '바꾸지 못했어요'); });

  if (!doc || slots.isLoading) return <Page><Skeleton h={360} /></Page>;
  if (slots.isError || !slots.data) return <Page><ErrorState message={errText(slots.error)} onRetry={() => slots.refetch()} /></Page>;
  const v = slots.data;
  const vpSheet = (doc.sheets ?? []).find((s) => s.role === 'VP');

  const choose = async (c: SlotCandidate) => {
    if (!sel || c.current) return;
    setBusy(c.name);
    setErr('');
    try {
      if (!c.asset) { const r = await postMessage(id, { text: `${sel.label} 칸을 일러스트로`, context: 'images' }); setJob(r.job_id); }
      else { await putSlot(id, sel.id, c.asset); await refresh(); }
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); }
  };
  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy('upload');
    try {
      const fm = await uploadFile(files[0], { confidential: true, purpose: 'vp' });
      const r = await addAttachment(id, fm.id, 'customer_photo');
      if (isJob(r)) setJob(r.job_id); else await refresh();
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); if (fileRef.current) fileRef.current.value = ''; }
  };
  const action = async (code: string) => {
    setErr('');
    try {
      if (code === 'VP-N' && vpSheet) nav(`/vp/${id}/result/layout?sheet=${vpSheet.id}&code=VP-N`);
      else if (code === 'VP-Q') { const r = await addSheet(id, { kind: 'reference', layout_code: 'VP-Q' }); setJob(r.job_id); }
      else if (code === 'Prod') { const r = await restyle(id); setJob(r.job_id); }
    } catch (e) { setErr(errText(e)); }
  };
  const send = async (text: string) => {
    try { const r = await postMessage(id, { text, context: 'images' }); setJob(r.job_id); } catch (e) { setErr(errText(e)); }
  };

  return (
    <Page dock={
      <Dock title="이미지" meta={`${v.counts.slots}칸 · 공식 실사 ${v.counts.official}`}
        headRight={<div className="vp-dock__alts">
          {(v.actions ?? []).map((a) => <button key={a.code} type="button" className="vp-alt" title={a.tip} onClick={() => action(a.code)} disabled={!!job}><b>{a.display}</b>{a.label}</button>)}
        </div>}
        input={{ placeholder: '이미지 요청 (예: 기둥 2는 매장에 걸린 모습으로)', label: '이미지 요청', onSend: send, busy: !!job }}
        actions={<>
          {job && <Spinner label={`바꾸는 중 · ${j.progress}%`} />}
          {err && <span className="vp-err">{err}</span>}
          <Link to={`/vp/${id}/result`} className="vp-btn">결과로</Link>
          <Link to={`/vp/${id}/export`} className="vp-btn vp-btn--primary">제안서 Value Props로</Link>
        </>} />
    }>
      <Agent text={v.intro}>
        <div className="vp-card" data-testid="vp-slots">
          <CardHead title="이미지 칸" meta={String(v.counts.slots)} right={<Link to="/vp/rules" state={{ back: `/vp/${id}/result/images` }} style={{ fontSize: 12, fontWeight: 600 }}>고르는 순서</Link>}>
            <span className="vp-card__sub">칸마다 가치를 만드는 제품 · 솔루션 → 공식 실사부터 찾아 넣음</span>
          </CardHead>
          {items.map((s) => (
            <div key={s.id} role="button" tabIndex={0} className={s.id === selId ? 'vp-slot vp-slot--sel' : 'vp-slot'} data-tier={s.tier}
              onClick={() => setSp({ slot: s.id }, { replace: true })} onKeyDown={(e) => { if (e.key === 'Enter') setSp({ slot: s.id }, { replace: true }); }}>
              <SlotImage s={s} />
              <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                <span className="vp-slot__code">{s.code}</span>
                <span className="vp-slot__label" title={s.label}>{s.label}</span>
              </span>
              <span className={`vp-tier vp-tier--${s.tier}`}>{s.tier_label}</span>
              <span className="vp-slot__why" title={s.why}>{s.why}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                <ModeChip mode={s.mode} />
                {s.meta && <button type="button" className="vp-mini vp-mini--ghost" aria-label={`${s.label} 이미지 정보`} onClick={(e) => { e.stopPropagation(); setInfo({ title: s.meta!.title || s.label, meta: s.meta! }); }}><Icon name="info" size={13} /></button>}
              </span>
            </div>
          ))}
        </div>
        {sel && (
          <div className="vp-card" data-testid="vp-slot-candidates">
            <CardHead title={cands.data?.header ?? sel.label} meta={undefined} right={<span className="vp-card__sub">{cands.data?.right}</span>}>
              <span className="vp-card__sub">— 바꿀 수 있는 후보</span>
            </CardHead>
            <div className="vp-icands">
              {cands.isLoading && [0, 1, 2, 3].map((i) => <Skeleton key={i} h={110} />)}
              {(cands.data?.items ?? []).map((c, i) => (
                <button key={i} type="button" className={c.current ? 'vp-icand vp-icand--cur' : 'vp-icand'} onClick={() => choose(c)} disabled={busy === c.name || !!job} aria-pressed={c.current}>
                  <span className="vp-icand__img">
                    {c.asset ? <Img src={c.asset.thumb_url || c.asset.std_url} alt={c.name} fit="cover" /> : <span className="vp-slot__img vp-slot__img--illust" style={{ width: '100%', height: '100%' }}>일러스트</span>}
                  </span>
                  <span className="vp-icand__name" title={c.name}>{c.name}</span>
                  <span className="vp-icand__tier">{c.tier_label}{c.current ? ' · 지금' : ''}</span>
                  {c.meta && <span role="button" tabIndex={0} className="vp-icand__info" aria-label={`${c.name} 이미지 정보`} onClick={(e) => { e.stopPropagation(); setInfo({ title: c.name, meta: c.meta! }); }}><Icon name="info" size={12} /></span>}
                </button>
              ))}
              <label className="vp-upload">
                <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => upload(e.target.files)} />
                {busy === 'upload' ? <span className="vp-spin" /> : <Icon name="upload" size={18} color="var(--wm-brand)" />}
                <b>사진 올리기</b>
                <span>고객 매장 사진은 공간 칸에 자동 배치</span>
              </label>
            </div>
          </div>
        )}
      </Agent>
      <Modal open={!!info} onClose={() => setInfo(null)} title="이미지 정보" width={560} ariaLabel="이미지 정보">
        {info && <MetaRows variant="sheet" rows={metaRows(info.meta)} />}
      </Modal>
    </Page>
  );
}

function SlotImage({ s }: { s: ImageSlot }) {
  if (!s.asset) return <span className="vp-slot__img vp-slot__img--illust">일러스트</span>;
  return <span className="vp-slot__img"><Img src={s.asset.thumb_url || s.asset.std_url} alt={s.label} fit={s.fit === 'contain' ? 'contain' : 'cover'} /></span>;
}

function dims(d?: { w?: number; h?: number; format?: string; bytes?: number | null } | null) {
  if (!d || !d.w) return '[확인 필요]';
  return [`${d.w} × ${d.h}`, d.format, d.bytes ? formatKB(d.bytes) : null].filter(Boolean).join(' · ');
}

function metaRows(m: Meta) {
  return [
    { k: '출처 페이지', v: m.source_page?.title || m.source_page?.url || '없음 — ' + (m.method || '생성 · 고객 제공'), href: m.source_page?.url || undefined },
    { k: '원본 파일', v: m.original_file_url || '없음', href: m.original_file_url || undefined },
    { k: '원본', v: `${dims(m.original)}${m.posted_at ? ` · 출처 게시 ${m.posted_at}` : ''}` },
    { k: '저장본', v: `${dims(m.stored)} · 긴 변 축소` },
    { k: '수집', v: `${(m.collected_at || '').slice(0, 10)} · ${m.method || '공식 페이지에서 수집'}` },
    { k: '사용 조건', v: m.rights || '[확인 필요]' },
    { k: '캡션', v: m.caption_rule || '—' },
    { k: '사용 이력', v: m.usage_history?.label || 'Winmate 제안서 0건' },
  ];
}
