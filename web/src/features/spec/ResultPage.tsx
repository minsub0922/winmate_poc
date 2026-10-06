/** SP3 — 시트 생성 결과(`/spec/:id`, 06-spec §4.10) */
import { useEffect, useState, type KeyboardEvent } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { PathIcon, cx, toast } from '@/ui';
import {
  createExport, downloadFile, errText, patchCell, saveSheet, useSheet, useSheetCache, waitExport, type Cell, type Row, type Sheet,
} from './api';
import { useRevise } from './revise';
import { Agent, BigButton, Dock, PromptInput, SpPage, UserBubble, useSpecShell } from './ui';

const DL = 'M12 4v12M6 10l6 6 6-6M4 20h16';
type Fmt = 'xlsx' | 'pdf' | 'pptx';

/** 시트 표(SP3) — 셀 클릭으로 그 자리 고치기 */
export function ResultTable({ s, editable, onSaved }: { s: Sheet; editable: boolean; onSaved: () => void }) {
  const [edit, setEdit] = useState<{ row: string; product: string; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const t = s.table!;
  const cols = s.products;
  const grid = { gridTemplateColumns: `1.2fr ${cols.map(() => '1fr').join(' ')}` };
  const existing = new Set(cols.filter((p) => p.role === 'existing').map((p) => p.id));
  const label = (r: Row) => `${r.label}${r.footnote_mark ? ` ${r.footnote_mark}` : ''}`;

  const save = async () => {
    if (!edit) return;
    setSaving(true);
    try {
      await patchCell(s.id, edit.row, edit.product, edit.text);
      setEdit(null);
      onSaved();
    } catch (e) { toast(errText(e)); } finally { setSaving(false); }
  };
  const start = (r: Row, c: Cell) => {
    if (!editable || r.row_key.startsWith('derived:')) return;
    setEdit({ row: r.id, product: c.product_id, text: c.state === 'pending' || c.state === 'sync_pending' ? '' : c.text });
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'Enter') { e.preventDefault(); void save(); }
    if (e.key === 'Escape') { e.preventDefault(); setEdit(null); }
  };

  return (
    <div className="sp-grid" style={grid} role="table" aria-label={t.title}>
      <div className="sp-th sp-th--label" role="columnheader">항목</div>
      {cols.map((p) => <div key={p.id} className={cx('sp-th', existing.has(p.id) && 'sp-th--existing')} role="columnheader">{p.column_label || p.display_name}</div>)}
      {t.rows.filter((r) => !r.hidden).map((r) => (
        <div key={r.id} className={cx('sp-grow', r.highlighted && 'sp-row--hl')} role="row" style={{ display: 'contents' }}>
          <div role="rowheader">{label(r)}</div>
          {(r.cells ?? []).map((c) => {
            const p = cols.find((x) => x.id === c.product_id);
            const editing = edit && edit.row === r.id && edit.product === c.product_id;
            const can = editable && !r.row_key.startsWith('derived:');
            const pending = c.state === 'pending' || c.state === 'sync_pending';
            return (
              <div key={c.product_id} role="cell" data-state={c.state} data-win={c.win ? 'true' : undefined}
                className={cx(c.win && 'sp-cell--win', pending && 'sp-cell--pending', c.state === 'edited' && 'sp-cell--edited',
                  existing.has(c.product_id) && 'sp-cell--existing', can && !editing && 'sp-cell--click')}
                tabIndex={can && !editing ? 0 : undefined}
                aria-label={can && !editing ? `${r.label} · ${p?.display_name ?? ''} 값 고치기: ${c.text}` : undefined}
                onClick={() => { if (!editing) start(r, c); }}
                onKeyDown={(e) => { if (!editing && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); start(r, c); } }}>
                {editing
                  ? <input className="sp-cellinput" autoFocus value={edit.text} disabled={saving} aria-label={`${r.label} · ${p?.display_name ?? ''} 값`}
                    onChange={(e) => setEdit({ ...edit, text: e.target.value })} onKeyDown={onKey} onBlur={() => setEdit(null)} />
                  : c.text}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

export default function ResultPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const loc = useLocation();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const cache = useSheetCache();
  const revise = useRevise(id, 'result');
  const [exporting, setExporting] = useState<Fmt | null>(null);
  const [saving, setSaving] = useState(false);

  useSpecShell(s, 3);

  // 아직 시트가 없거나 생성 중이면 이어서 할 화면으로
  useEffect(() => {
    if (!s) return;
    if ((!s.generated_at || s.ui_status === 'run') && s.resume_route && s.resume_route !== loc.pathname) nav(s.resume_route, { replace: true });
  }, [s, loc.pathname, nav]);

  if (sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;
  if (!s || !s.table) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const quick = async (format: Fmt) => {
    setExporting(format);
    try {
      const r = await createExport(s.id, { format });
      const rec = await waitExport(s.id, r.export_id);
      if (rec.status === 'done' && rec.file_id) downloadFile(rec.file_id, rec.filename);
      else toast(rec.error ?? '파일을 만들지 못했어요.');
    } catch (e) { toast(errText(e)); } finally { setExporting(null); }
  };
  const save = async () => {
    setSaving(true);
    try { cache.put(await saveSheet(s.id)); toast('저장했어요.'); } catch (e) { toast(errText(e)); } finally { setSaving(false); }
  };

  const t = s.table;
  const multi = s.products.length >= 2;
  const hl = s.options.highlight_wins !== false;
  const nWarn = s.warnings.open ?? 0;
  const qb = (f: Fmt, label: string, icon = true) => (
    <button type="button" className="sp-minibtn" onClick={() => void quick(f)} disabled={!!exporting} aria-busy={exporting === f || undefined}>
      {icon && <PathIcon d={DL} size={12} />}{exporting === f ? '만드는 중…' : label}
    </button>
  );

  return (
    <SpPage
      dock={
        <Dock title="Spec 시트" meta="3 / 3 · 완료"
          right={
            <div className="sp-chiprow">
              <button type="button" className="sp-pillbtn" onClick={() => nav(`/spec/${s.id}/products?mode=add`)}>제품 추가 비교</button>
              <button type="button" className="sp-pillbtn" onClick={() => nav(`/spec/${s.id}/edit`)}>항목 순서 바꾸기</button>
              <button type="button" className="sp-pillbtn" onClick={() => nav(`/spec/${s.id}/format?from=result&en=1`)}>영문 버전</button>
            </div>
          }
          row={
            <>
              <PromptInput label="수정 요청" placeholder="수정 요청 (예: 소비전력을 연간 전기료로 환산한 행 추가)" onSend={revise.send} busy={revise.busy} />
              <button type="button" className="sp-btn2" onClick={() => void save()} disabled={saving}>저장</button>
              <BigButton onClick={() => nav(`/spec/${s.id}/export`)}>제안서에 넣기</BigButton>
            </>
          }
        />
      }>
      <Agent text={s.agent?.sp3 ?? ''}>
        {nWarn > 0 && (
          <div className="sp-warnline" data-testid="sp-warnline">
            확인이 필요한 곳 <b className="sp-numf">{nWarn}</b> · <Link to={`/spec/${s.id}/warnings`} className="sp-link">보기</Link>
          </div>
        )}
        <div className="sp-card" data-testid="sp-sheet">
          <div className="sp-card__head">
            <div className="sp-card__title" data-testid="sp-sheet-title">{t.title}</div>
            <div className="sp-chiprow">
              {qb('xlsx', 'XLSX')}
              {qb('pdf', 'PDF')}
              {qb('pptx', '슬라이드 1장으로', false)}
            </div>
          </div>
          <ResultTable s={s} editable onSaved={() => void cache.refresh(s.id)} />
          {(t.footnotes ?? []).length > 0 && (
            <div className="sp-footnotes">{(t.footnotes ?? []).map((f) => <span key={f.mark}>{f.mark} {f.text}</span>)}</div>
          )}
          <div className="sp-card__foot">
            <span data-testid="sp-source-line">{t.source_line}</span>
            {multi && hl && <b data-testid="sp-win-count">우위 항목 {t.win_rows ?? 0}</b>}
          </div>
        </div>
      </Agent>
      {revise.userText && <UserBubble>{revise.userText}</UserBubble>}
      {revise.busy && <Agent text="요청을 반영하고 있어요…" />}
      {!revise.busy && revise.reply && <Agent text={revise.reply} />}
    </SpPage>
  );
}
