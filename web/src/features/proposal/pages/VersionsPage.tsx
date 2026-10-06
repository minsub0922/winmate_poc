/**
 * PR7V — 버전 · 변경 이력(§4.23, 보드 PR7V) — `/proposal/:id/versions?a=&b=&sheet=&change=`(`?export=1`).
 * 왼쪽: 이력 타임라인(버전만 · 모든 변경, 버전 카드 A/B/비교 표시, 이벤트 줄) · 「지금 상태를 v{n+1}로 저장」.
 * 오른쪽: A ⇄ B 비교(나란히 · 바뀐 곳만) · 바뀐 시트 탭 · 바뀐 곳 목록(되돌리기) · 이 시트만 vA로 · vA 전체로 되돌리기 · vB로 내보내기.
 */
import { useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, cx, toast, useConfirm } from '@/ui';
import { qk, restoreVersion, revertChange, saveVersion, useCompare, useProposal, useSheet, useSlides, useVersions } from '../api/proposal';
import { errText } from '../api/http';
import type { DiffItem } from '../api/types';
import { ErrorBand, LoadingCard, SpinIcon } from '../components/parts';
import { SlideView, type SlideDoc } from '../components/SlideView';
import { ResultToolbar, useExportParam } from '../components/ResultToolbar';
import { useProposalShell } from '../lib/useProposalShell';
import { ExportModal } from './ExportModal';

const show = (v: unknown) => (v === null || v === undefined ? '' : typeof v === 'string' ? v : typeof v === 'number' ? String(v) : JSON.stringify(v));

export function VersionsPage() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const [all, setAll] = useState(true);
  const vq = useVersions(id, all);
  const vv = vq.data;
  const sq = useSlides(id);
  const sv = sq.data;
  const cur = vv?.current ?? p?.version ?? 0;
  const a = sp.get('a') ? Number(sp.get('a')) : cur > 1 ? cur - 1 : null;
  const b = sp.get('b') ? Number(sp.get('b')) : cur || null;
  const [mode, setMode] = useState<'side' | 'changes'>('side');
  const sheet = sp.get('sheet');
  const cq = useCompare(id, a, b, sheet, mode);
  const cv = cq.data;
  const sheetId = sheet ?? cv?.sheet_id ?? cv?.changed_sheets?.[0]?.sheet_id ?? null;
  const shq = useSheet(id, b === cur ? sheetId ?? undefined : undefined);
  const [busy, setBusy] = useState<string | null>(null);
  const { confirm, dialog } = useConfirm();
  const ex = useExportParam();
  const focusChange = sp.get('change');
  useProposalShell({ p, step: 6 });
  useEffect(() => {
    if (!focusChange) return;
    const t = window.setTimeout(() => document.querySelector(`[data-change="${focusChange}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' }), 400);
    return () => window.clearTimeout(t);
  }, [focusChange, cv]);

  const setAB = (k: 'a' | 'b', n: number) => setSp((c) => {
    const x = new URLSearchParams(c);
    const other = k === 'a' ? b : a;
    if (other === n) return x; // 같은 버전에 A · B 둘 다는 안 됨
    x.set(k, String(n)); x.delete('sheet'); return x;
  });
  const pickSheet = (sid: string) => setSp((c) => { const x = new URLSearchParams(c); x.set('sheet', sid); return x; });
  const refresh = () => { if (id) { void qc.invalidateQueries({ queryKey: qk.p(id) }); } };
  const run = async (tag: string, fn: () => Promise<unknown>, ok?: string) => {
    setBusy(tag);
    try { await fn(); if (ok) toast(ok); refresh(); return true; } catch (e) { toast(errText(e)); return false; } finally { setBusy(null); }
  };

  const changed = cv?.changed_sheets ?? [];
  const diffs = useMemo(() => (cv?.diffs ?? []).filter((d) => !sheetId || d.sheet_id === sheetId), [cv, sheetId]);
  const curSheet = changed.find((s) => s.sheet_id === sheetId);

  if (pq.isError) return <div className="pr-page"><div className="pr-scroll"><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></div></div>;
  if (!p || !id) return <div className="pr-page"><div className="pr-scroll"><div className="pr-col"><LoadingCard /></div></div></div>;

  const boxes = (side: 'a' | 'b') => (
    <>
      {diffs.filter((d) => d.bbox).map((d) => (
        <span key={`${side}-${d.n}`} className={cx('pr-diffbox', side === 'a' && 'pr-diffbox--a')}
          style={{ left: `${(d.bbox!.x ?? 0) * 100}%`, top: `${(d.bbox!.y ?? 0) * 100}%`, width: `${(d.bbox!.w ?? 0.1) * 100}%`, height: `${(d.bbox!.h ?? 0.06) * 100}%` }}>
          <span className="pr-diffbox__n">{d.n}</span>
        </span>
      ))}
    </>
  );
  const sideSlide = (side: 'a' | 'b') => {
    const s = side === 'a' ? cv?.a : cv?.b;
    if (s?.png_url) return <div className="pr-slidebox" style={{ position: 'relative', width: '100%', aspectRatio: '16 / 9' }}><img src={s.png_url} alt="" className="pr-diffpng" />{boxes(side)}</div>;
    // PNG 렌더가 없으면 그 버전의 그 시트 display(CompareSide.display)로 직접 그린다
    if (s?.display && (!s.sheet_id || !sheetId || s.sheet_id === sheetId)) {
      return <SlideView doc={s.display as unknown as SlideDoc} no={curSheet?.sheet_no ?? shq.data?.sheet_no ?? 0} footer={p.title} overlay={boxes(side)} />;
    }
    if (side === 'b' && b === cur && shq.data) {
      return <SlideView doc={(shq.data.display ?? shq.data.content) as SlideDoc} no={shq.data.sheet_no} footer={p.title} overlay={boxes('b')} />;
    }
    return <div className="pr-diffph">{s ? `${s.label} 렌더를 준비하는 중이에요` : '버전을 고르세요'}</div>;
  };

  return (
    <div className="pr-res" data-testid="pr7v">
      <ResultToolbar id={id} tab="versions" fileName={sv?.file_name ?? p.title} pill={vv?.current_label ?? (cur ? `v${cur} · 현재` : null)}
        meta={vv ? vv.header_label || `버전 ${vv.versions.length} · 변경 기록 ${vv.change_count}` : null} openConfirm={sv?.open_confirm} onExport={() => ex.openExport({ version: b })} />
      <div className="pr-resbody">
        <aside className="pr-vleft" data-testid="pr7v-history">
          <div className="pr-row pr-row--between">
            <b style={{ fontSize: 14 }}>버전 · 변경 이력</b>
            <div role="radiogroup" aria-label="이력 보기" className="pr-miniseg">
              <button type="button" role="radio" aria-checked={!all} onClick={() => setAll(false)}>버전만</button>
              <button type="button" role="radio" aria-checked={all} onClick={() => setAll(true)}>모든 변경</button>
            </div>
          </div>
          <span className="pr-note" style={{ fontSize: 12 }}>두 버전에 <b style={{ color: 'var(--wm-text)' }}>A</b> · <b className="pr-brand">B</b>를 붙이면 바로 비교해요.</span>
          <div className="pr-vtimeline">
            {vq.isError ? <ErrorBand message={errText(vq.error)} onRetry={() => void vq.refetch()} /> : !vv ? <LoadingCard lines={5} /> : (
              <>
                {vv.versions.length === 0 && <span className="pr-note">아직 버전이 없어요. PPTX를 만들면 v1이 생겨요.</span>}
                {!!vv.pending_changes?.length && (
                  <div className="pr-vitem">
                    <span className="pr-vdot pr-vdot--pending" />
                    <div className="pr-vcard pr-vcard--pending">
                      <b style={{ fontSize: 12.5 }}>저장 전 변경 {vv.pending_changes.length}</b>
                      {vv.pending_changes.slice(0, 5).map((c) => <div key={c.change_id} className="pr-vchange" data-change={c.change_id}><span className="pr-num">{c.t}</span>{c.text}</div>)}
                    </div>
                  </div>
                )}
                {interleave(vv).map((row) => row.kind === 'event' ? (
                  <div key={`e-${row.at}`} className="pr-vevent"><Icon name="mail" size={12} color="var(--wm-text-subtle)" />{row.text}</div>
                ) : (
                  <div key={`v-${row.v.n}`} className="pr-vitem">
                    <span className={cx('pr-vdot', row.v.current && 'pr-vdot--cur')} />
                    <div className={cx('pr-vcard', (row.v.n === a || row.v.n === b) && 'pr-vcard--sel')} data-testid="pr7v-version">
                      <div className="pr-row" style={{ gap: 6 }}>
                        <b style={{ fontSize: 13 }}>{row.v.label}</b>
                        {row.v.current && <span className="pr-badge pr-badge--soft" style={{ height: 18, fontSize: 10.5 }}>현재</span>}
                        {row.v.derived_label && <span className="pr-badge pr-badge--gray" style={{ height: 18, fontSize: 10.5 }}>{row.v.derived_label}</span>}
                        <span className="pr-grow" />
                        {row.v.n === a ? <button type="button" className="pr-abtag pr-abtag--a" aria-label={`${row.v.label} · A로 비교 중`}>A</button>
                          : row.v.n === b ? <button type="button" className="pr-abtag pr-abtag--b" aria-label={`${row.v.label} · B로 비교 중`}>B</button>
                            : <button type="button" className="pr-abtag pr-abtag--cmp" aria-label={`${row.v.label}와 비교`} onClick={() => setAB(row.v.n < (b ?? 0) ? 'a' : 'b', row.v.n)}>비교</button>}
                      </div>
                      <span className="pr-note" style={{ fontSize: 11.5 }}>{row.v.time_label ? `${row.v.time_label} · ${row.v.author_label}` : row.v.author_label}</span>
                      <b style={{ fontSize: 13 }}>{row.v.desc}</b>
                      {all && (row.v.changes ?? []).map((c) => <div key={c.change_id} className={cx('pr-vchange', focusChange === c.change_id && 'pr-vchange--on')} data-change={c.change_id}><span className="pr-num">{c.t}</span>{c.text}</div>)}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
          <button type="button" className="pr-vsave" disabled={busy === 'save'} onClick={() => void run('save', async () => { const r = await saveVersion(id); void vq.refetch(); setSp((c) => { const x = new URLSearchParams(c); x.set('b', String(r.n)); x.set('a', String(cur)); return x; }); }, '새 버전으로 저장했어요')} data-testid="pr7v-save">
            {busy === 'save' ? <SpinIcon size={13} /> : <Icon name="plus" size={13} strokeWidth={2.4} />}{vv?.next_save_label || `지금 상태를 v${cur + 1}로 저장`}</button>
          <span className="pr-note" style={{ fontSize: 11.5, textAlign: 'center' }}>{vv?.retention_note || '자동 저장 기록은 30일 동안 남아요'}</span>
        </aside>

        <section className="pr-rescenter" style={{ padding: '16px 24px' }} data-testid="pr7v-compare">
          {!a || !b ? <div className="pr-empty">비교할 버전이 아직 없어요. 버전이 두 개 이상이면 A · B를 붙여 비교할 수 있어요.</div> : (
            <>
              <div className="pr-row" style={{ gap: 10 }}>
                <span className="pr-abtag pr-abtag--a" style={{ width: 'auto', padding: '0 7px' }}>A v{a}</span>
                <Icon name="refresh" size={14} color="var(--wm-text-subtle)" />
                <span className="pr-abtag pr-abtag--b" style={{ width: 'auto', padding: '0 7px' }}>B v{b}</span>
                <b style={{ fontSize: 14 }}>비교</b>
                <span className="pr-note">{cv?.header_label || (cv ? `바뀐 시트 ${changed.length} · 바뀐 곳 ${cv.diffs.length}` : '')}</span>
                <span className="pr-grow" />
                <div role="radiogroup" aria-label="비교 방식" className="pr-miniseg pr-miniseg--tabs">
                  <button type="button" role="radio" aria-checked={mode === 'side'} onClick={() => setMode('side')}>나란히</button>
                  <button type="button" role="radio" aria-checked={mode === 'changes'} onClick={() => setMode('changes')}>바뀐 곳만</button>
                </div>
              </div>
              {cq.isError ? <ErrorBand message={errText(cq.error)} onRetry={() => void cq.refetch()} /> : !cv ? <LoadingCard lines={6} /> : (
                <>
                  {changed.length > 0 && (
                    <div role="tablist" aria-label="바뀐 시트" className="pr-difftabs">
                      {changed.map((s) => (
                        <button key={s.sheet_id} type="button" role="tab" aria-selected={s.sheet_id === sheetId} onClick={() => pickSheet(s.sheet_id)}>
                          <b className="pr-num">{String(s.sheet_no).padStart(2, '0')}</b> {s.name}<span className="pr-diffcount">{s.count}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {changed.length === 0 && <div className="pr-band pr-band--muted">두 버전 사이에 바뀐 곳이 없어요.</div>}
                  {mode === 'side' && curSheet && (
                    <div className="pr-diffside">
                      <div className="pr-colflex" style={{ gap: 6, minWidth: 0 }}>
                        <span className="pr-row" style={{ gap: 6 }}><span className="pr-abtag pr-abtag--a" style={{ width: 'auto', padding: '0 6px' }}>A v{a}</span><span className="pr-note pr-ell">{cv.a.meta}</span></span>
                        {sideSlide('a')}
                      </div>
                      <div className="pr-colflex" style={{ gap: 6, minWidth: 0 }}>
                        <span className="pr-row" style={{ gap: 6 }}><span className="pr-abtag pr-abtag--b" style={{ width: 'auto', padding: '0 6px' }}>B v{b}</span><span className="pr-note pr-ell">{cv.b.meta}</span></span>
                        {sideSlide('b')}
                      </div>
                    </div>
                  )}
                  {diffs.length > 0 && (
                    <div className={cx('pr-card', mode === 'changes' && 'pr-difflist--big')} style={{ overflow: 'hidden' }} data-testid="pr7v-diffs">
                      {diffs.map((d) => <DiffRow key={d.n} d={d} on={!!focusChange && d.change_id === focusChange} busy={busy === `rv:${d.change_id}`}
                        onRevert={() => d.change_id && void run(`rv:${d.change_id}`, async () => { await revertChange(id, d.change_id!); void cq.refetch(); void vq.refetch(); }, '되돌렸어요 · 이력에 남겨 두었어요')} />)}
                    </div>
                  )}
                  <div className="pr-row" style={{ gap: 8, paddingTop: 4 }}>
                    <Icon name="info" size={14} color="var(--wm-brand)" />
                    <span className="pr-note pr-grow" style={{ fontSize: 12.5 }}>{cv.footer_note || `되돌려도 v${b}는 이력에 남아요. 언제든 다시 돌아올 수 있어요.`}</span>
                    {sheetId && <button type="button" className="pr-btn pr-btn--h38" disabled={!!busy} onClick={() => void run('sheet', () => restoreVersion(id, a, 'sheet', sheetId), `이 시트를 v${a} 내용으로 바꿨어요`)} data-testid="pr7v-restore-sheet">이 시트만 v{a}로</button>}
                    <button type="button" className="pr-btn pr-btn--h38" disabled={!!busy} data-testid="pr7v-restore-all" onClick={async () => {
                      const ok = await confirm({ title: `v${a} 전체로 되돌릴까요?`, message: `v${a} 내용으로 새 버전을 만들어요. 지금 버전(v${b})은 이력에 남아요.`, confirmLabel: '되돌리기', tone: 'dark' });
                      if (ok) await run('all', async () => { const r = await restoreVersion(id, a, 'all'); void vq.refetch(); if (r.new_version) setSp((c) => { const x = new URLSearchParams(c); x.set('b', String(r.new_version)); return x; }); }, `v${a} 전체로 되돌렸어요`);
                    }}>v{a} 전체로 되돌리기</button>
                    <button type="button" className="pr-btn pr-btn--h38 pr-btn--primary" onClick={() => ex.openExport({ version: b })} data-testid="pr7v-export"><Icon name="download" size={14} strokeWidth={2.2} />v{b}로 내보내기</button>
                  </div>
                </>
              )}
            </>
          )}
        </section>
      </div>
      {dialog}
      {ex.open && <ExportModal proposalId={id} open onClose={ex.closeExport} initialLang={ex.lang} version={ex.version} />}
    </div>
  );
}

type Row = { kind: 'version'; v: NonNullable<ReturnType<typeof useVersions>['data']>['versions'][number] } | { kind: 'event'; at: string; text: string };
/** 버전(최신 먼저) 사이에 이벤트 줄을 시각 순서로 끼운다 */
function interleave(vv: NonNullable<ReturnType<typeof useVersions>['data']>): Row[] {
  const vs = [...vv.versions].sort((x, y) => y.n - x.n);
  const evs = [...(vv.events ?? [])].sort((x, y) => Date.parse(y.at) - Date.parse(x.at));
  const out: Row[] = [];
  let ei = 0;
  for (const v of vs) {
    while (ei < evs.length && Date.parse(evs[ei].at) > Date.parse(v.created_at)) { out.push({ kind: 'event', at: evs[ei].at, text: evs[ei].text }); ei += 1; }
    out.push({ kind: 'version', v });
  }
  while (ei < evs.length) { out.push({ kind: 'event', at: evs[ei].at, text: evs[ei].text }); ei += 1; }
  return out;
}

function DiffRow({ d, on, busy, onRevert }: { d: DiffItem; on: boolean; busy: boolean; onRevert: () => void }) {
  return (
    <div className={cx('pr-diffrow', on && 'pr-diffrow--on')} data-change={d.change_id ?? undefined} data-testid="pr7v-diff">
      <span className="pr-diffno">{d.n}</span>
      <span className="pr-colflex" style={{ gap: 1, width: 120, flexShrink: 0 }}><b style={{ fontSize: 13 }}>{d.where}</b><span className="pr-note" style={{ fontSize: 11.5 }}>{d.kind}</span></span>
      <span className="pr-difffrom">{d.from_swatch && <i className="pr-swatchsm" style={{ background: d.from_swatch }} />}<s>{show(d.from)}</s></span>
      <Icon name="arrowRight" size={13} color="var(--wm-text-muted)" />
      <span className="pr-diffto">{d.to_swatch && <i className="pr-swatchsm" style={{ background: d.to_swatch }} />}{show(d.to)}</span>
      <span className="pr-grow pr-note pr-ell" style={{ fontSize: 12, textAlign: 'right' }}>{d.why}</span>
      {d.revertable !== false && d.change_id && <button type="button" className="pr-mini" aria-label={`${d.where} 변경 되돌리기`} onClick={onRevert} disabled={busy}>{busy ? <SpinIcon size={11} /> : null}되돌리기</button>}
    </div>
  );
}
