/**
 * PR7P — 미리보기 · 시트 편집(§4.20, 보드 PR7P) — `/proposal/:id/preview/:sheetNo?`(`?filter=inferred` · `?panel=evidence` · `?export=1`).
 * 결과 툴바 | 레일(섹션별 시트 · 수정됨 · 확정 필요) | 큰 미리보기(요소 선택 → 미니 툴바) · 발표자 노트 · 시트 상태 | 시트 편집 패널
 * (선택 요소 필드 → 「적용」 = PATCH ops + If-Match rev, 「행 삭제」, 이 시트 다시 만들기(옵션 칩 · 재생성 · 템플릿 바꾸기), W와 대화).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, cx, toast } from '@/ui';
import { patchSheet, qk, rewriteSheet, useProposal, useSheet, useSheetMessages, useSlides } from '../api/proposal';
import { errText, isApiError, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import { ErrorBand, LoadingCard, Prompt, Rich, SpinIcon } from '../components/parts';
import { SlideThumb } from '../components/SlideThumb';
import { MiniToolbar, SlideView, fieldsAt, hasPlaceholder, valueAt, type SlideDoc, type SlideField, type SlideSel } from '../components/SlideView';
import { ResultToolbar, useExportParam } from '../components/ResultToolbar';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { ExportModal } from './ExportModal';

const REGEN = [['same_template', '같은 템플릿'], ['concise', '더 간결하게'], ['emphasize_numbers', '수치 강조']] as const;

export function PreviewPage() {
  const { id, no } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const filter = sp.get('filter');
  const panel = sp.get('panel');
  const sq = useSlides(id, filter);
  const sv = sq.data;
  const flat = useMemo(() => (sv?.sections ?? []).flatMap((s) => s.sheets.map((sh) => ({ ...sh, sectionName: s.name, sectionLabel: s.label, sectionKey: s.key }))), [sv]);
  const cur = flat.find((x) => String(x.sheet_no) === no) ?? flat[0];
  const idx = cur ? flat.indexOf(cur) : -1;
  const shq = useSheet(id, cur?.sheet_id);
  const sh = shq.data;
  const mq = useSheetMessages(id, cur?.sheet_id);
  const [sel, setSel] = useState<SlideSel | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [regen, setRegen] = useState<Record<string, boolean>>({ same_template: true, concise: false, emphasize_numbers: false });
  const [notesEdit, setNotesEdit] = useState<string | null>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const ex = useExportParam();
  useProposalShell({ p, step: 6 });

  useEffect(() => { setSel(null); setDraft({}); setNotesEdit(null); }, [cur?.sheet_id]);
  // 경로에 번호가 없으면 첫 시트 번호로
  useEffect(() => { if (id && !no && cur) nav(R.preview(id, cur.sheet_no, Object.fromEntries(sp.entries())), { replace: true }); }, [id, no, cur, nav, sp]);

  const refresh = () => {
    if (!id) return;
    void qc.invalidateQueries({ queryKey: qk.sub(id, 'sheet', cur?.sheet_id) });
    void qc.invalidateQueries({ queryKey: qk.sub(id, 'sheet-msgs', cur?.sheet_id) });
    void qc.invalidateQueries({ queryKey: qk.sub(id, 'slides') });
    void qc.invalidateQueries({ queryKey: qk.sub(id, 'confirm') });
  };
  const ev = useJobEvents(job, {
    onDone: (j) => { setJob(null); if (j.status === 'failed') toast(jobErrText(j.error)); refresh(); },
  });

  const doc = (sh?.display ?? sh?.content ?? null) as SlideDoc | null;
  const fields = fieldsAt(doc, sel);
  const val = (f: SlideField) => draft[f.path] ?? f.value;

  const patch = async (ops: Array<{ op: 'set' | 'insert' | 'delete' | 'move'; path: string; value?: unknown }>, reason: string, tag: string) => {
    if (!id || !sh) return false;
    setBusy(tag);
    try {
      const r = await patchSheet(id, sh.id, ops, sh.rev, reason);
      qc.setQueryData(qk.sub(id, 'sheet', sh.id), r.sheet);
      void qc.invalidateQueries({ queryKey: qk.sub(id, 'slides') });
      void qc.invalidateQueries({ queryKey: qk.sub(id, 'confirm') });
      if (r.resolved_item_ids?.length) toast(`확정 필요 ${r.resolved_item_ids.length}곳을 해결했어요`);
      return true;
    } catch (e) {
      if (isApiError(e) && e.code === 'REV_CONFLICT') { toast('다른 곳에서 이 시트가 바뀌었어요 · 새로 불러왔어요'); void shq.refetch(); }
      else toast(errText(e));
      return false;
    } finally { setBusy(null); }
  };
  const apply = async () => {
    const ops = fields.filter((f) => draft[f.path] !== undefined && draft[f.path] !== f.value).map((f) => ({ op: 'set' as const, path: f.path, value: draft[f.path] }));
    if (!ops.length) { toast('바뀐 내용이 없어요'); return; }
    if (await patch(ops, 'PR7P 필드 수정', 'apply')) setDraft({});
  };
  const del = async () => {
    if (!sel) return;
    if (await patch([{ op: 'delete', path: sel.path }], `${sel.label} 삭제`, 'delete')) { setSel(null); setDraft({}); toast(`${sel.label}을 지웠어요 · 버전에서 되돌릴 수 있어요`); }
  };
  const rewrite = async (b: { target_path?: string | null; instruction?: string | null; options?: Record<string, boolean> }, tag: string) => {
    if (!id || !sh) return;
    setBusy(tag);
    try { const r = await rewriteSheet(id, sh.id, b); setJob(r.job_id); void mq.refetch(); }
    catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const saveNotes = async () => {
    if (notesEdit === null) return;
    if (await patch([{ op: 'set', path: '/notes', value: notesEdit }], '발표자 노트 수정', 'notes')) setNotesEdit(null);
  };
  const go = (k: number) => { const t = flat[k]; if (t && id) nav(R.preview(id, t.sheet_no, Object.fromEntries(sp.entries()))); };

  if (pq.isError) return <div className="pr-page"><div className="pr-scroll"><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></div></div>;
  if (!p || !id) return <div className="pr-page"><div className="pr-scroll"><div className="pr-col"><LoadingCard /></div></div></div>;

  const tpl = sh?.template;
  const confirmOpen = (sh?.confirm_items ?? []).filter((c) => c.status === 'open');
  const statusLine = sh?.confirm_label || (confirmOpen.length ? `이 시트에 확정 필요 ${confirmOpen.length}곳 · ${confirmOpen.map((c) => c.text).join(' · ')}` : null);
  const msgs = mq.data?.items ?? [];
  const running = !!job;

  return (
    <div className="pr-res" data-testid="pr7p">
      <ResultToolbar id={id} tab="preview" fileName={sv?.file_name ?? p.title} pill={sv?.version_label ?? (p.version ? `v${p.version} · 수정 ${p.edits_since_version ?? 0}` : null)}
        meta={sv?.toolbar_label ?? (sv ? `시트 ${sv.sheets_total} + 표지 · 목차 · 자동 저장됨` : null)} openConfirm={sv?.open_confirm} onExport={() => ex.openExport()} />
      <div className="pr-resbody">
        <nav aria-label="슬라이드" className="pr-rail2" data-testid="pr7p-rail">
          <div className="pr-row pr-row--between" style={{ height: 20 }}>
            <b style={{ fontSize: 12.5 }}>시트 {sv?.sheets_total ?? flat.length}</b>
            <span className="pr-note" style={{ fontSize: 11.5 }}>{sv?.rail_label ?? (sv ? `표지 · 목차 포함 ${sv.slides_total}장` : '')}</span>
          </div>
          {filter === 'inferred' && (
            <div className="pr-filterchip">추론한 시트만<button type="button" aria-label="필터 해제" onClick={() => setSp((c) => { const x = new URLSearchParams(c); x.delete('filter'); return x; })}><Icon name="x" size={12} /></button></div>
          )}
          {sv && sv.sections.length > 0 && (
            <select aria-label="섹션으로 이동" className="pr-railsel" value={cur?.sectionKey ?? ''} onChange={(e) => { const s = sv.sections.find((x) => x.key === e.target.value); if (s?.sheets[0]) nav(R.preview(id, s.sheets[0].sheet_no, Object.fromEntries(sp.entries()))); }}>
              {sv.sections.map((s) => <option key={s.key} value={s.key}>{s.label || `${String(s.no).padStart(2, '0')} ${s.name}`}</option>)}
            </select>
          )}
          <div className="pr-rail2__list">
            {sq.isError ? <ErrorBand message={errText(sq.error)} onRetry={() => void sq.refetch()} /> : !sv ? <LoadingCard lines={5} /> : sv.sections.map((s) => (
              <div key={s.key} className="pr-colflex" style={{ gap: 2 }}>
                <div className="pr-rail2__label"><span>{s.label || `${String(s.no).padStart(2, '0')} ${s.name}`}</span><span className="pr-num">{s.sheets.length}</span></div>
                {s.sheets.map((r) => {
                  const on = r.sheet_id === cur?.sheet_id;
                  return (
                    <Link key={r.sheet_id} to={R.preview(id, r.sheet_no, Object.fromEntries(sp.entries()))} aria-label={r.aria_label || `${r.sheet_no} ${r.title}`} aria-current={on ? 'page' : undefined}
                      className={cx('pr-railrow', on && 'pr-railrow--on')} data-testid="pr7p-rail-sheet">
                      <span className="pr-railrow__no pr-num">{String(r.sheet_no).padStart(2, '0')}</span>
                      <span className="pr-colflex" style={{ gap: 4, minWidth: 0 }}>
                        <span className="pr-railrow__thumb">
                          <SlideThumb url={r.thumb_url} label={r.title} inferred={r.inferred} />
                          {r.edited && <span className="pr-railbadge pr-railbadge--dark">수정됨</span>}
                          {r.confirm && <span className="pr-railbadge pr-railbadge--brand">확정 필요</span>}
                        </span>
                        <span className="pr-ell pr-railrow__title">{r.title}</span>
                      </span>
                    </Link>
                  );
                })}
              </div>
            ))}
            {sv && flat.length === 0 && <div className="pr-empty">{filter === 'inferred' ? '추론으로 채운 시트가 없어요' : '아직 시트가 없어요'}</div>}
          </div>
        </nav>

        <section className="pr-rescenter" data-testid="pr7p-preview">
          {cur && (
            <div className="pr-row" style={{ height: 34, gap: 8 }}>
              <span className="pr-noblock pr-num">{String(cur.sheet_no).padStart(2, '0')}</span>
              <b className="pr-ell" style={{ fontSize: 15 }}>{sh?.title ?? cur.title}</b>
              <span className="pr-note" style={{ fontSize: 12.5, whiteSpace: 'nowrap' }}>{sh?.section_name ?? cur.sectionName}</span>
              {tpl?.code && sh && (
                <Link to={R.template(id, sh.section_key, sh.id)} className="pr-tplchip" data-testid="pr7p-template">
                  <b className="pr-num">{tpl.code}</b><span className="pr-muted pr-ell">{tpl.name ?? ''}</span><span className="pr-brand" style={{ fontWeight: 600 }}>바꾸기</span>
                </Link>
              )}
              <span className="pr-grow" />
              <button type="button" className="pr-navbtn" aria-label="이전 슬라이드" disabled={idx <= 0} onClick={() => go(idx - 1)}><Icon name="chevronLeft" size={14} strokeWidth={2.2} /></button>
              <span className="pr-num" style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-text-2)', whiteSpace: 'nowrap' }}>{cur.sheet_no} / {sv?.sheets_total ?? flat.length}</span>
              <button type="button" className="pr-navbtn" aria-label="다음 슬라이드" disabled={idx < 0 || idx >= flat.length - 1} onClick={() => go(idx + 1)}><Icon name="chevronRight" size={14} strokeWidth={2.2} /></button>
            </div>
          )}
          {shq.isError ? <ErrorBand message={errText(shq.error)} onRetry={() => void shq.refetch()} /> : !sh ? (cur ? <LoadingCard lines={6} /> : null) : (
            <>
              <div style={{ position: 'relative' }}>
                <SlideView doc={doc} no={sh.sheet_no} footer={p.title} renderUrl={sh.render?.url ?? sh.thumb_url} sel={sel?.path ?? null}
                  onSelect={(s) => { setSel(s); setDraft({}); }}
                  toolbar={sel && <MiniToolbar label={sel.kind === 'row' ? '선택한 행' : `선택한 ${sel.label}`}
                    onEdit={() => window.setTimeout(() => firstFieldRef.current?.focus(), 0)}
                    onRewrite={() => void rewrite({ target_path: sel.path, options: regen }, 'rw-el')}
                    onDelete={sel.deletable ? () => void del() : undefined} />} />
                {running && <div className="pr-slideoverlay"><SpinIcon size={16} /> W가 이 시트를 다시 쓰는 중이에요 · {Math.round(ev.progress)}%</div>}
              </div>
              <div className="pr-notescard" data-testid="pr7p-notes">
                <div className="pr-row pr-row--between"><b style={{ fontSize: 12 }}>발표자 노트</b><span className="pr-subtle" style={{ fontSize: 11.5 }}>{doc?.notes ? 'W 작성 · 눌러서 수정' : '눌러서 쓰기'}</span></div>
                {notesEdit !== null ? (
                  <>
                    <textarea className="pr-textarea" value={notesEdit} onChange={(e) => setNotesEdit(e.target.value)} rows={3} aria-label="발표자 노트" autoFocus />
                    <div className="pr-row" style={{ justifyContent: 'flex-end', gap: 6 }}>
                      <button type="button" className="pr-mini" onClick={() => setNotesEdit(null)}>취소</button>
                      <button type="button" className="pr-mini pr-mini--primary" onClick={() => void saveNotes()} disabled={busy === 'notes'}>저장</button>
                    </div>
                  </>
                ) : (
                  <button type="button" className="pr-notesbody" onClick={() => setNotesEdit(doc?.notes ?? '')}>{doc?.notes ? <Rich text={doc.notes} /> : <span className="pr-subtle">발표자 노트가 없어요</span>}</button>
                )}
              </div>
              {statusLine && (
                <div className="pr-sheetstatus" data-testid="pr7p-status">
                  <Icon name="info" size={15} color="var(--wm-brand)" />
                  <span className="pr-ell pr-grow">{statusLine}</span>
                  <Link to={R.confirm(id)} className="pr-link" style={{ fontSize: 12 }}>확정 필요 목록</Link>
                </div>
              )}
            </>
          )}
        </section>

        <aside aria-label="시트 편집" className="pr-resaside" data-testid="pr7p-edit">
          <div className="pr-resaside__head"><b style={{ fontSize: 14 }}>시트 편집</b><span className="pr-note">{cur ? `${String(cur.sheet_no).padStart(2, '0')} ${sh?.title ?? cur.title}` : ''}</span></div>
          {(panel === 'evidence' || sh?.inferred) && sh && (sh.evidence_note || sh.sources?.length) ? (
            <div className="pr-evidence" data-testid="pr7p-evidence">
              <div className="pr-row" style={{ gap: 6 }}><span className="pr-badge pr-badge--dark">추론</span><b style={{ fontSize: 12.5 }}>추론 근거</b></div>
              {sh.evidence_note && <span style={{ fontSize: 12.5, lineHeight: 1.55 }}>{sh.evidence_note}</span>}
              {!!sh.sources?.length && (
                <div className="pr-colflex" style={{ gap: 2 }}>
                  {sh.sources.slice(0, 5).map((s, i) => s.url
                    ? <a key={i} href={s.url} target="_blank" rel="noreferrer" className="pr-ell" style={{ fontSize: 11.5 }}>{s.label}</a>
                    : <span key={i} className="pr-ell pr-note">{s.label}</span>)}
                </div>
              )}
            </div>
          ) : null}
          <div className="pr-resaside__sec">
            {sel && fields.length ? (
              <>
                <div className="pr-row" style={{ gap: 6 }}>
                  <b style={{ fontSize: 12.5 }}>선택 · {sel.label}</b>
                  {(() => { const r = valueAt(doc, sel.path) as { new?: boolean; recent?: boolean } | undefined; return r && (r.new || r.recent) ? <span className="pr-badge pr-badge--dark" style={{ height: 18, fontSize: 10.5 }}>방금 추가</span> : null; })()}
                  <span className="pr-grow" />
                  <button type="button" className="pr-mini pr-mini--ghost" onClick={() => { setSel(null); setDraft({}); }}>선택 해제</button>
                </div>
                <div className="pr-fieldgrid">
                  {fields.map((f, i) => (
                    <div key={f.path} className={cx('pr-field', f.wide && 'pr-field--wide')}>
                      <label htmlFor={`pr7p-f-${i}`} style={{ fontSize: 11.5 }}>{f.label}</label>
                      <div className={cx('pr-editbox', i === 0 && 'pr-editbox--focus')}>
                        <input id={`pr7p-f-${i}`} ref={i === 0 ? firstFieldRef : undefined} value={val(f)} onChange={(e) => setDraft((d) => ({ ...d, [f.path]: e.target.value }))}
                          onKeyDown={(e) => { if (e.key === 'Enter') void apply(); }} data-testid="pr7p-field" />
                        {hasPlaceholder(val(f)) && <span className="pr-phpill">확정 필요</span>}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="pr-row" style={{ gap: 8, paddingTop: 2 }}>
                  {sel.deletable && <button type="button" className="pr-mini" style={{ height: 30 }} onClick={() => void del()} disabled={!!busy} data-testid="pr7p-delete">{sel.kind === 'row' ? '행 삭제' : '삭제'}</button>}
                  <span className="pr-grow" />
                  <button type="button" className="pr-mini pr-mini--primary" style={{ height: 30, padding: '0 14px' }} onClick={() => void apply()} disabled={!!busy} data-testid="pr7p-apply">{busy === 'apply' ? <SpinIcon size={12} color="currentColor" /> : null}적용</button>
                </div>
              </>
            ) : (
              <span className="pr-note" style={{ fontSize: 12.5 }}>미리보기에서 표 행 · 문단 · 이미지를 누르면 여기서 고칠 수 있어요.</span>
            )}
          </div>
          <div className="pr-resaside__div" />
          <div className="pr-resaside__sec">
            <div className="pr-row pr-row--between"><b style={{ fontSize: 12.5 }}>이 시트 다시 만들기</b><span className="pr-subtle" style={{ fontSize: 11.5 }}>다른 시트는 그대로</span></div>
            <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
              {REGEN.map(([k, l]) => <button key={k} type="button" className="pr-quick pr-quick--toggle" aria-pressed={!!regen[k]} onClick={() => setRegen((r) => ({ ...r, [k]: !r[k] }))}>{l}</button>)}
            </div>
            <div className="pr-row" style={{ gap: 8 }}>
              {sh && <Link to={R.template(id, sh.section_key, sh.id)} className="pr-mini" style={{ height: 34, padding: '0 12px', fontSize: 12.5 }}>템플릿 바꾸기</Link>}
              <button type="button" className="pr-mini pr-mini--primary pr-grow" style={{ height: 34, justifyContent: 'center', fontSize: 12.5 }} disabled={!sh || running || !!busy} onClick={() => void rewrite({ options: regen }, 'regen')} data-testid="pr7p-regen">
                {running ? <SpinIcon size={13} color="currentColor" /> : <Icon name="refresh" size={13} strokeWidth={2.2} />}이 시트 재생성</button>
            </div>
            {sh && (
              <Link to={normalizeRoute(p.sections?.find((s) => s.key === sh.section_key)?.route) ?? R.section(id, sh.section_key)} className="pr-link" style={{ fontSize: 12 }}>
                섹션 전체를 다시 쓰려면 {sh.section_name} 섹션 열기<Icon name="chevronRight" size={12} strokeWidth={2.4} /></Link>
            )}
          </div>
          <div className="pr-resaside__div" />
          <div className="pr-chat" data-testid="pr7p-chat">
            <div className="pr-chat__list">
              {msgs.slice(-6).map((m) => m.role === 'user'
                ? <div key={m.id} className="pr-chat__me">{m.text}</div>
                : (
                  <div key={m.id} className="pr-row" style={{ gap: 8, alignItems: 'flex-start' }}>
                    <span className="pr-chat__w">W</span>
                    <span className="pr-colflex" style={{ gap: 4, minWidth: 0 }}>
                      <span style={{ fontSize: 12.5, lineHeight: 1.55 }}><Rich text={m.text} /></span>
                      {!!m.change_ids?.length && <Link to={R.versions(id, { change: m.change_ids[0] })} className="pr-link" style={{ fontSize: 12 }}>바뀐 곳 보기 · 되돌리기</Link>}
                    </span>
                  </div>
                ))}
              {running && <div className="pr-row pr-note" style={{ gap: 6 }}><SpinIcon size={12} />W가 고치는 중이에요</div>}
            </div>
            <Prompt placeholder="이 시트 수정 요청" label="이 시트 수정 요청" busy={running || busy === 'chat'} onSend={(t) => rewrite({ instruction: t, options: regen }, 'chat')} testId="pr7p-ask" />
          </div>
        </aside>
      </div>
      {ex.open && <ExportModal proposalId={id} open onClose={ex.closeExport} initialLang={ex.lang} version={ex.version} />}
    </div>
  );
}

