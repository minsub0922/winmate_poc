/**
 * Spec 시트 · ② 시트 작성(보드 webapp1 SP2 · 고치기 SP2_Edit) — 최종본(SP_View) 위 단계 팝업(StepModal) 본문. 상세 페이지: ./FlowPages.tsx
 * 왼쪽 DSS 제품(330 · 체크 = 시트에 넣기, 오른쪽 모델 칩 = 모델 고르기 · 바꾸기 · 수량) | 오른쪽 형식 · 항목 · 표기 칩 + 미리보기(130 + 제품 칸).
 * 값은 공식 카탈로그(KB)에서만, 없는 값은 [확인 필요]. 보드 px 그대로(sheet.css) · 패널 안에서만 스크롤. 저장(시트 만들기 / 저장 · vN)하면 XLSX 를 만들고 팝업이 닫힌다.
 * Storyboard 의 DSS 가 바뀌었으면(보드에 없음) 머리 아래 안내 줄 하나(AiBar · 「다시 가져오기」) — 그 줄만큼 작업 그리드가 줄고 나머지 칸은 그대로.
 * 팝업 안에서는 Storyboard 페이지로 가는 뒤로 링크를 그리지 않는다(팝업 머리의 Storyboard 칩 · ×).
 */
import { useState, type ReactNode } from 'react';
import { CONTENT, FlowBar, useShellPage } from '@/shell';
import { AiBar, FlowFooter, FlowHead, FlowPanel, FlowScreen, LinkedStoryboardBar, cx, toast, useInStepPopup } from '@/ui';
import { ITEM_KO, WARN_SHORT, dssChangeText, resyncToast, useSfActions, type SFDoc, type SFRow, type SFStageOut } from './api';
import { ModelDialog } from './ModelDialog';
import './sheet.css';

const FORMATS = [['compare', '비교표'], ['per_product', '제품별 1장']] as const;
const NOTATIONS = [['ko_mm', '한국어 · mm'], ['en_inch', '영문 · inch']] as const;
const PENDING = new Set(['[확인 필요]', '[To be confirmed]']);

const errText = (e: unknown, fallback: string) => (e as Error)?.message || fallback;

function Check({ on }: { on: boolean }) {
  return (
    <span className={cx('sf-box', on && 'sf-box--on')} aria-hidden>
      {on && <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>}
    </span>
  );
}

/** 제품 줄(보드 s-row: 44 · 체크 20 · 이름 13/600 · 공간 11.5) + 모델 칩(보드에 없음 — 모델 고르기 · 바꾸기)
 *  DSS 다시 가져오기 표시(보드에 없음): 새로 들어온 행은 공간 줄 뒤 「DSS에서 새로」, 빠진 행은 경고 「DSS에서 빠짐」 + 지우기 × */
function ProductRow({ r, onToggle, onModel, onRemove }: { r: SFRow; onToggle: () => void; onModel: () => void; onRemove: () => void }) {
  const warn = r.warnings[0];
  const chip = r.display_name ?? '모델 고르기';
  const gone = r.dss_status === 'removed';
  return (
    <div className={cx('sf-row', gone && 'sf-row--gone')} data-testid="sf-row" data-row={r.name} data-dss={r.dss_status ?? undefined}>
      <button type="button" className="sf-row__check" role="checkbox" aria-checked={r.on} aria-label={r.name} onClick={onToggle}>
        <Check on={r.on} />
        <span className="sf-row__txt">
          <span className="sf-row__t">{r.name}</span>
          <span className="sf-row__sp">{r.spaces.join(' · ') || '공간 없음'}
            {r.dss_status === 'added' && <em className="sf-row__new"> · DSS에서 새로</em>}
            {warn && <em className="sf-row__warn" title={r.warnings.map((w) => w.text).join('\n')}> · {WARN_SHORT[warn.kind] ?? '확인 필요'}</em>}</span>
        </span>
      </button>
      {gone && <button type="button" className="sf-rowdel" onClick={onRemove} aria-label={`${r.name} 지우기`} title="DSS에서 빠진 제품 · 시트에서 지우기">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg></button>}
      <button type="button" className={cx('sf-model', !r.model_code && 'sf-model--none', !!warn && r.model_code && 'sf-model--warn')} onClick={onModel}
        aria-label={`${r.name} 모델 ${r.model_code ? '바꾸기' : '고르기'}`} title={r.model_code ? `${r.display_name} · ${r.model_code}` : '공식 카탈로그 모델을 골라 주세요'}>
        {chip}
      </button>
    </div>
  );
}

function ChipRow({ k, first, children }: { k: string; first?: boolean; children: ReactNode }) {
  return (
    <div className={cx('sf-opt', !first && 'sf-opt--line')} role="group" aria-label={k}>
      <span className="sf-opt__k">{k}</span>
      <div className="sf-opt__vs">{children}</div>
    </div>
  );
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return <button type="button" className={cx('sf-chip', on && 'sf-chip--on')} aria-pressed={on} onClick={onClick}>{children}</button>;
}

function Cell({ t, head, label }: { t: string; head?: boolean; label?: boolean }) {
  const pend = !head && !label && PENDING.has(t);
  return <span className={cx('sf-cell', head && 'sf-cell--head', label && 'sf-cell--label', pend && 'sf-cell--pend')} title={t} role={head ? 'columnheader' : label ? 'rowheader' : 'cell'}>{t}</span>;
}

/** 그리드 한 줄(display: contents — 칸은 부모 그리드에 놓인다) */
function Row({ children }: { children: ReactNode }) {
  return <div role="row" style={{ display: 'contents' }}>{children}</div>;
}

/** 미리보기(보드: 130px + 제품 칸 · 12px · 칸 36). 제품이 3개를 넘으면 3칸 폭을 유지하고 가로로 스크롤 */
function Preview({ doc }: { doc: SFDoc }) {
  const rows = doc.rows.filter((r) => r.on);
  const cols = doc.columns.filter((c) => c.on);
  const en = doc.notation === 'en_inch';
  const P = en ? '[To be confirmed]' : '[확인 필요]';
  if (doc.format === 'per_product') {
    return (
      <div className="sf-sheets">
        {rows.map((r) => (
          <div key={r.key} className="sf-one" role="table" aria-label={`${r.name} 스펙`}>
            <div className="sf-one__head"><b>{r.name}</b>
              <span>{r.model_code ? `${r.display_name} · ${r.model_code}` : P} · {r.spaces.join(' · ') || '—'} · {en ? 'Qty' : '수량'} {r.qty ?? P}</span></div>
            <div className="sf-grid" style={{ gridTemplateColumns: '180px minmax(0, 1fr)' }}>{/* 보드에 없는 보기 — 영문 항목 이름이 잘리지 않게 180 */}
              {cols.map((c) => <Row key={c.key}><Cell t={c.label} label /><Cell t={r.cells[c.key] ?? P} /></Row>)}
            </div>
          </div>
        ))}
      </div>
    );
  }
  const n = rows.length;
  const track = n > 3 ? `calc((100% - 130px) / 3)` : 'minmax(0, 1fr)';
  return (
    <div className="sf-scroll">
      <div className="sf-grid" role="table" aria-label="미리보기 비교표" style={{ gridTemplateColumns: `130px repeat(${n}, ${track})` }}>
        <Row><Cell t={en ? 'Item' : '항목'} head label />{rows.map((r) => <Cell key={r.key} t={r.name} head />)}</Row>
        {cols.map((c) => <Row key={c.key}><Cell t={c.label} label />{rows.map((r) => <Cell key={r.key} t={r.cells[c.key] ?? P} />)}</Row>)}
      </div>
    </div>
  );
}

/**
 * ② 시트 작성 — 팝업 안 본문(보드 SP2 · SP2_Edit). 바닥 주 버튼: 새로 「시트 만들기」 · 고치기 「저장 · vN」(saveLabel).
 * 저장하면 XLSX 를 만들고 onSaved(응답) — 페이지가 팝업을 닫아 최종본을 보인다(완료 화면 없음).
 * 팝업 밖(이전 주소에서 바로 그릴 때)에서는 Storyboard 바 · 뒤로 링크를 그대로 그린다.
 */
export function SheetStep({ doc, saveLabel = '시트 만들기', onSaved }: { doc: SFDoc; saveLabel?: string; onSaved: (r: SFStageOut) => void }) {
  const inPop = useInStepPopup();
  const act = useSfActions(doc.id);
  const [modelKey, setModelKey] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  useShellPage({ section: CONTENT.sp.label, title: doc.title || CONTENT.sp.short, hasTask: true });
  const on = doc.rows.filter((r) => r.on).length;
  const c = doc.counts;
  const fail = (e: unknown) => toast(errText(e, '바꾸지 못했어요'));
  const toggleRow = (r: SFRow) => act.patchRow(r.key, { on: !r.on }, (d) => ({ ...d, rows: d.rows.map((x) => (x.key === r.key ? { ...x, on: !r.on } : x)) })).catch(fail);
  const setItems = (items: string[]) => act.patch({ items }, (d) => ({ ...d, items, columns: d.columns.map((x) => ({ ...x, on: items.includes(x.key) })) })).catch(fail);
  const toggleItem = (k: string) => setItems(doc.items.includes(k) ? doc.items.filter((x) => x !== k) : doc.columns.map((x) => x.key).filter((x) => x === k || doc.items.includes(x)));
  const setFormat = (k: (typeof FORMATS)[number][0]) => act.patch({ format: k }, (d) => ({ ...d, format: k })).catch(fail);
  const save = async () => {
    setSaving(true);
    try { onSaved(await act.finish()); } catch (e) { toast(errText(e, '저장하지 못했어요.')); } finally { setSaving(false); }
  };
  const resync = async () => {
    if (syncing) return;
    setSyncing(true);
    try { toast(resyncToast((await act.resync()).last_resync)); } catch (e) { toast(errText(e, 'DSS를 다시 가져오지 못했어요.')); } finally { setSyncing(false); }
  };
  const removeRow = (r: SFRow) => act.deleteRow(r.key).then(() => toast(`${r.name}을(를) 시트에서 지웠어요`)).catch(fail);
  const fmtLabel = FORMATS.find(([k]) => k === doc.format)?.[1] ?? '비교표';
  const summary = on && (c.warnings || c.pending_cells) ? `확인 필요 값 ${c.pending_cells} · 경고 ${c.warnings}` : undefined;
  const why = !on ? '시트에 넣을 제품을 골라 주세요' : !doc.items.length ? '항목을 하나 이상 골라 주세요' : undefined;
  return (
    <FlowScreen pad="20px 40px 20px 40px" gap={12} className="sf-screen"
      bar={doc.sb_id ? <FlowBar sbIds={[doc.sb_id]} current="sp" note="Storyboard를 그대로 가져왔어요 · 사전 작업 DSS 확인됨" />
        : <LinkedStoryboardBar chips={[]} emptyText="연결된 Storyboard가 없어요" />}>
      <FlowHead title="DSS 제품으로 스펙 시트를 만들어요" desc={`${doc.dss_ref ?? 'DSS'}에서 고른 제품을 그대로 가져왔어요. 값은 공식 카탈로그에서 채워요.`} />
      {doc.dss_changed && (
        <AiBar actionLabel={syncing ? '가져오는 중…' : '다시 가져오기'} onAction={resync}>
          <span data-testid="sf-dss-changed" title={[...doc.dss_changed.added_names ?? []].map((n) => `+ ${n}`).concat((doc.dss_changed.removed_names ?? []).map((n) => `− ${n}`)).join('\n') || undefined}>
            {dssChangeText(doc.dss_changed)}</span>
        </AiBar>
      )}
      <div className="wm-flow__grid sf-grid2">
        <FlowPanel className="sf-products" data-testid="sf-products">
          <div className="sf-lhead"><span className="sf-lhead__t">제품</span><span className="sf-lhead__n">{on} / {doc.rows.length} 선택</span></div>
          <div className="sf-list" role="group" aria-label="시트에 넣을 제품">
            {doc.rows.map((r) => <ProductRow key={r.key} r={r} onToggle={() => toggleRow(r)} onModel={() => setModelKey(r.key)} onRemove={() => removeRow(r)} />)}
            {!doc.rows.length && <div className="sf-empty">DSS에 제품이 없어요 · DSS에서 공간별 제품을 먼저 골라 주세요</div>}
          </div>
        </FlowPanel>
        <div className="sf-right">
          <div className="sf-opts" data-testid="sf-options">
            <ChipRow k="형식" first>{FORMATS.map(([k, t]) => <Chip key={k} on={doc.format === k} onClick={() => setFormat(k)}>{t}</Chip>)}</ChipRow>
            <ChipRow k="항목">{doc.columns.map((col) => <Chip key={col.key} on={col.on} onClick={() => toggleItem(col.key)}>{ITEM_KO[col.key] ?? col.label}</Chip>)}</ChipRow>
            <ChipRow k="표기">{NOTATIONS.map(([k, t]) => <Chip key={k} on={doc.notation === k} onClick={() => act.patch({ notation: k }).catch(fail)}>{t}</Chip>)}</ChipRow>
          </div>
          <div className="sf-preview" data-testid="sf-preview">
            <div className="sf-preview__h">미리보기 · {fmtLabel}</div>
            {why ? <div className="sf-empty">{why}</div> : <Preview doc={doc} />}
          </div>
        </div>
      </div>
      <FlowFooter back={inPop ? undefined : doc.sb_id ? { to: `/storyboard/flow/${doc.sb_id}`, label: 'Storyboard' } : { to: '/spec', label: '목록' }}
        summary={why ?? summary} summaryTone="warn"
        primary={{ label: saveLabel, onClick: save, busy: saving, disabled: !!why }} />
      <ModelDialog doc={doc} rowKey={modelKey} onClose={() => setModelKey(null)}
        onPick={(code) => act.patchRow(modelKey!, { model_code: code })}
        onQty={(qty) => act.patchRow(modelKey!, { qty }, (d) => ({ ...d, rows: d.rows.map((x) => (x.key === modelKey ? { ...x, qty } : x)) }))}
        onClear={() => act.patchRow(modelKey!, { clear_model: true })} />
    </FlowScreen>
  );
}
