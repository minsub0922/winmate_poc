/** SP3E — 시트 편집(`/spec/:id/edit?session=`, 06-spec §4.12) — 조작은 세션에 쌓이고 `편집 완료` 때 한 번에 반영 */
import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useJob } from '@/api/jobs';
import { Modal, PathIcon, Button, cx, toast } from '@/ui';
import {
  addEditOps, commitEdit, createEditSession, discardEdit, editAction, editMessage, errText, getEditSession, isApiError, useSheet, useSheetCache,
  type EditOp, type EditView,
} from './api';
import { Agent, BigButton, Dock, PromptInput, SpPage, UserBubble, useSpecShell } from './ui';

type ERow = EditView['rows'][number];
const EYE = 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z';
const EYE_OFF = 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z M4 4l16 16';
const STAR = 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3z';
const MEMO = 'M5 4h14v11l-5 5H5z M14 20v-5h5 M8.5 9h7 M8.5 12.5h4';
const AGENT = '편집 모드예요. 행을 끌어 순서를 바꾸고, 오른쪽 아이콘으로 숨기기 · 강조 · 메모를 달 수 있어요. 숨긴 행은 내보낼 때 빠지고, 메모는 각주나 내부 메모로 남길 수 있어요.';

function tagClass(t: string) {
  if (t === '강조') return 'sp-etag--hl';
  if (t === '숨김') return 'sp-etag--hid';
  if (t === '추가됨') return 'sp-etag--add';
  return 'sp-etag--mv';
}

function Grip({ on }: { on: boolean }) {
  return (
    <svg width="9" height="13" viewBox="0 0 10 14" fill={on ? 'var(--wm-brand)' : 'var(--wm-line-dashed)'} aria-hidden="true">
      {[2.5, 7, 11.5].map((y) => [2.5, 7.5].map((x) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.3" />))}
    </svg>
  );
}

function MemoEditor({ row, onSave, onDelete, onClose }:
  { row: ERow; onSave: (text: string, mode: 'footnote' | 'internal') => void; onDelete: () => void; onClose: () => void }) {
  const [text, setText] = useState(row.memo?.text ?? '');
  const [mode, setMode] = useState<'footnote' | 'internal'>((row.memo?.mode as 'footnote' | 'internal') ?? 'footnote');
  const id = `sp-memo-${row.id}`;
  return (
    <div className="sp-ememo" onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}>
      <label htmlFor={id} className="wm-sr-only">{row.label} 메모</label>
      <textarea id={id} value={text} onChange={(e) => setText(e.target.value)} autoFocus />
      <div className="sp-ememo__side">
        <div role="radiogroup" aria-label="메모 표시">
          {([['footnote', '시트에 각주로 표시'], ['internal', '내부 메모만 (내보내지 않음)']] as const).map(([k, label]) => (
            <button key={k} type="button" role="radio" aria-checked={mode === k} className="sp-wc__radio sp-ememo__radio" onClick={() => setMode(k)}>
              <span className="sp-wc__dot" />{label}
            </button>
          ))}
        </div>
        <div className="sp-ememo__btns">
          <button type="button" className="sp-ememo__del" onClick={onDelete} disabled={!row.memo}>삭제</button>
          <button type="button" className="sp-ememo__save" onClick={() => onSave(text.trim(), mode)} disabled={!text.trim()}>메모 저장</button>
        </div>
      </div>
    </div>
  );
}

export default function EditPage() {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const cache = useSheetCache();
  const [v, setV] = useState<EditView | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showHidden, setShowHidden] = useState(true);
  const [memoRow, setMemoRow] = useState<string | null>(null);
  const [colMode, setColMode] = useState(false);
  const [addMenu, setAddMenu] = useState(false);
  const [histOpen, setHistOpen] = useState(false);
  const [drag, setDrag] = useState<{ id: string; over: number | null } | null>(null);
  const [msgJob, setMsgJob] = useState<string | null>(null);
  const [userText, setUserText] = useState<string | null>(null);
  const [reply, setReply] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const started = useRef(false);
  const ses = sp.get('session');

  useSpecShell(s, 3);

  // 세션 열기(새로고침해도 유지 — ?session=)
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        if (ses) {
          try {
            const view = await getEditSession(id, ses);
            if (view.status === 'open') { setV(view); return; }
          } catch (e) { if (!isApiError(e, 'NOT_FOUND')) throw e; }
        }
        const made = await createEditSession(id);
        setV(made.view);
        setSp({ session: made.id }, { replace: true });
      } catch (e) { setErr(errText(e)); }
    })();
  }, [id, ses, setSp]);

  useJob(msgJob, {
    onDone: async (j) => {
      setMsgJob(null);
      const r = (j.result ?? {}) as { reply?: string | null; needs_clarification?: string | null };
      setReply(r.needs_clarification || r.reply || null);
      if (j.status === 'failed') toast(j.error?.message ?? '요청을 처리하지 못했어요.');
      if (v) { try { setV(await getEditSession(id, v.session_id)); } catch (e) { toast(errText(e)); } }
    },
  });

  if (err) return <SpPage><Agent text={`편집을 시작하지 못했어요. ${err}`} /></SpPage>;
  if (!v || !s) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const run = async (ops: EditOp[]) => {
    try { setV(await addEditOps(id, v.session_id, ops)); } catch (e) { toast(errText(e)); }
  };
  const act = async (a: 'undo' | 'redo' | 'reset') => {
    try { setV(await editAction(id, v.session_id, a)); } catch (e) { toast(errText(e)); }
  };
  const send = async (text: string) => {
    setUserText(text);
    setReply(null);
    try { setMsgJob((await editMessage(id, v.session_id, text)).job_id); } catch (e) { toast(errText(e)); }
  };
  const commit = async (rebase = false) => {
    setBusy(true);
    try {
      const saved = await commitEdit(id, v.session_id, rebase);
      cache.put(saved);
      nav(`/spec/${id}`, { replace: true });
    } catch (e) {
      if (isApiError(e, 'VERSION_CONFLICT')) setConflict(true);
      else toast(errText(e));
    } finally { setBusy(false); }
  };
  const cancel = async () => {
    try { await discardEdit(id, v.session_id); } catch { /* 이미 닫힌 세션 */ }
    nav(`/spec/${id}`, { replace: true });
  };

  const rows = v.rows.filter((r) => showHidden || !r.hidden);
  const idx = (rid: string) => v.rows.findIndex((r) => r.id === rid);
  const move = (r: ERow, delta: number) => {
    const to = idx(r.id) + delta;
    if (to < 0 || to >= v.rows.length) return;
    void run([{ op: 'move_row', row_id: r.id, to_index: to }]);
  };
  const onGripKey = (e: KeyboardEvent<HTMLButtonElement>, r: ERow) => {
    if (!e.altKey) return;
    if (e.key === 'ArrowUp') { e.preventDefault(); move(r, -1); }
    if (e.key === 'ArrowDown') { e.preventDefault(); move(r, 1); }
  };
  const onDragOver = (e: DragEvent<HTMLDivElement>, r: ERow) => {
    if (!drag) return;
    e.preventDefault();
    const box = e.currentTarget.getBoundingClientRect();
    const i = idx(r.id) + (e.clientY > box.top + box.height / 2 ? 1 : 0);
    if (drag.over !== i) setDrag({ ...drag, over: i });
  };
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!drag || drag.over === null) { setDrag(null); return; }
    const from = idx(drag.id);
    const to = drag.over > from ? drag.over - 1 : drag.over;
    setDrag(null);
    if (to !== from) void run([{ op: 'move_row', row_id: drag.id, to_index: to }]);
  };
  const moveCol = (pid: string, delta: number) => {
    const i = v.columns.findIndex((c) => c.product_id === pid);
    const to = i + delta;
    if (to < 0 || to >= v.columns.length) return;
    void run([{ op: 'move_column', product_id: pid, to_index: to }]);
  };

  const meta = v.summary_text.replace(/^시트 편집 · /, '');

  return (
    <SpPage
      dock={
        <Dock title="시트 편집" meta={meta}
          right={
            <div className="sp-chiprow" style={{ position: 'relative' }}>
              <button type="button" className="sp-pillbtn" aria-expanded={histOpen} onClick={() => setHistOpen(!histOpen)}>변경 내역</button>
              <button type="button" className="sp-pillbtn" onClick={() => void act('reset')} disabled={!v.summary.total}>모두 되돌리기</button>
              {histOpen && (
                <div className="sp-menu sp-menu--up" role="dialog" aria-label="변경 내역">
                  {v.history.length ? v.history.map((h) => <div key={h.n} className="sp-menu__item">{h.n}. {h.text}</div>)
                    : <div className="sp-menu__item sp-muted">변경 없음</div>}
                  {v.can_undo && <button type="button" onClick={() => void act('undo')}>마지막 변경 되돌리기</button>}
                </div>
              )}
            </div>
          }
          row={
            <>
              <PromptInput label="말로 고치기" placeholder="말로 고치기 (예: 소비전력 행을 맨 아래로, 보증도 강조)" onSend={send} busy={!!msgJob} />
              <button type="button" className="sp-btn2" onClick={() => void cancel()}>취소</button>
              <button type="button" className="sp-bigbtn" onClick={() => void commit()} disabled={busy} aria-busy={busy || undefined}>
                <PathIcon d="M5 12l5 5L20 7" size={16} strokeWidth={2.2} /><span>편집 완료</span>
              </button>
            </>
          }
        />
      }>
      <Agent text={AGENT}>
        <div className="sp-et" data-testid="sp-edit">
          <div className="sp-et__tools">
            <div className="sp-et__left">
              <span className="sp-et__badge"><PathIcon d="M4 20h4L19 9l-4-4L4 16v4z" size={10} strokeWidth={2.6} />편집 중</span>
              <span className="sp-et__title">{v.title}</span>
            </div>
            <div className="sp-et__right">
              <button type="button" className="sp-icbtn sp-icbtn--tool" aria-label="실행 취소" onClick={() => void act('undo')} disabled={!v.can_undo}>
                <PathIcon d="M9 14L4 9l5-5 M4 9h10a6 6 0 0 1 0 12h-3" size={15} />
              </button>
              <button type="button" className="sp-icbtn sp-icbtn--tool" aria-label="다시 실행" onClick={() => void act('redo')} disabled={!v.can_redo}>
                <PathIcon d="M15 14l5-5-5-5 M20 9H10a6 6 0 0 0 0 12h3" size={15} />
              </button>
              <span className="sp-et__sep" />
              <button type="button" role="switch" aria-checked={showHidden} className="sp-et__switch" onClick={() => setShowHidden(!showHidden)}>
                <span>숨긴 행 보기 <span className="sp-numf sp-muted2">{v.hidden_count}</span></span>
                <span className="sp-et__track"><span /></span>
              </button>
              <button type="button" className="sp-minibtn" aria-pressed={colMode} onClick={() => setColMode(!colMode)}>
                <PathIcon d="M7 4L3 8l4 4M3 8h14M17 12l4 4-4 4M21 16H7" size={12} strokeWidth={2.2} />열 순서 바꾸기
              </button>
            </div>
          </div>
          <div className="sp-et__head">
            <span className="sp-et__g" />
            <span className="sp-et__k">항목</span>
            {v.columns.map((c, i) => (
              <span key={c.product_id} className="sp-et__c sp-et__c--head">
                {colMode && <button type="button" className="sp-et__colmv" aria-label={`${c.label} 왼쪽으로`} disabled={i === 0} onClick={() => moveCol(c.product_id, -1)}>‹</button>}
                {c.label}
                {colMode && <button type="button" className="sp-et__colmv" aria-label={`${c.label} 오른쪽으로`} disabled={i === v.columns.length - 1} onClick={() => moveCol(c.product_id, 1)}>›</button>}
              </span>
            ))}
            <span className="sp-et__acts sp-et__acts--head">숨김 · 강조 · 메모</span>
          </div>
          <div onDragLeave={() => drag && setDrag({ ...drag, over: drag.over })}>
            {rows.map((r) => {
              const sel = memoRow === r.id;
              const i = idx(r.id);
              const dropBefore = drag && drag.over === i && drag.id !== r.id;
              return (
                <div key={r.id}>
                  <div className={cx('sp-erow', r.hidden && 'sp-erow--hidden', r.highlighted && 'sp-erow--hl', sel && 'sp-erow--sel', dropBefore && 'sp-erow--drop')}
                    data-testid="sp-erow" data-row={r.label} onDragOver={(e) => onDragOver(e, r)} onDrop={onDrop}>
                    <button type="button" className="sp-et__g sp-grip" aria-label="끌어서 순서 바꾸기" draggable
                      onDragStart={(e) => { e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', r.id); setDrag({ id: r.id, over: null }); }}
                      onDragEnd={() => setDrag(null)} onKeyDown={(e) => onGripKey(e, r)}>
                      <Grip on={!!r.moved || sel || drag?.id === r.id} />
                    </button>
                    <span className="sp-et__k">
                      <span className="sp-erow__name">{r.label}</span>
                      {(r.tags ?? []).map((t) => <span key={t} className={cx('sp-etag', tagClass(t))}>{t}</span>)}
                    </span>
                    {(r.cells ?? []).map((c) => (
                      <span key={c.product_id} className={cx('sp-et__c', !r.hidden && c.win && 'sp-et__c--win', !r.hidden && (c.state === 'pending' || c.state === 'sync_pending') && 'sp-et__c--pend')}
                        title={c.text}>{c.text}</span>
                    ))}
                    <span className="sp-et__acts">
                      <button type="button" className={cx('sp-icbtn', r.hidden && 'sp-icbtn--on')} aria-label={r.hidden ? '다시 보이기' : '숨기기'}
                        onClick={() => void run([{ op: r.hidden ? 'show_row' : 'hide_row', row_id: r.id }])}>
                        <PathIcon d={r.hidden ? EYE_OFF : EYE} size={15} strokeWidth={1.9} />
                      </button>
                      <button type="button" className={cx('sp-icbtn', r.highlighted && 'sp-icbtn--on')} aria-label="강조" aria-pressed={!!r.highlighted}
                        onClick={() => void run([{ op: r.highlighted ? 'unhighlight_row' : 'highlight_row', row_id: r.id }])}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill={r.highlighted ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" aria-hidden="true"><path d={STAR} /></svg>
                      </button>
                      <button type="button" className={cx('sp-icbtn', (r.memo || sel) && 'sp-icbtn--on')} aria-label="메모" aria-expanded={sel}
                        onClick={() => setMemoRow(sel ? null : r.id)}>
                        <PathIcon d={MEMO} size={14} strokeWidth={1.9} />
                      </button>
                    </span>
                  </div>
                  {sel && (
                    <MemoEditor row={r} onClose={() => setMemoRow(null)}
                      onSave={(text, mode) => { setMemoRow(null); void run([{ op: 'set_memo', row_id: r.id, text, mode }]); }}
                      onDelete={() => { setMemoRow(null); void run([{ op: 'delete_memo', row_id: r.id }]); }} />
                  )}
                </div>
              );
            })}
            {drag && drag.over === v.rows.length && <div className="sp-erow--dropend" />}
          </div>
          <div className="sp-et__add">
            <div style={{ position: 'relative' }}>
              <button type="button" className="sp-et__addbtn" aria-expanded={addMenu} onClick={() => setAddMenu(!addMenu)} disabled={!v.addable_rows.length}>
                <PathIcon d="M12 5v14M5 12h14" size={13} strokeWidth={2.4} />항목 추가
              </button>
              {addMenu && (
                <div className="sp-menu sp-menu--up" role="menu" aria-label="추가할 항목">
                  {v.addable_rows.map((a) => (
                    <button key={a.row_key} type="button" role="menuitem" onClick={() => { setAddMenu(false); void run([{ op: 'add_rows', row_keys: [a.row_key] }]); }}>{a.label}</button>
                  ))}
                </div>
              )}
            </div>
            {v.missing_items.length > 0 && <span className="sp-et__miss">빠진 항목</span>}
            {v.missing_items.map((m) => (
              <button key={m.key} type="button" className="sp-et__mchip" onClick={() => void run([{ op: 'add_rows', item_key: m.key }])}>{m.label}</button>
            ))}
            <span style={{ flex: 1 }} />
            <span className="sp-et__count" data-testid="sp-visible">보이는 행 <b className="sp-numf">{v.visible}</b> / {v.total}</span>
          </div>
        </div>
      </Agent>
      {userText && <UserBubble>{userText}</UserBubble>}
      {msgJob && <Agent text="말씀하신 대로 편집에 더하고 있어요…" />}
      {!msgJob && reply && <Agent text={reply} />}
      <Modal open={conflict} onClose={() => setConflict(false)} title="시트가 바뀌었어요" variant="dialog" width={420}
        footer={
          <>
            <Button onClick={() => { setConflict(false); void cancel(); }}>버리기</Button>
            <Button variant="primary" onClick={() => { setConflict(false); void commit(true); }}>다시 얹기</Button>
          </>
        }>
        시트가 바뀌었어요. 최신 시트에 내 편집을 다시 얹을까요?
      </Modal>
    </SpPage>
  );
}
