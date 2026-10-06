/**
 * PRU4 — 섹션 작성 · 원본 대조(개선 · 수정, §4.29) · PRU4B — 흐름 가이드(흐름 차용, §4.30).
 * SectionPage 가 `?view=compare|new_only|guide` 일 때 이 화면을 그린다. `&sheet=<sheetId>` = 섹션 안 시트.
 * 원본 대조: 원본 시트(읽기 전용 · 줄 마커) ↔ 새 시트(제목 · 줄 편집 = PATCH, 줄 추가 · 원본 줄 끌어오기, 되돌리기 = W 초안 값).
 * 흐름 가이드: 이 자리의 역할(원본 내용은 보이지 않음) + 새 시트(원본 내용 0줄) + 수치 플레이스홀더.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, Thumb, cx, toast } from '@/ui';
import { confirmSection, patchSheet, pullLines, qk, useReuseView, useSheet } from '../api/proposal';
import { errText, isApiError } from '../api/http';
import type { Proposal, ReuseLineView } from '../api/types';
import { Dock, ErrorBand, LoadingCard, NextButton, SpinIcon } from '../components/parts';
import { hasPlaceholder } from '../components/SlideView';
import { SECTIONS, TYPES, tplOf, type SectionKey } from '../lib/catalog';
import { R } from '../lib/routes';

type View = 'compare' | 'guide' | 'new_only';
const MARK_LABEL: Record<string, string> = { keep: '유지', update: '갱신', new: '신규', drop: '제외' };

/** content 안에서 줄 id 의 텍스트 경로(JSON pointer) */
function pathOf(content: unknown, lineId: string): string | null {
  const slots = (content as { slots?: Record<string, Record<string, unknown>> } | null)?.slots ?? {};
  for (const [k, s] of Object.entries(slots)) {
    const items = s.items as Array<{ id?: string }> | undefined;
    const i = items?.findIndex((x) => x?.id === lineId) ?? -1;
    if (i >= 0) return `/slots/${k}/items/${i}/text`;
    const rows = s.rows as Array<{ id?: string }> | undefined;
    const j = rows?.findIndex((x) => x?.id === lineId) ?? -1;
    if (j >= 0) return `/slots/${k}/rows/${j}/label`;
    const cols = s.columns as Array<{ items?: Array<{ id?: string }> }> | undefined;
    if (Array.isArray(cols)) {
      for (let c = 0; c < cols.length; c += 1) {
        const ci = cols[c]?.items?.findIndex((x) => x?.id === lineId) ?? -1;
        if (ci >= 0) return `/slots/${k}/columns/${c}/items/${ci}/text`;
      }
    }
  }
  return null;
}
/** 줄을 더할 목록(첫 items 칸) */
function listPath(content: unknown): { path: string; n: number } | null {
  const slots = (content as { slots?: Record<string, Record<string, unknown>> } | null)?.slots ?? {};
  for (const [k, s] of Object.entries(slots)) if (Array.isArray(s.items)) return { path: `/slots/${k}/items`, n: (s.items as unknown[]).length };
  return null;
}
/** 서버 머리 문구가 「표준 1 / 8 · Market Intelligence · 시트 3장 …」이면 앞(단계 · 섹션 이름)은 이미 보이므로 뒤만 */
function headTail(label: string | null | undefined, name: string | undefined) {
  if (!label) return '';
  const i = name ? label.indexOf(name) : -1;
  return i >= 0 ? label.slice(i + name!.length).replace(/^\s*·\s*/, '') : label;
}
const withView = (route: string, view: View) => (route.includes('/sections/') ? `${route}${route.includes('?') ? '&' : '?'}view=${view}` : route);

export function ReuseSectionView({ p, sectionKey, view, keys, prevRoute, nextRoute, onView }:
  { p: Proposal; sectionKey: SectionKey; view: View; keys: SectionKey[]; prevRoute: string; nextRoute: string; onView: (v: View | null) => void }) {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const sheetParam = sp.get('sheet');
  const vq = useReuseView(p.id, sectionKey, sheetParam, view);
  const v = vq.data;
  const sheetId = v?.new_sheet?.sheet_id ?? v?.sheet_id ?? sheetParam ?? null;
  const shq = useSheet(p.id, sheetId ?? undefined);
  const sh = shq.data;
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [pullOpen, setPullOpen] = useState(false);
  useEffect(() => { setDraft({}); setPullOpen(false); }, [sheetId]);
  const borrow = (v?.mode ?? (p.reuse?.mode as string | undefined)) === 'borrow';
  // 흐름 차용 모드는 원본 대조를 서버도 거부(403 BORROW_MODE_CONTENT_HIDDEN) → 흐름 가이드로
  useEffect(() => { if (vq.error && isApiError(vq.error, 'BORROW_MODE_CONTENT_HIDDEN') && view === 'compare') onView('guide'); }, [vq.error, view, onView]);

  const refresh = () => { void vq.refetch(); void qc.invalidateQueries({ queryKey: qk.sub(p.id, 'sheet', sheetId) }); void qc.invalidateQueries({ queryKey: qk.p(p.id) }); };
  const patch = async (ops: Array<{ op: 'set' | 'insert' | 'delete' | 'move'; path: string; value?: unknown }>, reason: string, tag: string) => {
    if (!sheetId) return false;
    setBusy(tag);
    try { const r = await patchSheet(p.id, sheetId, ops, sh?.rev, reason); qc.setQueryData(qk.sub(p.id, 'sheet', sheetId), r.sheet); void vq.refetch(); return true; }
    catch (e) { if (isApiError(e, 'REV_CONFLICT')) { toast('다른 곳에서 바뀌었어요 · 새로 불러왔어요'); refresh(); } else toast(errText(e)); return false; }
    finally { setBusy(null); }
  };
  const saveLine = async (ln: ReuseLineView, text: string) => {
    if (text === ln.text) return;
    // 줄 id = 시트 content 의 JSON 포인터([backend] 3차) — 아니면 내용에서 찾는다
    const path = ln.id.startsWith('/') ? ln.id : sh ? pathOf(sh.content, ln.id) : null;
    if (!path) { toast('이 줄을 고칠 위치를 찾지 못했어요'); return; }
    if (await patch([{ op: 'set', path, value: text }], '원본 대조 줄 수정', `ln:${ln.id}`)) setDraft((d) => { const n = { ...d }; delete n[ln.id]; return n; });
  };
  const saveTitle = async (text: string) => {
    if (!v || text === (v.new_sheet.title ?? '')) return;
    if (await patch([{ op: 'set', path: '/title', value: text }], '시트 제목 수정', 'title')) setDraft((d) => { const n = { ...d }; delete n.__title; return n; });
  };
  const addLine = async () => {
    const lp = sh ? listPath(sh.content) : null;
    if (!lp) { toast('줄을 더할 칸이 없어요'); return; }
    await patch([{ op: 'insert', path: `${lp.path}/${lp.n}`, value: { text: '' } }], '줄 추가', 'add');
  };
  const pull = async (lineIds: string[] | null) => {
    if (!sheetId) return;
    setBusy('pull');
    try { const s = await pullLines(p.id, sheetId, lineIds ? { line_ids: lineIds } : { all: true }); qc.setQueryData(qk.sub(p.id, 'sheet', sheetId), s); void vq.refetch(); setPullOpen(false); toast(lineIds ? '원본 줄을 가져왔어요' : '원본 줄을 모두 가져왔어요'); }
    catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const goNext = async () => {
    setBusy('next');
    try { await confirmSection(p.id, sectionKey); } catch { /* 확정 실패해도 이동 */ } finally { setBusy(null); }
    void qc.invalidateQueries({ queryKey: qk.p(p.id) });
    nav(withView(nextRoute, view));
  };
  const pickSheet = (sid: string) => setSp((c) => { const x = new URLSearchParams(c); x.set('sheet', sid); return x; });

  const T = TYPES[(p.type as keyof typeof TYPES) ?? 'standard'] ?? TYPES.standard;
  const i0 = Math.max(0, keys.indexOf(sectionKey));
  const sheets = (v?.section_sheets ?? []) as Array<Record<string, unknown>>;
  const tally = v?.tally ?? {};
  const srcLines = v?.source_sheet?.lines ?? [];
  const newLines = v?.new_sheet?.lines ?? [];
  const pullable = srcLines.filter((l) => !newLines.some((n) => n.source_line_id === l.id));
  const curStrip = sheets.find((s) => s.selected === true) ?? sheets.find((s) => String(s.sheet_id ?? s.id ?? '') === sheetId);

  const viewSeg = (
    <div role="radiogroup" aria-label="보기" className="pr-miniseg pr-miniseg--tabs">
      <button type="button" role="radio" aria-checked={view === 'compare'} disabled={borrow} aria-disabled={borrow || undefined}
        title={borrow ? (v?.compare_disabled_reason || '흐름 차용 모드에선 원본 내용을 보여주지 않아요') : undefined} onClick={() => !borrow && onView('compare')} data-testid="pru4-view-compare">원본 대조</button>
      <button type="button" role="radio" aria-checked={view === 'new_only'} onClick={() => onView('new_only')} data-testid="pru4-view-new">새 시트만</button>
      <button type="button" role="radio" aria-checked={view === 'guide'} onClick={() => onView('guide')} data-testid="pru4-view-guide">흐름 가이드</button>
    </div>
  );

  const dock = (
    <Dock testId="pru4-dock" title={view === 'guide' ? '흐름 가이드 작성' : '원본 대조 작성'} meta={v?.footer_label?.replace(/^(원본 대조|흐름 가이드) 작성 · /, '') || '4 / 6'}
      right={<span className="pr-row" style={{ gap: 6 }}>
        {view === 'guide'
          ? ([['writing', '작성 중', 'pr-vchip pr-vchip--auto'], ['waiting', '대기', 'pr-vchip pr-vchip--drop'], ['confirm', '확정 필요', 'pr-vchip pr-vchip--update']] as const).map(([k, l, c]) => <span key={k} className={c}>{l} {tally[k] ?? 0}</span>)
          : (['update', 'keep', 'new', 'drop'] as const).map((k) => <span key={k} className={cx('pr-vchip', `pr-vchip--${k}`)}>{MARK_LABEL[k]} {tally[k] ?? 0}줄</span>)}
      </span>}
      hint={view === 'guide' ? `원본${v?.source_label ? ` ${v.source_label.replace(/^원본 · /, '').split(' p.')[0]}` : ''} 내용은 한 줄도 들어가지 않아요. 역할 · 순서만 따르고, 수치는 확정 필요 목록에서 채워요.` : '원본과 다른 곳은 시트에 \'원본 대비\' 노트가 남아요 · 되돌리기 가능'}
      foot={<>
        <Link to={withView(prevRoute, view)} className="pr-btn">이전 섹션</Link>
        {view !== 'guide' && <button type="button" className="pr-btn" disabled={!sheetId || !!busy || !pullable.length} onClick={() => void pull(null)} data-testid="pru4-pull-all">{busy === 'pull' ? <SpinIcon size={13} /> : null}원본 줄 전부 가져오기</button>}
        <NextButton onClick={() => void goNext()} busy={busy === 'next'} testId="pru4-next">{i0 < keys.length - 1 ? '다음 섹션' : '다음: 디자인 템플릿'}</NextButton>
      </>} />
  );

  return (
    <div className="pr-page pr-page--wide" data-testid={view === 'guide' ? 'pru4b' : 'pru4'}>
      <div className="pr-scroll pr-scroll--tight">
        <div className="pr-col pr-col--wide pr-col--gap14">
          <div className="pr-card pr-pru4head">
            <span className="pr-rail__type pr-num">{T.short} {i0 + 1} / {keys.length}</span>
            <b style={{ fontSize: 16 }}>{SECTIONS[sectionKey]?.name ?? sectionKey}</b>
            <span className="pr-note pr-ell" style={{ fontSize: 12.5 }}>{headTail(v?.header_label, SECTIONS[sectionKey]?.name)}</span>
            <span className="pr-grow" />
            {v?.source_label && <span className="pr-note pr-ell" style={{ fontSize: 11.5, maxWidth: 260 }}>{v.source_label}</span>}
            {viewSeg}
          </div>
          {vq.isError && !isApiError(vq.error, 'BORROW_MODE_CONTENT_HIDDEN') ? <ErrorBand message={errText(vq.error)} onRetry={() => void vq.refetch()} /> : !v ? <LoadingCard lines={8} /> : view === 'guide' ? (
            <div className="pr-pru4b">
              <div className="pr-card" style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12 }} data-testid="pru4b-guide">
                <div className="pr-row pr-row--between"><b style={{ fontSize: 13 }}>≡ 흐름 가이드 · 이 자리의 역할</b><span className="pr-note" style={{ fontSize: 11.5 }}>{v.guide_label}</span></div>
                {(v.guide ?? []).map((g) => (
                  <div key={g.no} className="pr-guidestep">
                    <span className={cx('pr-guideno', g.status === 'writing' && 'pr-guideno--on')}>{g.no}</span>
                    <div className="pr-colflex" style={{ gap: 4, minWidth: 0 }}>
                      <span className="pr-row" style={{ gap: 6 }}><b style={{ fontSize: 14 }}>{g.title}</b><span className={g.status === 'writing' ? 'pr-vchip pr-vchip--auto' : 'pr-vchip pr-vchip--drop'}>{g.status_label}</span></span>
                      <div className="pr-guidegrid">
                        <span className="pr-subtle">역할</span><b>{g.role}</b>
                        <span className="pr-subtle">원본에서</span><span className="pr-row" style={{ gap: 6, minWidth: 0 }}><span className="pr-ell pr-muted">{g.from_source}</span><span className="pr-badge pr-badge--gray" style={{ height: 16, fontSize: 9.5 }}>내용 안 가져옴</span></span>
                        <span className="pr-brand" style={{ fontWeight: 600 }}>이번엔</span><span>{g.this_time}</span>
                      </div>
                      {!!g.chips?.length && <span className="pr-row pr-row--wrap" style={{ gap: 4, paddingLeft: 58 }}>{g.chips.map((c) => <span key={c} className={/^R\d/.test(c) ? 'pr-rqchip pr-rqchip--lg' : /플레이스홀더|확정/.test(c) ? 'pr-vchip pr-vchip--update' : 'pr-cftag'}>{c}</span>)}</span>}
                    </div>
                  </div>
                ))}
                {!v.guide?.length && <span className="pr-note">이 섹션의 흐름 가이드가 아직 없어요</span>}
              </div>
              <NewSheetCard v={v} sh={sh} draft={draft} setDraft={setDraft} busy={busy} onTitle={saveTitle} onLine={saveLine} onAdd={addLine} guide p={p} sectionKey={sectionKey} />
            </div>
          ) : (
            <div className={cx('pr-pru4', view === 'new_only' && 'pr-pru4--single')}>
              {view === 'compare' && v.source_sheet && (
                <div className="pr-card pr-srcsheet" data-testid="pru4-source">
                  <div className="pr-cardhead" style={{ height: 40, background: 'var(--wm-surface-2)' }}>
                    <b style={{ fontSize: 13 }}>원본 시트</b><span className="pr-note pr-ell" style={{ fontSize: 12 }}>{v.source_sheet.page_label} {v.source_sheet.title_label ?? ''}</span>
                    <span className="pr-grow" /><span className="pr-badge pr-badge--gray">읽기 전용</span>
                  </div>
                  <div className="pr-colflex" style={{ padding: '12px 14px', gap: 8 }}>
                    <div className="pr-srcthumb">{v.source_sheet.thumb_url ? <img src={v.source_sheet.thumb_url} alt="" /> : <Thumb kind="cards" n={3} />}<span className="pr-note" style={{ position: 'absolute', right: 10, bottom: 6, fontSize: 10.5 }}>{v.source_sheet.kind_label}</span></div>
                    <b style={{ fontSize: 13 }}>{v.source_sheet.title}</b>
                    {srcLines.map((l) => (
                      <div key={l.id} className="pr-row" style={{ gap: 8 }} data-testid="pru4-source-line">
                        <span className={cx('pr-vchip', `pr-vchip--${l.mark === 'drop' ? 'drop' : l.mark}`)} style={{ height: 18, fontSize: 10.5 }}>{MARK_LABEL[l.mark] ?? l.mark}</span>
                        <span className={cx('pr-ell', l.mark === 'drop' && 'pr-strike')} style={{ fontSize: 12.5 }}>{l.text}</span>
                      </div>
                    ))}
                    {v.source_sheet.images_note && <span className="pr-note" style={{ fontSize: 11.5, borderTop: '1px solid var(--wm-line)', paddingTop: 8 }}><Icon name="image" size={11} /> {v.source_sheet.images_note}</span>}
                  </div>
                </div>
              )}
              {view === 'compare' && (
                <div className="pr-connectors" aria-hidden="true">
                  {(srcLines.length ? srcLines : newLines).map((l) => <span key={l.id} className={cx('pr-conn', `pr-conn--${l.mark}`)}>{l.mark === 'drop' ? '×' : l.mark === 'new' ? '+' : '→'}</span>)}
                </div>
              )}
              <NewSheetCard v={v} sh={sh} draft={draft} setDraft={setDraft} busy={busy} onTitle={saveTitle} onLine={saveLine} onAdd={addLine} p={p} sectionKey={sectionKey}
                head={curStrip ? `${curStrip.sheet_no != null ? `${String(curStrip.sheet_no).padStart(2, '0')} ` : ''}${String(curStrip.name ?? curStrip.title ?? '')} · 편집 중` : undefined}
                pullable={pullable} pullOpen={pullOpen} setPullOpen={setPullOpen} onPull={(ids) => void pull(ids)} />
            </div>
          )}
          {sheets.length > 0 && (
            <div className="pr-card pr-secsheets" data-testid="pru4-sheets">
              <span className="pr-colflex" style={{ gap: 2, width: 110, flexShrink: 0 }}><b style={{ fontSize: 13 }}>이 섹션의 시트</b><span className="pr-note" style={{ fontSize: 11.5 }}>{sheets.length}장{v?.source_label && view !== 'guide' ? ` · ${v.source_label.replace(/^원본 · [^p]*/, '원본 ')}` : view === 'guide' ? ' · 흐름 순서' : ''}</span></span>
              {sheets.map((s, i) => {
                const sid = String(s.sheet_id ?? s.id ?? i);
                const on = typeof s.selected === 'boolean' ? s.selected : sid === sheetId;
                const verdict = String(s.verdict ?? s.status ?? '');
                return (
                  <button key={sid} type="button" aria-pressed={on} className={cx('pr-secsheet', on && 'pr-secsheet--on')} onClick={() => pickSheet(sid)}>
                    <span className="pr-secsheet__thumb">{s.thumb_url ? <img src={String(s.thumb_url)} alt="" /> : <Thumb code={s.template_code ? String(s.template_code) : undefined} kind={s.template_code ? tplOf(String(s.template_code)).kind : 'table'} n={3} />}</span>
                    <span className="pr-colflex" style={{ gap: 2, minWidth: 0, alignItems: 'flex-start' }}>
                      <span className="pr-note pr-num" style={{ fontSize: 11 }}>{String(s.page_label ?? (s.sheet_no ? String(s.sheet_no).padStart(2, '0') : ''))}</span>
                      <b className="pr-ell" style={{ fontSize: 13 }}>{String(s.name ?? s.title ?? '')}</b>
                      {s.role ? <span className="pr-note pr-ell" style={{ fontSize: 11 }}>{String(s.role)}</span> : null}
                      <span className={cx('pr-vchip', verdict === 'writing' ? 'pr-vchip--auto' : verdict === 'waiting' ? 'pr-vchip--drop' : `pr-vchip--${verdict}`)} style={{ height: 18, fontSize: 10.5 }}>{String(s.verdict_label ?? s.status_label ?? '')}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
      {dock}
    </div>
  );
}

function NewSheetCard({ v, sh, draft, setDraft, busy, onTitle, onLine, onAdd, guide, p, sectionKey, head, pullable, pullOpen, setPullOpen, onPull }: {
  v: NonNullable<ReturnType<typeof useReuseView>['data']>; sh: ReturnType<typeof useSheet>['data']; draft: Record<string, string>; setDraft: (f: (d: Record<string, string>) => Record<string, string>) => void;
  busy: string | null; onTitle: (t: string) => void; onLine: (l: ReuseLineView, t: string) => void; onAdd: () => void; guide?: boolean; p: Proposal; sectionKey: SectionKey; head?: string;
  pullable?: ReuseLineView[]; pullOpen?: boolean; setPullOpen?: (o: boolean) => void; onPull?: (ids: string[]) => void;
}) {
  const ns = v.new_sheet;
  const lines = ns.lines ?? [];
  const title = draft.__title ?? ns.title ?? '';
  const tpl = sh?.template;
  const placeholders = (v.placeholders ?? []) as Array<Record<string, unknown>>;
  const km = useMemo(() => String((sh?.display as { subtitle?: string } | undefined)?.subtitle ?? ''), [sh]);
  return (
    <div className={cx('pr-card pr-newsheet', !guide && 'pr-newsheet--edit')} data-testid="pru4-new">
      <div className="pr-cardhead" style={{ height: 40 }}>
        <b style={{ fontSize: 13 }}>새 시트{guide ? ` · ${ns.title ?? ''}` : ''}</b>
        {!guide && <span className="pr-note pr-ell" style={{ fontSize: 12 }}>{head ?? (sh ? `${String(sh.sheet_no).padStart(2, '0')} ${sh.title} · 편집 중` : ns.title_label)}</span>}
        {guide && <span className="pr-vchip pr-vchip--keep" style={{ height: 20 }}><Icon name="check" size={10} strokeWidth={3} />원본 내용 0줄 사용 · 구조만</span>}
        <span className="pr-grow" />
        {ns.rq_label && <span className="pr-vchip pr-vchip--keep">{ns.rq_label}</span>}
        {guide && tpl?.code && sh && (
          <Link to={R.template(p.id, sectionKey, sh.id)} className="pr-tplchip"><b className="pr-num">{tpl.code}</b><span className="pr-muted pr-ell">{tpl.source === 'industry' ? '업종 레이아웃' : tpl.name ?? ''} · {tpl.mode === 'pinned' ? '직접' : '자동 추천'}</span><span className="pr-brand" style={{ fontWeight: 600 }}>바꾸기</span></Link>
        )}
      </div>
      <div className="pr-colflex" style={{ padding: '12px 14px', gap: 10, flex: 1 }}>
        <div className="pr-field">
          <label htmlFor="pru4-title" style={{ fontSize: 11.5 }}>시트 제목{ns.title_label && ns.title_label !== '시트 제목' && !guide ? <span style={{ color: 'var(--wm-warn)', fontWeight: 600 }}> · {ns.title_label}</span> : null}</label>
          <div className="pr-editbox" style={{ height: 40, background: 'var(--wm-surface)' }}>
            <input id="pru4-title" value={title} onChange={(e) => setDraft((d) => ({ ...d, __title: e.target.value }))} onBlur={(e) => onTitle(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} style={{ fontWeight: 600, fontSize: 13.5 }} data-testid="pru4-title" />
          </div>
        </div>
        {guide && km && (
          <div className="pr-field"><label style={{ fontSize: 11.5 }}>Key Message</label><div className="pr-editbox" style={{ height: 38, background: 'var(--wm-surface)' }}><input value={draft.__km ?? km} onChange={(e) => setDraft((d) => ({ ...d, __km: e.target.value }))} aria-label="Key Message" readOnly={busy === 'title'} /></div></div>
        )}
        {!guide && <span className="pr-note" style={{ fontSize: 11.5 }}>본문 불릿 · 줄마다 원본 대비 표시</span>}
        <div className={cx(guide ? 'pr-guidelines' : 'pr-colflex')} style={guide ? undefined : { gap: 8 }}>
          {lines.map((l, i) => {
            const val = draft[l.id] ?? l.text;
            return (
              <div key={l.id} className={cx('pr-lineedit', `pr-lineedit--${l.mark}`, l.edited && 'pr-lineedit--edited')} data-testid="pru4-line" data-mark={l.mark}>
                <label htmlFor={`pru4-l-${l.id}`} className="wm-sr-only">불릿 {i + 1}</label>
                <input id={`pru4-l-${l.id}`} value={val} disabled={busy === `ln:${l.id}`} onChange={(e) => setDraft((d) => ({ ...d, [l.id]: e.target.value }))} onBlur={(e) => onLine(l, e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
                {hasPlaceholder(val) && <span className="pr-phpill">확정 필요</span>}
                {!guide && <span className={cx('pr-vchip', `pr-vchip--${l.mark}`)} style={{ height: 18, fontSize: 10.5 }}>{l.badge || MARK_LABEL[l.mark]}</span>}
                {!guide && l.edited && l.draft_text != null && l.draft_text !== val && <button type="button" className="pr-mini" style={{ height: 24 }} onClick={() => onLine(l, l.draft_text!)} title="W 초안 값으로">되돌리기</button>}
              </div>
            );
          })}
        </div>
        {!guide && (
          <div className="pr-filter">
            <button type="button" className="pr-addline" onClick={() => (pullable?.length ? setPullOpen?.(!pullOpen) : onAdd())} disabled={busy === 'add'} data-testid="pru4-add">
              <Icon name="plus" size={12} strokeWidth={2.6} />줄 추가 · 원본 줄 끌어오기</button>
            {pullOpen && (
              <div className="pr-menu" style={{ left: 0, right: 'auto', top: 40, minWidth: 320 }}>
                <button type="button" onClick={() => { setPullOpen?.(false); onAdd(); }}><Icon name="plus" size={12} /> 빈 줄 추가</button>
                {(pullable ?? []).map((l) => <button key={l.id} type="button" onClick={() => onPull?.([l.id])} className="pr-ell" style={{ maxWidth: 420 }}><span className={cx('pr-vchip', `pr-vchip--${l.mark}`)} style={{ height: 16, fontSize: 9.5, marginRight: 6 }}>{MARK_LABEL[l.mark]}</span>{l.text}</button>)}
              </div>
            )}
          </div>
        )}
        {guide && placeholders.length > 0 && (
          <div className="pr-phband" data-testid="pru4b-placeholders">
            <Icon name="warn" size={14} color="var(--wm-warn)" /><b style={{ fontSize: 12.5 }}>수치 플레이스홀더 {placeholders.length}곳</b>
            {placeholders.map((ph, i) => <span key={i} className="pr-phchip"><b>{String(ph.token ?? ph.value ?? '')}</b> {String(ph.label ?? '')}</span>)}
            <span className="pr-note pr-ell" style={{ fontSize: 11.5 }}>확정 필요 목록에 등록됨 · 원본 수치는 출처가 없어 쓰지 않아요</span>
          </div>
        )}
        {(ns.note || sh?.content) && !guide && <span className="pr-note" style={{ fontSize: 11.5, borderTop: '1px solid var(--wm-line)', paddingTop: 8, marginTop: 'auto' }}><Icon name="file" size={11} /> 시트 노트 · {ns.note || '원본 대비 변경이 노트에 남아요'}</span>}
      </div>
    </div>
  );
}
