/**
 * RQ7 고객 답변 붙여넣기 `/requirements/:rqId/reply` · RQ7B 바뀌는 곳 확인 `/requirements/:rqId/reply/:replyId`.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { useShellPage } from '@/shell';
import { Button, Icon, Skeleton, toast } from '@/ui';
import { AI_DOWN, errorText, requestStoryboardSync, rqApi, type ReplyChange } from '../api';
import { Arrow } from '../components/bits';
import { rqKey, useJobTicker, useRequirement } from '../hooks';
import { ro } from '../lib/format';

type Att = { file_id: string; name: string; label: string };
const draftKey = (id: string) => `rq-reply-draft:${id}`;
const labelOf = (name: string) => (name.split('.').pop() ?? '').toUpperCase().slice(0, 4) || 'FILE';

function loadDraft(id: string): { text: string; atts: Att[] } {
  try {
    const raw = window.localStorage.getItem(draftKey(id));
    if (raw) return JSON.parse(raw);
  } catch { /* 없음 */ }
  return { text: '', atts: [] };
}

export function ReplyPage() {
  const { rqId } = useParams();
  const navigate = useNavigate();
  const rq = useRequirement(rqId);
  useShellPage({ section: '고객 요구사항', title: rq.data?.title || '요구사항 정의서', hasTask: true });
  const [text, setText] = useState(() => (rqId ? loadDraft(rqId).text : ''));
  const [atts, setAtts] = useState<Att[]>(() => (rqId ? loadDraft(rqId).atts : []));
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!rqId) return;
    try { window.localStorage.setItem(draftKey(rqId), JSON.stringify({ text, atts })); } catch { /* 저장소 없음 */ }
  }, [rqId, text, atts]);

  const addFiles = useCallback(async (files: File[]) => {
    setUploading((n) => n + files.length);
    for (const f of files) {
      try {
        const meta = await uploadFile(f, { confidential: true, purpose: 'rq.reply' });
        const lower = f.name.toLowerCase();
        if (lower.endsWith('.eml') || lower.endsWith('.msg')) {
          // 메일 파일 — 본문은 입력칸에, 첨부는 칩으로(제안)
          const r = await fetch(`/api/files/v1/files/${meta.id}/parsed`, { credentials: 'same-origin' });
          const p = r.ok ? await r.json() : null;
          const em = p?.email;
          if (em?.body) setText((t) => (t ? `${t}\n\n${em.body}` : em.body));
          const kids: Att[] = (em?.attachment_list ?? []).filter((a: { file_id?: string; inline?: boolean }) => a.file_id && !a.inline)
            .map((a: { file_id: string; name: string }) => ({ file_id: a.file_id, name: a.name, label: labelOf(a.name) }));
          setAtts((x) => [...x, ...kids]);
        } else {
          setAtts((x) => [...x, { file_id: meta.id, name: meta.name, label: labelOf(meta.name) }]);
        }
      } catch (e) {
        toast(errorText(e));
      } finally {
        setUploading((n) => n - 1);
      }
    }
  }, []);

  if (!rqId) return null;
  const canFind = (text.trim().length > 0 || atts.length > 0) && uploading === 0;
  const find = async () => {
    setBusy(true);
    try {
      const acc = await rqApi.createReply(rqId, text, atts.map((a) => a.file_id));
      navigate(`/requirements/${rqId}/reply/${acc.ref.id}`);
    } catch (e) {
      toast(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="rq-root">
      <div className="rq-center">
        <div className="rq-center__col"
          onDragOver={(e) => { if (Array.from(e.dataTransfer.types).includes('Files')) e.preventDefault(); }}
          onDrop={(e) => { if (e.dataTransfer.files.length) { e.preventDefault(); void addFiles(Array.from(e.dataTransfer.files)); } }}>
          <div className="rq-headrow" style={{ alignItems: 'center' }}>
            <h1 className="rq-h1">답변을 붙여 넣어 주세요</h1>
            <span className="rq-grow" />
            {(rq.data?.version ?? 0) > 0 && <Link className="rq-backlink" to={`/requirements/${rqId}`}><Icon name="chevronLeft" size={14} />정의서 v{rq.data?.version}</Link>}
          </div>
          <div className="rq-replycard">
            <textarea aria-label="붙여 넣은 고객 답변" value={text} onChange={(e) => setText(e.target.value)} />
            {(atts.length > 0 || uploading > 0) && (
              <div className="rq-replycard__atts">
                {atts.map((a) => (
                  <span key={a.file_id} className="rq-filechip" data-att={a.name}>
                    <span className="rq-src rq-src--dark">{a.label}</span>
                    <span className="rq-filechip__name">{a.name}</span>
                    <button type="button" className="rq-iconx" aria-label="빼기" onClick={() => setAtts((x) => x.filter((y) => y.file_id !== a.file_id))}><Icon name="x" size={11} strokeWidth={2.4} /></button>
                  </span>
                ))}
                {uploading > 0 && <span className="rq-filechip"><span className="rq-reading" role="status" aria-label="올리는 중" /></span>}
              </div>
            )}
            <div className="rq-replycard__foot">
              <input ref={input} type="file" multiple hidden data-testid="reply-file-input" onChange={(e) => { const fs = Array.from(e.target.files ?? []); e.target.value = ''; void addFiles(fs); }} />
              <Button h={38} icon={<Icon name="upload" size={14} color="var(--wm-brand)" />} onClick={() => input.current?.click()}>파일 첨부</Button>
              <span className="rq-grow" />
              <Button h={48} variant="primary" style={{ padding: '0 20px', fontSize: 15, fontWeight: 700 }} loading={busy} disabled={!canFind}
                disabledReason="고객 답변을 붙여 넣거나 파일을 첨부해 주세요" iconRight={<Icon name="arrowRight" size={15} />} onClick={() => void find()}>바뀌는 곳 찾기</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ReplyReviewPage() {
  const { rqId, replyId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const rq = useRequirement(rqId);
  useShellPage({ section: '고객 요구사항', title: rq.data?.title || '요구사항 정의서', hasTask: true });
  const key = ['rq-reply', replyId];
  const rp = useQuery({ queryKey: key, enabled: !!rqId && !!replyId, queryFn: () => rqApi.reply(rqId!, replyId!) });
  const r = rp.data;
  const refetch = useCallback(() => { void qc.invalidateQueries({ queryKey: ['rq-reply', replyId] }); }, [qc, replyId]);
  useJobTicker(r?.status === 'analyzing' ? r.job_id : null, refetch);
  const [propagate, setPropagate] = useState(true);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(false);
  const [selOverride, setSelOverride] = useState<Record<string, boolean>>({});
  if (!rqId || !replyId) return null;
  const analyzing = !r || r.status === 'analyzing';
  const changes = (r?.changes ?? []).map((c) => (c.id in selOverride ? { ...c, selected: selOverride[c.id] } : c));
  const selected = changes.filter((c) => c.selected);
  const nextV = (rq.data?.version ?? r?.base_version ?? 0) + 1;
  const impact = r?.storyboard_impact;

  const toggle = async (c: ReplyChange) => {
    if (!r) return;
    const ids = changes.filter((x) => (x.id === c.id ? !x.selected : x.selected)).map((x) => x.id);
    setSelOverride((m) => ({ ...m, [c.id]: !c.selected }));
    try {
      const res = await rqApi.selectChanges(rqId, replyId, ids);
      qc.setQueryData(key, res);
    } catch (e) {
      toast(errorText(e));
      setSelOverride((m) => { const x = { ...m }; delete x[c.id]; return x; });
      refetch();
    }
  };
  const apply = async () => {
    setBusy(true);
    try {
      const doProp = propagate && (impact?.count ?? 0) > 0;
      const res = await rqApi.applyReply(rqId, replyId, selected.map((c) => c.id), doProp);
      for (const l of res.pending_sync_links) if (l.service === 'storyboard') void requestStoryboardSync(l.ref_id, rqId, res.version);
      try { window.localStorage.removeItem(`rq-reply-draft:${rqId}`); } catch { /* 없음 */ }
      await qc.invalidateQueries({ queryKey: rqKey(rqId) });
      void qc.invalidateQueries({ queryKey: ['rq-questions', rqId] });
      navigate(`/requirements/${rqId}?v=${res.version}`);
    } catch (e) {
      toast(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const links = impact?.links ?? [];
  const previewHref = (sb: string) => `/storyboard/${sb}/versions?preview_rq=${rqId}&reply=${replyId}`;
  return (
    <div className="rq-root">
      <div className="rq-center">
        <div className="rq-center__col">
          <h1 className="rq-h1" aria-live="polite">
            {analyzing ? '바뀌는 곳을 찾는 중이에요' : r?.status === 'failed' ? '바뀌는 곳을 찾지 못했어요'
              : changes.length === 0 ? '바뀌는 곳이 없어요' : <><span className="wm-num">{changes.length}</span>곳이 바뀌어요</>}
          </h1>
          {r?.status === 'failed' && (
            <p style={{ margin: 0, color: 'var(--wm-text-muted)' }}>
              {r.error?.code === 'LLM_UNAVAILABLE' || r.error?.code === 'POLICY_CONFIDENTIAL' ? AI_DOWN : r.error?.message}
            </p>
          )}
          {analyzing && (
            <div className="rq-rows" aria-busy="true">
              {Array.from({ length: 3 }, (_, i) => <div key={i} className="rq-skelrow"><Skeleton w={18} h={18} r={4} /><Skeleton w={90} h={14} /><Skeleton w={`${30 + i * 10}%`} h={14} /></div>)}
            </div>
          )}
          {!analyzing && changes.length > 0 && (
            <div className="rq-rows" data-testid="change-list">
              {changes.map((c) => (
                <label key={c.id} className="rq-row" data-change={c.label}>
                  <input type="checkbox" checked={c.selected} disabled={r?.status !== 'ready'} onChange={() => void toggle(c)} aria-label={`${c.label} 바꾸기`} />
                  <span className="rq-row__label rq-row__label--w">{c.label}</span>
                  {c.before_display ? <span className="rq-before">{c.before_display}</span> : <span className="rq-add">추가</span>}
                  <Arrow />
                  <span className="rq-after" title={c.after_display}>{c.after_display}</span>
                </label>
              ))}
            </div>
          )}
          {!analyzing && (impact?.count ?? 0) > 0 && r?.status === 'ready' && (
            <div className="rq-rows" data-testid="storyboard-line">
              <div className="rq-row" style={{ position: 'relative' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, cursor: 'pointer' }}>
                  <input type="checkbox" checked={propagate} onChange={(e) => setPropagate(e.target.checked)} />
                  <span style={{ fontSize: 14.5, fontWeight: 600 }}>Storyboard <span className="wm-num">{impact!.count}</span>곳에도 반영</span>
                </label>
                {links.length === 1
                  ? <Link to={previewHref(links[0].ref_id)} style={{ fontSize: 13, fontWeight: 600 }}>미리 보기</Link>
                  : <button type="button" className="rq-link-btn" onClick={() => setPreview((p) => !p)}>미리 보기</button>}
                {preview && links.length > 1 && (
                  <div className="rq-vermenu" style={{ left: 'auto', right: 12, top: 44 }} role="menu">
                    {links.map((l) => <Link key={l.ref_id} role="menuitem" className="rq-vermenu__row" to={previewHref(l.ref_id)}>{l.title || l.ref_id}</Link>)}
                  </div>
                )}
              </div>
            </div>
          )}
          <div className="rq-foot">
            <Link className="rq-backlink" to={`/requirements/${rqId}/reply`}><Icon name="chevronLeft" size={14} />뒤로</Link>
            <span className="rq-grow" />
            {r?.status === 'applied' ? (
              <Link to={`/requirements/${rqId}?v=${r.applied_version}`} className="wm-btn wm-btn--h48 wm-btn--primary" style={{ padding: '0 22px' }}>정의서 v{r.applied_version}</Link>
            ) : !analyzing && changes.length > 0 && r?.status === 'ready' && (
              <Button h={48} variant="primary" style={{ padding: '0 22px', fontSize: 15, fontWeight: 700 }} loading={busy} disabled={selected.length === 0}
                disabledReason="반영할 곳을 골라 주세요" iconRight={<Icon name="arrowRight" size={15} />} onClick={() => void apply()}>v{nextV}{ro(nextV)} 저장</Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
