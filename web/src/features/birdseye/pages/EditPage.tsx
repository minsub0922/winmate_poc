/** BE4E — 배치 직접 수정(`/birdseye/:id/layout/edit`, §4.8): 편집 도구 3 · 표시 4 · 변경 수 · 되돌리기 · 경고 카드 · 자동 조정 · 말로 수정. */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, toast } from '@/ui';
import { useJob } from '@/api/jobs';
import { be, errText, qk, useBe, type LayoutWarning, type Op, type SessionView } from '../api';
import { PlanCanvas, type Tool } from '../PlanCanvas';
import { Agent, BePage, Dock, Loading, MainButton, PromptBar, SubButton, useBeShell } from '../ui';

const W_EDIT = '직접 수정 모드입니다. 제품과 가구를 끌어서 옮기면 시야각 · 동선 · 전원 위치를 바로 다시 확인하고, 문제가 생긴 곳을 번호로 표시합니다.';

export default function EditPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const [view, setView] = useState<SessionView | null>(null);
  const [tool, setTool] = useState<Tool>('move');
  const [show, setShow] = useState({ fans: true, paths: true, power: true, dims: false });
  const [pick, setPick] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const started = useRef(false);
  useBeShell(bq.data, 4);

  const reload = async (sid: string) => setView(await be.session(sid));
  useJob(job, { onDone: () => { setJob(null); if (view) void reload(view.session_id); } });

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const s = await be.newSession(id);
        let v = await be.session(s.session_id);
        const mv = sp.get('move');
        if (mv) {
          const [target, dx, dy] = mv.split(':');
          v = await be.sessionOps(s.session_id, { ops: [{ op: 'move', item: target, dx: Number(dx), dy: Number(dy) }] });
        }
        setView(v);
      } catch (e) { setErr(errText(e)); }
    })();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return <BePage><Agent text={err} /></BePage>;
  if (!view || bq.isLoading) return <Loading />;
  const sid = view.session_id;
  const ops = async (o: Op[]) => { try { setView(await be.sessionOps(sid, { ops: o })); } catch (e) { toast(errText(e)); } };
  const undo = async () => { try { setView(await be.sessionOps(sid, { undo: true })); } catch (e) { toast(errText(e)); } };
  const redo = async () => { try { setView(await be.sessionOps(sid, { redo: true })); } catch (e) { toast(errText(e)); } };
  const act = async (w: LayoutWarning, action: 'fix' | 'ignore' | 'memo' | 'add_power', extra: { fix_id?: string; pos?: number[] } = {}) => {
    try { setView(await be.warning(sid, w.id, { action, fix_id: extra.fix_id ?? null, pos: extra.pos ?? null })); } catch (e) { toast(errText(e)); }
  };
  const autofix = async () => { try { setView(await be.autofix(sid)); } catch (e) { toast(errText(e)); } };
  const cancel = async () => { try { await be.discard(sid); } catch { /* 이미 닫힘 */ } nav(`/birdseye/${id}/layout`); };
  const apply = async () => {
    setBusy(true);
    try {
      await be.commit(sid);
      await Promise.all([qc.invalidateQueries({ queryKey: qk.layout(id) }), qc.invalidateQueries({ queryKey: qk.one(id) })]);
      nav(`/birdseye/${id}/layout`);
    } catch (e) { toast(errText(e)); setBusy(false); }
  };

  const open = view.warnings.filter((w) => w.status === 'open');
  const shown = view.warnings.filter((w) => w.status === 'open' || w.status === 'memo' || w.status === 'fixed');
  const pickWarn = view.warnings.find((w) => w.id === pick);

  return (
    <BePage testId="be4e" dock={(
      <Dock title="배치 직접 수정" meta={<>경고 {open.length} · 4 / 5</>}
        right={<button type="button" className="be-btn be-btn--sm" onClick={() => void autofix()} disabled={!open.length} data-testid="be4e-autofix">경고 모두 자동 조정</button>}
        foot={(
          <>
            <PromptBar label="말로 수정" placeholder="말로 수정 (예: The Wall을 다시 가운데로, 벤치는 2열로)" busy={!!job} testId="be4e-nl"
              onSend={async (t) => { try { const r = await be.layoutNlEdit(id, t, sid); setJob(r.job_id); } catch (e) { toast(errText(e)); return false; } }} />
            <SubButton onClick={() => void cancel()} testId="be4e-cancel">취소</SubButton>
            <MainButton onClick={apply} busy={busy} testId="be4e-apply">수정 적용</MainButton>
          </>
        )}>
        <div className="be-warns" data-testid="be4e-warnings">
          {!shown.length && <span className="be-muted be-small">경고가 없어요</span>}
          {shown.map((w) => (
            <div key={w.id} className={w.status === 'open' ? 'be-warn' : w.status === 'fixed' ? 'be-warn be-warn--fixed' : 'be-warn be-warn--muted'} data-testid={`be4e-warn-${w.kind}`}
              title={w.tooltip}>
              <span className={w.status === 'open' ? 'be-badge-n' : 'be-badge-n be-badge-n--ok'}>{w.status === 'open' ? w.n : '✓'}</span>
              <div className="be-warn__body">
                <div className="be-warn__title">{w.title_ko}<Icon name="info" size={12} title={w.tooltip} />
                  {w.status !== 'open' && <span className="be-muted be-small">{w.status === 'fixed' ? '조정함' : w.status === 'memo' ? '메모로 남김' : '무시'}</span>}</div>
                <div className="be-warn__msg">{w.message_ko}</div>
              </div>
              {w.status === 'open' && (
                <div className="be-warn__acts">
                  {(w.fixes ?? []).map((f) => <button key={f.id} type="button" className="be-btn be-btn--sm" onClick={() => void act(w, 'fix', { fix_id: f.id })}>{f.label_ko}</button>)}
                  {w.kind === 'power' ? (
                    <>
                      <button type="button" className="be-btn be-btn--sm" aria-pressed={pick === w.id} onClick={() => setPick(pick === w.id ? null : w.id)}>
                        {pick === w.id ? '배치안에서 콘센트 자리 누르기' : '전원 위치 추가'}
                      </button>
                      <button type="button" className="be-btn be-btn--sm" onClick={() => void act(w, 'memo')}>메모로 남기기</button>
                    </>
                  ) : <button type="button" className="be-btn be-btn--sm" onClick={() => void act(w, 'ignore')}>무시</button>}
                </div>
              )}
            </div>
          ))}
        </div>
      </Dock>
    )}>
      <Agent text={W_EDIT}>
        <div className="be-canvas-head" style={{ flexWrap: 'wrap', gap: 8 }}>
          <div className="be-tools">
            <div className="be-seg" role="group" aria-label="편집 도구">
              {([['move', '이동'], ['rotate', '회전'], ['measure', '치수 재기']] as const).map(([k, l]) => (
                <button key={k} type="button" aria-pressed={tool === k} onClick={() => setTool(k)}>{l}</button>
              ))}
            </div>
            <span className="be-sep" />
            <span className="be-flabel">표시</span>
            {([['fans', '시야각'], ['paths', '동선'], ['power', '전원 위치'], ['dims', '치수']] as const).map(([k, l]) => (
              <button key={k} type="button" className={show[k] ? 'be-pill be-pill--on' : 'be-pill'} aria-pressed={show[k]} onClick={() => setShow({ ...show, [k]: !show[k] })}>{l}</button>
            ))}
          </div>
          <div className="be-row">
            <span className="be-small" data-testid="be4e-changes">변경 <b className="wm-num">{view.changes_count}</b> 건</span>
            <button type="button" className="be-btn be-btn--sm" aria-label="되돌리기" disabled={!view.can_undo} onClick={() => void undo()}><Icon name="undo" size={14} /></button>
            <button type="button" className="be-btn be-btn--sm" aria-label="다시 실행" disabled={!view.can_redo} onClick={() => void redo()}><Icon name="refresh" size={14} /></button>
          </div>
        </div>
        {view.plan && (
          <PlanCanvas plan={{ ...view.plan, power_points: view.layout.power_points?.length ? view.layout.power_points : view.plan.power_points }}
            items={view.layout.items} groups={view.layout.groups} width={760} height={360} overlays={view.overlays} show={show}
            warnings={view.warnings} ghosts={view.moves} tool={pickWarn ? null : tool} pickPoint={!!pickWarn} legend="edit" testId="be4e-canvas"
            onMove={(target, dx, dy) => void ops([{ op: 'move', item: target, dx, dy }])}
            onRotate={(target, deg) => void ops([{ op: 'rotate', item: target, deg }])}
            onPick={(x, y) => { if (pickWarn) { void act(pickWarn, 'add_power', { pos: [x, y] }); setPick(null); } }} />
        )}
      </Agent>
    </BePage>
  );
}
