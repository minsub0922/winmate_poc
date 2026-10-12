/**
 * Spec 시트 최종본 본문(보드 webapp1 v62 View content=sp · SP_View · SP_Draft) — 칸은 보드 인라인 px 그대로(spview.css).
 *   옵션 줄(h44 · 형식 · 표기 · 값 · 파일 + 오른쪽 경고 칩) → 비교표 칸(190 · 160 · 항목마다 1fr · 머리 40 sticky · 줄 44) → 아래 안내 한 줄.
 *   저장 전(작성 중 · 새로)에는 ② 시트 작성 자리표시(StepSlot big)만.
 * 값은 시트 문서(공식 카탈로그 값)를 그대로 — 없는 값은 [확인 필요](주황). 본문 data 속성은 단계 팝업과 겹치지 않게 `data-v…`.
 */
import { StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import { WARN_SHORT, type SFDoc, type SFRow } from './api';
import './spview.css';

const P = '[확인 필요]';
const PENDING = new Set([P, '[To be confirmed]']);
export const FORMAT_KO: Record<string, string> = { compare: '비교표', per_product: '제품별 1장' };
export const NOTATION_KO: Record<string, string> = { ko_mm: '한국어 · mm', en_inch: '영문 · inch' };
/** 옵션 줄 오른쪽에 그대로 보이는 경고 칩 수(나머지는 「경고 +n」 하나로) */
const WARN_MAX = 2;

/** 저장(시트 만들기)한 적이 있나 — 저장하면 status done · ver 1 이상 */
export const spSaved = (d: SFDoc) => d.status === 'done' || d.ver != null;
/** 마친 단계 수 — 1(Storyboard) · 2(저장) */
export const spDone = (d: SFDoc) => (spSaved(d) ? 2 : 1);

/** DSS 수량 원문의 단위(「로비 2대 · 라운지 1대」 → 대) — 공간마다 같은 단위일 때만(아니면 개수만) */
function unitOf(note: string | null | undefined): string {
  const us = [...(note ?? '').matchAll(/\d+\s*(대|식|개|세트)(?=\s*(?:·|$))/g)].map((m) => m[1]);
  return us.length && us.every((u) => u === us[0]) ? us[0] : '';
}

/** 「공간 · 수량」 칸(보드: `로비 · 1식` · `회의실 · 실당 1대` · `회의실 · [확인 필요]`) — 공간 하나면 DSS 수량 원문 그대로,
 *  공간이 여럿이거나 사람이 고친 수량이면 더한 개수(+ 원문 단위). 원문은 칸 title 에 */
export function spaceQty(r: SFRow): string {
  const sp = r.spaces.join(' · ') || '공간 없음';
  const one = r.spaces.length === 1 ? r.spaces[0] : null;
  if (!r.qty_edited && one && r.qty_note?.startsWith(`${one} `)) return `${sp} · ${r.qty_note.slice(one.length + 1)}`;
  return `${sp} · ${r.qty != null ? `${r.qty}${unitOf(r.qty_note)}` : P}`;
}

function C({ t, cls, title, role = 'cell' }: { t: string; cls?: string; title?: string; role?: string }) {
  return <span className={cx('spv-c', cls)} role={role} title={title ?? t}><span>{t}</span></span>;
}

export function SpViewBody({ d, done, status, onStep, fileName }: {
  d: SFDoc | null; done: number; status: DetailStatus; onStep: (k: number) => void;
  /** 저장 때 만든 XLSX 이름 — undefined 면 불러오는 중, null 이면 만들지 못함 */
  fileName?: string | null;
}) {
  if (!d || done < 2) {
    return <StepSlot n={2} label="시트 작성" what="DSS 제품의 스펙 비교표 · XLSX" next={done === 1} cta={status === 'draft'} onOpen={() => onStep(2)} big />;
  }
  const rows = d.rows.filter((r) => r.on);
  const cols = d.items.map((k) => d.columns.find((c) => c.key === k) ?? { key: k, label: k, on: true });
  const warns = rows.flatMap((r) => r.warnings.map((w) => ({ t: `${r.name} · ${WARN_SHORT[w.kind] ?? '확인 필요'}`, full: `${r.name} · ${w.text}` })));
  const more = warns.slice(WARN_MAX);
  const opts: [string, string][] = [
    ['형식', FORMAT_KO[d.format] ?? d.format], ['표기', NOTATION_KO[d.notation] ?? d.notation], ['값', '공식 카탈로그'],
    ['파일', fileName === undefined ? '—' : fileName ?? 'XLSX 없음'],
  ];
  return (
    <div className="spv">
      <div className="fl-vbar spv-bar" data-testid="spv-options">
        {opts.map(([k, v]) => <span key={k} className="spv-opt" data-vopt={k}><b>{k}</b>{v}</span>)}
        <span className="spv-gap" />
        {warns.slice(0, WARN_MAX).map((w) => <span key={w.full} className="spv-warn" title={w.full}>{w.t}</span>)}
        {!!more.length && <span className="spv-warn" title={more.map((w) => w.full).join('\n')}>경고 +{more.length}</span>}
      </div>
      <div className="spv-panel" data-testid="spv-table">
        <div className="spv-grid" role="table" aria-label="스펙 비교표" style={{ gridTemplateColumns: `190px 160px repeat(${cols.length}, minmax(0, 1fr))` }}>
          <div role="row" className="spv-row">
            <C t="제품" cls="spv-c--h" role="columnheader" />
            <C t="공간 · 수량" cls="spv-c--h" role="columnheader" />
            {cols.map((c) => <C key={c.key} t={c.label} cls="spv-c--h" role="columnheader" />)}
          </div>
          {rows.map((r) => {
            const warn = !!r.warnings.length;
            return (
              <div key={r.key} role="row" className="spv-row" data-vrow={r.name}>
                <C t={r.name} cls={cx('spv-c--p', warn && 'spv-c--pw')} role="rowheader"
                  title={[r.model_code ? `${r.display_name ?? r.name} · ${r.model_code}` : r.name, ...r.warnings.map((w) => `⚠ ${w.text}`)].join('\n')} />
                <C t={spaceQty(r)} cls="spv-c--sq" title={r.qty_note ? `DSS · ${r.qty_note}${r.qty_edited ? ` → 수량 ${r.qty ?? P}(고침)` : ''}` : undefined} />
                {cols.map((c) => {
                  const v = r.cells[c.key] ?? P;
                  return <C key={c.key} t={v} cls={PENDING.has(v) ? 'spv-c--pend' : undefined} />;
                })}
              </div>
            );
          })}
        </div>
        {!rows.length && <div className="spv-empty">시트에 넣은 제품이 없어요 · 시트 작성 단계에서 제품을 골라 주세요</div>}
      </div>
      <span className="fl-vfoot">값은 공식 카탈로그에서 채워요 · 카탈로그에 없는 값은 [확인 필요]로 남겨요</span>
    </div>
  );
}
