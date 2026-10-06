/**
 * PR7C — 검토 · 코멘트 · 승인(§4.22, 보드 PR7C) — `/proposal/:id/review/:no?`(`?export=1`).
 * 왼쪽: 검토 요청(보낸 시각 · 마감 · 검토자 상태 · 메시지) · 공유 링크 · 다시 검토 요청 · 코멘트가 있는 시트.
 *   검토 요청 전이면 작성 모드(검토자 고르기 · 마감 · 메시지 → `POST …/review-requests`).
 * 가운데: 슬라이드 + 코멘트 핀(누르면 그 자리에 코멘트) · 시트 확인 격자 · W 수정안 만들기(`review:apply-comments` → PR7V 비교).
 * 오른쪽: 코멘트(workspace 코멘트 API) — 열린 · 해결 · 답글 · 확정 필요로 보내기 · 해결 · W 제안 적용.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Icon, cx, toast } from '@/ui';
import {
  applyComments, applySuggestion, createConfirmItem, decideReview, getSuggestion, putCheck, qk, requestReview, resubmitReview, shareLink, suggestComment,
  useProposal, useReview, useSheet, useSlides,
} from '../api/proposal';
import { commentsKey, createComment, patchComment, useComments, useMe, useUsers, type WsComment } from '../api/comments';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import { ErrorBand, LoadingCard, Prompt, Rich, SpinIcon, Switch } from '../components/parts';
import { SlideView, type SlideDoc } from '../components/SlideView';
import { ResultToolbar, useExportParam } from '../components/ResultToolbar';
import { koDate, whenLabel } from '../lib/format';
import { R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { ExportModal } from './ExportModal';

const ST_CLS: Record<string, string> = { approved: 'pr-revst pr-revst--ok', changes_requested: 'pr-revst pr-revst--chg', pending: 'pr-revst' };

export function ReviewPage() {
  const { id, no } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const rq = useReview(id);
  const rv = rq.data;
  const sq = useSlides(id);
  const sv = sq.data;
  const me = useMe();
  const flat = useMemo(() => (sv?.sections ?? []).flatMap((s) => s.sheets.map((sh) => ({ ...sh, sectionName: s.name }))), [sv]);
  const firstWithComments = rv?.comment_sheets?.find((c) => c.open > 0)?.sheet_no;
  const cur = flat.find((x) => String(x.sheet_no) === no) ?? flat.find((x) => x.sheet_no === firstWithComments) ?? flat[0];
  const idx = cur ? flat.indexOf(cur) : -1;
  const shq = useSheet(id, cur?.sheet_id);
  const sh = shq.data;
  const target = rv?.comment_target ?? (id ? `proposal:${id}` : null);
  const cmq = useComments(target);
  const all = cmq.data ?? [];
  const [pins, setPins] = useState(true);
  const [tab, setTab] = useState<'open' | 'resolved'>('open');
  const [selPin, setSelPin] = useState<string | null>(null);
  const [anchor, setAnchor] = useState<{ x: number; y: number } | null>(null);
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const ex = useExportParam();
  useProposalShell({ p, step: 6 });
  useEffect(() => { setSelPin(null); setAnchor(null); setReplyTo(null); }, [cur?.sheet_id]);

  const refresh = () => { if (id) { void qc.invalidateQueries({ queryKey: qk.sub(id, 'review') }); void qc.invalidateQueries({ queryKey: qk.p(id) }); } if (target) void qc.invalidateQueries({ queryKey: commentsKey(target) }); };
  const ev = useJobEvents(job, {
    onDone: (j) => {
      setJob(null);
      if (j.status !== 'succeeded') { toast(jobErrText(j.error, '수정안을 만들지 못했어요')); return; }
      refresh();
      const v = Number((j.result as Record<string, unknown> | undefined)?.version ?? 0);
      if (id) nav(R.versions(id, { a: rv?.review?.version ?? null, b: v || null }));
    },
  });

  const roots = all.filter((c) => !c.parent_id);
  const forSheet = roots.filter((c) => c.anchor?.sheet_id === cur?.sheet_id);
  const openC = forSheet.filter((c) => !c.resolved);
  const doneC = forSheet.filter((c) => c.resolved);
  const replies = (cid: string) => all.filter((c) => c.parent_id === cid);
  const pinNo = (c: WsComment) => openC.indexOf(c) + 1;

  const send = async (text: string) => {
    if (!target || !id || !cur) return;
    const body = text.trim();
    if (!body) return;
    try {
      await createComment(replyTo
        ? { target, body, parent_id: replyTo }
        : { target, body, anchor: { proposal_id: id, version: rv?.review?.version ?? p?.version ?? null, sheet_id: cur.sheet_id, element_ref: null, x: anchor?.x ?? null, y: anchor?.y ?? null } });
      setReplyTo(null); setAnchor(null);
      void qc.invalidateQueries({ queryKey: commentsKey(target) });
      void qc.invalidateQueries({ queryKey: qk.sub(id, 'review') });
    } catch (e) { toast(errText(e)); }
  };
  const act = async (tag: string, fn: () => Promise<unknown>, ok?: string) => {
    setBusy(tag);
    try { await fn(); if (ok) toast(ok); refresh(); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };

  if (pq.isError) return <div className="pr-page"><div className="pr-scroll"><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></div></div>;
  if (!p || !id) return <div className="pr-page"><div className="pr-scroll"><div className="pr-col"><LoadingCard /></div></div></div>;
  const review = rv?.review ?? null;
  const reviewers = rv?.reviewers ?? [];
  const mine = reviewers.find((r) => r.me || r.user_id === me.data?.user_id);
  const doc = (sh?.display ?? sh?.content ?? null) as SlideDoc | null;
  const grid = rv?.check_grid ?? [];

  const overlay = pins && cur ? (
    <>
      {forSheet.filter((c) => c.anchor?.x != null && c.anchor?.y != null).map((c) => (
        <button key={c.id} type="button" className={cx('pr-pin', c.resolved && 'pr-pin--done', selPin === c.id && 'pr-pin--on')} style={{ left: `${(c.anchor!.x as number) * 100}%`, top: `${(c.anchor!.y as number) * 100}%` }}
          aria-label={c.resolved ? '해결된 코멘트' : `코멘트 ${pinNo(c)}`} onClick={(e) => { e.stopPropagation(); setSelPin(c.id); setTab(c.resolved ? 'resolved' : 'open'); }}>
          {c.resolved ? <Icon name="check" size={10} strokeWidth={3} /> : pinNo(c)}
        </button>
      ))}
      {anchor && <span className="pr-pin pr-pin--new" style={{ left: `${anchor.x * 100}%`, top: `${anchor.y * 100}%` }}>+</span>}
    </>
  ) : null;

  return (
    <div className="pr-res" data-testid="pr7c">
      <ResultToolbar id={id} tab="review" fileName={sv?.file_name ?? p.title}
        pill={rv?.version_label ?? (review ? `v${review.version} · ${review.status_label}` : p.version ? `v${p.version}` : null)}
        meta={rv ? `코멘트 열린 ${rv.comments_open ?? 0} · 해결 ${rv.comments_resolved ?? 0}` : null} openConfirm={sv?.open_confirm}
        extra={rv?.approvals ? <span className="pr-note" style={{ fontSize: 12.5, whiteSpace: 'nowrap' }} data-testid="pr7c-approvals">승인 <b className="pr-num" style={{ color: 'var(--wm-text)' }}>{rv.approvals.done} / {rv.approvals.total}</b></span> : null}
        onExport={() => ex.openExport()} />
      <div className="pr-resbody">
        <aside className="pr-revleft" data-testid="pr7c-request">
          {rq.isError ? <ErrorBand message={errText(rq.error)} onRetry={() => void rq.refetch()} /> : !rv ? <LoadingCard lines={6} /> : !review ? (
            <RequestComposer id={id} onSent={() => refresh()} />
          ) : (
            <>
              <div className="pr-colflex" style={{ gap: 4 }}>
                <div className="pr-row" style={{ gap: 8 }}><b style={{ fontSize: 15 }}>검토 요청</b><span className="pr-badge pr-badge--soft">{review.status_label}</span></div>
                <span className="pr-note" style={{ fontSize: 12 }}>{review.sent_label || [review.requested_at ? `${whenLabel(review.requested_at)} 보냄` : null, review.due_date ? `마감 ${koDate(review.due_date)}` : null].filter(Boolean).join(' · ')}</span>
              </div>
              <div className="pr-colflex" style={{ gap: 0 }}>
                <div className="pr-row pr-row--between" style={{ height: 28 }}><b style={{ fontSize: 12.5 }}>검토자 {reviewers.length}</b><AddReviewer id={id} existing={reviewers.map((r) => r.user_id)} onAdded={refresh} /></div>
                {reviewers.map((r) => (
                  <div key={r.user_id} className="pr-revrow2" data-testid="pr7c-reviewer">
                    <span className="pr-avatar">{r.initial}</span>
                    <span className="pr-colflex pr-grow" style={{ gap: 0 }}><b style={{ fontSize: 13 }}>{r.name}</b><span className="pr-note" style={{ fontSize: 11.5 }}>{r.role}</span></span>
                    {r === mine && rv.can_decide ? (
                      <span className="pr-row" style={{ gap: 4 }}>
                        <button type="button" className="pr-mini pr-mini--primary" disabled={!!busy} onClick={() => void act('approve', () => decideReview(id, 'approve'), '승인했어요')} data-testid="pr7c-approve">승인</button>
                        <button type="button" className="pr-mini" disabled={!!busy} onClick={() => void act('chg', () => decideReview(id, 'request_changes'), '수정을 요청했어요')}>수정 요청</button>
                      </span>
                    ) : <span className={ST_CLS[r.status] ?? 'pr-revst'}>{r.status === 'approved' && <Icon name="check" size={11} strokeWidth={3} />}{r.status_label}</span>}
                  </div>
                ))}
              </div>
              {review.message && <div className="pr-revmsg">“{review.message}”</div>}
              <ShareBox id={id} label={rv.share_permission_label} />
              <button type="button" className="pr-btn pr-btn--h38 pr-revresend" disabled={!!busy} onClick={() => void act('resend', () => resubmitReview(id, review.id), '같은 검토자에게 다시 요청했어요')} data-testid="pr7c-resubmit">코멘트 반영 후 다시 검토 요청</button>
              <div className="pr-resaside__div" style={{ margin: 0 }} />
              <div className="pr-colflex" style={{ gap: 2 }}>
                <b style={{ fontSize: 12.5, padding: '4px 0 6px' }}>코멘트가 있는 시트</b>
                {(rv.comment_sheets ?? []).length === 0 && <span className="pr-note">아직 코멘트가 없어요</span>}
                {(rv.comment_sheets ?? []).map((c) => (
                  <Link key={c.sheet_id} to={R.review(id, c.sheet_no)} className={cx('pr-csheet', c.sheet_id === cur?.sheet_id && 'pr-csheet--on')} aria-current={c.sheet_id === cur?.sheet_id ? 'page' : undefined}>
                    <span className="pr-num pr-subtle" style={{ width: 22, fontSize: 11.5, fontWeight: 700 }}>{String(c.sheet_no).padStart(2, '0')}</span>
                    <span className="pr-ell pr-grow" style={{ fontSize: 13 }}>{c.name}</span>
                    {c.open > 0 ? <span className="pr-cpill pr-cpill--open">열린 {c.open}</span> : <span className="pr-cpill">해결 {c.resolved}</span>}
                  </Link>
                ))}
              </div>
            </>
          )}
        </aside>

        <section className="pr-rescenter" data-testid="pr7c-slide">
          {cur && (
            <div className="pr-row" style={{ height: 34, gap: 8 }}>
              <span className="pr-noblock pr-num">{String(cur.sheet_no).padStart(2, '0')}</span>
              <b className="pr-ell" style={{ fontSize: 15 }}>{sh?.title ?? cur.title}</b>
              <span className="pr-note" style={{ fontSize: 12.5, whiteSpace: 'nowrap' }}>{cur.sectionName} · 코멘트 {forSheet.length}</span>
              <span className="pr-grow" />
              <span className="pr-pinswitch"><Switch on={pins} onChange={setPins} label="코멘트 핀" />코멘트 핀</span>
              <button type="button" className="pr-navbtn" aria-label="이전 슬라이드" disabled={idx <= 0} onClick={() => nav(R.review(id, flat[idx - 1].sheet_no))}><Icon name="chevronLeft" size={14} strokeWidth={2.2} /></button>
              <button type="button" className="pr-navbtn" aria-label="다음 슬라이드" disabled={idx < 0 || idx >= flat.length - 1} onClick={() => nav(R.review(id, flat[idx + 1].sheet_no))}><Icon name="chevronRight" size={14} strokeWidth={2.2} /></button>
            </div>
          )}
          {shq.isError ? <ErrorBand message={errText(shq.error)} onRetry={() => void shq.refetch()} /> : sh ? (
            <SlideView doc={doc} no={sh.sheet_no} footer={p.title} renderUrl={sh.render?.url ?? sh.thumb_url} overlay={overlay}
              onSlideClick={pins ? (x, y) => { setAnchor({ x, y }); setReplyTo(null); setSelPin(null); } : undefined} />
          ) : cur ? <LoadingCard lines={6} /> : <div className="pr-empty">아직 시트가 없어요</div>}
          {anchor && <div className="pr-note" style={{ fontSize: 12 }}>핀 자리를 골랐어요 · 오른쪽 아래에 코멘트를 남기면 이 자리에 붙어요 <button type="button" className="pr-link" style={{ fontSize: 12 }} onClick={() => setAnchor(null)}>취소</button></div>}
          {grid.length > 0 && (
            <div className="pr-card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }} data-testid="pr7c-grid">
              <div className="pr-row pr-row--between">
                <b style={{ fontSize: 13 }}>{rv?.check_label ?? `시트 확인 ${grid.filter((g) => g.state === 'ok').length} / ${grid.length}`}</b>
                <span className="pr-legend">
                  <span><i className="pr-legend__sw pr-legend__sw--on" />확인됨</span>
                  <span><i className="pr-legend__sw" style={{ borderColor: 'var(--wm-brand)' }} />열린 코멘트</span>
                  <span><i className="pr-legend__sw" style={{ background: 'var(--wm-surface-3)', border: 'none' }} />아직</span>
                </span>
              </div>
              <div className="pr-checkgrid">
                {grid.map((g) => (
                  <button key={g.sheet_id} type="button" className={cx('pr-checkcell', `pr-checkcell--${g.state}`, g.sheet_id === cur?.sheet_id && 'pr-checkcell--cur')}
                    title={`${String(g.sheet_no).padStart(2, '0')} · ${g.state === 'ok' ? '확인됨' : g.state === 'open' ? '열린 코멘트' : '아직 확인 전'}`}
                    onClick={() => { if (mine && g.sheet_id === cur?.sheet_id && g.state !== 'open') void act(`chk:${g.sheet_id}`, () => putCheck(id, g.sheet_id, g.state === 'ok' ? 'todo' : 'ok')); else nav(R.review(id, g.sheet_no)); }}>
                    {String(g.sheet_no).padStart(2, '0')}
                  </button>
                ))}
              </div>
            </div>
          )}
          {(rv?.comments_open ?? 0) > 0 && (
            <div className="pr-card pr-wsuggest" data-testid="pr7c-suggest">
              <span className="pr-chat__w" style={{ width: 26, height: 26, borderRadius: 7 }}>W</span>
              <span className="pr-grow" style={{ fontSize: 13, lineHeight: 1.55 }}>{rv?.suggest_text || `열린 코멘트 ${rv?.comments_open}건을 반영한 수정안을 만들 수 있어요. 새 버전으로 저장하고 바뀐 곳을 비교해 드릴게요.`}</span>
              <button type="button" className="pr-btn pr-btn--h38 pr-btn--primary" disabled={!!job} onClick={() => void act('apply', async () => { const r = await applyComments(id); setJob(r.job_id); })} data-testid="pr7c-apply">
                {job ? <><SpinIcon size={13} color="currentColor" />{Math.round(ev.progress)}%</> : '수정안 만들기'}</button>
            </div>
          )}
        </section>

        <aside className="pr-resaside" aria-label="코멘트" data-testid="pr7c-comments">
          <div className="pr-resaside__head">
            <span className="pr-row" style={{ gap: 8, minWidth: 0 }}><b style={{ fontSize: 14 }}>코멘트</b><span className="pr-note pr-ell">{cur ? `${String(cur.sheet_no).padStart(2, '0')} ${cur.title}` : ''}</span></span>
            <div role="radiogroup" aria-label="코멘트 보기" className="pr-miniseg">
              <button type="button" role="radio" aria-checked={tab === 'open'} onClick={() => setTab('open')}>열린 {openC.length}</button>
              <button type="button" role="radio" aria-checked={tab === 'resolved'} onClick={() => setTab('resolved')}>해결 {doneC.length}</button>
            </div>
          </div>
          <div className="pr-colflex" style={{ gap: 10, padding: 12, flex: 1, overflowY: 'auto' }}>
            {cmq.isError && <ErrorBand message={errText(cmq.error)} onRetry={() => void cmq.refetch()} />}
            {(tab === 'open' ? openC : doneC).length === 0 && <span className="pr-note" style={{ padding: 8 }}>{tab === 'open' ? '이 시트에 열린 코멘트가 없어요. 슬라이드를 눌러 핀을 꽂고 코멘트를 남겨 보세요.' : '해결한 코멘트가 없어요'}</span>}
            {tab === 'open' && openC.map((c) => (
              <CommentCard key={c.id} id={id} c={c} no={pinNo(c)} on={selPin === c.id} replies={replies(c.id)} onSelect={() => setSelPin(c.id)}
                onReply={() => { setReplyTo(c.id); setAnchor(null); }} replying={replyTo === c.id} sheetId={cur?.sheet_id ?? null} onChanged={refresh} />
            ))}
            {/* 보드: 열린 코멘트 아래에 해결된 코멘트를 한 줄 카드로 함께 보여준다 */}
            {doneC.map((c) => (
              <div key={c.id} className="pr-cdone">
                <span className="pr-cficon pr-cficon--ok" style={{ background: 'var(--wm-text-subtle)' }}><Icon name="check" size={10} strokeWidth={3} /></span>
                <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
                  <b style={{ fontSize: 12.5 }}>해결됨 · {c.author_name} · {whenLabel(c.updated_at)}</b>
                  <span className="pr-ell pr-note">{c.body}</span>
                </span>
                <Link to={R.versions(id)} className="pr-link" style={{ fontSize: 12 }}>변경 보기</Link>
              </div>
            ))}
          </div>
          <div style={{ padding: '10px 16px 16px', borderTop: '1px solid var(--wm-line)' }}>
            {replyTo && <div className="pr-note" style={{ fontSize: 11.5, paddingBottom: 6 }}>답글 쓰는 중 · <button type="button" className="pr-link" style={{ fontSize: 11.5 }} onClick={() => setReplyTo(null)}>취소</button></div>}
            <Prompt placeholder={replyTo ? '답글 남기기' : '코멘트 남기기 · @로 멘션'} label="코멘트 남기기" onSend={send} testId="pr7c-input" />
          </div>
        </aside>
      </div>
      {ex.open && <ExportModal proposalId={id} open onClose={ex.closeExport} initialLang={ex.lang} version={ex.version} />}
    </div>
  );
}

function CommentCard({ id, c, no, on, replies, onSelect, onReply, replying, sheetId, onChanged }:
  { id: string; c: WsComment; no: number; on: boolean; replies: WsComment[]; onSelect: () => void; onReply: () => void; replying: boolean; sheetId: string | null; onChanged: () => void }) {
  const qc = useQueryClient();
  const sg = useQuery({ queryKey: ['pr', 'sugg', id, c.id], queryFn: () => getSuggestion(id, c.id), retry: 0, refetchInterval: (q) => (q.state.data?.status === 'running' ? 2500 : false) });
  const s = sg.data;
  const [busy, setBusy] = useState<string | null>(null);
  const run = async (tag: string, fn: () => Promise<unknown>, ok?: string) => {
    setBusy(tag);
    try { await fn(); if (ok) toast(ok); onChanged(); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  return (
    <div className={cx('pr-ccard', on && 'pr-ccard--on')} onClick={onSelect} data-testid="pr7c-comment">
      <div className="pr-row" style={{ gap: 6 }}>
        <span className="pr-pinno">{no}</span>
        <span className="pr-avatar pr-avatar--sm">{c.author_name.slice(-2, -1) || c.author_name.slice(0, 1)}</span>
        <b style={{ fontSize: 13 }}>{c.author_name}</b>
        <span className="pr-note" style={{ fontSize: 11.5 }}>{whenLabel(c.created_at)}</span>
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.6 }}>{c.body}</div>
      {replies.length > 0 && (
        <div className="pr-creplies">
          {replies.map((r) => (
            <div key={r.id} className="pr-colflex" style={{ gap: 2 }}>
              <span className="pr-row" style={{ gap: 6 }}><span className="pr-avatar pr-avatar--xs">{r.author_name.slice(0, 1)}</span><b style={{ fontSize: 12.5 }}>{r.author_name}</b><span className="pr-note" style={{ fontSize: 11 }}>· {whenLabel(r.created_at)}</span></span>
              <span style={{ fontSize: 12.5, lineHeight: 1.55 }}>{r.body}</span>
            </div>
          ))}
        </div>
      )}
      {s?.status === 'done' && s.suggestion_text && (
        <div className="pr-csugg">
          <span className="pr-chat__w">W</span>
          <span className="pr-grow" style={{ fontSize: 12.5, lineHeight: 1.5 }}><Rich text={s.suggestion_text} /></span>
          <button type="button" className="pr-mini pr-mini--primary" disabled={!!busy} onClick={(e) => { e.stopPropagation(); void run('apply', async () => { await applySuggestion(id, c.id); void qc.invalidateQueries({ queryKey: qk.sub(id, 'sheet', sheetId) }); }, '수정안을 적용했어요'); }}>적용</button>
        </div>
      )}
      {s?.status === 'running' && <span className="pr-note pr-row" style={{ gap: 6 }}><SpinIcon size={11} />W가 수정안을 만드는 중이에요</span>}
      <div className="pr-row pr-row--wrap" style={{ gap: 6 }} onClick={(e) => e.stopPropagation()}>
        <button type="button" className="pr-mini" aria-pressed={replying} onClick={onReply}>답글</button>
        <button type="button" className="pr-mini" disabled={!!busy || !sheetId} onClick={() => void run('cfm', () => createConfirmItem(id, { sheet_id: sheetId!, text: c.body, from_comment_id: c.id, tag: '검토 코멘트' }), '확정 필요 목록에 보냈어요')}>확정 필요로 보내기</button>
        {(!s || s.status === 'none') && <button type="button" className="pr-mini pr-mini--ghost" aria-label="W 수정안" title="W에게 수정안 받기" style={{ padding: '0 5px' }} disabled={!!busy} onClick={() => void run('sg', async () => { await suggestComment(id, c.id); void sg.refetch(); })}><span className="pr-chat__w" style={{ width: 18, height: 18, fontSize: 10 }}>W</span></button>}
        <span className="pr-grow" />
        <button type="button" className="pr-mini pr-mini--primary" disabled={!!busy} onClick={() => void run('res', () => patchComment(c.id, { resolved: true }), '해결했어요')} data-testid="pr7c-resolve"><Icon name="check" size={12} strokeWidth={2.6} />해결</button>
      </div>
    </div>
  );
}

function ShareBox({ id, label }: { id: string; label?: string }) {
  const [perm, setPerm] = useState<'team_comment' | 'team_view'>('team_comment');
  const [busy, setBusy] = useState(false);
  const copy = async () => {
    setBusy(true);
    try {
      const r = await shareLink(id, perm);
      const url = r.url.startsWith('http') ? r.url : `${window.location.origin}${r.url}`;
      try { await navigator.clipboard.writeText(url); toast('링크를 복사했어요'); } catch { toast(url); }
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };
  return (
    <div className="pr-colflex" style={{ gap: 6 }}>
      <b style={{ fontSize: 12.5 }}>공유</b>
      <div className="pr-row" style={{ gap: 6 }}>
        <select aria-label="링크 권한" className="pr-railsel pr-grow" style={{ margin: 0, height: 34, background: 'var(--wm-surface)' }} value={perm} onChange={(e) => setPerm(e.target.value as typeof perm)}>
          <option value="team_comment">{perm === 'team_comment' && label ? label : '팀 내부 · 코멘트 가능'}</option>
          <option value="team_view">팀 내부 · 보기만</option>
        </select>
        <button type="button" className="pr-mini" style={{ height: 34 }} disabled={busy} onClick={() => void copy()} data-testid="pr7c-share"><Icon name="link" size={13} />링크 복사</button>
      </div>
    </div>
  );
}

function AddReviewer({ id, existing, onAdded }: { id: string; existing: string[]; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const uq = useUsers(q, open);
  const add = async (uid: string) => {
    try { await requestReview(id, { reviewer_ids: [...existing, uid] }); toast('검토자를 추가했어요'); setOpen(false); onAdded(); } catch (e) { toast(errText(e)); }
  };
  return (
    <div className="pr-filter">
      <button type="button" className="pr-link" style={{ fontSize: 12.5, height: 'auto', border: 'none', padding: 0 }} onClick={() => setOpen((o) => !o)} aria-expanded={open}><Icon name="plus" size={12} strokeWidth={2.6} />추가</button>
      {open && (
        <div className="pr-menu" style={{ minWidth: 220, top: 26 }}>
          <input className="pr-input pr-input--white" style={{ height: 32, fontSize: 12.5 }} placeholder="이름 검색" value={q} onChange={(e) => setQ(e.target.value)} autoFocus aria-label="검토자 검색" />
          {(uq.data ?? []).filter((u) => !existing.includes(u.id)).slice(0, 8).map((u) => <button key={u.id} type="button" onClick={() => void add(u.id)}>{u.name}<span className="pr-note"> · {u.role || u.org || u.username}</span></button>)}
          {uq.data && uq.data.filter((u) => !existing.includes(u.id)).length === 0 && <span className="pr-note" style={{ padding: '6px 10px' }}>추가할 사람이 없어요</span>}
        </div>
      )}
    </div>
  );
}

/** 검토 요청 작성(검토자 · 마감 · 메시지) — 바뀐 내용이 있으면 서버가 버전을 먼저 저장하고 그 버전으로 요청 */
function RequestComposer({ id, onSent }: { id: string; onSent: () => void }) {
  const [q, setQ] = useState('');
  const uq = useUsers(q);
  const [picked, setPicked] = useState<Array<{ id: string; name: string }>>([]);
  const [due, setDue] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const me = useMe();
  const sendReq = async () => {
    setBusy(true);
    try { await requestReview(id, { reviewer_ids: picked.map((x) => x.id), due_date: /^\d{4}-\d{2}-\d{2}$/.test(due) ? due : null, message: msg.trim() || null }); toast('검토 요청을 보냈어요'); onSent(); }
    catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };
  const cands = (uq.data ?? []).filter((u) => u.id !== me.data?.user_id && !picked.some((x) => x.id === u.id));
  return (
    <div className="pr-colflex" style={{ gap: 12 }} data-testid="pr7c-compose">
      <div className="pr-colflex" style={{ gap: 4 }}>
        <b style={{ fontSize: 15 }}>검토 요청</b>
        <span className="pr-note" style={{ fontSize: 12 }}>검토자에게 지금 버전을 보내요. 바뀐 내용이 있으면 새 버전으로 저장한 뒤 보내요.</span>
      </div>
      <div className="pr-field">
        <label htmlFor="pr7c-who">검토자</label>
        <input id="pr7c-who" className="pr-input pr-input--white" placeholder="@ 이름으로 찾기" value={q} onChange={(e) => setQ(e.target.value.replace(/^@/, ''))} />
        {picked.length > 0 && <div className="pr-row pr-row--wrap" style={{ gap: 4 }}>{picked.map((x) => <span key={x.id} className="pr-chip pr-chip--brand">{x.name}<button type="button" className="pr-chip__x" aria-label={`${x.name} 빼기`} onClick={() => setPicked((ps) => ps.filter((y) => y.id !== x.id))}><Icon name="x" size={10} /></button></span>)}</div>}
        <div className="pr-colflex" style={{ gap: 0, maxHeight: 160, overflowY: 'auto' }}>
          {cands.slice(0, 6).map((u) => <button key={u.id} type="button" className="pr-userpick" onClick={() => setPicked((ps) => [...ps, { id: u.id, name: u.name }])}><span className="pr-avatar pr-avatar--xs">{u.name.slice(0, 1)}</span>{u.name}<span className="pr-note">{u.role || u.org}</span></button>)}
          {uq.data && cands.length === 0 && <span className="pr-note" style={{ padding: '4px 0' }}>고를 수 있는 사람이 없어요</span>}
        </div>
      </div>
      <div className="pr-field"><label htmlFor="pr7c-due">마감</label><input id="pr7c-due" type="date" className="pr-input pr-input--white" value={due} onChange={(e) => setDue(e.target.value)} /></div>
      <div className="pr-field"><label htmlFor="pr7c-msg">메시지</label><textarea id="pr7c-msg" className="pr-textarea" style={{ borderColor: 'var(--wm-line)', boxShadow: 'none' }} rows={3} placeholder="예) 1차 제출본입니다. Why Samsung 수치 위주로 봐주세요." value={msg} onChange={(e) => setMsg(e.target.value)} /></div>
      <button type="button" className="pr-btn pr-btn--primary" disabled={!picked.length || busy} onClick={() => void sendReq()} data-testid="pr7c-send">{busy ? <SpinIcon color="currentColor" /> : null}검토 요청 보내기</button>
    </div>
  );
}
