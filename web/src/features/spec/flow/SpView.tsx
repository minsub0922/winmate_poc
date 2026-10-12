/**
 * SP_View — 저장한 Spec 시트 보기(보드 webapp1 View content=sp · SP_View). 저장 뒤 · 목록 · 작업 내역 · 허브 cells[].route 로 열면 이 화면이다.
 * 띠 h44(형식 · 표기 · 값 · 파일 | 경고 알약) → 흰 판 하나의 표(190 · 160 · 항목 n × 1fr · 머리 h40 고정 · 줄 h44) → 아래 안내 11.5. 후속 작업 없음.
 * 머리 actions = 「XLSX 내려받기」(저장 때 만든 파일 — `GET /v1/spec-flows/{id}/stage` 의 file). 값은 이 문서(SFDoc)에서만, 없는 값은 [확인 필요](주황).
 */
import { FlowContentView, useFlow, whenText } from '@/shell';
import { PathIcon, cx } from '@/ui';
import { ITEM_KO, WARN_SHORT, useSfStage, type SFDoc, type SFRow } from './api';

const FORMAT_KO: Record<string, string> = { compare: '비교표', per_product: '제품별 1장' };
const NOTATION_KO: Record<string, string> = { ko_mm: '한국어 · mm', en_inch: '영문 · inch' };
const PENDING = new Set(['[확인 필요]', '[To be confirmed]']);
/** 띠에 다 보이는 경고 알약 수 — 넘치면 「+n」(나머지는 title) */
const MAX_WARN = 2;
const DL_ICON = 'M12 4v11 M7 10l5 5 5-5 M5 20h14';

/** 저장 시각 — 문서 응답에는 저장 시각이 없어 허브 이력(같은 참조 · 판의 sp 저장)에서 읽는다. 없으면 meta 에서 빠진다 */
function useSavedAt(d: SFDoc): string | null {
  const flow = useFlow(d.sb_id ?? null).data;
  const h = (flow?.history ?? []).filter((x) => x.key === 'sp' && x.ref === (d.code ?? d.id) && (d.ver == null || x.ver === d.ver));
  return h.length ? h[h.length - 1].at : null;
}

/** 수량 글(보드 「로비 · 1식」 · 「회의실 · 실당 1대」 · 「회의실 · [확인 필요]」) — 값은 문서에서만:
 *  개수(qty)가 있으면 개수 + DSS 원문 단위(qty_note 의 단위가 모두 같을 때, 아니면 대) · 개수가 없고 공간이 하나면 DSS 원문 그대로(실당 1대 · 2×2) · 그 밖은 [확인 필요] */
function qtyText(r: SFRow, P: string): string {
  const note = (r.qty_note ?? '').trim();
  if (r.qty != null) {
    const units = [...note.matchAll(/\d+\s*(대|식|개|세트)/g)].map((m) => m[1]);
    return `${r.qty}${units.length && units.every((x) => x === units[0]) ? units[0] : '대'}`;
  }
  const sp = r.spaces.length === 1 ? r.spaces[0] : null;
  const raw = sp && note.startsWith(`${sp} `) ? note.slice(sp.length + 1).trim() : '';
  return raw && !PENDING.has(raw) && !raw.includes(' · ') ? raw : P;
}

export function SpView({ doc }: { doc: SFDoc }) {
  const savedAt = useSavedAt(doc);
  const stage = useSfStage(doc.id);
  const file = stage.data?.file ?? null;
  const en = doc.notation === 'en_inch';
  const P = en ? '[To be confirmed]' : '[확인 필요]';
  const rows = doc.rows.filter((r) => r.on);
  const cols = doc.columns.filter((c) => c.on);
  const fmt = FORMAT_KO[doc.format] ?? '비교표';
  const warns = rows.flatMap((r) => r.warnings.map((w) => ({ key: `${r.key}:${w.kind}`, t: `${r.display_name ?? r.name} · ${WARN_SHORT[w.kind] ?? '확인 필요'}`, full: w.text })));
  const shown = warns.slice(0, MAX_WARN);
  const rest = warns.slice(MAX_WARN);
  const opts: [string, string][] = [['형식', fmt], ['표기', NOTATION_KO[doc.notation] ?? '한국어 · mm'], ['값', '공식 카탈로그'], ['파일', file?.name ?? '—']];
  const xlsx = file
    ? <a className="fl-view__btn spv-dl" href={`${file.url}?download=1`} download={file.name} title={file.name}><PathIcon d={DL_ICON} size={14} strokeWidth={2.2} />XLSX 내려받기</a>
    : <button type="button" className="fl-view__btn spv-dl" disabled title={stage.isLoading ? undefined : 'XLSX를 만들지 못했어요 · 편집에서 다시 저장해 주세요'}>
        <PathIcon d={DL_ICON} size={14} strokeWidth={2.2} />XLSX 내려받기</button>;
  return (
    <FlowContentView stageKey="sp" sbIds={doc.sb_id ? [doc.sb_id] : []} title={doc.title || 'Spec 시트'} refVer={`${doc.code ?? doc.id} v${doc.ver ?? 1}`}
      meta={[savedAt && `${whenText(savedAt)} 저장`, `제품 ${rows.length}`, `항목 ${cols.length}`, fmt]} actions={xlsx}>
      <div className="spv">
        <div className="fl-vstrip spv-strip" data-testid="spv-strip">
          {opts.map(([k, v]) => <span key={k} className="spv-opt"><b>{k}</b>{v}</span>)}
          <span className="spv-grow" />
          {shown.map((w) => <span key={w.key} className="spv-warn" title={w.full}>{w.t}</span>)}
          {rest.length > 0 && <span className="spv-warn" title={rest.map((w) => `${w.t} — ${w.full}`).join('\n')}>+{rest.length}</span>}
        </div>
        <div className="fl-vcard spv-card" data-testid="spv-card">
          <div className="spv-grid" role="table" aria-label="스펙 시트" style={{ gridTemplateColumns: `190px 160px repeat(${cols.length}, minmax(0, 1fr))` }}>
            <div role="row" className="spv-row">
              <span role="columnheader" className="spv-cell spv-cell--head">제품</span>
              <span role="columnheader" className="spv-cell spv-cell--head">공간 · 수량</span>
              {cols.map((c) => <span key={c.key} role="columnheader" className="spv-cell spv-cell--head" title={c.label}>{ITEM_KO[c.key] ?? c.label}</span>)}
            </div>
            {rows.map((r) => {
              const warn = r.warnings.length > 0;
              const q = qtyText(r, P);
              return (
                <div key={r.key} role="row" className="spv-row" data-row={r.name}>
                  <span role="rowheader" className={cx('spv-cell spv-cell--name', warn && 'spv-cell--warnname')}
                    title={r.model_code ? `${r.name} · ${r.display_name} · ${r.model_code}` : r.name}>{r.name}</span>
                  <span role="cell" className="spv-cell spv-cell--space" title={r.qty_note ?? undefined}>
                    {r.spaces.join(' · ') || '—'} · {q}
                  </span>
                  {cols.map((c) => {
                    const t = r.cells[c.key] ?? P;
                    return <span key={c.key} role="cell" className={cx('spv-cell', PENDING.has(t) && 'spv-cell--pend')} title={t}>{t}</span>;
                  })}
                </div>
              );
            })}
          </div>
        </div>
        <span className="fl-vnote">값은 공식 카탈로그에서 채워요 · 카탈로그에 없는 값은 [확인 필요]로 남겨요</span>
      </div>
    </FlowContentView>
  );
}
