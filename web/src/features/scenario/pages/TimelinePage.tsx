/**
 * SC2E · 타임라인 · 페르소나 편집(§4.6) — 시간대 × 역할 격자(비트 카드 끌어 옮기기 · 빈 칸 「+ 장면」 · W 추천 장면 · 시간대 · 역할 추가 · 레인 순서),
 * 되돌리기 · 다시 실행(50단계), 오른쪽 인물 · 페르소나(저장하면 그 레인 문장 다시 다듬기 잡), 장면 나누기 · 같은 시간 합치기 · 빈 시간대 정리 ·
 * 텍스트로 보기, 편집 요청(LLM 타임라인 연산 잡). 모든 편집은 바로 저장(timeline/ops).
 */
import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { cx, Icon } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi, type Beat, type Role, type Slot, type Timeline, type TimelineOp, type TimelineScene } from '../api';
import { qk, useInvalidate, useJobsPulse, useScenario, waitJob } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Ask, Btn, Ico, Loading, NextButton, Note, P, StatusIcon } from '../parts';

const BEAT_MIME = 'application/x-sc-beat';
const LANE_MIME = 'application/x-sc-lane';

type Edit =
  | { kind: 'add'; slotId: string; roleId: string }
  | { kind: 'beat'; beatId: string }
  | { kind: 'slot'; slotId: string }
  | { kind: 'role-add' }
  | null;

export default function TimelinePage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const tlq = useQuery({ queryKey: qk.timeline(id), queryFn: () => scApi.timeline(id), enabled: !!id });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [edit, setEdit] = useState<Edit>(null);
  const [sel, setSel] = useState<string | null>(null); // 선택 장면(장면 나누기)
  const [roleSel, setRoleSel] = useState<string | null>(null);
  const [drag, setDrag] = useState<{ beatId: string; from: string; isNew: boolean } | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const [laneDrag, setLaneDrag] = useState<string | null>(null);
  const [jobNote, setJobNote] = useState<string | null>(null);

  const s = sc.data;
  const t = tlq.data;
  const activeKind = s?.active_job?.kind;
  const skeleton = activeKind === 'skeleton';
  const pulseJob = s?.active_job?.job_id ?? t?.job_id ?? null;
  useJobsPulse([pulseJob], () => { void tlq.refetch(); void inv.sc(id); });
  // 골격 · 편집 요청 · 레인 다듬기가 도는 동안은 2초마다 다시 읽는다(SSE 가 끊겨도)
  useEffect(() => {
    if (!s?.active_job && !(t?.rewriting_role_ids ?? []).length) return;
    const h = window.setInterval(() => { void tlq.refetch(); void inv.sc(id); }, 2_000);
    return () => window.clearInterval(h);
  }, [s?.active_job, t?.rewriting_role_ids]); // eslint-disable-line react-hooks/exhaustive-deps

  useShellPage({ section: SECTION, title: s?.title ?? '', stepper: stepper(2), sidebarGroup: 'scenario' });

  const slots = useMemo(() => [...(t?.slots ?? [])].sort((a, b) => a.ord - b.ord), [t]);
  const roles = useMemo(() => [...(t?.roles ?? [])].sort((a, b) => a.ord - b.ord), [t]);
  const scenes = t?.scenes ?? [];
  const selectedRole = roles.find((r) => r.id === roleSel) ?? roles[0];
  if (sc.isLoading || tlq.isLoading || !s || !t) return <Loading />;

  const apply = async (ops: TimelineOp[]) => {
    setErr(null);
    try { const nt = await scApi.ops(id, ops); qc.setQueryData(qk.timeline(id), nt); return true; } catch (e) { setErr(errMessage(e)); return false; }
  };
  const undo = async () => { try { qc.setQueryData(qk.timeline(id), await scApi.undo(id)); } catch (e) { setErr(errMessage(e)); } };
  const redo = async () => { try { qc.setQueryData(qk.timeline(id), await scApi.redo(id)); } catch (e) { setErr(errMessage(e)); } };
  const cellBeats = (slotId: string, roleId: string) => {
    const out: Array<{ scene: TimelineScene; beat: Beat }> = [];
    for (const x of scenes.filter((y) => y.slot_id === slotId).sort((a, b) => a.ord_in_slot - b.ord_in_slot)) {
      for (const b of x.beats) if (b.role_id === roleId) out.push({ scene: x, beat: b });
    }
    return out;
  };
  const sug = t.suggestions?.scene;
  const sugRoles = t.suggestions?.roles ?? [];

  const onDrop = async (slotId: string, roleId: string, e: DragEvent) => {
    e.preventDefault();
    const raw = e.dataTransfer.getData(BEAT_MIME);
    setOver(null); setDrag(null);
    if (!raw) return;
    const { beatId } = JSON.parse(raw) as { beatId: string };
    await apply([{ op: 'move_beat', beat_id: beatId, to_slot_id: slotId, to_role_id: roleId }]);
  };
  const runJob = async (key: string, start: () => Promise<{ job_id: string }>, note: string) => {
    setBusy(key); setErr(null); setJobNote(note);
    try {
      const acc = await start();
      await inv.sc(id);
      const r = await waitJob(acc.job_id, { timeoutMs: 120_000 });
      if (r.status !== 'succeeded') setErr(r.error?.message ? `편집하지 못했어요 · ${r.error.message}` : '편집하지 못했어요 · 잠시 뒤 다시 시도해 주세요');
    } catch (e) { setErr(errMessage(e)); } finally {
      setBusy(null); setJobNote(null); await tlq.refetch(); await inv.sc(id);
    }
  };
  const next = async () => {
    setBusy('next'); setErr(null);
    try { await scApi.patch(id, { step: 3 }); await inv.sc(id); nav(route.solutions(id)); } catch (e) { setErr(errMessage(e)); setBusy(null); }
  };
  const tooMany = s.notices?.too_many;

  return (
    <section className="sc-screen" data-testid="sc2e">
      <div className="sc-scroll sc-scroll--tight">
        <div className="sc-col sc-col--wide" style={{ gap: 12 }}>
          <div className="sc-w">
            <span className="sc-w__logo" aria-hidden="true">W</span>
            <div className="sc-w__body" style={{ gap: 4 }}>
              <div className="sc-w__text" data-testid="sc2e-w">
                {skeleton ? '골격을 만드는 중이에요. 시간대 · 역할 · 장면이 곧 채워져요.'
                  : <>입력하신 하루를 시간대 × 역할로 나눴어요. 장면을 끌어 옮기거나 빈 칸에 추가하고, 오른쪽에서 인물을 다듬어 주세요.{tooMany ? ` 장면이 ${tooMany}개로 많아요. 같은 시간 장면을 합쳐 보세요.` : ''}</>}
              </div>
              {s.notices?.real_names && <div className="sc-w__note" data-testid="sc2e-realnames"><Icon name="info" size={13} />실제 인물 이름은 역할로 바꿔 썼어요</div>}
              {(jobNote || activeKind === 'timeline_edit') && <div className="sc-w__note"><span className="wm-spinner" aria-hidden="true" />{jobNote ?? '편집 요청을 반영하는 중이에요'}</div>}
            </div>
          </div>
          <div className="sc-tlwrap">
            <div className="sc-board" data-testid="sc2e-board" aria-busy={skeleton || undefined}>
              <div className="sc-board__head">
                <div style={{ fontSize: 13.5, fontWeight: 700 }} data-testid="sc2e-head">
                  타임라인 <span style={{ fontSize: 12, color: 'var(--wm-text-muted)', fontWeight: 500 }}>· 시간대 {slots.length} · 역할 {roles.length} · 장면 {scenes.length}</span>
                </div>
                <div className="sc-row" style={{ gap: 6 }}>
                  <button type="button" className="sc-tbtn sc-tbtn--icon" aria-label="되돌리기" disabled={!t.can_undo} onClick={() => void undo()} data-testid="sc2e-undo"><Ico d={P.undo} size={13} sw={2.2} /></button>
                  <button type="button" className="sc-tbtn sc-tbtn--icon" aria-label="다시 실행" disabled={!t.can_redo} onClick={() => void redo()} data-testid="sc2e-redo"><Ico d={P.redo} size={13} sw={2.2} /></button>
                  <button type="button" className="sc-tbtn" onClick={() => void apply([{ op: 'add_slot', after_slot_id: slots[slots.length - 1]?.id ?? null, label: '새 시간대' }])} data-testid="sc2e-add-slot">
                    <Ico d={P.plus} size={10} sw={2.8} />시간대
                  </button>
                  <button type="button" className="sc-tbtn" onClick={() => setEdit({ kind: 'role-add' })} data-testid="sc2e-add-role"><Ico d={P.plus} size={10} sw={2.8} />역할</button>
                </div>
              </div>
              {skeleton ? (
                <div className="sc-board__wait"><span className="wm-spinner" aria-hidden="true" />골격을 만드는 중이에요</div>
              ) : (
                <div className="sc-grid" style={{ gridTemplateColumns: `108px repeat(${Math.max(1, slots.length)}, minmax(130px, 1fr))`, gridTemplateRows: `52px repeat(${roles.length}, minmax(120px, auto)) 42px` }}
                  role="grid" aria-label="시간대 × 역할">
                  <div className="sc-grid__corner">역할 \ 시간</div>
                  {slots.map((sl) => <SlotHead key={sl.id} sl={sl} editing={edit?.kind === 'slot' && edit.slotId === sl.id || sl.is_new && edit === null && !sl.label}
                    onEdit={() => setEdit({ kind: 'slot', slotId: sl.id })} onDone={() => setEdit(null)}
                    onSave={(patch) => apply([{ op: 'set_slot', slot_id: sl.id, ...patch }])}
                    onRemove={() => apply([{ op: 'remove_slot', slot_id: sl.id }])} />)}
                  {roles.map((r) => (
                    <LaneRow key={r.id} r={r}>
                      <div className={cx('sc-lane', selectedRole?.id === r.id && 'sc-lane--sel', laneDrag === r.id && 'sc-lane--drag')} draggable data-testid="sc2e-lane"
                        onDragStart={(e) => { e.dataTransfer.setData(LANE_MIME, r.id); e.dataTransfer.effectAllowed = 'move'; setLaneDrag(r.id); }}
                        onDragEnd={() => setLaneDrag(null)}
                        onDragOver={(e) => { if (e.dataTransfer.types.includes(LANE_MIME)) e.preventDefault(); }}
                        onDrop={(e) => {
                          const from = e.dataTransfer.getData(LANE_MIME);
                          setLaneDrag(null);
                          if (!from || from === r.id) return;
                          e.preventDefault();
                          const ids = roles.map((x) => x.id).filter((x) => x !== from);
                          ids.splice(ids.indexOf(r.id), 0, from);
                          void apply([{ op: 'reorder_roles', role_ids: ids }]);
                        }}
                        onClick={() => setRoleSel(r.id)} role="rowheader" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') setRoleSel(r.id); }}>
                        <span className="sc-lane__ini">{r.initial}</span>
                        <span className="sc-lane__name">{r.name}</span>
                        <span className="sc-lane__count">장면 {r.scene_count}</span>
                        {(r.rewriting || (t.rewriting_role_ids ?? []).includes(r.id)) && <span className="sc-lane__busy" data-testid="sc2e-lane-busy"><StatusIcon kind="gen" size={11} />문장 다듬는 중</span>}
                      </div>
                      {slots.map((sl) => {
                        const key = `${sl.id}|${r.id}`;
                        const items = cellBeats(sl.id, r.id);
                        const showSug = sug && sug.slot_id === sl.id && sug.role_id === r.id;
                        const isOrigin = drag && drag.from === key;
                        return (
                          <div key={key} className={cx('sc-cell', over === key && 'sc-cell--over', items.length === 0 && !showSug && 'sc-cell--empty')} role="gridcell" data-testid="sc2e-cell"
                            data-slot={sl.label} data-role={r.name}
                            onDragOver={(e) => { if (e.dataTransfer.types.includes(BEAT_MIME)) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; if (over !== key) setOver(key); } }}
                            onDragLeave={(e) => { if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) setOver((o) => (o === key ? null : o)); }}
                            onDrop={(e) => void onDrop(sl.id, r.id, e)}>
                            {items.map(({ scene, beat }) => (
                              isOrigin && drag?.beatId === beat.id ? (
                                <div key={beat.id} className="sc-beat sc-beat--origin">원래 위치</div>
                              ) : edit?.kind === 'beat' && edit.beatId === beat.id ? (
                                <BeatEditor key={beat.id} text={beat.text} place={beat.place} onCancel={() => setEdit(null)}
                                  onSave={async (text, place) => { if (await apply([{ op: 'set_beat', beat_id: beat.id, text, place }])) setEdit(null); }} />
                              ) : (
                                <div key={beat.id} className={cx('sc-beat', sel === scene.id && 'sc-beat--sel', scene.is_new && 'sc-beat--new')} draggable tabIndex={0}
                                  data-testid="sc2e-beat" data-label={beat.label}
                                  onDragStart={(e) => { e.dataTransfer.setData(BEAT_MIME, JSON.stringify({ beatId: beat.id })); e.dataTransfer.effectAllowed = 'move'; window.setTimeout(() => setDrag({ beatId: beat.id, from: key, isNew: scene.is_new }), 0); }}
                                  onDragEnd={() => { setDrag(null); setOver(null); }}
                                  onClick={() => setSel(sel === scene.id ? null : scene.id)} onDoubleClick={() => setEdit({ kind: 'beat', beatId: beat.id })}
                                  onKeyDown={(e) => { if (e.key === 'Enter') setEdit({ kind: 'beat', beatId: beat.id }); if (e.key === 'Delete') void apply([{ op: 'remove_beat', beat_id: beat.id }]); }}
                                  aria-label={`${beat.label} · ${beat.text}`}>
                                  <span className={cx('sc-beat__label', !beat.primary && 'sc-beat__label--pov')}>
                                    {!beat.primary && <Ico d={P.link} size={10} sw={2.4} />}{beat.label}
                                  </span>
                                  <span className="sc-beat__text">{beat.text}</span>
                                  <span style={{ flex: 1 }} />
                                  {beat.place && <span className="sc-beat__place"><Ico d={P.pin} size={10} sw={2.4} /><span className="wm-ellipsis">{beat.place}</span></span>}
                                  <button type="button" className="sc-beat__x" aria-label="장면 카드 지우기" onClick={(e) => { e.stopPropagation(); void apply([{ op: 'remove_beat', beat_id: beat.id }]); }}>
                                    <Icon name="x" size={10} strokeWidth={2.6} />
                                  </button>
                                </div>
                              )
                            ))}
                            {showSug && (
                              <div className="sc-beat sc-beat--sug" data-testid="sc2e-suggestion">
                                <span className="sc-beat__label"><span className="sc-wmini">W</span>추천 장면</span>
                                <span className="sc-beat__text">{sug.text}</span>
                                <span style={{ flex: 1 }} />
                                <span className="sc-row" style={{ gap: 8 }}>
                                  <button type="button" className="sc-link" style={{ fontSize: 11, fontWeight: 700 }} onClick={() => void apply([{ op: 'accept_suggestion' }])} data-testid="sc2e-sug-add">추가</button>
                                  <button type="button" className="sc-link sc-link--muted" style={{ fontSize: 11 }} onClick={() => void apply([{ op: 'dismiss_suggestion' }])} data-testid="sc2e-sug-close">닫기</button>
                                </span>
                              </div>
                            )}
                            {over === key && drag && drag.from !== key && (
                              <div className="sc-beat sc-beat--drop">{drag.isNew ? '새 장면 · 이동 중' : ''}<span>여기에 놓기</span></div>
                            )}
                            {edit?.kind === 'add' && edit.slotId === sl.id && edit.roleId === r.id ? (
                              <BeatEditor text="" place="" onCancel={() => setEdit(null)}
                                onSave={async (text, place) => { if (await apply([{ op: 'add_beat', slot_id: sl.id, role_id: r.id, text, place }])) setEdit(null); }} />
                            ) : items.length === 0 && !showSug && !(over === key) && (
                              <button type="button" className="sc-addbeat" aria-label="장면 추가" onClick={() => setEdit({ kind: 'add', slotId: sl.id, roleId: r.id })} data-testid="sc2e-add-beat">
                                <Ico d={P.plus} size={10} sw={2.8} />장면
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </LaneRow>
                  ))}
                  <div className="sc-grid__foot sc-grid__foot--first">
                    {edit?.kind === 'role-add' ? (
                      <NameInput placeholder="역할 이름" onCancel={() => setEdit(null)} onSave={async (name) => { if (await apply([{ op: 'add_role', name }])) setEdit(null); }} />
                    ) : (
                      <button type="button" className="sc-addbeat" onClick={() => setEdit({ kind: 'role-add' })} data-testid="sc2e-role-add"><Ico d={P.plus} size={10} sw={2.8} />역할 추가</button>
                    )}
                  </div>
                  <div className="sc-grid__foot" style={{ gridColumn: `span ${Math.max(1, slots.length)}` }} data-testid="sc2e-role-sugs">
                    {sugRoles.length > 0 && <span>추천 역할</span>}
                    {sugRoles.map((name) => (
                      <button key={name} type="button" className="sc-rolesug" onClick={() => void apply([{ op: 'add_role', name, suggested: true }])} data-testid="sc2e-role-sug">+ {name}</button>
                    ))}
                    <span style={{ color: 'var(--wm-text-subtle)' }}>· 레인을 끌어 순서를 바꿀 수 있어요</span>
                  </div>
                </div>
              )}
            </div>
            <Personas id={id} roles={roles} selected={selectedRole} onSelect={setRoleSel} onTimeline={(nt) => qc.setQueryData(qk.timeline(id), nt)}
              onError={setErr} onAdd={async (name) => apply([{ op: 'add_role', name }])} refetch={() => tlq.refetch()} />
          </div>
          {err && <Note tone="err" testId="sc2e-err" onClose={() => setErr(null)}>{err}</Note>}
        </div>
      </div>
      <div className="sc-dock">
        <div className="sc-card sc-card--wide" data-testid="sc2e-card">
          <div className="sc-card__head">
            <div className="sc-row" style={{ gap: 8, fontSize: 13, fontWeight: 600 }}>
              <span>타임라인 편집 <span style={{ color: 'var(--wm-text-muted)', fontWeight: 500 }}>· 2 / 4</span></span>
              <span className="sc-row" style={{ gap: 4, fontSize: 12, color: 'var(--wm-text-muted)', fontWeight: 500 }} data-testid="sc2e-changes">
                <Ico d={P.check} size={12} sw={2.6} color="var(--wm-brand)" />변경 {t.changes_count}건 · 자동 저장됨
              </span>
            </div>
            <div className="sc-row" style={{ gap: 6 }}>
              <button type="button" className="sc-pill sc-pill--h30" disabled={!sel} title={!sel ? '나눌 장면 카드를 먼저 고르세요' : undefined}
                onClick={() => void apply([{ op: 'split_scene', scene_id: sel }]).then((ok) => { if (ok) setSel(null); })} data-testid="sc2e-split">장면 나누기</button>
              <button type="button" className="sc-pill sc-pill--h30" onClick={() => void apply([{ op: 'merge_same_time' }])} data-testid="sc2e-merge">같은 시간 장면 합치기</button>
              <button type="button" className="sc-pill sc-pill--h30" onClick={() => void apply([{ op: 'prune_empty_slots' }])} data-testid="sc2e-prune">빈 시간대 정리</button>
              <Link to={`${route.input(id)}?view=text`} className="sc-pill sc-pill--h30" data-testid="sc2e-text">텍스트로 보기</Link>
            </div>
          </div>
          <div className="sc-card__foot" style={{ gap: 10 }}>
            <Ask id="sc2e-ask" label="편집 요청" placeholder="요청 (예: 손님 레인 18:00에 퇴근길 픽업 장면 추가, 점장 장면은 한 문장으로 짧게)" sendLabel="보내기" testId="sc2e-ask"
              disabled={busy === 'nl' || skeleton} busy={busy === 'nl'} onSubmit={(text) => runJob('nl', () => scApi.nlEdit(id, text), '편집 요청을 반영하는 중이에요')} />
            <Btn to={route.input(id)} testId="sc2e-prev">이전</Btn>
            <NextButton onClick={() => void next()} busy={busy === 'next'} disabled={scenes.length === 0 || skeleton} reason="장면을 하나 이상 만들어 주세요" testId="sc2e-next">솔루션 · 제품 입력</NextButton>
          </div>
        </div>
      </div>
    </section>
  );
}

function LaneRow({ children }: { r: Role; children: React.ReactNode }) {
  return <div style={{ display: 'contents' }} role="row">{children}</div>;
}

function SlotHead({ sl, editing, onEdit, onDone, onSave, onRemove }:
  { sl: Slot; editing: boolean; onEdit: () => void; onDone: () => void; onSave: (p: { time?: string | null; label?: string }) => Promise<boolean>; onRemove: () => Promise<boolean> }) {
  const [time, setTime] = useState(sl.time ?? '');
  const [label, setLabel] = useState(sl.label);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { setTime(sl.time ?? ''); setLabel(sl.label); }, [sl.time, sl.label]);
  useEffect(() => { if (editing) ref.current?.focus(); }, [editing]);
  const save = async () => {
    if (label.trim() !== sl.label || (time.trim() || null) !== (sl.time ?? null)) await onSave({ label: label.trim() || sl.label, time: time.trim() || null });
    onDone();
  };
  return (
    <div className={cx('sc-slot', (sl.is_new || editing) && 'sc-slot--new')} role="columnheader" data-testid="sc2e-slot" data-new={sl.is_new || undefined}>
      <span className="sc-row" style={{ justifyContent: 'space-between' }}>
        {editing ? (
          <input className="sc-slot__time-in" value={time} placeholder="00:00" aria-label="시각" onChange={(e) => setTime(e.target.value)} maxLength={5}
            onKeyDown={(e) => { if (e.key === 'Enter') void save(); if (e.key === 'Escape') onDone(); }} />
        ) : <span className="sc-slot__time wm-num">{sl.time ?? '—'}</span>}
        {sl.is_new ? <span className="sc-slot__new">새 시간대</span> : !editing && (
          <button type="button" className="sc-slot__edit" aria-label={`${sl.label} 시간대 고치기`} onClick={onEdit}><Ico d={P.pencil} size={11} sw={2.2} /></button>
        )}
      </span>
      {editing || sl.is_new ? (
        <span className="sc-row" style={{ gap: 3 }}>
          <input ref={ref} className="sc-slot__label-in" value={label} aria-label="시간대 이름" onChange={(e) => setLabel(e.target.value)} onBlur={() => void save()}
            onKeyDown={(e) => { if (e.key === 'Enter') void save(); if (e.key === 'Escape') { setLabel(sl.label); onDone(); } }} />
          {editing && <button type="button" className="sc-slot__edit" aria-label="시간대 지우기" onMouseDown={(e) => e.preventDefault()} onClick={() => void onRemove()}><Ico d={P.trash} size={11} /></button>}
        </span>
      ) : <span className="sc-slot__label">{sl.label}</span>}
    </div>
  );
}

function BeatEditor({ text, place, onSave, onCancel }: { text: string; place: string; onSave: (t: string, p: string) => Promise<void>; onCancel: () => void }) {
  const [t, setT] = useState(text);
  const [p, setP] = useState(place);
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);
  const save = () => { if (t.trim()) void onSave(t.trim(), p.trim()); else onCancel(); };
  return (
    <div className="sc-beat sc-beat--edit" data-testid="sc2e-beat-editor">
      <textarea ref={ref} value={t} placeholder="한 줄 내용" aria-label="장면 내용" maxLength={80} onChange={(e) => setT(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); save(); } if (e.key === 'Escape') onCancel(); }} />
      <input value={p} placeholder="장소" aria-label="장소" maxLength={32} onChange={(e) => setP(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); save(); } if (e.key === 'Escape') onCancel(); }} />
      <span className="sc-row" style={{ gap: 8 }}>
        <button type="button" className="sc-link" style={{ fontSize: 11 }} onClick={save}>저장</button>
        <button type="button" className="sc-link sc-link--muted" style={{ fontSize: 11 }} onClick={onCancel}>취소</button>
      </span>
    </div>
  );
}

function NameInput({ placeholder, onSave, onCancel }: { placeholder: string; onSave: (v: string) => Promise<void>; onCancel: () => void }) {
  const [v, setV] = useState('');
  return (
    <input className="sc-input" style={{ height: 28, fontSize: 12, width: '100%' }} autoFocus value={v} placeholder={placeholder} aria-label={placeholder}
      onChange={(e) => setV(e.target.value)} onBlur={() => (v.trim() ? void onSave(v.trim()) : onCancel())}
      onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing && v.trim()) void onSave(v.trim()); if (e.key === 'Escape') onCancel(); }} />
  );
}

/** 오른쪽 인물 · 페르소나 패널 */
function Personas({ id, roles, selected, onSelect, onTimeline, onError, onAdd, refetch }:
  { id: string; roles: Role[]; selected?: Role; onSelect: (rid: string) => void; onTimeline: (t: Timeline) => void; onError: (m: string) => void;
    onAdd: (name: string) => Promise<boolean>; refetch: () => void }) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');
  const [intro, setIntro] = useState('');
  const [addWant, setAddWant] = useState<'wants' | 'pains' | null>(null);
  useEffect(() => { setName(selected?.name ?? ''); setIntro(selected?.intro ?? ''); }, [selected?.id, selected?.name, selected?.intro]);

  const save = async (body: { name?: string; intro?: string; wants?: string[]; pains?: string[] }) => {
    if (!selected) return;
    try {
      const nt = await scApi.patchRole(id, selected.id, body);
      onTimeline(nt);
      if (nt.job_id) {
        void waitJob(nt.job_id, { timeoutMs: 120_000 }).then(() => refetch());
      }
    } catch (e) { onError(errMessage(e)); }
  };
  const refs = (r: Role) => (r.scene_refs ?? []).map((x) => (x.is_new ? '새 장면' : String(x.no)));
  const refLine = (r: Role) => {
    const xs = refs(r);
    if (!xs.length) return '';
    const nums = xs.filter((x) => x !== '새 장면');
    return [nums.length ? `장면 ${nums.join(' · ')}` : '', ...xs.filter((x) => x === '새 장면')].filter(Boolean).join(' · ');
  };
  return (
    <div className="sc-persona" data-testid="sc2e-personas">
      <div className="sc-board__head">
        <div style={{ fontSize: 13.5, fontWeight: 700 }}>인물 · 페르소나 <span style={{ fontSize: 12, color: 'var(--wm-text-muted)', fontWeight: 500 }} data-testid="sc2e-persona-count">· {roles.length}명</span></div>
        <button type="button" className="sc-tbtn" onClick={() => setAdding(true)} data-testid="sc2e-persona-add"><Ico d={P.plus} size={10} sw={2.8} />추가</button>
      </div>
      <div className="sc-persona__list">
        {roles.map((r) => (
          <button key={r.id} type="button" className={cx('sc-prow', selected?.id === r.id && 'sc-prow--sel')} onClick={() => onSelect(r.id)} data-testid="sc2e-persona">
            <span className="sc-prow__ini">{r.initial}</span>
            <span className="sc-prow__name">{r.name}</span>
            <span className="sc-prow__refs">{refLine(r)}</span>
          </button>
        ))}
        {adding && <div style={{ padding: '4px 4px' }}><NameInput placeholder="역할 이름" onCancel={() => setAdding(false)} onSave={async (v) => { if (await onAdd(v)) setAdding(false); }} /></div>}
      </div>
      {selected && (
        <div className="sc-persona__detail" data-testid="sc2e-persona-detail">
          <div className="sc-pfield">
            <label htmlFor="sc2e-pn">역할 이름</label>
            <input id="sc2e-pn" className="sc-pinput" value={name} onChange={(e) => setName(e.target.value)}
              onBlur={() => { if (name.trim() && name.trim() !== selected.name) void save({ name: name.trim() }); }}
              onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
          </div>
          <div className="sc-pfield">
            <label htmlFor="sc2e-pd">한 줄 소개</label>
            <input id="sc2e-pd" className="sc-pinput" value={intro} onChange={(e) => setIntro(e.target.value)}
              onBlur={() => { if (intro.trim() !== (selected.intro ?? '')) void save({ intro: intro.trim() }); }}
              onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
          </div>
          {(['wants', 'pains'] as const).map((k) => {
            const list = selected[k] ?? [];
            return (
              <div key={k} className="sc-pfield" data-testid={`sc2e-${k}`}>
                <span>{k === 'wants' ? '원하는 것' : '불편한 점'}</span>
                <div className="sc-row sc-wrap" style={{ gap: 6 }}>
                  {list.map((w) => (
                    <span key={w} className={cx('sc-pchip', k === 'pains' && 'sc-pchip--gray')}>
                      {w}
                      <button type="button" className="sc-chip__x" aria-label={`${w} 지우기`} onClick={() => void save({ [k]: list.filter((x) => x !== w) })}><Icon name="x" size={9} strokeWidth={3} /></button>
                    </span>
                  ))}
                  {addWant === k ? (
                    <span style={{ width: 150 }}><NameInput placeholder={k === 'wants' ? '원하는 것' : '불편한 점'} onCancel={() => setAddWant(null)}
                      onSave={async (v) => { setAddWant(null); await save({ [k]: [...list, v] }); }} /></span>
                  ) : (
                    <button type="button" className="sc-pchip__add" aria-label="추가" onClick={() => setAddWant(k)} data-testid={`sc2e-${k}-add`}><Ico d={P.plus} size={10} sw={2.8} /></button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div className="sc-persona__foot"><Ico d="M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 8v5 M12 16v.5" size={13} sw={2.2} color="var(--wm-brand)" /><span className="wm-ellipsis">인물을 바꾸면 그 레인의 장면 문장에 반영돼요</span></div>
    </div>
  );
}
