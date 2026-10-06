/**
 * 섹션 작성 화면 18개(PRS1–8 · PRQ1–5 · PRX1–5) = SectionStep(§4.4 · §4.14) + 모드:
 *   기본 `/proposal/:id/sections/:key` · 템플릿 고르기 `…/sheets/:sheetId/template`(§4.16) · 추출 확인 `…/imports/:importId`(DnD_MIExtract)
 *   · 원본 대조/흐름 가이드 `?view=compare|guide&sheet=`(PRU4 · PRU4B) · 딸깍 팝오버 `?oneclick=1`(OneClickConfirm) · 다른 기능 반입 `?handoff=sho_…`(SP4).
 * 드래그 앤 드롭(§3.8 · §4.15): 하단 드롭 영역 + 셸 팝오버 · 사이드바(`useShellPage({accepts, acceptsWork})`), `POST …/imports`.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { DropZone, Icon, Modal, Thumb, toast, type DragPayload, type DragType } from '@/ui';
import type { FeatureCode } from '@/shell';
import {
  confirmSection, deleteLink, fillSection, invalidateProposal, postImport, qk, sectionRequest, undoImport, useProposal, useSection,
} from '../api/proposal';
import { errText, isApiError, isMissing, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { Proposal, SectionSheet, SectionView } from '../api/types';
import { Agent, ArrowRight, Dock, ErrorBand, LoadingCard, PrPage, SpinIcon, SrcIcon } from '../components/parts';
import { FEATURE_KEY, ITEM_LABEL, ROLES, SECTIONS, SOLS, TYPES, isSectionKey, tplOf, type ItemKind, type SectionKey } from '../lib/catalog';
import { handoffFeature, normalizeRoute, R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { ExtractPanel } from './ExtractPanel';
import { TemplatePanel, type Pick } from './TemplatePanel';
import { ReuseSectionView } from '../reuse/ReuseSectionView';

const LAST_PICK = (id: string, key: string) => `pr:lastsheet:${id}:${key}`;
const readLast = (id: string, key: string) => { try { return sessionStorage.getItem(LAST_PICK(id, key)); } catch { return null; } };
const writeLast = (id: string, key: string, v: string) => { try { sessionStorage.setItem(LAST_PICK(id, key), v); } catch { /* */ } };

/** 쓸 수 있는 섹션 키(유형 순서 · 켠 섹션) */
function enabledKeys(p: Proposal | undefined): SectionKey[] {
  const keys = TYPES[p?.type ?? 'standard'].secs;
  if (!p?.sections?.length) return keys;
  return keys.filter((k) => { const s = p.sections!.find((x) => x.key === k); return !s || (s.enabled !== false && !s.hidden); });
}

const codeOf = (s: SectionSheet) => s.template_info?.code ?? s.template ?? '';
function cardTag(s: SectionSheet, override?: Pick | null) {
  if (override) return override.mode === 'pinned' ? `${override.code} · 직접` : `자동 · ${override.code}`;
  if (s.tag) return s.tag;
  return s.template_info?.mode === 'pinned' ? `${codeOf(s)} · 직접` : `자동 · ${codeOf(s)}`;
}
function cardStatus(s: SectionSheet, opts: { picking: boolean; recent: boolean; filling: boolean }) {
  if (opts.picking) return { text: '템플릿 고르는 중', cls: 'pr-sheetcard__status pr-sheetcard__status--hl', need: false };
  if (opts.recent || s.status === 'updated') return { text: '업데이트됨', cls: 'pr-sheetcard__status pr-sheetcard__status--hl', need: false };
  if (s.status === 'need') return { text: s.status_label ?? '자료 필요', cls: 'pr-sheetcard__status pr-sheetcard__status--need', need: true };
  if (s.status === 'filling' || opts.filling) return { text: '작성 중', cls: 'pr-sheetcard__status', need: false };
  return { text: s.status_label && s.status_label !== '업데이트됨' ? s.status_label : s.role_name || ROLES[s.role]?.name || s.title, cls: 'pr-sheetcard__status', need: false };
}

export function SectionPage() {
  const { id, key: rawKey, sheetId, importId } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const loc = useLocation();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const vRaw = sp.get('view');
  const view = vRaw === 'compare' || vRaw === 'guide' || vRaw === 'new_only' ? vRaw : null;

  // 유형에 없는 섹션 키 → 같은 MI 끼리 · 아니면 첫 섹션(다른 기능이 `/sections/mi` 로 보낸 경우 등)
  const keys = useMemo(() => enabledKeys(p), [p]);
  const allKeys = TYPES[p?.type ?? 'standard'].secs;
  useEffect(() => {
    if (!p || !rawKey || !p.type) return;
    if (allKeys.includes(rawKey as SectionKey)) return;
    const alt = rawKey === 'mi' && allKeys.includes('bigMi') ? 'bigMi' : rawKey === 'bigMi' && allKeys.includes('mi') ? 'mi' : keys[0];
    nav(`${R.section(p.id, alt)}${loc.search}`, { replace: true });
  }, [p, rawKey, allKeys, keys, nav, loc.search]);
  const key = (isSectionKey(rawKey) ? rawKey : 'mi') as SectionKey;

  const sq = useSection(id, key);
  const v: SectionView | undefined = sq.data && Array.isArray(sq.data.sheets) ? sq.data : undefined;
  const def = SECTIONS[key];
  // 기존 제안서 활용 제안서는 섹션 화면이 원본 대조 · 흐름 가이드 보기로 열린다(PRU4 · PRU4B)
  useEffect(() => {
    if (!v?.reuse_view || vRaw || sheetId || importId) return;
    setSp((cur) => { const x = new URLSearchParams(cur); x.set('view', v.reuse_view!); return x; }, { replace: true });
  }, [v?.reuse_view, vRaw, sheetId, importId, setSp]);
  const invalidate = useCallback(() => { if (id) { void qc.invalidateQueries({ queryKey: qk.sub(id, 'section', key) }); void invalidateProposal(qc, id); } }, [id, key, qc]);

  // ── 초안 작성 잡(section_fill) ──
  const [fillJob, setFillJob] = useState<string | null>(null);
  const [reqJob, setReqJob] = useState<string | null>(null);
  const [jobErr, setJobErr] = useState<string | null>(null);
  const activeFill = fillJob ?? (v?.status === 'filling' ? v.fill_job_id ?? null : null);
  const fj = useJobEvents(activeFill, { onDone: (j) => { setFillJob(null); if (j.status === 'failed') setJobErr(jobErrText(j.error)); invalidate(); } });
  const rj = useJobEvents(reqJob, { onDone: (j) => { setReqJob(null); if (j.status === 'failed') setJobErr(jobErrText(j.error)); invalidate(); } });
  const entered = useRef<string | null>(null);
  useEffect(() => {
    if (!id || !v || entered.current === `${id}:${key}`) return;
    entered.current = `${id}:${key}`;
    const needDraft = v.needs_fill ?? (v.status === 'stale' || (v.status !== 'empty' && v.status !== 'filling' && v.sources.length > 0 && v.sheets.some((s) => s.status === 'need')));
    if (needDraft && !v.fill_job_id) {
      fillSection(id, key, v.status === 'stale' ? 'sources_changed' : 'enter').then((r) => setFillJob(r.job_id)).catch((e) => { if (!isMissing(e)) setJobErr(errText(e)); });
    }
  }, [id, key, v]);
  // 잡 이벤트가 끊겨도 「작성 중」이 남지 않게
  useEffect(() => { if (v?.status !== 'filling') return; const t = window.setInterval(() => void sq.refetch(), 3000); return () => window.clearInterval(t); }, [v?.status, sq]);

  // ── 다른 기능에서 넘겨받기(?handoff=sho_… · SP4) ──
  const handoff = sp.get('handoff');
  const [handoffNote, setHandoffNote] = useState<{ label: string; importId?: string } | null>(null);
  useEffect(() => {
    if (!id || !handoff || !p) return;
    // 기능 = feature → 작업 id 접두사(ca_ · mi_ …) → 넘김 id 접두사(hof_ 는 mi · competitor 공통이라 섹션으로 짐작)
    const feature = handoffFeature(sp, handoff.startsWith('hof_') ? (key === 'why' ? 'competitor' : 'mi') : null);
    // hof_(mi · competitor)는 서버가 넘김 기록을 못 찾아 분석 id 가 필요 — ?link= 로 받은 값을 ref_id 로(없으면 422 SOURCE_REQUIRED)
    const refId = sp.get('link') ?? sp.get('ref') ?? undefined;
    setSp((cur) => { const x = new URLSearchParams(cur); x.delete('handoff'); x.delete('feature'); x.delete('link'); x.delete('ref'); return x; }, { replace: true });
    postImport(id, { section_key: key, via: 'handoff', source: { feature, handoff_id: handoff, ...(refId ? { ref_id: refId } : {}) } })
      .then((r) => { setHandoffNote({ label: r.label || def.name, importId: r.import_id ?? undefined }); if (r.job_id) setReqJob(r.job_id); invalidate(); })
      .catch((e) => toast(errText(e)));
  }, [id, handoff, p]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── 드롭 · 추가 ──
  const accepts: ItemKind[] = (v?.accepts?.items as ItemKind[] | undefined) ?? def.accepts;
  const sideCodes = (v?.accepts?.sidebar?.length ? v.accepts.sidebar : def.sideFeatures).map((s) => (s.length <= 3 ? s.toUpperCase() : (Object.entries(FEATURE_KEY).find(([, k]) => k === s)?.[0] ?? s))) as FeatureCode[];
  const dropTypes: DragType[] = [...(sideCodes.length ? (['work_item'] as DragType[]) : []), ...accepts];
  const imports = useRef(new Map<string, string>());
  const [recent, setRecent] = useState<{ affected: string[]; chip?: string } | null>(null);
  const onDrop = async (pl: DragPayload) => {
    if (!id) return false;
    try {
      if (pl.type === 'work_item') {
        const ref = pl.ref.replace(/^ws:item:/, '');
        const r = await postImport(id, { section_key: key, via: 'drag_sidebar', source: { feature: FEATURE_KEY[pl.feature ?? ''] ?? pl.feature, ref_id: ref, title: pl.label } });
        if (r.import_id) nav(normalizeRoute(r.route) ?? R.extract(id, key, r.import_id));
        return false;
      }
      const r = await postImport(id, { section_key: key, via: 'drag_item', source: { kind: pl.type, ref: pl.ref, label: pl.label, sub: pl.sub } });
      if (r.import_id) imports.current.set(pl.ref, r.import_id);
      setRecent({ affected: [...(r.affected_sheet_ids ?? []), ...(r.new_sheet_ids ?? [])], chip: r.source_chip?.id });
      if (r.job_id) setReqJob(r.job_id);
      invalidate();
      return { note: r.note ?? '' };
    } catch (e) { toast(errText(e)); return false; }
  };
  const onUndo = async (pl: DragPayload) => {
    const imp = imports.current.get(pl.ref);
    if (!id || !imp) return;
    try { await undoImport(id, imp); setRecent(null); invalidate(); } catch (e) { toast(errText(e)); }
  };
  const onAdd = async (type: DragType, refs: string[]) => {
    if (!id) return { added: [] };
    const ok: string[] = [];
    for (const ref of refs) {
      try { await postImport(id, { section_key: key, via: 'button', source: { kind: type as ItemKind, ref } }); ok.push(ref); } catch (e) { toast(errText(e)); }
    }
    invalidate();
    return { added: ok };
  };
  // 연결 자료의 셸 참조(SourceChip.ref — `kb:model:…` · `img:image:…`)로 팝오버 항목에 「✓ 추가됨」(AC-091, 새로고침 뒤에도)
  const added = useMemo(() => (v?.sources ?? []).map((s) => s.ref ?? '').filter((r) => r.startsWith('kb:') || r.startsWith('img:')), [v?.sources]);

  // ── 레이아웃 모드 ──
  const [pick, setPick] = useState<Pick | null>(null);
  useEffect(() => { setPick(null); }, [sheetId]);
  const selSheet = sheetId ? v?.sheets.find((s) => s.id === sheetId) : undefined;
  useEffect(() => { if (id && sheetId) writeLast(id, key, sheetId); }, [id, key, sheetId]);
  const mode: 'default' | 'layout' | 'extract' = importId ? 'extract' : sheetId ? 'layout' : 'default';

  useProposalShell({
    p, step: 4, oneClick: { from: 'sections', section: key }, oneClickOpen: sp.get('oneclick') === '1',
    accepts: mode === 'default' ? dropTypes : [], acceptsWork: sideCodes, added, onAdd, addable: accepts as DragType[],
    sidebarGroup: undefined,
  });

  const [srcOpen, setSrcOpen] = useState(false);
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const [busyNext, setBusyNext] = useState(false);

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p) return <PrPage><LoadingCard /></PrPage>;

  const i0 = Math.max(0, keys.indexOf(key));
  const prevRoute = normalizeRoute(v?.prev?.route) ?? (i0 > 0 ? R.section(p.id, keys[i0 - 1]) : R.compose(p.id, key));
  const nextRoute = normalizeRoute(v?.next?.route) ?? (i0 < keys.length - 1 ? R.section(p.id, keys[i0 + 1]) : R.design(p.id));
  const nextLabel = v?.next?.label ?? (i0 < keys.length - 1 ? `다음: ${SECTIONS[keys[i0 + 1]].short}` : '다음: 디자인 템플릿');
  const name = v?.name ?? def.name;
  const sheets = v?.sheets ?? [];
  const filling = !!activeFill || v?.status === 'filling';

  if (view) {
    return <ReuseSectionView p={p} sectionKey={key} view={view} keys={keys} prevRoute={prevRoute} nextRoute={nextRoute} onView={(nv) => setSp((cur) => { const x = new URLSearchParams(cur); if (nv) x.set('view', nv); else x.delete('view'); return x; })} />;
  }

  const goNext = async () => {
    setBusyNext(true);
    try { await confirmSection(p.id, key); invalidate(); nav(nextRoute); } catch (e) { if (isMissing(e)) nav(nextRoute); else toast(errText(e)); } finally { setBusyNext(false); }
  };
  const runQuick = async (q: string) => {
    setJobErr(null);
    if (q === '템플릿 바꾸기') {
      const last = readLast(p.id, key);
      const target = sheets.find((s) => s.id === last) ?? sheets[0];
      if (target) nav(R.template(p.id, key, target.id));
      return;
    }
    if (q === '수량 조정') { setText('수량 조정: '); window.setTimeout(() => inputRef.current?.focus(), 0); return; }
    if (q === '출처 보기') { setSrcOpen(true); return; }
    if (q === '조감도 새로 만들기') { nav(`/birdseye/new?return_to=${encodeURIComponent(R.section(p.id, key))}`); return; }
    if (q === '시점 추가') {
      const be = v?.sources.find((s) => s.feature === 'birdseye');
      nav(normalizeRoute(be?.route) ?? `/birdseye/new?return_to=${encodeURIComponent(R.section(p.id, key))}`);
      return;
    }
    try { const r = await fillSection(p.id, key, 'regen', q); setReqJob(r.job_id); } catch (e) {
      // 잡이 없는 빠른 요청은 서버가 422 QUICK_ACTION_NO_JOB 으로 화면 동작을 알려 준다(details.panel · navigate · prefill)
      if (isApiError(e, 'QUICK_ACTION_NO_JOB')) {
        const d = e.details as { panel?: string; navigate?: string; prefill?: string };
        if (d.navigate) { nav(normalizeRoute(d.navigate)!); return; }
        if (d.prefill) { setText(d.prefill); window.setTimeout(() => inputRef.current?.focus(), 0); return; }
        if (d.panel === 'sources') { setSrcOpen(true); return; }
        if (d.panel === 'template') { const last = readLast(p.id, key); const t = sheets.find((s) => s.id === last) ?? sheets[0]; if (t) nav(R.template(p.id, key, t.id)); return; }
      }
      toast(errText(e));
    }
  };
  const sendRequest = async () => {
    const t = text.trim();
    if (!t) return;
    setText('');
    setJobErr(null);
    try { const r = await sectionRequest(p.id, key, t); setReqJob(r.job_id); } catch (e) { toast(errText(e)); setText(t); }
  };
  const unlink = async (lnk: string) => {
    try { await deleteLink(p.id, lnk); toast('연결 해제됨'); invalidate(); } catch (e) { toast(errText(e)); }
  };

  // 레일
  const rail = v?.rail ?? allKeys.map((k) => {
    const s = p.sections?.find((x) => x.key === k);
    return { key: k, label: SECTIONS[k].short, count: s?.sheet_count ?? SECTIONS[k].sheets.length, done: !!s?.confirmed, optional: TYPES[p.type ?? 'standard'].opt.includes(k), current: k === key, enabled: s?.enabled !== false };
  });
  const totalSheets = v?.total_sheets ?? rail.reduce((a, r) => a + (r.enabled === false ? 0 : r.count), 0);

  // 레이아웃 모드: 시트가 5장보다 많으면 같은 솔루션 그룹만
  let shown = sheets;
  let sheetLabel = v?.sheet_label ?? `시트 ${sheets.length}`;
  if (mode === 'layout' && selSheet && sheets.length > 5) {
    const g = selSheet.solution_code ?? '';
    shown = sheets.filter((s) => (s.solution_code ?? '') === g).slice(0, 5);
    sheetLabel = `${g ? SOLS[g]?.[0] ?? g : '통합'} 시트 ${shown.length} · 섹션 전체 ${sheets.length}`;
  }
  const intro = mode === 'extract' ? 'MI 작업에서 이 섹션에 쓸 내용을 뽑았습니다. 어느 시트에, 어떤 템플릿으로 들어갈지 함께 표시했어요.'
    : mode === 'layout' ? '메시지와 데이터에 맞는 템플릿을 고르세요. 자동 추천을 두거나 직접 골라 고정해요.' : (v?.intro ?? def.intro);
  const quick = v?.quick_actions?.length ? v.quick_actions : [...def.quick, '템플릿 바꾸기'];
  const workLabel = (def.side[0] ?? '').replace(/ 작업$/, '');
  const busyJob = !!reqJob;

  const dock = (
    <Dock testId="pr-section-dock"
      title={<>{name} <span className="pr-muted" style={{ fontWeight: 500 }}>· 섹션 {v?.no ?? i0 + 1} / {v?.total ?? keys.length} · 시트 {sheets.length}</span></>}
      right={quick.map((q) => <button key={q} type="button" className="pr-quick" disabled={busyJob} onClick={() => void runQuick(q)}>{q}</button>)}>
      {mode === 'default' && (
        <DropZone accept={dropTypes} acceptWork={sideCodes} workLabel={workLabel} onDrop={onDrop} onUndo={onUndo} style={{ marginTop: 0 }}
          chipLabels={{ product: ITEM_LABEL.product, solution: ITEM_LABEL.solution, image: ITEM_LABEL.image, case: ITEM_LABEL.case }}
          dragTitle={(pl) => (pl.type === 'work_item' ? '놓으면 이 섹션에 필요한 내용만 추출합니다' : <>여기에 놓아 「{pl.label}」 추가</>)}
          dragSub={(pl) => (pl.type === 'work_item' ? `추출 결과를 확인한 뒤 ${name} 시트에 반영됩니다` : `→ ${name} · 관련 시트가 함께 업데이트됩니다`)} />
      )}
      <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
        <label htmlFor="pr-sec-req" className="wm-sr-only">섹션 수정 요청</label>
        <div className="pr-prompt">
          <input id="pr-sec-req" ref={inputRef} placeholder={v?.placeholder ?? `${name} 수정 요청 (예: 시트 순서 바꾸기, 내용 보강)`} value={text} onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void sendRequest(); } }} data-testid="pr-sec-req" />
          <button type="button" className={text.trim() && !busyJob ? 'pr-send pr-send--on' : 'pr-send'} aria-label="보내기" disabled={!text.trim() || busyJob} onClick={() => void sendRequest()}>
            {busyJob ? <SpinIcon size={13} color="currentColor" /> : <Icon name="arrowUp" size={15} strokeWidth={2.2} />}
          </button>
        </div>
        <Link to={prevRoute} className="pr-btn" data-testid="pr-sec-prev">이전</Link>
        <button type="button" className="pr-btn pr-btn--primary" onClick={() => void goNext()} disabled={busyNext} data-testid="pr-sec-next">
          {busyNext ? <SpinIcon color="currentColor" /> : null}<span>{nextLabel}</span><ArrowRight />
        </button>
      </div>
    </Dock>
  );

  return (
    <div className="pr-page" data-testid="pr-section" data-section={key} data-mode={mode}>
      <nav className="pr-rail" aria-label="섹션" data-testid="pr-rail">
        <span className="pr-rail__type">{v?.type_name ?? TYPES[p.type ?? 'standard'].name}</span>
        {rail.map((r) => (
          <Link key={r.key} to={R.section(p.id, r.key)} title={`${SECTIONS[r.key as SectionKey]?.name ?? r.label}${r.optional ? ' (선택 섹션)' : ''}`}
            aria-current={r.key === key ? 'page' : undefined}
            className={['pr-rail__chip', r.optional && 'pr-rail__chip--opt', r.done && r.key !== key && 'pr-rail__chip--done', r.key === key && 'pr-rail__chip--cur', r.enabled === false && 'pr-rail__chip--off'].filter(Boolean).join(' ')}>
            {r.done && r.key !== key && <Icon name="check" size={11} strokeWidth={3} />}
            <span>{r.label}</span><span className="pr-rail__count">{r.count}</span>
          </Link>
        ))}
        <span className="pr-rail__total" data-testid="pr-rail-total">시트 {totalSheets}</span>
      </nav>
      <div className="pr-scroll pr-scroll--tight">
        <div className="pr-col pr-col--gap14" style={{ gap: 16 }}>
          <Agent testId="pr-section-intro" text={intro}>
            {sq.isError && <ErrorBand message={isMissing(sq.error) ? '섹션 정보를 아직 받지 못했어요. 잠시 후 다시 시도해 주세요' : errText(sq.error)} onRetry={() => void sq.refetch()} />}
            {jobErr && <ErrorBand message={jobErr} onRetry={() => { setJobErr(null); void fillSection(p.id, key, 'regen').then((r) => setFillJob(r.job_id)).catch((e) => setJobErr(errText(e))); }} />}
            {handoffNote && (
              <div className="pr-band" data-testid="pr-handoff-band">
                <Icon name="check" size={14} color="var(--wm-brand)" strokeWidth={2.8} />
                <span className="pr-grow">「{handoffNote.label}」 넣었어요 · 이 섹션 시트에 반영됩니다</span>
                {handoffNote.importId && <button type="button" className="pr-mini" onClick={() => { void undoImport(p.id, handoffNote.importId!).then(() => { setHandoffNote(null); invalidate(); }).catch((e) => toast(errText(e))); }}>실행 취소</button>}
              </div>
            )}
            {mode === 'extract' && importId && (
              <ExtractPanel proposalId={p.id} importId={importId} sectionName={name}
                onApplied={() => { invalidate(); nav(R.section(p.id, key), { replace: true }); }} />
            )}
            {mode !== 'extract' && !v && !sq.isError && <LoadingCard lines={3} />}
            {mode !== 'extract' && v && (
              <>
                {mode === 'default' && (
                  <div className="pr-sec" data-testid="pr-sources">
                    <div className="pr-label">연결된 자료</div>
                    <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
                      {v.sources.map((s) => (
                        <span key={s.id} className={['pr-src', recent?.chip === s.id && 'pr-src--new', s.stale && 'pr-src--stale'].filter(Boolean).join(' ')} data-testid="pr-source"
                          title={s.stale ? '원 작업이 바뀌었어요 — 다시 가져오면 반영돼요' : undefined}>
                          <SrcIcon kind={s.feature?.startsWith('kb_') ? s.feature.slice(3) : s.feature} size={13} />
                          <span>{s.label}</span>
                          <button type="button" className="pr-chip__x" aria-label="연결 해제" onClick={() => void unlink(s.id)}>×</button>
                        </span>
                      ))}
                      {v.sources.length === 0 && <span className="pr-src__none" data-testid="pr-no-sources">{v.empty_sources_label || '아직 연결된 자료가 없어요 — 아래 영역에 끌어다 놓으세요'}</span>}
                    </div>
                  </div>
                )}
                <div className="pr-sec">
                  <div className="pr-row pr-row--between">
                    <span className="pr-label" data-testid="pr-sheet-label">{sheetLabel} · 누르면 템플릿 변경</span>
                    <Link to={R.compose(p.id, key)} className="pr-link" style={{ fontSize: 12 }}><Icon name="plus" size={12} strokeWidth={2.4} />시트 추가 · 빼기</Link>
                  </div>
                  <div className="pr-sheets" data-testid="pr-sheets">
                    {shown.map((s) => {
                      const picking = mode === 'layout' && s.id === sheetId;
                      const code = picking && pick ? pick.code : codeOf(s);
                      const t = tplOf(code);
                      const st = cardStatus(s, { picking, recent: !!recent?.affected.includes(s.id), filling: filling && s.status !== 'ready' && s.status !== 'updated' });
                      const hl = picking || st.cls.includes('--hl');
                      const tag = cardTag(s, picking ? pick : null);
                      return (
                        <Link key={s.id} to={R.template(p.id, key, s.id)} data-testid="pr-sheet-card" data-sheet={s.id}
                          className={['pr-sheetcard', hl && 'pr-sheetcard--hl', s.inferred && 'pr-sheetcard--inferred'].filter(Boolean).join(' ')}>
                          <span className="pr-sheetcard__thumb">
                            <Thumb code={code || undefined} kind={t.kind} n={code === 'SC-A' ? 3 : t.n} src={s.thumb_url ?? undefined} />
                            <span className={tag.endsWith('· 직접') ? 'pr-sheetcard__tag pr-sheetcard__tag--pin' : 'pr-sheetcard__tag'}>{tag}</span>
                            {s.inferred && <span className="pr-sheetcard__badge">추론</span>}
                          </span>
                          <span className="pr-sheetcard__title">{s.title}</span>
                          <span className={st.cls}><span className={st.need ? 'pr-dot pr-dot--empty' : 'pr-dot'} />{st.text}</span>
                        </Link>
                      );
                    })}
                    {sheets.length === 0 && <span className="pr-src__none">이 섹션에 넣을 시트가 없어요 — 「시트 추가 · 빼기」로 고르세요</span>}
                  </div>
                </div>
                {mode === 'layout' && selSheet && (
                  <TemplatePanel key={selSheet.id} proposalId={p.id} sectionKey={key} sheet={selSheet} industry={p.customer?.industry_code ?? null}
                    pinnedCount={sheets.filter((s) => s.template_info?.mode === 'pinned').length} pick={pick} onPick={setPick}
                    onApplied={() => { invalidate(); nav(R.section(p.id, key)); }} onClose={() => nav(R.section(p.id, key))} />
                )}
                {mode === 'layout' && !selSheet && v && <ErrorBand message="그 시트를 찾지 못했어요" onRetry={() => nav(R.section(p.id, key))} />}
                {(filling || busyJob) && (
                  <div className="pr-band pr-band--muted" data-testid="pr-section-working">
                    <SpinIcon /> <span className="pr-grow">{busyJob ? `${name} 시트를 다시 쓰는 중이에요` : `${name} 시트 초안을 쓰는 중이에요`}{(busyJob ? rj.progress : fj.progress) ? ` · ${Math.round(busyJob ? rj.progress : fj.progress)}%` : ''}</span>
                  </div>
                )}
              </>
            )}
          </Agent>
        </div>
      </div>
      {dock}
      <Modal open={srcOpen} onClose={() => setSrcOpen(false)} title="출처 보기" ariaLabel="출처 보기" width={560}>
        <div className="pr-colflex" data-testid="pr-sources-panel">
          {(v?.sources ?? []).length === 0 && <div className="pr-note">연결된 자료가 없어요.</div>}
          {(v?.sources ?? []).map((s) => (
            <div key={s.id} className="pr-row" style={{ fontSize: 13 }}><SrcIcon kind={s.feature} size={14} /><span className="pr-grow">{s.label}</span>{s.stale && <span className="pr-badge pr-badge--warn">업데이트됨</span>}</div>
          ))}
        </div>
      </Modal>
    </div>
  );
}
