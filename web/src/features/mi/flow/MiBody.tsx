/**
 * MI 본문(보드 webapp1 MIBody · 상태 stage empty | searching | found) — 검색 조건 · 검색어 띠 + 시장 · 고객사 · 사용자 세 칸.
 * 찾은 정보는 그 자리에서 담기 · 빼기(누르는 즉시 저장) · 문장 고치기(문장을 누르면 글 칸 · 떠날 때 저장). 체크한 것만 Storyboard 에 담긴다.
 * 저장한 MI 를 고치면 이 화면에서 바꾼 줄에 표시(보드 MI3_Edit: 뺀 줄 = 안쪽 막대 + 「이번에 뺌」, 고친 문장 = cd-in--chg) — 저장 · 되돌리기 하면 지운다.
 * 원문: 검색 도구가 URL 을 줬으면 그 URL, 요약형 검색(URL 없음)이면 그 문장을 뽑은 검색 결과 글(URL 을 만들지 않는다).
 * px 는 보드 인라인 값 그대로(miflow.css · 접두어 mif-).
 */
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Modal, cx, toast } from '@/ui';
import { GROUPS, itemsOf, mfKey, nOn, qsOf, type MFDoc, type MFItem, type MFResult, type useMfActions } from './api';

type Actions = ReturnType<typeof useMfActions>;
export type Stage = 'empty' | 'searching' | 'found';
/** 이 화면에서 처음 바꾸기 전 값(줄 id → 담음 · 문장) — 지금 값과 다르면 「고친 줄」 */
export type Touched = Record<string, { kept?: boolean; summary?: string }>;

const SPIN = 'M12 3a9 9 0 1 1-9 9';
const SPARK = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z';
const EMPTY_TEXT: Record<string, string> = { 시장: '업계 · 시장 동향', 고객사: '고객사 사업 · 공시 · 보도', 사용자: '공간을 쓰는 사람 · 수요 조사' };
/** 화면 아래 줄에 보이지 않는 안내(보드 각주가 이미 말함) */
const QUIET = ['요약형 웹 검색이라'];

const srcLine = (it: MFItem) => {
  const s = it.source;
  return [s.name && s.name !== s.type ? s.name : null, s.date].filter(Boolean).join(' · ');
};

/** 검색어 줄(보드: 「시장 3 · 고객사 3 · 사용자 3 — 첫 검색어 · … 외」) */
export function queryLine(d: MFDoc) {
  const qs = qsOf(d);
  const on = GROUPS.map((g) => qs[g.key].filter((q) => q.on !== false && q.text.trim()).map((q) => q.text));
  const heads = on.map((l) => l[0]).filter(Boolean);
  const more = on.some((l) => l.length > 1);
  return `${GROUPS.map((g, i) => `${g.label} ${on[i].length}`).join(' · ')}${heads.length ? ` — ${heads.join(' · ')}${more ? ' 외' : ''}` : ''}`;
}

export function MiBody({ doc, actions, stage, mode, onOpenSearch, touched, onTouch }: {
  doc: MFDoc; actions: Actions; stage: Stage; mode: 'saved' | 'editing' | 'new' | 'draft';
  onOpenSearch: () => void; touched: Touched; onTouch: (id: string, before: { kept?: boolean; summary?: string }) => void;
}) {
  const qc = useQueryClient();
  const [editId, setEditId] = useState<string | null>(null);
  const [orig, setOrig] = useState<MFItem | null>(null);
  const saved = mode === 'saved' || mode === 'editing';
  const running = stage === 'searching';
  const nq = GROUPS.reduce((a, g) => a + nOn(qsOf(doc)[g.key]), 0);
  // 띠: 검색어가 있으면(찾음 · 찾는 중 · 작성 중) 검색 조건 · 검색어, 아니면 점선 안내(새로 만들기 — 검색 팝업에서 이어져요)
  const hasQ = stage === 'found' || running || (mode === 'draft' && nq > 0 && doc.phase !== 'analyzing');
  const found = stage === 'found';
  const runLabel = mode === 'draft' && !found ? '검색 시작' : found ? '검색어 · 조건 고치고 다시 검색' : '검색 팝업 열기';
  const runPrimary = !hasQ || (mode === 'draft' && !found);
  const filters = [doc.filters?.period ?? '최근 1년', ...(doc.filters?.sourceTypes ?? [])];
  const target = (doc.ver ?? 0) + 1;

  /** 담기 · 빼기는 바로 보이게(캐시 먼저) → 서버(고친 곳 수가 돌아온다) */
  const toggle = async (it: MFItem) => {
    onTouch(it.id, { kept: it.kept });
    const prev = qc.getQueryData(mfKey(doc.id)) as MFDoc | undefined;
    if (prev) {
      const items = itemsOf(prev).map((x) => (x.id === it.id ? { ...x, kept: !it.kept } : x));
      const kept = items.filter((x) => x.kept);
      const byg = Object.fromEntries(GROUPS.map((gg) => [gg.label, [kept.filter((x) => x.group === gg.label).length, items.filter((x) => x.group === gg.label).length]]));
      qc.setQueryData(mfKey(doc.id), { ...prev, items, counts: { ...prev.counts, kept: kept.length, numberCheck: kept.filter((x) => x.numberCheck).length, by_group: byg } });
    }
    try { await actions.item(it.id, { kept: !it.kept }); } catch (e) { toast((e as Error).message || '바꾸지 못했어요'); await actions.refresh(); }
  };
  const saveText = async (it: MFItem, text: string) => {
    setEditId(null);
    const t = text.replace(/\s+/g, ' ').trim();
    if (t === it.summary || (!t && it.summary === it.summary_orig)) return;
    onTouch(it.id, { summary: it.summary });
    try { await actions.item(it.id, { summary: t }); } catch (e) { toast((e as Error).message || '문장을 고치지 못했어요'); }
  };

  const warn = found ? (doc.warnings ?? []).filter((w) => !QUIET.some((q) => w.startsWith(q))).join(' · ') : '';
  return (
    <div className="mif-body" data-stage={stage} data-mode={mode}>
      <div className={cx('mif-strip', !hasQ && 'mif-strip--empty')} data-testid="mif-strip">
        {hasQ ? (
          <>
            <span className="mif-strip__k">검색 조건</span>
            {filters.map((c) => <span key={c} className="mif-strip__chip">{c}</span>)}
            <span className="mif-strip__sep" aria-hidden />
            <span className="mif-strip__k">검색어</span>
            <span className="mif-strip__q" title={queryLine(doc)}>{queryLine(doc)}</span>
          </>
        ) : (
          <>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" className="mif-strip__spark" aria-hidden><path d={SPARK} /></svg>
            <span className="mif-strip__empty">{doc.phase === 'analyzing' ? 'Storyboard를 읽고 검색어 · 검색 조건을 만드는 중이에요 — 검색 팝업에서 이어져요' : '검색어 · 검색 조건이 준비됐어요 — 검색 팝업에서 웹 검색을 시작해요'}</span>
          </>
        )}
        {running && (
          <span className="mif-strip__run" role="status">
            <svg className="mif-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden><path d={SPIN} /></svg>
            웹에서 찾는 중 · 1–2분
          </span>
        )}
        {!running && (
          <button type="button" className={cx('mif-run', runPrimary && 'mif-run--primary')} onClick={onOpenSearch}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>
            {runLabel}
          </button>
        )}
      </div>

      <div className="mif-cols3">
        {GROUPS.map((g) => {
          const all = itemsOf(doc).filter((x) => x.group === g.label);
          // 담은 것 먼저 · 뺀 것은 아래(보드: 흐리게 · 취소선)
          const rows = [...all.filter((x) => x.kept), ...all.filter((x) => !x.kept)];
          const kept = all.filter((x) => x.kept).length;
          const showItems = found || (running && saved);
          return (
            <section key={g.key} className="mif-gcol" data-group={g.key} aria-label={`${g.label} 찾은 정보`}>
              <div className="mif-gcol__head">
                <span className="mif-gcol__h">{g.label}</span>
                <span className="mif-gcol__n">{showItems ? `${kept}/${all.length}` : ''}</span>
                <span style={{ flexGrow: 1 }} />
                <span className="mif-gcol__sub">{showItems && !running ? `담음 ${kept}` : running ? '찾는 중' : ''}</span>
              </div>
              <div className="mif-gcol__body">
                {!showItems && !running && (
                  <div className="mif-ph"><b>검색하면 여기에 모여요</b><span>{EMPTY_TEXT[g.label]}</span></div>
                )}
                {running && !saved && [1, 2, 3].map((k) => (
                  <div key={k} className="mif-skel" aria-hidden><i style={{ width: '92%' }} /><i style={{ width: '64%' }} /><i className="mif-skel--s" style={{ width: '40%' }} /></div>
                ))}
                {showItems && !rows.length && (
                  <div className="mif-ph"><b>{g.label}에서 찾은 정보가 없어요</b><span>검색어를 바꾸거나 기간 · 출처 조건을 넓혀 다시 검색해 보세요.</span></div>
                )}
                {showItems && rows.map((it) => {
                  const t = touched[it.id];
                  // 고친 표시(보드 MI3_Edit): 담기 · 빼기를 바꾼 줄 = 안쪽 막대(뺐으면 「이번에 뺌」), 고친 문장 = cd-in--chg
                  const offNow = saved && t?.kept !== undefined && t.kept && !it.kept;
                  const rowChg = saved && t?.kept !== undefined && t.kept !== it.kept;
                  const textChg = saved && t?.summary !== undefined && t.summary !== it.summary;
                  const fresh = it.addedIn === `v${target}`;
                  const tag = offNow ? '이번에 뺌' : !saved ? '새로 찾음' : fresh ? '새로 찾음' : it.addedIn !== 'v1' ? `${it.addedIn}에서 찾음` : '';
                  return (
                    <div key={it.id} className={cx('mif-item', rowChg && 'mif-item--chg')} data-item={it.id} data-kept={it.kept}>
                      <button type="button" role="checkbox" aria-checked={it.kept} aria-label={`${it.kept ? '빼기' : '담기'} · ${it.summary}`}
                        className={cx('mif-box', it.kept && 'mif-box--on')} onClick={() => toggle(it)}>
                        {it.kept && <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12l5 5L20 7" /></svg>}
                      </button>
                      <span className="mif-item__txt">
                        {editId === it.id
                          ? <EditText it={it} onSave={(v) => saveText(it, v)} onCancel={() => setEditId(null)} />
                          : (
                            <button type="button" className={cx('mif-item__t', !it.kept && 'mif-item__t--off', textChg && 'cd-in--chg mif-item__t--chg')}
                              onClick={() => setEditId(it.id)} aria-label={`문장 고치기 · ${it.summary}`} title="눌러서 문장을 고쳐요">{it.summary}</button>
                          )}
                        <span className="mif-item__meta">
                          <span className="mif-kind">{it.source.type}</span>
                          {srcLine(it) && <span className="mif-src">{srcLine(it)}</span>}
                          {it.numberCheck && <span className="mif-numchk" title={`${it.numberCheck.note ?? '수치는 원문에서 확인해야 해요'} · ${(it.numberCheck.values ?? []).join(' · ')}`}>수치 원문 확인</span>}
                          {tag && <span className={cx('mif-tag', offNow ? 'mif-tag--off' : 'mif-tag--new')}>{tag}</span>}
                          <span style={{ flexGrow: 1 }} />
                          {it.source.url
                            ? <a className="mif-orig" href={it.source.url} target="_blank" rel="noreferrer noopener">원문</a>
                            : <button type="button" className="mif-orig" onClick={() => setOrig(it)}>원문</button>}
                        </span>
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
      <span className="mif-foot">
        체크한 것만 Storyboard에 담겨요 · 문장을 눌러 바로 고쳐요 · 문장은 원문을 줄여 쓴 것이고 수치는 원문에서 확인해요
        {warn && <b className="mif-foot__warn" title={warn}> · {warn}</b>}
      </span>
      <OriginDialog item={orig} result={orig ? (doc.results ?? []).find((r) => r.id === orig.result_id) ?? null : null} onClose={() => setOrig(null)} />
    </div>
  );
}

/** 문장 고치기(보드 MI3_Edit: 글 칸 h62 · 1.5px 파란 선) — 떠날 때 · Enter 에 한 번 저장, Esc 는 그대로 */
function EditText({ it, onSave, onCancel }: { it: MFItem; onSave: (t: string) => void; onCancel: () => void }) {
  const [v, setV] = useState(it.summary);
  const ref = useRef<HTMLTextAreaElement>(null);
  const done = useRef(false);
  useEffect(() => { const el = ref.current; if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); } }, []);
  const save = () => { if (done.current) return; done.current = true; onSave(v); };
  return (
    <>
      <label className="cd-sr" htmlFor={`mif-e-${it.id}`}>정리 문장</label>
      <textarea id={`mif-e-${it.id}`} ref={ref} className="mif-edit" value={v} maxLength={200} onChange={(e) => setV(e.target.value)} onBlur={save}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); save(); }
          if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done.current = true; onCancel(); }
        }} />
    </>
  );
}

/** 원문(URL 없음) — 이 문장을 뽑은 검색 결과 글 그대로 */
function OriginDialog({ item, result, onClose }: { item: MFItem | null; result: MFResult | null; onClose: () => void }) {
  return (
    <Modal open={!!item} onClose={onClose} width={640} title="원문 · 검색 결과" bodyStyle={{ padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 12 }}
      footer={<div className="mif-origfoot"><span>요약형 웹 검색이라 원문 링크가 없어요 · 수치는 원문에서 확인해 주세요</span>
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h38" onClick={onClose}>닫기</button></div>}>
      {item && (
        <>
          <div className="mif-orig__row"><span>검색어</span><b>{result?.query ?? item.query ?? '—'}</b></div>
          <div className="mif-orig__row"><span>출처</span><b>{[item.source.type, srcLine(item)].filter(Boolean).join(' · ')}</b></div>
          <div className="mif-orig__row"><span>뽑은 문장</span><b>{item.summary_orig}</b></div>
          <div className="mif-orig__text">{result?.summary || '검색 결과 글이 남아 있지 않아요.'}</div>
          {!!result?.sources?.length && (
            <div className="mif-orig__srcs">{result.sources.map((s) => <a key={s.url} href={s.url} target="_blank" rel="noreferrer noopener">{s.title || s.url}</a>)}</div>
          )}
        </>
      )}
    </Modal>
  );
}
