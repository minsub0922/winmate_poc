/** MI3R — 부분 재분석 · 대화형 수정 `/mi/:id/revise?rev=` · 새 요청 `?scope=area&area=competitor&text=` (§4.13) */
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/ui';
import {
  addRound, applyRevision, discardRevision, errText, patchChange, qk, revertAll, startRevision, startRun, useAnalysis, useResult, useRevision,
  type Area, type Change, type CompareTable, type ResultView, type RevisionScope,
} from '../api';
import { AREA_NAME } from '../lib';
import { TabBody } from '../blocks';
import {
  Agent, BigButton, CompareGrid, Dock, ErrorBand, Ic, LoadingCard, MiPage, P, Pill, PromptInput, ResultTabs, SecButton, Spin, UserBubble, useAid, useMiShell,
} from '../parts';

type ScopeKey = 'area' | 'rows' | 'strengths';

export function RevisePage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [sp, setSp] = useSearchParams();
  const rev = sp.get('rev');
  const a = useAnalysis(aid);
  useMiShell(a.data, 3);
  const [poll, setPoll] = useState<number | false>(false);
  const rv = useRevision(aid, rev, poll);
  const view = rv.data;
  const status = view?.revision.status;
  useEffect(() => { setPoll(rev && (!view || status === 'running') ? 1500 : false); }, [rev, view, status]);
  const base = useResult(aid, {});
  const initArea = (sp.get('area') as Area | null) ?? ((view?.revision.scope.area as Area | undefined) ?? 'competitor');
  const [tab, setTab] = useState<Area>(initArea);
  useEffect(() => { if (view?.revision.scope.area) setTab(view.revision.scope.area as Area); }, [view?.revision.scope.area]);
  const [scopeKey, setScopeKey] = useState<ScopeKey>('area');
  const [rows, setRows] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  const r: ResultView | undefined = (view?.preview as ResultView | null | undefined) ?? base.data;
  const changes = view?.changes ?? [];
  const live = changes.filter((c) => !c.reverted);
  const reverted = changes.filter((c) => c.reverted);
  const running = !!rev && (!view || status === 'running');
  const scopeOf = (k: ScopeKey): RevisionScope => (k === 'rows' ? { kind: 'rows', ids: rows } : k === 'strengths' ? { kind: 'strengths' } : { kind: 'area', area: tab });

  // `?text=` 로 들어오면(후속 질문 · 업종 칩) 바로 요청
  useEffect(() => {
    const text = sp.get('text');
    if (rev || !aid || !text || pending) return;
    void request(text);
  }, [aid]); // eslint-disable-line react-hooks/exhaustive-deps

  async function request(text: string) {
    if (!aid) return;
    setPending(text);
    try {
      if (rev && view && status !== 'discarded' && status !== 'applied') {
        await addRound(aid, rev, text, scopeOf(scopeKey));
        void qc.invalidateQueries({ queryKey: qk.revision(aid, rev) });
        setPoll(1500);
      } else {
        const out = await startRevision(aid, scopeOf(scopeKey), text);
        const next = new URLSearchParams(sp);
        next.set('rev', out.revision_id);
        next.delete('text');
        setSp(next, { replace: true });
      }
    } catch (e) { toast(errText(e)); } finally { setPending(null); }
  }

  async function toggle(c: Change, reverted: boolean) {
    if (!aid || !rev) return;
    try {
      await patchChange(aid, rev, c.id, reverted);
      await qc.invalidateQueries({ queryKey: qk.revision(aid, rev) });
    } catch (e) { toast(errText(e)); }
  }

  async function doAll(kind: 'revert' | 'discard' | 'apply' | 'full') {
    if (!aid) return;
    setBusy(kind);
    try {
      if (kind === 'full') { await startRun(aid, { mode: 'full' }); nav(`/mi/${aid}/run`); return; }
      if (!rev) { nav(`/mi/${aid}/result?tab=${tab}`); return; }
      if (kind === 'revert') { await revertAll(aid, rev); await qc.invalidateQueries({ queryKey: qk.revision(aid, rev) }); return; }
      if (kind === 'discard') { await discardRevision(aid, rev); nav(`/mi/${aid}/result?tab=${tab}`); return; }
      await applyRevision(aid, rev);
      void qc.invalidateQueries({ queryKey: ['mi'] });
      nav(`/mi/${aid}/result?tab=${view?.revision.scope.area ?? tab}`);
    } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  }

  const rounds = (view?.revision.rounds ?? []) as Array<{ instruction?: string; scope?: RevisionScope }>;
  const scopeName = (sc?: RevisionScope | null) => (!sc ? '' : sc.kind === 'area' ? `${sc.area === 'competitor' ? '경쟁사' : AREA_NAME[sc.area as Area] ?? ''} 탭`
    : sc.kind === 'rows' ? `선택한 행 ${sc.ids?.length ?? 0}` : sc.kind === 'strengths' ? '강점 문장만' : '선택한 주장');
  const quick = view?.quick_suggestions ?? ['더 간결하게'];
  const tabArea = view?.revision.scope.area as Area | undefined;
  const chips = Object.entries(view?.chips ?? {}).filter(([, n]) => n > 0);
  const label = (k: string) => ({ row_add: '행 추가', value_edit: '값 수정', strength_edit: '강점 수정', row_remove: '행 삭제', text_edit: '문장 수정', source_add: '출처 추가' }[k] ?? k);

  return (
    <MiPage dock={
      <Dock title={<span className="mi-row" style={{ gap: 8 }}><span>다시 분석할 범위</span>
        <span className="mi-row" role="radiogroup" aria-label="다시 분석할 범위" style={{ gap: 6 }}>
          {([['area', `${tab === 'competitor' ? '경쟁사' : AREA_NAME[tab]} 탭`], ['rows', `선택한 행 ${rows.length}`], ['strengths', '강점 문장만']] as Array<[ScopeKey, string]>).map(([k, l]) => (
            <button key={k} type="button" role="radio" aria-checked={scopeKey === k} className="mi-pill" disabled={k === 'rows' && !rows.length}
              onClick={() => setScopeKey(k)}>{l}</button>
          ))}
        </span></span>}
        right={quick.map((q) => <Pill key={q} onClick={() => void request(q)} disabled={running}>{q}</Pill>)}
        row={
          <div className="mi-dock__row">
            <PromptInput label="수정 요청" placeholder="이어서 수정 요청 (예: 경쟁사 B 정책은 출처 찾아서 채워줘)" onSend={request} busy={!!pending || running} />
            <SecButton onClick={() => void doAll('discard')} disabled={!!busy}>적용 안 함</SecButton>
            <BigButton onClick={() => void doAll('apply')} busy={busy === 'apply'} disabled={!rev || running || !live.length || status !== 'proposed'}
              reason={!live.length ? '적용할 변경이 없어요' : undefined} arrow={false} icon={<Ic d={P.check} size={16} w={2.4} />} testId="mi3r-apply">
              변경 {live.length}건 적용
            </BigButton>
          </div>
        } />
    }>
      {rounds.length > 0
        ? rounds.map((x, i) => <UserBubble key={i}><b>{scopeName(x.scope ?? view?.revision.scope)}</b>{x.instruction ? ` · ${x.instruction}` : ''}</UserBubble>)
        : pending && <UserBubble><b>{scopeName(scopeOf(scopeKey))}</b> · {pending}</UserBubble>}
      <Agent text={running ? '다시 분석하고 있어요. 범위 밖 탭과 행은 그대로 둡니다.' : view?.agent_text ?? '다시 분석할 범위를 고르고 무엇을 고칠지 알려 주세요. 결과는 바로 바꾸지 않고 변경 안으로 보여 드려요.'}>
        {(rv.isError || base.isError) && <ErrorBand onRetry={() => { void rv.refetch(); void base.refetch(); }} />}
        {status === 'failed' && <ErrorBand message={(view?.revision.error as { message?: string } | null)?.message || '다시 분석하지 못했어요'} />}
        {!r && <LoadingCard lines={6} />}
        {r && (
          <div className="mi-card" data-testid="mi3r-card">
            <ResultTabs tabs={r.tabs} value={tab} onChange={setTab} revArea={tabArea ?? null} />
            <div className="mi-tabbody">
              {rev && (
                <div className="mi-revsum" data-testid="mi3r-summary">
                  <Ic d={P.refresh} size={15} className="mi-brand" />
                  <span className="mi-revsum__n">바뀐 곳 {view?.changed_count ?? 0}</span>
                  {chips.map(([k, n]) => <span key={k} className="mi-revchip">{label(k)} {n}</span>)}
                  {!running && <span className="mi-note">· 출처 +{view?.sources_added ?? 0} · {view?.duration_s ?? 0}초</span>}
                  <span className="mi-grow" />
                  <button type="button" className="mi-mini" onClick={() => void doAll('full')} disabled={!!busy}>전체 다시 분석</button>
                  <button type="button" className="mi-mini" onClick={() => void doAll('revert')} disabled={!!busy || !live.length}><Ic d={P.undo} size={12} w={2.2} />전부 되돌리기</button>
                </div>
              )}
              {running && <div className="mi-wait" data-testid="mi3r-wait"><Spin size={16} />다시 분석하는 중 · 약 {view?.eta_s ?? 20}초</div>}
              {!running && tab === 'competitor' && r.competitor?.table && (
                <CompetitorWithChanges table={r.competitor.table} changes={changes} onToggle={toggle} rows={rows} setRows={setRows} />
              )}
              {!running && tab === 'competitor' && r.competitor && <StrengthChanges r={r} changes={live} onToggle={toggle} />}
              {!running && tab !== 'competitor' && <TabBody r={r} area={tab} />}
              {!running && (tab === tabArea || view?.revision.scope.kind === 'claims') && <TextChanges changes={live.filter((c) => c.kind === 'text_edit')} onToggle={toggle} />}
              {!running && reverted.length > 0 && (
                <div className="mi-note" data-testid="mi3r-reverted">되돌린 변경 {reverted.length}건 ·{' '}
                  {reverted.map((c) => <button key={c.id} type="button" className="mi-link mi-link--under" onClick={() => void toggle(c, false)}>{label(c.kind)} 다시 적용</button>)}
                </div>
              )}
              {view?.footer && (
                <div className="mi-footer">
                  <span className="mi-ell" data-testid="mi3r-footer">{view.footer}</span>
                  <button type="button" className="mi-mini" onClick={() => nav(`/mi/${aid}/result?tab=${tab}&panel=sources`)}>출처 보기</button>
                </div>
              )}
            </div>
          </div>
        )}
      </Agent>
    </MiPage>
  );
}

/** 비교표 + 변경 표시 — 수정 칸(새 값 + 옛 값 취소선 + 되돌리기) · 추가 행(추가 · 빼기) · 행 앞 체크(선택한 행) */
function CompetitorWithChanges({ table, changes, onToggle, rows, setRows }:
  { table: CompareTable; changes: Change[]; onToggle: (c: Change, reverted: boolean) => void; rows: string[]; setRows: (r: string[]) => void }) {
  const live = changes.filter((c) => !c.reverted);
  const added = new Map(live.filter((c) => c.kind === 'row_add').map((c) => [String((c.target as { criterion_id?: string }).criterion_id), c]));
  const edits = new Map(live.filter((c) => c.kind === 'value_edit' && (c.target as { crt?: string }).crt)
    .map((c) => [`${(c.target as { crt: string }).crt}:${(c.target as { col: string }).col}`, c]));
  const removedRows = live.filter((c) => c.kind === 'row_remove' && (c.target as { criterion_id?: string }).criterion_id);
  const removedCols = live.filter((c) => c.kind === 'row_remove' && (c.target as { column?: string }).column);
  const editRow = (crt: string) => [...edits.values()].find((c) => (c.target as { crt: string }).crt === crt);
  const toggleRow = (crt: string) => setRows(rows.includes(crt) ? rows.filter((x) => x !== crt) : [...rows, crt]);
  return (
    <>
      <CompareGrid table={table}
        renderRowHead={(row) => {
          const add = added.get(row.criterion_id);
          const ed = editRow(row.criterion_id);
          const sel = (
            <label className="mi-cmp__sel"><input type="checkbox" checked={rows.includes(row.criterion_id)} onChange={() => toggleRow(row.criterion_id)}
              aria-label={`${row.name} 행 고르기`} /><span>{row.name}</span></label>
          );
          if (add) {
            return (
              <div role="rowheader" className="mi-cmp__rowhead--added" key={`h-${row.criterion_id}`}>
                <span style={{ fontWeight: 600 }}>{sel}</span>
                <span className="mi-chg-line"><span className="mi-chg">추가</span><button type="button" className="mi-link mi-link--under" onClick={() => onToggle(add, true)}>빼기</button></span>
              </div>
            );
          }
          if (ed) {
            return (
              <div role="rowheader" className="mi-cmp__rowhead--edited" key={`h-${row.criterion_id}`}>
                {sel}
                <span className="mi-chg-line"><span className="mi-chg">수정</span><button type="button" className="mi-link mi-link--under" onClick={() => onToggle(ed, true)}>되돌리기</button></span>
              </div>
            );
          }
          return <div role="rowheader" key={`h-${row.criterion_id}`}>{sel}</div>;
        }}
        renderCell={(row, col) => {
          const ed = edits.get(`${row.criterion_id}:${col.key}`);
          const cell = row.cells[col.key];
          if (ed) {
            return (
              <div key={col.key} role="cell" className="mi-cmp__cell--edited" data-changed="value_edit">
                <span style={{ fontWeight: 600 }}>{cell?.text ?? String(ed.after ?? '')}</span>
                <span className="mi-before">{String(ed.before ?? '')}</span>
              </div>
            );
          }
          if (added.has(row.criterion_id)) {
            return <div key={col.key} role="cell" className={col.samsung ? 'mi-cmp__cell--edited' : 'mi-cmp__cell--added'} data-changed="row_add">{cell?.text ?? '[확인 필요]'}</div>;
          }
          return undefined;
        }} />
      {(removedRows.length > 0 || removedCols.length > 0) && (
        <div className="mi-textchg" data-testid="mi3r-removed">
          {[...removedRows, ...removedCols].map((c) => (
            <div key={c.id} className="mi-row" style={{ gap: 8 }}>
              <span className="mi-chg">빼기</span>
              <span className="mi-before" style={{ fontSize: 12.5 }}>{(c.before as { name?: string; label?: string } | null)?.name ?? (c.before as { label?: string } | null)?.label ?? ''}</span>
              <span className="mi-grow" />
              <button type="button" className="mi-link mi-link--under" onClick={() => onToggle(c, true)}>되돌리기</button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function StrengthChanges({ r, changes, onToggle }: { r: ResultView; changes: Change[]; onToggle: (c: Change, reverted: boolean) => void }) {
  const edits = changes.filter((c) => c.kind === 'strength_edit');
  const ids = new Set(edits.map((c) => String((c.target as { strength_id?: string }).strength_id)));
  const rest = (r.competitor?.strengths ?? []).filter((s) => !ids.has(s.id));
  return (
    <div className="mi-block">
      <div className="mi-strengths__title">도출된 삼성 강점 {r.competitor?.strengths.length ?? 0}</div>
      {edits.map((c) => {
        const after = (c.after ?? {}) as { title?: string; note?: string };
        return (
          <div key={c.id} className="mi-strength-chg" data-changed="strength_edit">
            <span className="mi-chg">수정</span>
            <span className="mi-strength-chg__text"><b>강점 · {after.title}</b> — {after.note}</span>
            <button type="button" className="mi-mini mi-mini--ghost" onClick={() => onToggle(c, true)}>되돌리기</button>
          </div>
        );
      })}
      {rest.length > 0 && (
        <div className="mi-strengths">
          {rest.map((s) => <div key={s.id} className="mi-strength"><b>{s.title}</b> — {s.note}</div>)}
        </div>
      )}
    </div>
  );
}

function TextChanges({ changes, onToggle }: { changes: Change[]; onToggle: (c: Change, reverted: boolean) => void }) {
  if (!changes.length) return null;
  return (
    <div className="mi-block">
      {changes.map((c) => (
        <div key={c.id} className="mi-textchg" data-changed="text_edit">
          <div className="mi-row"><span className="mi-chg">수정</span><span className="mi-grow">{String(c.after ?? '')}</span>
            <button type="button" className="mi-mini mi-mini--ghost" onClick={() => onToggle(c, true)}>되돌리기</button></div>
          <span className="mi-before">{String(c.before ?? '')}</span>
        </div>
      ))}
    </div>
  );
}
