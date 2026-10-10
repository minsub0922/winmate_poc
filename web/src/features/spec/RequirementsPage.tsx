/** SP1R — 고객 요구 스펙 대응표(`/spec/legacy/new/requirements` → `/spec/:id/requirements`, 06-spec §4.6) */
import { useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { uploadFile } from '@/api/client';
import { useJob } from '@/api/jobs';
import { useShellPage } from '@/shell/ShellContext';
import { Button, Dropzone, Icon, Modal, ProductInput, Spinner, cx, toast, useEscape, type ProductToken } from '@/ui';
import {
  addRequirementDoc, complianceToItems, createSheet, errText, getAskDraft, getPage, patchCompliance, useSheet, useSheetCache,
  type AskDraft, type ComplianceRow, type PageView, type Sheet,
} from './api';
import { Agent, BigButton, Chip2, Dock, PromptInput, SECTION, SpPage, VIcon, stepper } from './ui';

const VERDICT = { pass: '충족', fail: '미충족', unknown: '확인 필요' } as const;
const ACCEPT = '.pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.txt';

export default function RequirementsPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id, { poll: (x) => (x?.compliance?.status === 'running' ? 1500 : false) });
  const s = sheetQ.data;
  const cache = useSheetCache();
  const comp = s?.compliance;
  const [job, setJob] = useState<string | null>(null);
  const [stepNote, setStepNote] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [filter, setFilter] = useState<'pass' | 'fail' | 'unknown' | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [quote, setQuote] = useState<{ row: ComplianceRow; x: number; y: number } | null>(null);
  const [page, setPage] = useState<PageView | null>(null);
  const [ask, setAsk] = useState<AskDraft | null>(null);
  const [targetMenu, setTargetMenu] = useState(false);
  const [pickOther, setPickOther] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const creating = useRef<Promise<Sheet> | null>(null);

  useJob(job, {
    onEvent: (e) => { if (e.type === 'step' && e.data?.note) setStepNote(String(e.data.note)); },
    onDone: (r) => { setJob(null); setStepNote(null); void cache.refresh(r.ref ?? id ?? ''); if (r.status === 'failed') toast(r.error?.message ?? '규격서를 읽지 못했어요.'); },
  });

  const ensure = async (): Promise<Sheet> => {
    if (s) return s;
    if (!creating.current) creating.current = createSheet({ start: 'requirements' });
    const made = await creating.current;
    cache.put(made);
    nav(`/spec/${made.id}/requirements`, { replace: true });
    return made;
  };

  const onFiles = async (files: File[]) => {
    const f = files[0];
    if (!f) return;
    setUploading(f.name);
    try {
      const sheet = await ensure();
      const meta = await uploadFile(f, { confidential: true, purpose: 'sp.requirements', projectId: sheet.project_id ?? undefined });
      const r = await addRequirementDoc(sheet.id, meta.id, note.trim() || undefined);
      setJob(r.job_id);
      void cache.refresh(sheet.id);
    } catch (e) { toast(errText(e)); } finally { setUploading(null); }
  };

  const rows = comp?.rows ?? [];
  const counts = comp?.counts ?? { pass: 0, fail: 0, unknown: 0 };
  const shown = filter ? rows.filter((r) => r.verdict === filter) : rows;
  const visible = expanded || filter ? shown : shown.slice(0, 8);
  const target = s?.products.find((p) => p.id === comp?.target_product_id);
  const altLabel = comp?.alternative_label;
  const inc = comp?.include ?? { table: true, spec: true, page_refs: true, alternative: false };
  const running = !!job || comp?.status === 'running' || !!uploading;
  const doc = comp?.docs?.[comp.docs.length - 1];

  const setInclude = async (k: 'table' | 'spec' | 'page_refs' | 'alternative', v: boolean) => {
    if (!s) return;
    try { const c = await patchCompliance(s.id, { include: { [k]: v } }); cache.qc.setQueryData(['spec', 'sheet', s.id], (o: Sheet | undefined) => (o ? { ...o, compliance: c } : o)); }
    catch (e) { toast(errText(e)); }
  };
  const setTarget = async (body: { target_product_id?: string; target_ref?: string }) => {
    if (!s) return;
    setTargetMenu(false);
    try { await patchCompliance(s.id, body); void cache.refresh(s.id); } catch (e) { toast(errText(e)); }
  };
  const openQuote = (row: ComplianceRow, el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    setQuote({ row, x: r.left, y: r.bottom });
  };
  const openPage = async (n: number) => {
    if (!s || !doc) return;
    try { setPage(await getPage(s.id, doc.id, n)); } catch (e) { toast(errText(e)); }
  };
  const toItems = async () => {
    if (!s) return;
    setBusy(true);
    try { cache.put(await complianceToItems(s.id)); nav(`/spec/${s.id}/items`); } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };

  useShellPage({ section: SECTION, title: s?.title_confirmed ? s.title : '새 작업', hasTask: true, stepper: stepper(1) });

  const hasTable = comp?.status === 'done' && rows.length > 0;
  return (
    <SpPage
      dock={
        <Dock title="고객 요구 스펙" meta={`요구 ${rows.length}개 · 1 / 3`}
          right={<button type="button" className="sp-link" onClick={() => fileInput.current?.click()} disabled={running}>{hasTable ? '다른 규격서 올리기' : '규격서 올리기'}</button>}
          row={
            hasTable ? (
              <>
                <Button h={44} onClick={async () => { try { setAsk(await getAskDraft(s!.id)); } catch (e) { toast(errText(e)); } }} disabled={!counts.unknown}>
                  확인 필요 {counts.unknown}건 담당자에게 묻기
                </Button>
                <Button h={44} onClick={() => nav(`/spec/${s!.id}/find?preset=alternatives`)} disabled={!counts.fail}>대안 모델 찾기</Button>
                <span style={{ flex: 1 }} />
                <BigButton onClick={() => void toItems()} busy={busy}>대응표로 시트 만들기</BigButton>
              </>
            ) : (
              <>
                <PromptInput label="함께 쓸 말" placeholder="규격서와 함께 전할 말 (예: 이 규격서 기준으로 QM55C 대응표를 만들어 주세요)"
                  onSend={(t) => { setNote(t); fileInput.current?.click(); }} busy={running} />
                <BigButton disabled title="규격서를 먼저 올려 주세요">대응표로 시트 만들기</BigButton>
              </>
            )
          }>
          <input ref={fileInput} type="file" hidden accept={ACCEPT} onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) void onFiles([f]); }} />
          {hasTable && (
            <div className="sp-chiprow" role="group" aria-label="시트에 넣기">
              <span style={{ fontSize: 12, color: 'var(--wm-text-muted)', fontWeight: 600, marginRight: 4 }}>시트에 넣기</span>
              <Chip2 h={30} on={!!inc.table} onClick={() => void setInclude('table', !inc.table)}>요구사항 대응표</Chip2>
              <Chip2 h={30} on={!!inc.spec} onClick={() => void setInclude('spec', !inc.spec)}>{target?.display_name ?? '모델'} 스펙표</Chip2>
              <Chip2 h={30} on={!!inc.page_refs} onClick={() => void setInclude('page_refs', !inc.page_refs)}>원문 쪽 번호 표기</Chip2>
              {altLabel && <Chip2 h={30} on={!!inc.alternative} onClick={() => void setInclude('alternative', !inc.alternative)}>대안 모델 {altLabel} 비교</Chip2>}
            </div>
          )}
          {!hasTable && note && <div className="sp-note">함께 쓸 말: {note}</div>}
        </Dock>
      }>
      {doc && (
        <div className="sp-filecard">
          <div className="sp-file" data-testid="sp1r-file">
            <span className="sp-file__ic">{doc.format}</span>
            <div>
              <div className="sp-file__name">{doc.name}</div>
              <div className="sp-file__meta">{doc.format} · {doc.pages || '…'}쪽 · {doc.status === 'done' ? `요구 항목 ${doc.recognized}개 인식` : '읽는 중'}</div>
            </div>
          </div>
          {comp?.note && <div className="sp-user">{comp.note}</div>}
        </div>
      )}
      {!doc && uploading && <div className="sp-filecard"><div className="sp-file"><Spinner /><span className="sp-file__name">{uploading}</span></div></div>}
      {!doc && !uploading && (
        <Agent text="고객 요구 규격서를 올려 주세요. 요구 항목을 찾아 카탈로그 스펙과 맞춰 보고 대응표를 만들어 드려요.">
          <Dropzone onFiles={(fs) => void onFiles(fs)} accept={ACCEPT} multiple={false} title="규격서를 끌어 놓거나 눌러서 고르기" hint="PDF · DOCX · XLSX · 이미지 · 고객 자료는 기밀로 다뤄요" />
        </Agent>
      )}
      {doc && running && <Agent text={stepNote ?? '규격서를 읽고 있어요'}><Spinner /></Agent>}
      {comp?.status === 'failed' && !running && <Agent text={`규격서를 읽지 못했어요. ${comp.error ?? ''}`} />}
      {hasTable && !running && (
        <Agent text={comp?.agent_text}>
          <div className="sp-card" data-testid="sp1r-table">
            <div className="sp-card__head">
              <div className="sp-card__title">
                요구사항 대응표
                <span style={{ position: 'relative', fontWeight: 500, color: 'var(--wm-text-muted)' }}>
                  <button type="button" className="sp-link" style={{ fontSize: 12.5 }} aria-haspopup="menu" aria-expanded={targetMenu} onClick={() => setTargetMenu((v) => !v)}>
                    대응 모델 {target?.display_name ?? '—'}<Icon name="chevronDown" size={13} />
                  </button>
                  {targetMenu && (
                    <div className="sp-menu" role="menu" style={{ top: 24, left: 0 }}>
                      {s!.products.map((p) => <button key={p.id} type="button" role="menuitem" onClick={() => void setTarget({ target_product_id: p.id })}>{p.display_name}</button>)}
                      <button type="button" role="menuitem" onClick={() => { setTargetMenu(false); setPickOther(true); }}>다른 모델 고르기…</button>
                    </div>
                  )}
                </span>
              </div>
              <div className="sp-chiprow">
                {(['pass', 'fail', 'unknown'] as const).map((k) => (
                  <button key={k} type="button" className="sp-chip sp-chip--h28" aria-pressed={filter === k || (k === 'unknown' && !filter && counts.unknown > 0)}
                    onClick={() => setFilter(filter === k ? null : k)} data-testid={`sp1r-sum-${k}`}>
                    <VIcon state={k} size={14} />{VERDICT[k]} {counts[k as keyof typeof counts] ?? 0}
                  </button>
                ))}
              </div>
            </div>
            <div className="sp-req" role="table">
              <div className="sp-th" role="columnheader">요구 항목</div><div className="sp-th" role="columnheader">고객 요구</div>
              <div className="sp-th" role="columnheader">{target?.display_name ?? '모델'}</div><div className="sp-th" role="columnheader">판정</div>
              <div className="sp-th" role="columnheader">원문</div>
              {visible.map((r) => (
                <ReqRow key={r.id} r={r} onAlt={() => nav(`/spec/${s!.id}/find?preset=row:${r.id}`)} onQuote={openQuote} />
              ))}
            </div>
            {!expanded && !filter && comp?.folded_line && (
              <div className="sp-more"><button type="button" className="sp-link" onClick={() => setExpanded(true)}>{comp.folded_line}</button></div>
            )}
            <div className="sp-card__foot">
              <span>원문 쪽 번호를 누르면 해당 문장이 표시됩니다</span>
              <button type="button" className="sp-link" onClick={() => void openPage(rows.find((r) => r.page)?.page ?? 1)}>원문과 나란히 보기</button>
            </div>
          </div>
        </Agent>
      )}
      {quote && <QuotePop q={quote} onClose={() => setQuote(null)} onPage={(n) => { setQuote(null); void openPage(n); }} />}
      <Modal open={!!page} onClose={() => setPage(null)} title={page ? `원문 p.${page.page}` : ''} width={900}>
        {page && <PageSide page={page} docPages={doc?.pages ?? 1} onPage={(n) => void openPage(n)} />}
      </Modal>
      <Modal open={!!ask} onClose={() => setAsk(null)} title={`확인 필요 ${ask?.count ?? 0}건 담당자에게 묻기`} width={560}
        footer={<>
          <Button onClick={() => { void navigator.clipboard?.writeText(ask?.text ?? ''); toast('초안을 복사했어요.'); }}>복사</Button>
          <Button variant="primary" onClick={() => { window.location.href = ask?.mailto ?? 'mailto:'; }}>메일로 열기</Button>
        </>}>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, margin: 0, lineHeight: 1.6 }}>{ask?.text}</pre>
      </Modal>
      <PickModel open={pickOther} onClose={() => setPickOther(false)} onPick={(ref) => { setPickOther(false); void setTarget({ target_ref: ref }); }} />
    </SpPage>
  );
}

function ReqRow({ r, onAlt, onQuote }: { r: ComplianceRow; onAlt: () => void; onQuote: (r: ComplianceRow, el: HTMLElement) => void }) {
  return (
    <div style={{ display: 'contents' }} className={cx(r.verdict === 'fail' && 'sp-req__fail')} role="row" data-testid="sp1r-row" data-item={r.item}>
      <div role="cell" style={r.verdict === 'fail' ? { background: 'var(--wm-bg)' } : undefined}>{r.item}</div>
      <div role="cell" style={r.verdict === 'fail' ? { background: 'var(--wm-bg)' } : undefined}>{r.requirement}</div>
      <div role="cell" style={{ fontWeight: 600, ...(r.value_text === '—' ? { color: 'var(--wm-text-subtle)' } : {}), ...(r.verdict === 'fail' ? { background: 'var(--wm-bg)' } : {}) }}>
        <span className="wm-ellipsis">{r.value_text}</span></div>
      <div role="cell" style={r.verdict === 'fail' ? { background: 'var(--wm-bg)' } : undefined}>
        <span className="sp-verdict">
          <VIcon state={r.verdict} size={16} />
          <span style={{ fontWeight: 600 }}>{VERDICT[r.verdict]}</span>
          {r.alternative && <span className="sp-verdict__note">대안 {r.alternative.label}</span>}
          {r.alternative && <button type="button" className="sp-link" style={{ fontSize: 11.5 }} onClick={onAlt}>대안 보기</button>}
          {!r.alternative && r.note && <span className="sp-verdict__note">{r.note}</span>}
        </span>
      </div>
      <div role="cell" style={r.verdict === 'fail' ? { background: 'var(--wm-bg)' } : undefined}>
        {r.page ? <button type="button" className="sp-pref" onClick={(e) => onQuote(r, e.currentTarget)}>p.{r.page}</button> : <span className="sp-muted">—</span>}
      </div>
    </div>
  );
}

function QuotePop({ q, onClose, onPage }: { q: { row: ComplianceRow; x: number; y: number }; onClose: () => void; onPage: (n: number) => void }) {
  useEscape(onClose);
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 40 }} onClick={onClose}>
      <div className="sp-quote" role="dialog" aria-label="원문 문장" style={{ left: Math.min(q.x - 260, window.innerWidth - 340), top: q.y + 6 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontSize: 11.5, color: 'var(--wm-text-muted)', marginBottom: 4 }}>원문 p.{q.row.page}</div>
        <div data-testid="sp1r-quote">“{q.row.quote}”</div>
        <div style={{ marginTop: 8 }}><button type="button" className="sp-link" onClick={() => onPage(q.row.page ?? 1)}>원문과 나란히 보기</button></div>
      </div>
    </div>
  );
}

function PageSide({ page, docPages, onPage }: { page: PageView; docPages: number; onPage: (n: number) => void }) {
  const parts = useMemo(() => {
    let text = page.text || '';
    const marks = (page.quotes ?? []).map((q) => q.text).filter(Boolean);
    const out: Array<{ t: string; m: boolean }> = [];
    while (text) {
      const hit = marks.map((m) => ({ m, i: text.indexOf(m) })).filter((x) => x.i >= 0).sort((a, b) => a.i - b.i)[0];
      if (!hit) { out.push({ t: text, m: false }); break; }
      if (hit.i > 0) out.push({ t: text.slice(0, hit.i), m: false });
      out.push({ t: hit.m, m: true });
      text = text.slice(hit.i + hit.m.length);
    }
    return out;
  }, [page]);
  return (
    <div className="sp-pageview">
      {page.image_url && <img src={page.image_url} alt={`원문 ${page.page}쪽`} />}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>
          {parts.map((p, i) => (p.m ? <mark key={i} className="sp-mark">{p.t}</mark> : <span key={i}>{p.t}</span>))}
        </div>
        <div className="sp-chiprow">
          {Array.from({ length: Math.max(1, docPages) }, (_, i) => i + 1).map((n) => (
            <Chip2 key={n} h={28} on={n === page.page} onClick={() => onPage(n)}>p.{n}</Chip2>
          ))}
        </div>
      </div>
    </div>
  );
}

function PickModel({ open, onClose, onPick }: { open: boolean; onClose: () => void; onPick: (ref: string) => void }) {
  const [v, setV] = useState<ProductToken[]>([]);
  return (
    <Modal open={open} onClose={onClose} title="대응 모델 고르기" variant="dialog" width={520}
      footer={<><Button onClick={onClose}>취소</Button><Button variant="primary" disabled={!v.length} onClick={() => v[0]?.ref && onPick(v[0].ref)}>이 모델로 판정</Button></>}>
      <ProductInput value={v} onChange={(n) => setV(n.slice(-1))} placeholder="모델명 입력…" placement="bottom" allowCustom={false} autoFocus />
    </Modal>
  );
}
