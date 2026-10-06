/** SP2L — 출력 형식 · 언어 · 단위(`/spec/:id/format`, 06-spec §4.8 · §4.16 · §4.18) */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { uploadFile } from '@/api/client';
import { useJob } from '@/api/jobs';
import { PathIcon, cx, josa, toast } from '@/ui';
import {
  addTemplate, errText, formatPreview, generate, isApiError, putFormat, removeTemplate, savePreferences, useSheet, useSheetCache,
  type FormatPreview, type FormatSettings, type Sheet,
} from './api';
import { Agent, BigButton, Dock, SpPage, UserBubble, useSpecShell } from './ui';

type Fmt = 'xlsx' | 'pdf' | 'pptx';
type Tab = Fmt;
const FMT_NAME: Record<Fmt, string> = { xlsx: 'Excel', pdf: 'PDF', pptx: 'PPT 슬라이드' };
const TAB_ICON: Record<Tab, string> = { xlsx: 'M4 4h16v16H4z M4 10h16 M10 4v16', pdf: 'M6 3h8l5 5v13H6V3z M14 3v5h5', pptx: 'M3 5h18v12H3z M8 21h8 M12 17v4' };
const PAPER_RATIO: Record<string, string> = { a4_landscape: '297 / 210', a4_portrait: '210 / 297', letter: '279 / 216' };

type Key = keyof Omit<FormatSettings, 'filename_base' | 'formats'>;
const GROUPS: Array<{ label: string; key: Key | 'formats'; chips: Array<[string, string]> }> = [
  { label: '형식', key: 'formats', chips: [['xlsx', 'Excel'], ['pdf', 'PDF'], ['pptx', 'PPT 슬라이드']] },
  { label: '언어', key: 'language', chips: [['ko', '한국어'], ['en', 'English'], ['ko_en', '한/영 병기']] },
  { label: '길이', key: 'length_unit', chips: [['mm', 'mm'], ['inch', 'inch'], ['both', '둘 다 표기']] },
  { label: '무게', key: 'weight_unit', chips: [['kg', 'kg'], ['lb', 'lb'], ['both', '둘 다 표기']] },
  { label: '용지', key: 'paper', chips: [['a4_landscape', 'A4 가로'], ['a4_portrait', 'A4 세로'], ['letter', 'Letter']] },
  { label: '숫자', key: 'number_format', chips: [['1,234.5', '1,234.5'], ['1.234,5', '1.234,5']] },
];

/** `Excel과 PDF로` · `Excel로` · `Excel, PDF와 PPT 슬라이드로` */
function formatList(fs: Fmt[]): string {
  const names = (['xlsx', 'pdf', 'pptx'] as Fmt[]).filter((f) => fs.includes(f)).map((f) => FMT_NAME[f]);
  if (!names.length) return '';
  // 세 이름(Excel · PDF · PPT 슬라이드) 모두 `로` 를 받는다(ㄹ 받침 · 모음 끝)
  const ro = `${names[names.length - 1]}로`;
  if (names.length === 1) return ro;
  const head = names.slice(0, -1);
  const prev = head[head.length - 1];
  return `${head.slice(0, -1).map((x) => `${x}, `).join('')}${prev}${josa(prev, '과', '와')} ${ro}`;
}

function basisText(f: FormatSettings): string {
  const lang = { ko: '한국어', en: '영문', ko_en: '한/영 병기' }[f.language ?? 'ko'];
  const len = { mm: 'mm', inch: 'inch', both: 'mm · inch' }[f.length_unit ?? 'mm'];
  const wt = { kg: 'kg', lb: 'lb', both: 'kg · lb' }[f.weight_unit ?? 'kg'];
  return `${lang} · ${len} · ${wt}`;
}

function initial(s: Sheet, english: boolean): FormatSettings {
  const base: FormatSettings = { ...s.format };
  const draft = s.format_draft ?? {};
  for (const [k, v] of Object.entries(draft)) if (v !== null && v !== undefined) (base as Record<string, unknown>)[k] = v;
  if (english) Object.assign(base, { language: 'en', length_unit: 'inch', weight_unit: 'lb' });
  if (!base.formats?.length) base.formats = ['xlsx'];
  return base;
}

export default function FormatPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const cache = useSheetCache();
  const from = sp.get('from') ?? '';
  const english = sp.get('en') === '1';
  const [f, setF] = useState<FormatSettings | null>(null);
  const [tab, setTab] = useState<Tab>('xlsx');
  const [pv, setPv] = useState<FormatPreview | null>(null);
  const [savedPref, setSavedPref] = useState(false);
  const [busy, setBusy] = useState(false);
  const [tplJob, setTplJob] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const seq = useRef(0);

  useEffect(() => {
    if (!s || f) return;
    const init = initial(s, english);
    setF(init);
    setTab((init.formats?.[0] as Tab) ?? 'xlsx');
  }, [s, f, english]);

  useSpecShell(s, 2);

  // 칩을 바꿀 때마다 미리보기(결정적 · 동기)
  const tplStatus = s?.template?.status;
  useEffect(() => {
    if (!s || !f) return;
    const n = ++seq.current;
    const t = window.setTimeout(() => {
      formatPreview(s.id, { ...f, tab })
        .then((r) => { if (n === seq.current) setPv(r); })
        .catch((e) => { if (n === seq.current) toast(errText(e)); });
    }, 120);
    return () => window.clearTimeout(t);
  }, [s?.id, f, tab, tplStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  useJob(tplJob, {
    onDone: (j) => {
      setTplJob(null);
      void cache.refresh(id);
      if (j.status === 'failed') toast(j.error?.message ?? '양식을 읽지 못했어요.');
    },
  });

  if (sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;
  if (!s || !f) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const set = (key: Key | 'formats', v: string) => {
    if (key === 'formats') {
      const cur = (f.formats ?? []) as Fmt[];
      const has = cur.includes(v as Fmt);
      if (has && cur.length === 1) return; // 최소 1
      const next = has ? cur.filter((x) => x !== v) : [...cur, v as Fmt];
      setF({ ...f, formats: next });
      if (has && tab === v) setTab(next[0] as Tab);
      return;
    }
    const next = { ...f, [key]: v } as FormatSettings;
    // 길이를 inch 로 바꾸면 무게 단위는 사용자가 따로 고른다(SP2L 은 6줄 모두 노출)
    setF(next);
  };
  const isOn = (key: Key | 'formats', v: string) => (key === 'formats' ? (f.formats ?? []).includes(v as Fmt) : f[key] === v);

  const requested = !!s.format_draft || english;
  const userText = s.format_draft ? s.agent?.user_text : null;
  const agent = requested
    ? `${formatList((f.formats ?? []) as Fmt[])} 만들고 ${basisText(f)} 기준으로 바꿨습니다. 단위가 바뀐 셀은 파랗게 표시했어요. 고객사 양식이 있으면 올려 주세요. 같은 칸 순서로 맞춰 드립니다.`
    : '출력 형식과 언어 · 단위를 골라 주세요. 고객사 양식이 있으면 올려 주세요. 같은 칸 순서로 맞춰 드립니다.';

  const savePref = async () => {
    try {
      const { filename_base: _fb, ...rest } = f;
      await savePreferences(rest);
      setSavedPref(true);
      window.setTimeout(() => setSavedPref(false), 2000);
    } catch (e) { toast(errText(e)); }
  };

  const onTemplate = async (file: File | undefined) => {
    if (!file) return;
    try {
      const meta = await uploadFile(file, { confidential: true, purpose: 'sp.template', projectId: s.project_id ?? undefined });
      const r = await addTemplate(s.id, meta.id);
      setTplJob(r.job_id);
      void cache.refresh(s.id);
    } catch (e) { toast(errText(e)); }
  };
  const dropTemplate = async () => {
    if (!s.template) return;
    try { await removeTemplate(s.id, s.template.id); void cache.refresh(s.id); } catch (e) { toast(errText(e)); }
  };

  const back = () => {
    if (from === 'result') nav(`/spec/${s.id}`);
    else if (from === 'export') nav(`/spec/${s.id}/export`);
    else nav(`/spec/${s.id}/items`);
  };

  const run = async () => {
    setBusy(true);
    try {
      const saved = await putFormat(s.id, f);
      cache.put(saved);
      const r = await generate(s.id, { mode: saved.generated_at ? 'rerender' : 'full' });
      nav(`/spec/${s.id}/generating?job=${r.job_id}`);
    } catch (e) {
      const running = isApiError(e, 'RUN_IN_PROGRESS') ? ((e.details as { job_id?: string }).job_id ?? s.active_job?.id) : null;
      if (running) { nav(`/spec/${s.id}/generating?job=${running}`); return; }
      toast(errText(e));
    } finally { setBusy(false); }
  };

  const fname = f.filename_base ?? pv?.filename_default ?? '';
  const tabState = (t: Tab) => (t === tab ? 'on' : (f.formats ?? []).includes(t) ? 'sel' : 'off');
  const cols = pv?.grid.cols ?? [];
  const gridCols = `30px 210px ${cols.slice(1).map(() => 'minmax(0, 1fr)').join(' ')}`;
  const tplBusy = !!tplJob || s.template?.status === 'running' || s.template?.status === 'queued';

  return (
    <SpPage
      dock={
        <Dock title="출력 형식 · 언어 · 단위" meta="2 / 3"
          right={
            <>
              <input ref={fileRef} type="file" hidden accept=".xlsx,.pdf,.docx,.png,.jpg,.jpeg" aria-label="고객사 양식 파일"
                onChange={(e) => { void onTemplate(e.target.files?.[0]); e.target.value = ''; }} />
              <button type="button" className="sp-link" onClick={() => fileRef.current?.click()} disabled={tplBusy}>
                <PathIcon d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" size={13} />
                {tplBusy ? '양식 맞추는 중…' : '고객사 양식 올리기'}
              </button>
              <button type="button" className="sp-link" onClick={() => void savePref()}>{savedPref ? '내 기본값으로 저장됨' : '내 기본값으로 저장'}</button>
            </>
          }
          row={
            <>
              <div className="sp-fname">
                <label htmlFor="sp-fname">파일명</label>
                <input id="sp-fname" value={fname} onChange={(e) => setF({ ...f, filename_base: e.target.value })} />
                <span>{pv?.ext_line ?? ''}</span>
              </div>
              <button type="button" className="sp-btn2" onClick={back}>이전</button>
              <BigButton onClick={() => void run()} busy={busy}>시트 생성</BigButton>
            </>
          }>
          <div className="sp-fgroups">
            {GROUPS.map((g) => (
              <div key={g.key} className="sp-fgroup" role="group" aria-label={g.label}>
                <span className="sp-fgroup__label">{g.label}</span>
                <div className="sp-fgroup__chips">
                  {g.chips.map(([v, label]) => (
                    <button key={v} type="button" className="sp-chip sp-chip--f" aria-pressed={isOn(g.key, v)} onClick={() => set(g.key, v)}>{label}</button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Dock>
      }>
      {userText && <UserBubble>{userText}</UserBubble>}
      <Agent text={agent}>
        <div className="sp-fp" data-testid="sp-format-preview">
          <div className="sp-fp__head">
            <div className="sp-fp__tabs" role="tablist" aria-label="미리보기 형식">
              {(['xlsx', 'pdf', 'pptx'] as Tab[]).map((t) => (
                <button key={t} type="button" role="tab" aria-selected={t === tab} data-state={tabState(t)}
                  className={cx('sp-fp__tab', `sp-fp__tab--${tabState(t)}`)} onClick={() => setTab(t)}>
                  <PathIcon d={TAB_ICON[t]} size={13} />{pv?.tab_labels?.[t] ?? FMT_NAME[t]}
                </button>
              ))}
            </div>
            <div className="sp-fp__right">
              {s.template && (
                <span className="sp-fp__tpl" data-testid="sp-template-chip">
                  고객사 양식 · {s.template.name}{tplBusy ? ' · 맞추는 중' : ''}
                  <button type="button" aria-label="양식 해제" onClick={() => void dropTemplate()}>
                    <PathIcon d="M6 6l12 12M18 6L6 18" size={11} strokeWidth={2.4} />
                  </button>
                </span>
              )}
              <span>미리보기</span>
              <span className="sp-fp__chip" data-testid="sp-format-chip">{pv?.chip_label ?? basisText(f).replace('영문', 'English')}</span>
            </div>
          </div>
          {tab === 'xlsx' && pv && (
            <>
              <div className="sp-fp__r sp-fp__colhead" style={{ gridTemplateColumns: gridCols }}>
                <span />{cols.map((c) => <span key={c}>{c}</span>)}
              </div>
              {pv.grid.rows.map((r) => (
                <div key={r.n} className="sp-fp__r" style={{ gridTemplateColumns: gridCols }} data-row={r.n}>
                  <span className="sp-fp__rn">{r.n}</span>
                  {r.cells[0]?.kind === 'title'
                    ? <span className="sp-fp__c sp-fp__c--title" style={{ gridColumn: '2 / -1' }}>{r.cells[0].text}</span>
                    : r.cells.map((c, i) => (
                      <span key={i} data-converted={c.converted ? 'true' : undefined}
                        className={cx('sp-fp__c', c.kind === 'head' && (i === 0 ? 'sp-fp__c--headl' : 'sp-fp__c--head'), c.kind === 'label' && 'sp-fp__c--label',
                          c.converted && 'sp-fp__c--conv', c.pending && !c.converted && 'sp-cell--pending')}
                        title={c.text}>{c.text}</span>
                    ))}
                </div>
              ))}
              <div className="sp-fp__foot">
                <div className="sp-fp__stabs">
                  {pv.sheet_tabs.map((t, i) => <span key={t} className={cx('sp-fp__stab', i === 0 && 'sp-fp__stab--on')}>{t}</span>)}
                </div>
                {pv.note_line && <span data-testid="sp-format-note">{pv.note_line}</span>}
              </div>
            </>
          )}
          {tab !== 'xlsx' && pv && (
            <div className="sp-fp__paperwrap">
              <div className={cx('sp-fp__paper', tab === 'pptx' && 'sp-fp__paper--slide')} style={{ aspectRatio: tab === 'pptx' ? '16 / 9' : PAPER_RATIO[f.paper ?? 'a4_landscape'] }}>
                <div className="sp-fp__ptitle">{pv.title}</div>
                <div className="sp-fp__pgrid" style={{ gridTemplateColumns: `1.3fr ${cols.slice(1).map(() => '1fr').join(' ')}` }}>
                  {pv.grid.rows.slice(1).map((r) => r.cells.map((c, i) => (
                    <span key={`${r.n}-${i}`} className={cx(c.kind === 'head' && 'sp-fp__ph', c.converted && 'sp-fp__c--conv', c.win && 'sp-cell--win')}>{c.text}</span>
                  )))}
                </div>
                {(pv.footnotes ?? []).map((fn) => <div key={fn.mark} className="sp-fp__pnote">{fn.mark} {fn.text}</div>)}
                <div className="sp-fp__psrc">{pv.source_line}</div>
              </div>
              {pv.note_line && <div className="sp-note" style={{ marginTop: 8 }}>{pv.note_line}</div>}
            </div>
          )}
        </div>
      </Agent>
    </SpPage>
  );
}
