/**
 * Spec 시트 상세(보드 webapp1 v63 View content=sp + SPBody · SP2 · SP_Draft · SP2_Edit · SP_View · SP2_Pick) — `/spec/flow/:id` 한 장.
 * 새로 만들기 · 작성 중 · 저장됨 · 고치는 중 모두 같은 화면이다(ContentDetail 이 머리 · 저장 · 되돌리기 · flow.json · 나가기 확인을 그린다).
 *   본문: 옵션 띠(형식 · 표기 · 항목 · 값 출처 · 경고 · 제품 고르기) → 비교표(190 · 160 · 항목 칸 minmax(116, 1fr), 머리 고정) → 시트에서 뺀 제품 → 각주.
 *   값은 공식 카탈로그(KB)에서만 · 읽기 전용. 카탈로그에 값이 없는 칸([확인 필요])은 노란 칸 — 사람이 원문 값을 그 자리에서 적는다(떠날 때 저장).
 *   제품 넣기 · 빼기 · DSS 밖 제품 더하기는 「제품 고르기」(ProdPicker), 모델 · 수량은 제품 이름을 눌러(ModelDialog · 보드에 없음).
 *   저장하면 그 자리에서 저장됨으로(XLSX 를 만들고 머리에 「XLSX 내려받기」). 저장한 뒤 고친 칸은 보드 표시(고른 칸 테두리 · cd-in--chg)를 단다.
 * Storyboard 의 DSS 가 바뀌었으면(보드에 없음) 본문 맨 위 안내 줄(AiBar · 「다시 가져오기」) — 그만큼 표 높이만 준다.
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useParams } from 'react-router';
import { ContentDetail, InlineInput, useFlow } from '@/shell';
import { AiBar, ErrorState, ProductPickerDialog, Skeleton, cx, toast, type PickGroup, type PickItem } from '@/ui';
import {
  ITEM_KO, WARN_CHIP, dssChangeText, resyncToast, useSfActions, useSpecFlow, type SFDoc, type SFRow, type SFStageOut,
} from './api';
import { ModelDialog } from './ModelDialog';
import './sheet.css';

const FORMATS = [['compare', '비교표'], ['per_product', '제품별 1장']] as const;
const NOTATIONS = [['ko_mm', '한국어 · mm'], ['en_inch', '영문 · inch']] as const;
type Fmt = (typeof FORMATS)[number][0];
type Nota = (typeof NOTATIONS)[number][0];

const errText = (e: unknown, fallback: string) => (e as Error)?.message || fallback;

/** 이 화면에서 고친 것(보드 SP2_Edit 표시) — 저장 · 되돌리기 하면 지운다 */
interface Marks { format: boolean; notation: boolean; items: boolean; added: string[]; cells: string[]; rows: string[] }
const NO_MARKS: Marks = { format: false, notation: false, items: false, added: [], cells: [], rows: [] };

function Chevron() {
  return <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M6 9l6 6 6-6" /></svg>;
}

/** 보드 SPBody 세그먼트(h32 · p3 · r8 · #f0f2f5) — 고른 값이 이 화면에서 바뀌었으면 2px 테두리 */
function Seg<T extends string>({ label, items, value, changed, onPick }: { label: string; items: ReadonlyArray<readonly [T, string]>; value: T; changed: boolean; onPick: (v: T) => void }) {
  return (
    <>
      <span className="spd-k">{label}</span>
      <span className="spd-seg" role="radiogroup" aria-label={label}>
        {items.map(([k, t]) => (
          <button key={k} type="button" role="radio" aria-checked={value === k} className={cx('spd-segb', value === k && 'spd-segb--on', value === k && changed && 'spd-segb--chg')}
            onClick={() => value !== k && onPick(k)}>{t}</button>
        ))}
      </span>
    </>
  );
}

/** 항목 고르기(보드: 「6개 고름」 버튼 · aria-haspopup=listbox) — 펼친 목록은 보드에 없어 띠 아래 작은 목록으로 */
function ItemPicker({ doc, label, changed, onToggle }: { doc: SFDoc; label: string; changed: boolean; onToggle: (k: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const down = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', down);
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('mousedown', down); document.removeEventListener('keydown', key); };
  }, [open]);
  return (
    <span className="spd-items" ref={ref}>
      <button type="button" className={cx('spd-itemsb', changed && 'spd-itemsb--chg')} aria-haspopup="listbox" aria-expanded={open} aria-label={`항목 · ${label}`}
        onClick={() => setOpen((o) => !o)}>{label}<Chevron /></button>
      {open && (
        <div className="spd-itemsl" role="listbox" aria-label="항목" aria-multiselectable="true">
          {doc.columns.map((c) => (
            <button key={c.key} type="button" role="option" aria-selected={c.on} className={cx('spd-opt', c.on && 'spd-opt--on')} onClick={() => onToggle(c.key)}>
              <span className={cx('spd-box', c.on && 'spd-box--on')} aria-hidden>
                {c.on && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>}
              </span>{ITEM_KO[c.key] ?? c.label}
            </button>
          ))}
        </div>
      )}
    </span>
  );
}

/** 표 한 줄(display: contents — 칸은 부모 그리드에 놓인다). data-* 는 e2e · 접근성 확인용 */
function Tr({ children, ...rest }: { children: ReactNode; [k: `data-${string}`]: string | undefined }) {
  return <div role="row" style={{ display: 'contents' }} {...rest}>{children}</div>;
}

type Act = ReturnType<typeof useSfActions>;

function Body({ doc, act, marks, mark, onModel }: {
  doc: SFDoc; act: Act; marks: Marks | null; mark: (m: Partial<Marks> | ((m: Marks) => Partial<Marks>)) => void; onModel: (k: string) => void;
}) {
  const flow = useFlow(doc.sb_id ?? null);
  const [pick, setPick] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const fail = (e: unknown) => toast(errText(e, '바꾸지 못했어요'));
  const en = doc.notation === 'en_inch';
  const P = en ? '[To be confirmed]' : '[확인 필요]';
  const cols = doc.columns.filter((c) => c.on);
  const rows = doc.rows.filter((r) => r.on);
  const outs = doc.rows.filter((r) => !r.on);
  const dss = doc.dss_ref ?? 'DSS';
  const warnRows = rows.filter((r) => r.warnings.length);

  const setFormat = (k: Fmt) => { mark({ format: true }); act.patch({ format: k }, (d) => ({ ...d, format: k })).catch(fail); };
  const setNotation = (k: Nota) => { mark({ notation: true }); act.patch({ notation: k }, (d) => ({ ...d, notation: k })).catch(fail); };
  const toggleItem = (k: string) => {
    const on = doc.items.includes(k);
    const items = doc.columns.map((c) => c.key).filter((x) => (x === k ? !on : doc.items.includes(x)));
    mark((m) => ({ items: true, added: on ? m.added.filter((x) => x !== k) : [...m.added, k] }));
    act.patch({ items }, (d) => ({ ...d, items, columns: d.columns.map((c) => ({ ...c, on: items.includes(c.key) })) })).catch(fail);
  };
  const setOn = (r: SFRow, on: boolean) => {
    mark((m) => ({ rows: [...m.rows, r.key] }));
    return act.patchRow(r.key, { on }, (d) => ({ ...d, rows: d.rows.map((x) => (x.key === r.key ? { ...x, on } : x)) })).catch(fail);
  };
  const writeCell = (r: SFRow, k: string, v: string) => {
    mark((m) => ({ cells: [...m.cells, `${r.key}:${k}`] }));
    const opt = (d: SFDoc) => ({ ...d, rows: d.rows.map((x) => {
      if (x.key !== r.key) return x;
      const manual = { ...x.manual };
      if (v) manual[k] = v; else delete manual[k];
      return { ...x, manual, cells: { ...x.cells, [k]: v || P } };
    }) });
    return act.patchRow(r.key, { cells: { [k]: v || null } }, opt).catch(fail);
  };
  const resync = async () => {
    if (syncing) return;
    setSyncing(true);
    try { toast(resyncToast((await act.resync()).last_resync)); } catch (e) { toast(errText(e, 'DSS를 다시 가져오지 못했어요.')); } finally { setSyncing(false); }
  };
  const removeRow = (r: SFRow) => act.deleteRow(r.key).then(() => toast(`${r.name}을(를) 시트에서 지웠어요`)).catch(fail);

  // 제품 고르기(보드 SP2_Pick · ProdPicker 760×640): DSS 제품(체크 = 시트에 넣기) · DSS 솔루션 · 카탈로그 검색(DSS 밖)
  const solutions = useMemo(() => {
    const st = ((flow.data?.stages ?? {}) as Record<string, unknown>).dss as { solutions?: Array<{ name?: string; ref?: string | null; links?: string[] }> } | undefined;
    return (st?.solutions ?? []).filter((s) => s.name).map((s) => ({ name: s.name!, ref: s.ref ?? null, links: s.links ?? [] }));
  }, [flow.data]);
  const dssRows = doc.rows.filter((r) => r.source !== 'catalog');
  const groups: PickGroup[] = [
    { label: `${dss} · 제품`, items: dssRows.map((r) => ({ name: r.name, kind: 'product' as const, ref: r.dss_ref ?? null,
      where: r.dss_status === 'removed' ? `${dss}에서 빠짐 · ${r.spaces.join(' · ')}` : `${dss} · ${r.spaces.join(' · ') || '공간 없음'}` })) },
    ...(solutions.length ? [{ label: `${dss} · 솔루션`, items: solutions.map((s) => ({ name: s.name, kind: 'solution' as const, ref: s.ref, where: `${dss} · ${s.links.join(' · ') || '솔루션'}` })) }] : []),
  ];
  const picked = doc.rows.filter((r) => r.on).map((r) => r.name);
  const togglePick = (it: PickItem) => {
    const r = doc.rows.find((x) => x.name === it.name);
    if (r && r.source === 'catalog' && r.on) { mark((m) => ({ rows: [...m.rows, r.key] })); void removeRow(r); return; }
    if (r) { void setOn(r, !r.on); return; }
    mark((m) => ({ rows: [...m.rows, `+${it.name}`] }));
    act.addRow({ name: it.name, ref: it.ref ?? null, kind: it.kind }).then(() => toast(`${it.name}을(를) 시트에 더했어요`)).catch(fail);
  };

  const added = marks?.added.filter((k) => doc.items.includes(k)) ?? [];
  const itemLabel = added.length && added.length <= 2 && doc.items.length > added.length
    ? `${doc.items.length - added.length}개 + ${added.map((k) => ITEM_KO[k] ?? k).join(' · ')} 고름` : `${doc.items.length}개 고름`;
  const w0 = warnRows.find((r) => r.warnings[0].kind === 'dss_removed') ?? warnRows[0];   // DSS 에서 빠진 제품이 먼저(새로 생긴 일)
  const warnText = w0 ? `${w0.name} · ${WARN_CHIP[w0.warnings[0].kind] ?? '확인 필요'}${warnRows.length > 1 ? ` 외 ${warnRows.length - 1}` : ''}` : '';
  const rowChg = (k: string) => !!marks?.rows.includes(k);
  const head = (t: string, k?: string) => <span key={k ?? t} role="columnheader" className={cx('spd-c spd-h', k && added.includes(k) && 'spd-h--new')} title={t}>{t}</span>;

  return (
    <div className="spd-body" data-testid="spd-body">
      {doc.dss_changed && (
        <AiBar actionLabel={syncing ? '가져오는 중…' : '다시 가져오기'} onAction={resync}>
          <span data-testid="sf-dss-changed" title={[...doc.dss_changed.added_names ?? []].map((n) => `+ ${n}`).concat((doc.dss_changed.removed_names ?? []).map((n) => `− ${n}`)).join('\n') || undefined}>
            {dssChangeText(doc.dss_changed)}</span>
        </AiBar>
      )}
      <div className="cd-strip spd-strip" data-testid="spd-strip">
        <Seg label="형식" items={FORMATS} value={doc.format as Fmt} changed={!!marks?.format} onPick={setFormat} />
        <Seg label="표기" items={NOTATIONS} value={doc.notation as Nota} changed={!!marks?.notation} onPick={setNotation} />
        <span className="spd-k">항목</span>
        <ItemPicker doc={doc} label={itemLabel} changed={!!marks?.items} onToggle={toggleItem} />
        <span className="spd-src"><b>값</b> 공식 카탈로그</span>
        <span className="spd-grow" />
        {w0 && (
          <button type="button" className="spd-warn" data-testid="spd-warn" onClick={() => onModel(w0.key)}
            title={warnRows.map((r) => `${r.name}: ${r.warnings.map((w) => w.text).join(' / ')}`).join('\n')}>{warnText}</button>
        )}
        <button type="button" className="spd-pick" onClick={() => setPick(true)}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><path d="M4 6h16 M4 12h10 M4 18h6" /></svg>
          제품 고르기 · {doc.counts.models}/{doc.counts.total}
        </button>
      </div>
      <div className="spd-table" data-testid="spd-table">
        <div className="spd-grid" role="table" aria-label="스펙 시트" style={{ gridTemplateColumns: `190px 160px repeat(${Math.max(cols.length, 1)}, minmax(116px, 1fr))` }}>
          <Tr>{head(en ? 'Product' : '제품', '_p')}{head(en ? 'Space · Qty' : '공간 · 수량', '_s')}{cols.map((c) => head(c.label, c.key))}</Tr>
          {rows.map((r) => {
            const warn = r.warnings[0];
            const gone = r.dss_status === 'removed';
            return (
              <Tr key={r.key} data-testid="spd-row" data-row={r.name} data-dss={r.dss_status ?? undefined} data-source={r.source}>
                <span role="rowheader" className={cx('spd-c spd-name', !!warn && 'spd-name--warn', rowChg(r.key) && 'cd-chgrow')}>
                  <button type="button" className="spd-namebtn" onClick={() => onModel(r.key)} aria-label={`${r.name} 모델 · 수량`}
                    title={r.model_code ? `${r.display_name} · ${r.model_code}${warn ? `\n${warn.text}` : ''}` : (warn?.text ?? '모델 고르기')}>{r.name}</button>
                  {gone && <button type="button" className="cd-x" onClick={() => removeRow(r)} aria-label={`${r.name} 지우기`} title="DSS에서 빠진 제품 · 시트에서 지우기">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg></button>}
                </span>
                <span role="cell" className={cx('spd-c spd-space', rowChg(r.key) && 'spd-c--chg')} title={r.qty_note ? `DSS · ${r.qty_note}` : undefined}>
                  {`${r.spaces.join(' · ') || (r.source === 'catalog' ? 'DSS 밖' : '공간 없음')} · ${r.qty_text || P}`}
                  {r.dss_status === 'added' && <em className="spd-new"> · DSS에서 새로</em>}
                  {gone && <em className="spd-gone"> · DSS에서 빠짐</em>}
                </span>
                {cols.map((c) => {
                  const nw = added.includes(c.key);
                  const bg = (nw || rowChg(r.key)) && 'spd-c--chg';
                  if (!r.editable.includes(c.key)) return <span key={c.key} role="cell" className={cx('spd-c spd-v', bg)} title={r.cells[c.key]}>{r.cells[c.key]}</span>;
                  const v = r.manual[c.key] ?? '';
                  return (
                    <span key={c.key} role="cell" className={cx('spd-c spd-in-c', bg)}>
                      <InlineInput value={v} label={`${r.name} ${ITEM_KO[c.key] ?? c.label}`} placeholder={P} maxLength={200}
                        className={cx('spd-in', v ? 'spd-in--man' : 'cd-in--warn')} changed={!!marks?.cells.includes(`${r.key}:${c.key}`)}
                        onCommit={(t) => writeCell(r, c.key, t)} />
                    </span>
                  );
                })}
              </Tr>
            );
          })}
        </div>
        {!rows.length && <div className="spd-empty">{doc.rows.length ? '시트에 넣은 제품이 없어요 · 「제품 고르기」나 아래 「다시 넣기」로 넣어 주세요' : 'DSS에 제품이 없어요 · DSS에서 공간별 제품을 먼저 골라 주세요'}</div>}
        {!!rows.length && !cols.length && <div className="spd-empty">항목을 하나 이상 골라 주세요</div>}
      </div>
      {!!outs.length && (
        <div className="spd-outs" data-testid="spd-outs">
          <span className="spd-outs__k">시트에서 뺀 제품</span>
          <span className="spd-outs__list">
            {outs.map((r) => (
              <span key={r.key} className="spd-out">{r.name}
                <button type="button" className="spd-outb" onClick={() => void setOn(r, true)} aria-label={`${r.name} 다시 넣기`}>다시 넣기</button></span>
            ))}
          </span>
        </div>
      )}
      <span className="spd-foot">값은 공식 카탈로그에서 채워요 · 카탈로그에 없는 값은 {P}로 남기고, 노란 칸에 원문 값을 바로 적어요
        {doc.format === 'per_product' && ' · 제품별 1장은 XLSX에서 제품마다 시트 한 장으로 나눠요'}</span>
      <ProductPickerDialog open={pick} onClose={() => setPick(false)} title="스펙 시트에 넣을 제품 고르기"
        sub={`${dss} 제품을 모두 가져왔어요. 시트에서 뺄 것은 끄고, DSS 밖 제품도 카탈로그에서 더할 수 있어요.`}
        groups={groups} picked={picked} onToggle={togglePick} min={1} />
    </div>
  );
}

function Detail({ doc }: { doc: SFDoc }) {
  const act = useSfActions(doc.id);
  const [modelKey, setModelKey] = useState<string | null>(null);
  const [marks, setMarks] = useState<Marks>(NO_MARKS);
  const saved = doc.ver != null;
  const mark = (m: Partial<Marks> | ((cur: Marks) => Partial<Marks>)) => { if (saved) setMarks((cur) => ({ ...cur, ...(typeof m === 'function' ? m(cur) : m) })); };
  const shown = saved && doc.changes > 0 ? marks : null;      // 저장한 판과 같아지면(고친 곳 0) 표시도 없앤다
  const c = doc.counts;
  const fmtLabel = FORMATS.find(([k]) => k === doc.format)?.[1] ?? '비교표';
  const check = doc.rows.filter((r) => r.on && (r.warnings.length || r.pending.length)).length;
  const facts = saved ? [`제품 ${c.models}`, `항목 ${c.columns}`, fmtLabel] : [`제품 ${c.models}`, ...(check ? [`확인 필요 ${check}`] : [])];
  const why = !c.models ? '시트에 넣을 제품을 골라 주세요' : !c.columns ? '항목을 하나 이상 골라 주세요' : null;
  const f = doc.file;
  const xlsx = saved && (f
    ? <a className="cd-btn spd-xlsx" href={`${f.url}?download=1`} download={f.name} title={f.name}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M12 4v11 M7 10l5 5 5-5 M5 20h14" /></svg>XLSX 내려받기</a>
    : <button type="button" className="cd-btn" disabled title="XLSX를 만들지 못했어요 · 다시 저장해 주세요">XLSX 내려받기</button>);
  return (
    <ContentDetail content="sp" saved={saved} changes={doc.changes} empty={!saved && doc.version <= 1}
      title={doc.title} refCode={doc.code} ver={doc.ver} savedAt={doc.saved_at} updatedAt={doc.updated_at} facts={facts}
      sbIds={doc.sb_id ? [doc.sb_id] : []} canSave={why ?? true} actions={xlsx || undefined}
      onSave={async () => { const out = await act.finish(); setMarks(NO_MARKS); return out; }}
      onRevert={async () => { await act.revert(); setMarks(NO_MARKS); }}
      savedToast={(o) => {
        const out = o as SFStageOut;
        const st = out.stage as { ref?: string; ver?: number };
        const n = out.flow_sync?.synced?.length ?? 0;
        return [`${st.ref ?? doc.code} v${st.ver ?? ''} 저장`, out.file ? `${out.file.name} 만들었어요` : 'XLSX는 만들지 못했어요', n ? `연결된 Storyboard ${n + 1}개에 반영` : ''].filter(Boolean).join(' · ');
      }}>
      <Body doc={doc} act={act} marks={shown} mark={mark} onModel={setModelKey} />
      <ModelDialog doc={doc} rowKey={modelKey} onClose={() => setModelKey(null)}
        onPick={(code) => { mark((m) => ({ rows: [...m.rows, modelKey!] })); return act.patchRow(modelKey!, { model_code: code }); }}
        onQty={(qty) => { mark((m) => ({ rows: [...m.rows, modelKey!] })); return act.patchRow(modelKey!, { qty }, (d) => ({ ...d, rows: d.rows.map((x) => (x.key === modelKey ? { ...x, qty } : x)) })); }}
        onClear={() => { mark((m) => ({ rows: [...m.rows, modelKey!] })); return act.patchRow(modelKey!, { clear_model: true }); }} />
    </ContentDetail>
  );
}

function Page({ id }: { id: string }) {
  const q = useSpecFlow(id);
  if (q.isError) return <div className="wm-page"><ErrorState message="Spec 시트를 불러오지 못했어요 · 지워졌거나 주소가 바뀌었을 수 있어요" onRetry={() => q.refetch()} /></div>;
  if (!q.data) return <div className="wm-page"><Skeleton h={480} r={14} /></div>;
  return <Detail doc={q.data} />;
}

/** `/spec/flow/:id` — 다른 시트로 옮기면 화면 상태를 새로 */
export function SheetPage() {
  const { id = '' } = useParams();
  return <Page key={id} id={id} />;
}
