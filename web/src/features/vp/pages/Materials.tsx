/**
 * VP1 — 재료(`/vp/new`, `/vp/:id/materials`): 연결할 수 있는 자료 · 재료 커버리지 · 도크(고객사 · 업종 · 덧붙일 내용 · 파일 · 가치 구조 만들기).
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, Skeleton, Chip } from '@/ui';
import { uploadFile } from '@/api/client';
import {
  addAttachment, collect, createVp, deleteAttachment, errText, getVp, patchVp, putSources, usePacks, useRefresh, useSourceCandidates, useVp,
  vpKeys, type VPDoc,
} from '../api';
import { Agent, Btn, CardHead, Dock, ICONS, Page, PIcon, SOURCE_ICON, Spinner, useDebounced, useJobDone, useVpShell } from '../parts';

const TYPE_SHORT: Record<string, string> = { standard: '표준', quickwin: '퀵윈', solution: 'Solution형' };
const EMPTY_COV = [
  { axis: 'challenge', label: '과제', todo: 'RFP를 올리면 과제를 바로 읽어요' },
  { axis: 'value', label: '가치', todo: '삼성 강점 · 메시지 DB에서 채워요' },
  { axis: 'evidence', label: '근거 수치', todo: '만들 때 사례 DB에서 찾아 채워요' },
  { axis: 'stakeholder', label: '이해관계자', todo: '이용자 관점은 사례에서 찾아요' },
];

export function MaterialsPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 1, { title: doc?.title ?? '새 작업' });
  const cands = useSourceCandidates(id);
  const packs = usePacks();
  const refresh = useRefresh(id);
  const [customer, setCustomer] = useState('');
  const [note, setNote] = useState('');
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [job, setJob] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const creating = useRef(false);
  const loaded = useRef<string | null>(null);

  useEffect(() => {
    if (doc && loaded.current !== doc.id) {
      loaded.current = doc.id;
      setCustomer(doc.customer_name ?? '');
      setNote(doc.note ?? '');
    }
  }, [doc]);

  /** 다른 기능에서 들어오기(E3 · E6 · E8): `/vp/new?sb=` · `?mi=` · `?rq=` → 소스 연결 + 재료 잡 바로 시작, `?proposal=&type=&title=` → 보낼 곳 */
  const entered = useRef(false);
  useEffect(() => {
    if (id || entered.current) return;
    const src = (['sb', 'mi', 'rq'] as const).map((k) => [k, sp.get(k)] as const).find(([, v]) => !!v);
    const pid = sp.get('proposal');
    if (!src && !pid) return;
    entered.current = true;
    const kind = src ? ({ sb: 'storyboard', mi: 'mi', rq: 'requirements' } as const)[src[0]] : null;
    const ptype = (['standard', 'quickwin', 'solution'] as const).find((t) => t === sp.get('type')) ?? 'standard';
    void (async () => {
      try {
        const d = await createVp({
          start: kind === 'storyboard' ? 'storyboard' : kind === 'mi' ? 'mi' : 'direct',
          source_refs: src && kind ? [{ kind, ref_id: src[1]! }] : undefined,
          target_proposal: pid ? { proposal_id: pid, title: sp.get('title') ?? '', type: ptype, section_label: 'Value Props' } : undefined,
          customer_name: sp.get('customer') || undefined,
        });
        qc.setQueryData(vpKeys.doc(d.id), d);
        if (src) { const r = await collect(d.id); setJob(r.job_id); }
        nav(`/vp/${d.id}/materials`, { replace: true });
      } catch (e) { setErr(errText(e)); }
    })();
  }, [id, sp]); // eslint-disable-line react-hooks/exhaustive-deps

  /** 되묻기로 — 질문이 들어간 최신 문서를 캐시에 넣고 옮긴다 */
  const toQuestions = async () => {
    if (!id) return;
    const fresh = await getVp(id).catch(() => null);
    if (fresh) qc.setQueryData(vpKeys.doc(id), fresh);
    nav(`/vp/${id}/questions`);
  };

  useEffect(() => {
    const aj = doc?.active_job;
    // 진행 중인 재료 잡이면 이어서 지켜본다(답을 기다리는 잡은 되묻기 화면에서 — 여기로 '이전'해 온 경우는 그대로 둔다)
    if (aj && aj.kind === 'vp.materials' && !['succeeded', 'failed', 'canceled', 'awaiting_input'].includes(aj.status)) setJob(aj.job_id);
  }, [doc?.active_job?.status, doc?.active_job?.job_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const j = useJobDone(job, async (snap) => {
    if (!id) return;
    const fresh = await getVp(id);
    qc.setQueryData(vpKeys.doc(id), fresh);
    setJob(null);
    if (snap.status === 'succeeded') nav((snap.result?.next_route as string) || fresh.resume_route);
    else if (snap.status === 'awaiting_input') nav(`/vp/${id}/questions`);
    else setErr(snap.error?.message || '재료를 정리하지 못했어요. 다시 시도해 주세요.');
  });
  useEffect(() => { if (j.status === 'awaiting_input' && id) void toQuestions(); }, [j.status, id]); // eslint-disable-line react-hooks/exhaustive-deps

  /** 첫 입력 때 작업을 만든다(`/vp/new` → `/vp/:id/materials`). */
  const ensure = async (extra: { customer_name?: string; note?: string } = {}): Promise<VPDoc | null> => {
    if (id) return doc ?? getVp(id).catch(() => null);
    if (creating.current) return null;
    creating.current = true;
    try {
      const d = await createVp({ start: 'direct', customer_name: (extra.customer_name ?? customer).trim() || undefined, note: extra.note ?? (note || undefined) });
      qc.setQueryData(vpKeys.doc(d.id), d);
      nav(`/vp/${d.id}/materials`, { replace: true });
      return d;
    } catch (e) {
      setErr(errText(e));
      return null;
    } finally {
      creating.current = false;
    }
  };

  useDebounced(customer, 600, async (v) => {
    if (!id) {
      if (v.trim()) await ensure({ customer_name: v });
      return;
    }
    if ((doc?.customer_name ?? '') === v.trim()) return;
    await patchVp(id, { customer_name: v.trim() }).catch((e) => setErr(errText(e)));
    await refresh();
  });
  useDebounced(note, 600, async (v) => {
    if (!id) {
      if (v.trim()) await ensure({ note: v });
      return;
    }
    if ((doc?.note ?? '') === v) return;
    await patchVp(id, { note: v }).catch((e) => setErr(errText(e)));
    await refresh();
  });

  const toggle = async (kind: string, ref_id: string, on: boolean) => {
    if (!id) return;
    setBusy('src');
    try {
      await putSources(id, [{ kind: kind as 'storyboard', ref_id, connected: on }]);
      await refresh();
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); }
  };

  const onFiles = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setBusy('file');
    setErr('');
    try {
      const d = await ensure();
      const vid = d?.id ?? id;
      if (!vid) return;
      for (const f of Array.from(files)) {
        const fm = await uploadFile(f, { confidential: true, purpose: 'vp' });
        await addAttachment(vid, fm.id);
      }
      await qc.invalidateQueries({ queryKey: vpKeys.doc(vid) });
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); if (fileRef.current) fileRef.current.value = ''; }
  };

  const pickIndustry = async (code: string | null) => {
    setPicking(false);
    const d = await ensure();
    const vid = d?.id ?? id;
    if (!vid) return;
    await patchVp(vid, code ? { industry: { code } } : { clear_industry: true }).catch((e) => setErr(errText(e)));
    await qc.invalidateQueries({ queryKey: vpKeys.doc(vid) });
  };

  const start = async () => {
    setErr('');
    const d = await ensure();
    const vid = d?.id ?? id;
    if (!vid) return;
    setBusy('collect');
    try {
      if (customer.trim() && (d?.customer_name ?? '') !== customer.trim()) await patchVp(vid, { customer_name: customer.trim() });
      const r = await collect(vid, note);
      setJob(r.job_id);
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); }
  };

  const ind = doc?.industry;
  const cov = doc?.coverage?.length ? doc.coverage : EMPTY_COV.map((c) => ({ ...c, percent: 0, summary: '아직 없어요', level: '부족' }));
  const items = cands.data?.items ?? [];
  const tp = doc?.target_proposal;
  const running = !!job;
  const pct = j.progress;

  return (
    <Page dock={
      <Dock title="재료" meta="1 / 3">
        <div className="vp-form">
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span className="vp-form__label">고객사</span>
            <span className="vp-input"><input aria-label="고객사" value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="예: A 커피 프랜차이즈" /></span>
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span className="vp-form__label">업종 <span>· {ind?.caption?.replace(/^업종 · /, '') ?? '자동 판별'}</span></span>
            <div className="vp-ind">
              {ind && <span className="vp-auto" data-mode={ind.mode}>{ind.mode === 'pin' ? '고정' : '자동'}</span>}
              <span className="vp-ind__name">{ind?.name ?? '판별 전'}</span>
              <span className="vp-ind__pack">{ind ? ind.pack?.label : '재료를 정리하면 MI와 같은 기준으로 판별해요'}</span>
              <button type="button" className="vp-ind__btn" aria-haspopup="dialog" aria-expanded={picking} onClick={() => setPicking((x) => !x)}>바꾸기</button>
              {picking && (
                <div className="vp-indpick" role="dialog" aria-label="업종 고르기">
                  {(packs.data?.items ?? []).map((p) => <Chip key={p.code} on={ind?.code === p.code} onClick={() => pickIndustry(p.code)}>{p.name}</Chip>)}
                  <Chip on={ind?.code === 'GEN'} onClick={() => pickIndustry('GEN')}>범용</Chip>
                  {ind?.mode === 'pin' && <Chip onClick={() => pickIndustry(null)}>자동 판별로</Chip>}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="vp-note">
          <label className="wm-sr-only" htmlFor="vp-note">덧붙일 내용</label>
          <textarea id="vp-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="덧붙일 내용 (예: 결재는 CFO, 비용 절감이 1순위, 경쟁사 이야기는 빼 주세요)" />
        </div>
        {!!doc?.attachments?.length && (
          <div className="vp-files" aria-label="첨부한 파일">
            {doc.attachments.map((a) => (
              <span key={a.id} className="vp-file" title={a.summary || a.filename}>
                <Icon name="file" size={13} /><span>{a.filename}{a.summary ? ` · ${a.summary}` : ''}</span>
                <button type="button" aria-label={`${a.filename} 빼기`} onClick={async () => { if (id) { await deleteAttachment(id, a.id); await refresh(); } }}><Icon name="x" size={12} /></button>
              </span>
            ))}
          </div>
        )}
        <div className="vp-dock__row" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
            <input ref={fileRef} type="file" multiple hidden data-testid="vp-file-input" onChange={(e) => onFiles(e.target.files)} />
            <button type="button" className="vp-attach" aria-label="파일 첨부" onClick={() => fileRef.current?.click()} disabled={busy === 'file'}>
              {busy === 'file' ? <span className="vp-spin" /> : <PIcon d={ICONS.clip} size={16} />}
            </button>
            <span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>RFP를 올리면 평가 기준 · 결재 구조까지 읽어요</span>
          </div>
          {err && <span className="vp-err">{err}</span>}
          {running
            ? <Spinner label={`재료를 정리하고 있어요 · ${pct}%`} />
            : <Btn primary onClick={start} busy={busy === 'collect'}>가치 구조 만들기</Btn>}
        </div>
      </Dock>
    }>
      <Agent text="누구에게 어떤 가치를 말할지 정리할게요. 연결할 자료를 찾아 두었어요 — 연결하면 과제 · 가치 · 근거 수치 · 이해관계자를 알아서 뽑고, 빈 곳은 비워 두셔도 됩니다.">
        <div className="vp-card" data-testid="vp-sources">
          <CardHead title="연결할 수 있는 자료" meta={id ? (cands.data?.found_label ?? '찾는 중') : '고객사를 적으면 같은 고객사의 최근 작업을 찾아요'}
            right={<span className="vp-auto"><Icon name="bolt" size={11} />자동으로 찾음</span>} />
          {id && cands.isLoading && <div style={{ padding: 12 }}><Skeleton h={40} /></div>}
          {items.map((s) => (
            <label key={`${s.kind}:${s.ref_id}`} className="vp-srcrow">
              <input type="checkbox" checked={!!s.connected} disabled={busy === 'src'} aria-label={`${s.title} 연결`} onChange={(e) => toggle(s.kind, s.ref_id, e.target.checked)} />
              <span className="vp-srcrow__icon"><PIcon d={SOURCE_ICON[s.kind] ?? SOURCE_ICON.case} size={15} /></span>
              <span style={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, minWidth: 0 }}>
                <span className="vp-srcrow__title"><span>{s.kind_label} · </span>{s.title}</span>
                <span className="vp-srcrow__gives">{s.gives?.summary || '읽는 중'}</span>
              </span>
              <span className={s.connected ? 'vp-srcst vp-srcst--on' : 'vp-srcst vp-srcst--rec'}>{s.connected ? '연결됨' : '연결 추천'}</span>
            </label>
          ))}
          <div className="vp-card__foot">
            <span style={{ color: 'var(--wm-brand)', display: 'inline-flex' }}><PIcon d={ICONS.monitor} size={14} /></span>
            <span className="wm-ellipsis">
              {tp?.title
                ? <>보낼 곳 · <b>{tp.title}</b> · {TYPE_SHORT[tp.type ?? 'standard']} · Value Props 섹션 — 시트 수를 이 유형에 맞춰요</>
                : <>보낼 곳 · 연결 안 됨 — 3장 기본으로 만들고 보낼 때 맞춰요</>}
            </span>
          </div>
        </div>
        <div className="vp-card" data-testid="vp-coverage">
          <div className="vp-cov">
            <div className="vp-cov__head">
              <span className="vp-card__title">재료 커버리지 <small style={{ color: 'var(--wm-text-muted)', fontWeight: 500, fontSize: 13 }}>· 연결한 자료 기준 · 4축</small></span>
              <Link to="/vp/rules" state={{ back: id ? `/vp/${id}/materials` : '/vp/new' }} style={{ fontSize: 12, fontWeight: 600 }}>무엇을 보고 판단하나</Link>
            </div>
            {cov.map((a) => (
              <div key={a.axis} className="vp-cov__row">
                <span className="vp-cov__k">{a.label}</span>
                <span className="vp-cov__bar" role="progressbar" aria-label={`${a.label} 커버리지`} aria-valuenow={a.percent} aria-valuemin={0} aria-valuemax={100}>
                  <i className={a.percent >= 90 ? 'full' : undefined} style={{ width: `${a.percent}%` }} />
                </span>
                <span className="vp-cov__v">{a.summary}</span>
                <span className={a.level === '충분' ? 'vp-cov__lv vp-cov__lv--full' : 'vp-cov__lv'}>{a.level}</span>
                <span className="vp-cov__todo">{a.todo}</span>
              </div>
            ))}
          </div>
        </div>
      </Agent>
    </Page>
  );
}
