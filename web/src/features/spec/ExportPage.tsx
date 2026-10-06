/** SP4 — 내보내기 · 제안서로(`/spec/:id/export`, 06-spec §4.13) */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { Modal, PathIcon, cx, toast } from '@/ui';
import {
  createExport, createHandoff, downloadFile, errText, getPackage, isApiError, shareSheet, useSheet, waitExport, type Package, type Sheet,
} from './api';
import { useRevise } from './revise';
import { Agent, BigButton, Dock, PromptInput, SpPage, UserBubble, useSpecShell } from './ui';

type Fmt = 'xlsx' | 'pdf' | 'pptx';
type Tpl = 'SC-A' | 'SC-B' | 'SD-A';
type PType = 'standard' | 'quickwin' | 'solution';
const AGENT = "시트를 어디로 보낼까요? 파일로 내려받거나, 작성 중인 제안서의 '제품 스펙' 섹션에 바로 넣을 수 있어요. 숨긴 행은 빠지고 강조 · 각주 메모는 그대로 넘어갑니다.";
const FORMATS: Array<{ f: Fmt; name: string; note: string; icon: string; btn: string; ext: string }> = [
  { f: 'xlsx', name: 'Excel (.xlsx)', note: '값 수정 · 견적 첨부용', icon: 'M4 4h16v16H4z M4 10h16 M4 15h16 M10 4v16', btn: 'Excel 다운로드', ext: '.xlsx' },
  { f: 'pdf', name: 'PDF', note: '메일 · 인쇄용, 레이아웃 고정', icon: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h5', btn: 'PDF 다운로드', ext: '.pdf' },
  { f: 'pptx', name: 'PPT 슬라이드', note: '1장 · 삼성 B2B 표준 디자인', icon: 'M3 5h18v12H3z M8 21h8 M12 17v4', btn: 'PPT 다운로드', ext: '.pptx' },
];
const TPLS: Array<[Tpl, string]> = [['SC-A', '사양 비교표'], ['SC-B', '요구사항 대응표'], ['SD-A', '제품별 상세']];
const SECTION_NO: Record<string, string> = { standard: '08', quickwin: '05' };
const DL = 'M12 4v12M6 10l6 6 6-6M4 20h16';
const CHEV = 'M6 9l6 6 6-6';

interface Target { id: string; title: string; type: PType; section_no: string; subtitle?: string | null; linkId?: string }

function defaultTemplates(s: Sheet): Tpl[] {
  const spec: Tpl = s.products.length >= 2 ? 'SC-A' : 'SD-A';
  if (s.kind === 'req') return s.compliance?.include?.spec === false ? ['SC-B'] : ['SC-B', spec];
  return [spec];
}

function Check({ on, onChange, children }: { on: boolean; onChange: (v: boolean) => void; children: string }) {
  return (
    <button type="button" role="checkbox" aria-checked={on} className="sp-xcheck" onClick={() => onChange(!on)}>
      <span className="sp-xcheck__box"><PathIcon d="M5 12l5 5L20 7" size={9} strokeWidth={3.6} /></span>
      <span>{children}</span>
    </button>
  );
}

/** 제안서 시트 미리보기(패키지 첫 장) */
function SlidePreview({ pkg, sectionNo, footer }: { pkg: Package | null; sectionNo: string; footer: string }) {
  const sheet = pkg?.sheets[0];
  const d = (sheet?.data ?? {}) as {
    title?: string; columns?: Array<{ label: string } | string>;
    rows?: Array<{ label?: string; item?: string; highlighted?: boolean; footnote_mark?: string | null; cells?: Array<{ text: string; win?: boolean; pending?: boolean }>;
      requirement?: string; value?: string; verdict?: string }>;
    groups?: Array<{ name: string; rows: Array<{ label: string; text?: string; cells?: Array<{ text: string }> }> }>;
    footnotes?: Array<{ mark: string; text: string }>;
  };
  const cols = (d.columns ?? []).map((c) => (typeof c === 'string' ? c : c.label));
  let head: string[] = [];
  let body: Array<{ k: string; vals: Array<{ t: string; win?: boolean; pend?: boolean }>; hl?: boolean }> = [];
  if (sheet?.template === 'SC-A') {
    head = ['항목', ...cols];
    const withMark = (l: string, m?: string | null) => (m && !l.endsWith(m) ? `${l} ${m}` : l);
    body = (d.rows ?? []).map((r) => ({ k: withMark(r.label ?? '', r.footnote_mark), hl: r.highlighted,
      vals: (r.cells ?? []).map((c) => ({ t: c.text, win: c.win, pend: c.pending })) }));
  } else if (sheet?.template === 'SD-A') {
    head = ['항목', '값'];
    body = (d.groups ?? []).flatMap((g) => g.rows.map((r) => ({ k: r.label, vals: [{ t: r.text ?? r.cells?.[0]?.text ?? '' }] })));
  } else if (sheet?.template === 'SC-B') {
    head = cols.length ? cols : ['항목', '요구', '제안 값', '판정'];
    body = (d.rows ?? []).map((r) => ({ k: r.item ?? '', vals: [{ t: r.requirement ?? '' }, { t: r.value ?? '' }, { t: r.verdict ?? '' }] }));
  }
  const grid = { gridTemplateColumns: `104px ${head.slice(1).map(() => 'minmax(0, 1fr)').join(' ')}` };
  return (
    <div className="sp-slide" aria-label="제안서 시트 미리보기" role="img">
      <div className="sp-slide__bar" />
      <div className="sp-slide__sec">{sectionNo} · 제품 스펙</div>
      <div className="sp-slide__title">{d.title ?? ''}</div>
      <div className="sp-slide__table">
        <div className="sp-slide__row sp-slide__row--head" style={grid}>{head.map((h, i) => <span key={i}>{h}</span>)}</div>
        {body.slice(0, 9).map((r, i) => (
          <div key={i} className={cx('sp-slide__row', r.hl && 'sp-slide__row--hl')} style={grid}>
            <span>{r.k}</span>
            {r.vals.map((v, j) => <span key={j} className={cx(v.win && 'sp-slide__win', v.pend && 'sp-slide__pend')}>{v.t}</span>)}
          </div>
        ))}
      </div>
      {(d.footnotes ?? []).slice(0, 1).map((f) => <div key={f.mark} className="sp-slide__note">{f.mark} {f.text}</div>)}
      <div className="sp-slide__foot"><span>{footer}</span><span className="sp-numf">CONFIDENTIAL</span></div>
    </div>
  );
}

export default function ExportPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const revise = useRevise(id, 'export');
  useSpecShell(s, 3, { complete: true });

  const [fmt, setFmt] = useState<Fmt | null>(null);
  const [lang, setLang] = useState<string | null>(null);
  const [len, setLen] = useState<string | null>(null);
  const [dropHidden, setDropHidden] = useState(true);
  const [memoNotes, setMemoNotes] = useState(true);
  const [keepPending, setKeepPending] = useState(true);
  const [fname, setFname] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [tpls, setTpls] = useState<Tpl[] | null>(null);
  const [target, setTarget] = useState<Target | null | undefined>(undefined);
  const [mode, setMode] = useState<'replace' | 'add'>((sp.get('mode') as 'replace' | 'add') || 'replace');
  const [pkg, setPkg] = useState<Package | null>(null);
  const [sending, setSending] = useState(false);
  const [picker, setPicker] = useState(false);
  const [plist, setPlist] = useState<Target[] | null | 'error'>(null);

  // 기본값(시트 형식 · 연결 · 대상)
  useEffect(() => {
    if (!s || fmt) return;
    setFmt(((s.format.formats ?? ['xlsx'])[0] ?? 'xlsx') as Fmt);
    setLang(s.format.language ?? 'ko');
    setLen(s.format.length_unit ?? 'mm');
    setTpls(defaultTemplates(s));
    const linkParam = sp.get('link');
    const lk = (s.links ?? []).find((l) => l.id === linkParam) ?? (s.links ?? [])[0];
    const tp = s.target_proposal;
    if (lk && (linkParam || !tp)) setTarget({ id: lk.proposal_id, title: lk.proposal_title, type: 'standard', section_no: lk.section_no, linkId: lk.id });
    else if (tp) setTarget({ id: tp.id, title: tp.title, type: (tp.type ?? 'standard') as PType, section_no: tp.section_no ?? SECTION_NO[tp.type ?? 'standard'] ?? '08', subtitle: tp.subtitle });
    else setTarget(null);
  }, [s, fmt, sp]);

  const tplKey = (tpls ?? []).join(',');
  useEffect(() => {
    if (!s || !tpls?.length) return;
    let off = false;
    getPackage(s.id, tpls, lang ?? undefined).then((p) => { if (!off) setPkg(p); }).catch((e) => { if (!off) toast(errText(e)); });
    return () => { off = true; };
  }, [s?.id, s?.version, tplKey, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const meta = useMemo(() => FORMATS.find((x) => x.f === fmt) ?? FORMATS[0], [fmt]);
  if (sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;
  if (!s || !fmt || target === undefined) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const t = s.table;
  const hidden = t?.hidden_rows ?? 0;
  const memos = (t?.footnotes ?? []).length;
  const base = (fname ?? s.format.filename_base ?? s.agent?.filename_default ?? 'Spec').replace(/\.(xlsx|pdf|pptx)$/i, '');
  const overrides = { language: lang as 'ko' | 'en' | 'ko_en', length_unit: len as 'mm' | 'inch' | 'both', ...(len === 'inch' ? { weight_unit: 'lb' as const } : len === 'both' ? { weight_unit: 'both' as const } : {}) };
  const options = { drop_hidden: hidden ? dropHidden : true, memo_footnotes: memos ? memoNotes : true, keep_pending_marks: keepPending };

  const download = async () => {
    setDownloading(true);
    try {
      const r = await createExport(s.id, { format: fmt, overrides, options, filename: base });
      const rec = await waitExport(s.id, r.export_id);
      if (rec.status === 'done' && rec.file_id) downloadFile(rec.file_id, rec.filename);
      else toast(rec.error ?? '파일을 만들지 못했어요.');
    } catch (e) { toast(errText(e)); } finally { setDownloading(false); }
  };

  const handoff = async (toNew: boolean) => {
    setSending(true);
    try {
      const tg = toNew ? null : target;
      const r = await createHandoff(s.id, {
        proposal_id: tg?.id ?? null, proposal_type: tg?.type ?? 'standard', proposal_title: tg?.title ?? null, section_no: tg?.section_no ?? null,
        templates: tpls ?? undefined, mode, options,
      });
      nav(r.open_route);
    } catch (e) {
      toast(isApiError(e, 'NO_SPEC_SECTION') ? "Solution형 제안서에는 '제품 스펙' 섹션이 없어요." : errText(e));
    } finally { setSending(false); }
  };

  const share = async () => {
    try {
      const r = await shareSheet(s.id);
      await navigator.clipboard?.writeText(new URL(r.share_url, window.location.origin).href).catch(() => undefined);
      toast('링크를 복사했어요');
    } catch (e) { toast(errText(e)); }
  };

  const openPicker = async () => {
    setPicker(true);
    setPlist(null);
    try {
      const r = await fetch('/api/proposal/v1/proposals?limit=50', { credentials: 'same-origin' });
      if (!r.ok) throw new Error(String(r.status));
      const body = await r.json();
      const items = ((body.items ?? []) as Array<{ id: string; title: string; type?: string; proposal_type?: string }>)
        .map((p) => ({ id: p.id, title: p.title, type: (p.type ?? p.proposal_type ?? 'standard') as PType, section_no: SECTION_NO[p.type ?? p.proposal_type ?? 'standard'] ?? '08' }))
        .filter((p) => p.type !== 'solution');
      setPlist(items);
    } catch { setPlist('error'); }
  };

  const solution = target?.type === 'solution';
  const sectionNo = target?.section_no ?? '08';
  const already = !!target && (s.links ?? []).some((l) => l.proposal_id === target.id);
  const footer = [s.customer_name, target?.subtitle ?? target?.title].filter(Boolean).join(' · ');
  const hasComp = !!s.compliance && (s.compliance.rows ?? []).length > 0;

  return (
    <SpPage
      dock={
        <Dock title="내보내기" meta={`Spec 시트 완료 · ${s.agent?.saved_label ?? '저장 전'}`}
          right={
            <div className="sp-chiprow">
              <button type="button" className="sp-pillbtn" onClick={() => void handoff(true)} disabled={sending}>
                <PathIcon d="M12 5v14M5 12h14" size={12} strokeWidth={2.4} />새 제안서로 시작
              </button>
              <button type="button" className="sp-pillbtn" onClick={() => void share()}>
                <PathIcon d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" size={12} />링크로 공유
              </button>
            </div>
          }
          row={
            <>
              <PromptInput label="내보내기 요청" placeholder="요청 (예: 영문 PDF도 함께 만들어줘)" onSend={revise.send} busy={revise.busy} />
              <button type="button" className="sp-btn2" onClick={() => nav(`/spec/${s.id}`)}>이전</button>
              <BigButton onClick={() => void handoff(!target)} busy={sending} disabled={solution || !tpls?.length}>제안서에 넣기</BigButton>
            </>
          }
        />
      }>
      <Agent text={AGENT}>
        <div className="sp-xtwo">
          <section className="sp-xcard" aria-label="파일로 내보내기">
            <div className="sp-xcard__head">
              <span className="sp-xcard__ic"><PathIcon d={DL} size={16} /></span>
              <div className="sp-xcard__ht"><b>파일로 내보내기</b><span>고객에게 바로 보낼 때</span></div>
            </div>
            <div className="sp-xfmts" role="radiogroup" aria-label="파일 형식">
              {FORMATS.map((x) => (
                <button key={x.f} type="button" role="radio" aria-checked={fmt === x.f} className="sp-xfmt" onClick={() => setFmt(x.f)}>
                  <span className="sp-xfmt__ic"><PathIcon d={x.icon} size={15} strokeWidth={1.9} /></span>
                  <span className="sp-xfmt__t"><b>{x.name}</b><span>{x.note}</span></span>
                  <span className="sp-xfmt__radio" />
                </button>
              ))}
            </div>
            <div className="sp-xopts">
              <div className="sp-xopts__line">
                <label className="sp-dd"><span className="wm-sr-only">언어</span>
                  <select value={lang ?? 'ko'} onChange={(e) => setLang(e.target.value)}>
                    <option value="ko">한국어</option><option value="en">English</option><option value="ko_en">한/영 병기</option>
                  </select>
                  <PathIcon d={CHEV} size={11} strokeWidth={2.4} color="var(--wm-text-muted)" />
                </label>
                <label className="sp-dd"><span className="wm-sr-only">길이 단위</span>
                  <select value={len ?? 'mm'} onChange={(e) => setLen(e.target.value)}>
                    <option value="mm">mm</option><option value="inch">inch</option><option value="both">둘 다 표기</option>
                  </select>
                  <PathIcon d={CHEV} size={11} strokeWidth={2.4} color="var(--wm-text-muted)" />
                </label>
                <span style={{ flex: 1 }} />
                <button type="button" className="sp-link" onClick={() => nav(`/spec/${s.id}/format?from=export`)}>언어 · 단위 자세히</button>
              </div>
              {hidden > 0 && <Check on={dropHidden} onChange={setDropHidden}>{`숨긴 행 ${hidden}개 빼기`}</Check>}
              {memos > 0 && <Check on={memoNotes} onChange={setMemoNotes}>메모를 각주로 넣기</Check>}
              <Check on={keepPending} onChange={setKeepPending}>[확정 필요] 칸 표시 유지</Check>
            </div>
            <div className="sp-xname">
              <label htmlFor="sp-xfname">파일명</label>
              <div className="sp-xname__box"><input id="sp-xfname" value={`${base}${meta.ext}`} onChange={(e) => setFname(e.target.value)} /></div>
            </div>
            <span style={{ flex: 1 }} />
            <button type="button" className="sp-xdl" onClick={() => void download()} disabled={downloading} aria-busy={downloading || undefined}>
              <PathIcon d={DL} size={14} strokeWidth={2.2} />{downloading ? '파일을 만드는 중…' : meta.btn}
            </button>
          </section>

          <section className={cx('sp-xcard sp-xcard--main', solution && 'sp-dim')} aria-label="제안서 '제품 스펙'으로" aria-disabled={solution || undefined}>
            <div className="sp-xcard__head">
              <span className="sp-xcard__ic sp-xcard__ic--brand"><PathIcon d="M3 4h18v12H3z M8 20h8 M12 16v4 M7 12l3-3 2 2 4-4" size={16} strokeWidth={1.9} /></span>
              <div className="sp-xcard__ht">
                <b>제안서 '제품 스펙'으로<span className="sp-xrec">추천</span></b>
                <span>시트째 넣고, 시트와 연결을 유지해요</span>
              </div>
            </div>
            <div className="sp-xtarget" data-testid="sp-target">
              <div className="sp-xtarget__t">
                {target ? (
                  <>
                    <b>{target.title}</b>
                    <span>{sectionNo} 제품 스펙</span>
                  </>
                ) : (
                  <>
                    <b className="sp-muted">넣을 제안서가 아직 없어요</b>
                    <span>새 제안서로 시작하거나 제안서를 골라 주세요</span>
                  </>
                )}
              </div>
              <button type="button" className="sp-link sp-xtarget__chg" onClick={() => void openPicker()}>바꾸기<PathIcon d={CHEV} size={11} strokeWidth={2.4} /></button>
            </div>
            {solution && <div className="sp-note" role="alert">Solution형 제안서에는 '제품 스펙' 섹션이 없어요.</div>}
            <div className="sp-chiprow" role="group" aria-label="시트 종류">
              {TPLS.map(([k, label]) => {
                const on = (tpls ?? []).includes(k);
                const disabled = k === 'SC-B' && !hasComp;
                return (
                  <button key={k} type="button" className="sp-chip sp-chip--h28" aria-pressed={on} disabled={disabled}
                    onClick={() => setTpls((cur) => { const c = cur ?? []; const n = on ? c.filter((x) => x !== k) : [...c, k]; return n.length ? n : c; })}>{label}</button>
                );
              })}
            </div>
            <SlidePreview pkg={pkg} sectionNo={sectionNo} footer={footer} />
            <div className="sp-xcarry" data-testid="sp-carry">
              {(pkg?.lines ?? []).map((ln) => (
                <div key={ln} className="sp-xcarry__line"><PathIcon d="M5 12l5 5L20 7" size={13} strokeWidth={2.6} color="var(--wm-brand)" /><span>{ln}</span></div>
              ))}
            </div>
            {already && (
              <div className="sp-xexist">
                <span>이 섹션에 '스펙 비교' 시트가 이미 있어요</span>
                <div className="sp-xexist__radios" role="radiogroup" aria-label="기존 시트 처리">
                  {([['replace', '새 버전으로 교체'], ['add', '시트 하나 더 추가']] as const).map(([k, label]) => (
                    <button key={k} type="button" role="radio" aria-checked={mode === k} className="sp-wc__radio" onClick={() => setMode(k)}>
                      <span className="sp-wc__dot" />{label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>
      </Agent>
      {revise.userText && <UserBubble>{revise.userText}</UserBubble>}
      {revise.busy && <Agent text="요청을 처리하고 있어요…" />}
      {!revise.busy && revise.reply && <Agent text={revise.reply} />}

      <Modal open={picker} onClose={() => setPicker(false)} title="제안서 고르기" width={480}>
        {plist === null && <div className="sp-note">제안서 목록을 불러오는 중…</div>}
        {plist === 'error' && <div className="sp-note" role="alert">제안서 목록을 불러오지 못했어요. 새 제안서로 시작할 수 있어요.</div>}
        {Array.isArray(plist) && !plist.length && <div className="sp-note">넣을 수 있는 제안서(표준 · 퀵윈)가 없어요.</div>}
        {Array.isArray(plist) && plist.length > 0 && (
          <div className="sp-menu sp-menu--static" role="listbox" aria-label="제안서">
            {plist.map((p) => (
              <button key={p.id} type="button" role="option" aria-selected={target?.id === p.id}
                onClick={() => { setTarget(p); setPicker(false); }}>{p.title} · {p.section_no} 제품 스펙</button>
            ))}
          </div>
        )}
      </Modal>
    </SpPage>
  );
}
