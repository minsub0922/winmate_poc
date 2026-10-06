/**
 * RQ4 저장 완료 `/requirements/:rqId/saved?v=` · RQ5 고객에게 물을 것 `…/questions` · RQ6 정의서 `/requirements/:rqId(?v=)`.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useShellPage } from '@/shell';
import { Button, Icon, Skeleton, toast } from '@/ui';
import { errorText, rqApi, type CustomerQuestion, type Keyman, type RequirementVersion, type UsageLink } from '../api';
import { KeymanTag, KmAvatar, WeightBar } from '../components/bits';
import { rqKey, useRequirement } from '../hooks';
import { eul, rqTime } from '../lib/format';
import { STEPS } from './FormPage';

// ── RQ4 ────────────────────────────────────────────────

export function SavedPage() {
  const { rqId } = useParams();
  const [sp] = useSearchParams();
  const rq = useRequirement(rqId);
  const n = Number(sp.get('v')) || rq.data?.version || 0;
  useShellPage({ section: '고객 요구사항', title: rq.data?.title || '새 요구사항', hasTask: true, stepper: { steps: STEPS, current: 3, complete: true } });
  if (!rqId) return null;
  const open = rq.data?.open_question_count ?? 0;
  const next = [
    { title: '전략 수립 Storyboard', to: `/storyboard/new?rq=${rqId}`, icon: 'sparkle' as const, hi: true },
    { title: 'Market Intelligence', to: `/mi/new?rq=${rqId}`, icon: 'search' as const },
    { title: 'B2B 제안서', to: `/proposal/new?rq=${rqId}`, icon: 'file' as const },
  ];
  return (
    <div className="rq-root">
      <div className="rq-center rq-center--stepper">
        <div className="rq-center__col">
          <div className="rq-saved">
            <span className="rq-saved__check" aria-hidden="true"><Icon name="check" size={26} strokeWidth={3} /></span>
            <h1 className="rq-h1" style={{ marginTop: 10 }}>저장했어요</h1>
            <span className="rq-saved__v" data-testid="saved-version">v{n}</span>
            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
              <Link to={`/requirements/${rqId}?v=${n}`} className="wm-btn wm-btn--h40" style={{ padding: '0 16px' }}>정의서 보기</Link>
              {open > 0 && (
                <Link to={`/requirements/${rqId}/questions`} className="wm-btn wm-btn--h40" style={{ padding: '0 16px' }}>
                  고객에게 물을 것 <span className="wm-num" style={{ color: 'var(--wm-brand)', fontWeight: 800, marginLeft: 6 }}>{open}</span>
                </Link>
              )}
            </div>
          </div>
          <div className="rq-next">
            <div className="rq-next__title">다음</div>
            {next.map((c) => (
              <Link key={c.title} to={c.to} className={`rq-nextcard ${c.hi ? 'rq-nextcard--hi' : ''}`} data-next={c.title}>
                <span className="rq-nextcard__icon" aria-hidden="true"><Icon name={c.icon} size={18} /></span>
                <span style={{ flex: 1 }}>{c.title}</span>
                <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── RQ5 ────────────────────────────────────────────────

export function QuestionsPage() {
  const { rqId } = useParams();
  const qc = useQueryClient();
  const rq = useRequirement(rqId);
  useShellPage({ section: '고객 요구사항', title: rq.data?.title || '새 요구사항', hasTask: true });
  const qq = useQuery({ queryKey: ['rq-questions', rqId], enabled: !!rqId, queryFn: () => rqApi.questions(rqId!, 'open') });
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  // 체크는 화면 상태가 먼저(제어 체크박스가 서버 응답 전에 되돌아가지 않게)
  const [mailOverride, setMailOverride] = useState<Record<string, boolean>>({});
  if (!rqId) return null;
  const items = (qq.data?.items ?? []).map((q) => (q.id in mailOverride ? { ...q, include_in_mail: mailOverride[q.id] } : q));
  const keymen = rq.data?.form.keymen ?? [];
  const checked = items.filter((q) => q.include_in_mail);

  const toggle = async (q: CustomerQuestion) => {
    const next = !q.include_in_mail;
    setMailOverride((m) => ({ ...m, [q.id]: next }));
    try {
      await rqApi.patchQuestion(rqId, q.id, { include_in_mail: next });
      void qc.invalidateQueries({ queryKey: ['rq-questions', rqId] });
    } catch (e) {
      toast(errorText(e));
      setMailOverride((m) => { const c = { ...m }; delete c[q.id]; return c; });
    }
  };
  const copy = async () => {
    setBusy(true);
    try {
      const d = await rqApi.mailDraft(rqId, checked.map((q) => q.id));
      await navigator.clipboard.writeText(d.body);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      toast(e instanceof Error && e.name === 'NotAllowedError' ? '클립보드에 복사하지 못했어요' : errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="rq-root">
      <div className="rq-center">
        <div className="rq-center__col">
          <div className="rq-headrow" style={{ alignItems: 'center' }}>
            <h1 className="rq-h1">고객에게 물을 것 <span className="rq-n" data-testid="q-count">{items.length}</span></h1>
            <span className="rq-grow" />
            <Link className="rq-backlink" to={`/requirements/${rqId}`}><Icon name="chevronLeft" size={14} />정의서</Link>
          </div>
          {qq.isLoading ? <div className="rq-rows"><div className="rq-skelrow"><Skeleton w="60%" h={14} /></div></div> : items.length === 0 ? (
            <p style={{ margin: 0, color: 'var(--wm-text-subtle)' }}>지금은 물을 것이 없어요</p>
          ) : (
            <div className="rq-rows" data-testid="question-list">
              {items.map((q) => {
                const km = keymen.find((k) => k.id === q.keyman_id);
                return (
                  <label key={q.id} className="rq-row" data-question={q.text}>
                    <input type="checkbox" checked={q.include_in_mail} onChange={() => void toggle(q)} aria-label={q.text} />
                    <span className="rq-row__text" style={{ fontSize: 14.5 }}>
                      {q.text}
                      {q.origin.kind === 'storyboard' && <span style={{ color: 'var(--wm-text-subtle)', fontWeight: 400, marginLeft: 8, fontSize: 13 }}>Storyboard{q.origin.place_label ? ` · ${q.origin.place_label}` : ''}</span>}
                    </span>
                    {km && <KeymanTag km={km} />}
                  </label>
                );
              })}
            </div>
          )}
          <div className="rq-foot">
            <Link className="rq-textlink" to={`/requirements/${rqId}/reply`} style={{ textDecoration: 'none' }}>답변 반영하기</Link>
            <span className="rq-grow" />
            {items.length > 0 && (
              <Button h={48} variant="primary" style={{ padding: '0 22px', fontSize: 15, fontWeight: 700 }} icon={<Icon name="copy" size={15} />} loading={busy}
                disabled={checked.length === 0} disabledReason="메일에 넣을 질문을 골라 주세요" onClick={() => void copy()}>
                {copied ? '복사했어요' : '메일 문구 복사'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── RQ6 ────────────────────────────────────────────────

const USES: Array<{ service: string; label: string; to: (id: string) => string }> = [
  { service: 'storyboard', label: 'Storyboard', to: (id) => `/storyboard/new?rq=${id}` },
  { service: 'mi', label: 'MI', to: (id) => `/mi/new?rq=${id}` },
  { service: 'proposal', label: '제안서', to: (id) => `/proposal/new?rq=${id}` },
];

export function DocPage() {
  const { rqId } = useParams();
  const [sp] = useSearchParams();
  const navigate = useNavigate();
  const rq = useRequirement(rqId);
  const latest = rq.data?.version ?? 0;
  const n = Number(sp.get('v')) || latest;
  const vq = useQuery({ queryKey: ['rq-version', rqId, n], enabled: !!rqId && n > 0, queryFn: () => rqApi.version(rqId!, n), staleTime: 60_000 });
  const links = useQuery({ queryKey: ['rq-links', rqId], enabled: !!rqId, queryFn: () => rqApi.links(rqId!) });
  const [menu, setMenu] = useState(false);
  useShellPage({ section: '고객 요구사항', title: rq.data?.title || '요구사항 정의서', hasTask: true });
  if (!rqId) return null;
  if (rq.data && latest === 0 && !rq.isFetching) return <Navigate to={`/requirements/${rqId}/form`} replace />;
  const v = vq.data;

  const share = async () => {
    try {
      const r = await rqApi.share(rqId);
      await navigator.clipboard.writeText(new URL(r.url, window.location.origin).toString()).catch(() => undefined);
      toast('링크를 복사했어요');
    } catch (e) {
      toast(errorText(e));
    }
  };
  const openUse = (service: string, to: string) => {
    const mine = (links.data?.items ?? []).filter((l: UsageLink) => l.service === service).sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    navigate(mine[0]?.route || to);
  };
  return (
    <div className="rq-root">
      <div className="rq-center">
        <div className="rq-center__col">
          <div className="rq-headrow" style={{ alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
              <span style={{ position: 'relative', display: 'inline-flex', gap: 10, alignItems: 'center' }}>
                <button type="button" className="rq-eyebrow" style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer' }}
                  aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu((m) => !m)} data-testid="doc-version">정의서 v{n}</button>
                {n !== latest && latest > 0 && <Link to={`/requirements/${rqId}`} style={{ fontSize: 12.5, color: 'var(--wm-text-subtle)' }}>최신 v{latest}</Link>}
                {menu && <VersionMenu rqId={rqId} current={n} latest={latest} onClose={() => setMenu(false)} />}
              </span>
              <h1 className="rq-h1 wm-ellipsis">{v ? (v.project_name || v.title || '요구사항 정의서') : <Skeleton w={320} h={28} />}</h1>
              {v && (
                <div style={{ fontSize: 13.5, color: 'var(--wm-text-muted)' }}>
                  {v.customer_name || '—'} · 최종 제안대상 <b style={{ color: 'var(--wm-text)' }}>{v.final_audience || '—'}</b>
                </div>
              )}
            </div>
            <span className="rq-grow" />
            <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
              <Link to={`/requirements/${rqId}/questions`} className="wm-btn wm-btn--h38" style={{ padding: '0 14px' }}>
                물을 것 <span className="wm-num" style={{ color: 'var(--wm-brand)', fontWeight: 800, marginLeft: 6 }}>{rq.data?.open_question_count ?? 0}</span>
              </Link>
              <Link to={`/requirements/${rqId}/form`} className="wm-btn wm-btn--h38" style={{ padding: '0 14px' }}>고치기</Link>
              <Button h={38} onClick={() => void share()}>공유</Button>
            </div>
          </div>
          {!v ? <div className="rq-doc"><Skeleton w="100%" h={22} /><Skeleton w="70%" h={16} /><Skeleton w="60%" h={16} /></div> : <DocCard v={v} onUse={openUse} rqId={rqId} />}
        </div>
      </div>
    </div>
  );
}

function DocCard({ v, onUse, rqId }: { v: RequirementVersion; onUse: (service: string, to: string) => void; rqId: string }) {
  const ks = v.snapshot.form.keymen as Keyman[];
  const multi = ks.length >= 2;
  const note = v.snapshot.author_note?.value ?? v.snapshot.form.author_note?.value;
  const nc = new Set(v.snapshot.items_flat.filter((i) => i.needs_confirmation).map((i) => i.id));
  return (
    <div className="rq-doc">
      <div className="rq-doc__barrow">
        <span className="rq-doc__label">키맨별 요구사항</span>
        {multi && <WeightBar keymen={ks} size="md" />}
      </div>
      {ks.map((k) => (
        <div key={k.id} data-keyman={k.name}>
          <div className="rq-doc__km">
            <KmAvatar name={k.name} colorIndex={k.color_index} size={22} />
            <span>{k.name}</span>
            {multi && <small>{k.weight}%</small>}
          </div>
          {k.items.map((it, i) => (
            <div key={it.id} className="rq-doc__item" data-item={it.text}>
              <span className="rq-item__n">{i + 1}</span>
              <span className="t" title={it.text}>{it.text}</span>
              {(it.evidence ?? []).length > 0 && <span className="rq-src rq-src--dark" title={it.evidence.map((e) => e.name).join(', ')}>근거</span>}
              {nc.has(it.id) && <span className="rq-dash">확인 필요</span>}
            </div>
          ))}
        </div>
      ))}
      {note && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, paddingTop: 8 }}>
          <span className="rq-doc__label">제작자 의견<span title="고객 문서 제외" style={{ display: 'inline-flex', color: 'var(--wm-text-subtle)' }} data-testid="note-lock"><Icon name="lock" size={13} title="고객 문서 제외" /></span></span>
          <div className="rq-doc__note">{note}</div>
        </div>
      )}
      <div className="rq-doc__uses">
        <span style={{ fontSize: 13, color: 'var(--wm-text-subtle)' }}>쓰는 곳</span>
        <span className="rq-grow" />
        {USES.map((u) => <button key={u.service} type="button" className="rq-usechip" onClick={() => onUse(u.service, u.to(rqId))}>{u.label}</button>)}
      </div>
    </div>
  );
}

const REASON: Record<string, string> = { direct: '바로 저장', deep: '심층 작성', edit: '고침', reply: '고객 답변', restore: '되돌리기' };

function VersionMenu({ rqId, current, latest, onClose }: { rqId: string; current: number; latest: number; onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const vs = useQuery({ queryKey: ['rq-versions', rqId, latest], queryFn: () => rqApi.versions(rqId) });
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const off = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    window.addEventListener('mousedown', off);
    return () => window.removeEventListener('mousedown', off);
  }, [onClose]);
  const restore = async (n: number) => {
    try {
      const r = await rqApi.restoreVersion(rqId, n);
      await qc.invalidateQueries({ queryKey: rqKey(rqId) });
      onClose();
      navigate(`/requirements/${rqId}?v=${r.version}`);
      toast(`v${n}의 내용으로 v${r.version}${eul(r.version)} 만들었어요`);
    } catch (e) {
      toast(errorText(e));
    }
  };
  return (
    <div ref={ref} role="menu" className="rq-vermenu" aria-label="버전">
      {(vs.data?.items ?? []).map((x) => (
        <div key={x.version} className="rq-vermenu__row" role="menuitem">
          <b className="wm-num" style={{ color: x.version === current ? 'var(--wm-brand)' : undefined }}>v{x.version}</b>
          <span style={{ color: 'var(--wm-text-muted)' }}>{rqTime(x.created_at)} · {x.note || REASON[x.reason] || x.reason}</span>
          <span className="rq-grow" />
          <Link to={`/requirements/${rqId}?v=${x.version}`} onClick={onClose} style={{ fontSize: 12.5, fontWeight: 600 }}>보기</Link>
          {x.version !== latest && <button type="button" className="rq-link-btn" onClick={() => void restore(x.version)}>이 버전으로 되돌리기</button>}
        </div>
      ))}
    </div>
  );
}
