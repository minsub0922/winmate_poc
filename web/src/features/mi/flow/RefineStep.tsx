/**
 * MI3 정제(보드 webapp1 MI3.dc.html) — 찾은 정보를 시장 · 고객사 · 사용자 탭으로, 줄마다 담기/빼기 · 출처(종류 · 이름 · 날짜) · 수치 원문 확인 ·
 * v1에서 유지 / 새로 찾음 · 원문 · 문장 고치기. 담은 것만 Storyboard 에 들어간다.
 * 원문: 검색 도구가 URL 을 줬으면 그 URL 을 열고, 요약형 검색(URL 없음)이면 그 문장을 뽑은 검색 결과 글을 보여 준다(URL 을 만들지 않는다).
 */
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Modal, cx, toast } from '@/ui';
import { GROUPS, itemsOf, mfKey, type MFDoc, type MFItem, type MFResult, type MFStageOut, type useMfActions } from './api';

type Actions = ReturnType<typeof useMfActions>;

const srcLine = (it: MFItem) => {
  const s = it.source;
  return [s.name && s.name !== s.type ? s.name : null, s.date].filter(Boolean).join(' · ');
};

export function RefineView({ doc, actions, onFinished }: { doc: MFDoc; actions: Actions; onFinished: (out: MFStageOut, prev: { ver: number | null; kept: number }) => void }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState(() => Math.max(0, GROUPS.findIndex((g) => itemsOf(doc).some((x) => x.group === g.label))));
  const [editId, setEditId] = useState<string | null>(null);
  const [orig, setOrig] = useState<MFItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [back, setBack] = useState(false);
  const target = (doc.ver ?? 0) + 1;
  const editing = doc.ver != null;
  const by = doc.counts.by_group ?? {};
  const g = GROUPS[tab];
  const rows = itemsOf(doc).filter((x) => x.group === g.label);

  /** 담기 · 빼기는 바로 보이게(캐시 먼저) → 서버 */
  const toggle = async (it: MFItem) => {
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
    if (t === it.summary) return;
    try { await actions.item(it.id, { summary: t }); } catch (e) { toast((e as Error).message || '문장을 고치지 못했어요'); }
  };
  const finish = async () => {
    setSaving(true);
    try { onFinished(await actions.finish(), { ver: doc.ver ?? null, kept: doc.saved_kept ?? 0 }); } catch (e) { toast((e as Error).message || '저장하지 못했어요'); setSaving(false); }
  };
  const toSearch = async () => {
    setBack(true);
    try { await actions.patch({ phase: 'search' }); } catch (e) { toast((e as Error).message || '검색어 화면으로 가지 못했어요'); setBack(false); }
  };
  const warn = (doc.warnings ?? []).join(' · ');
  return (
    <>
      <div className="mif-head">
        <div className="wm-flow__titles">
          <h1 className="wm-flow__h1">찾은 정보를 정리해요</h1>
          <span className="wm-flow__desc">담은 것만 Storyboard에 들어가요. 문장은 원문을 줄여 쓴 것이고, 수치는 원문에서 확인해야 해요.</span>
        </div>
        <span className="mif-countline" data-testid="mif-count">찾은 {doc.counts.found} · 담음 {doc.counts.kept}</span>
      </div>
      <div className="mif-tabs" role="tablist" aria-label="찾은 정보 묶음">
        {GROUPS.map((gg, i) => {
          const [k, n] = by[gg.label] ?? [0, 0];
          return (
            <button key={gg.key} type="button" role="tab" aria-selected={i === tab} className={cx('mif-tab', i === tab && 'mif-tab--on')} onClick={() => { setTab(i); setEditId(null); }}>
              {gg.label}<span className="mif-tab__n">{k}/{n}</span>
            </button>
          );
        })}
      </div>
      <div className="mif-list" role="tabpanel" aria-label={`${g.label} 찾은 정보`} data-testid="mif-list">
        {!rows.length && (
          <div className="mif-empty"><b>{g.label}에서 찾은 정보가 없어요</b><span>검색어를 바꾸거나 기간 · 출처 조건을 넓혀 다시 검색해 보세요.</span></div>
        )}
        {rows.map((it) => (
          <div key={it.id} className="mif-row" data-item={it.id} data-kept={it.kept}>
            <button type="button" role="checkbox" aria-checked={it.kept} aria-label={`${it.kept ? '빼기' : '담기'} · ${it.summary}`} className={cx('mif-chk', it.kept && 'mif-chk--on')} onClick={() => toggle(it)}>
              {it.kept && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12l5 5L20 7" /></svg>}
            </button>
            <span className="mif-row__txt">
              {editId === it.id
                ? <EditLine it={it} onSave={(t) => saveText(it, t)} onCancel={() => setEditId(null)} />
                : <span className={cx('mif-row__t', !it.kept && 'mif-row__t--off')} title={it.summary}>{it.summary}</span>}
              <span className="mif-row__meta">
                <span className="mif-kind">{it.source.type}</span>
                {srcLine(it) && <span>{srcLine(it)}</span>}
                {it.numberCheck && <span className="mif-numchk" title={`${it.numberCheck.note ?? '수치는 원문에서 확인해야 해요'} · ${(it.numberCheck.values ?? []).join(' · ')}`}>수치 원문 확인</span>}
              </span>
            </span>
            {editing && <span className={cx('mif-tag', it.addedIn === `v${target}` ? 'mif-tag--new' : 'mif-tag--old')}>{it.addedIn === `v${target}` ? '새로 찾음' : `${it.addedIn}에서 유지`}</span>}
            {it.source.url
              ? <a className="mif-ghost30" href={it.source.url} target="_blank" rel="noreferrer noopener">원문</a>
              : <button type="button" className="mif-ghost30" onClick={() => setOrig(it)}>원문</button>}
            {/* 고치는 중이면 「완료」(입력칸을 벗어나면 저장 · Esc 는 취소) */}
            <button type="button" className="mif-link30" onClick={() => setEditId(editId === it.id ? null : it.id)}>{editId === it.id ? '완료' : '문장 고치기'}</button>
          </div>
        ))}
      </div>
      <div className="wm-flow__foot mif-foot">
        <button type="button" className="wm-flow__back mif-backbtn" onClick={toSearch} disabled={back}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M15 6l-6 6 6 6" /></svg>검색어 고치기
        </button>
        <span style={{ flexGrow: 1 }} />
        {doc.counts.kept === 0 ? <span className="wm-flow__summary wm-flow__summary--warn">담은 정보가 하나 이상 있어야 저장할 수 있어요</span>
          : warn && <span className="wm-flow__summary mif-warnline" title={warn}>{warn}</span>}
        <button type="button" className="wm-flow__primary" onClick={finish} disabled={saving || doc.counts.kept === 0} aria-busy={saving || undefined}>
          {saving ? '저장 중…' : `MI 저장 · v${target}`}
        </button>
      </div>
      <OriginDialog item={orig} result={orig ? (doc.results ?? []).find((r) => r.id === orig.result_id) ?? null : null} onClose={() => setOrig(null)} />
    </>
  );
}

function EditLine({ it, onSave, onCancel }: { it: MFItem; onSave: (t: string) => void; onCancel: () => void }) {
  const [v, setV] = useState(it.summary);
  const ref = useRef<HTMLInputElement>(null);
  const done = useRef(false);
  useEffect(() => { ref.current?.focus(); ref.current?.select(); }, []);
  const save = () => { if (done.current) return; done.current = true; onSave(v); };
  return (
    <>
      <label className="wm-sr" htmlFor={`mif-edit-${it.id}`}>고친 문장</label>
      <input id={`mif-edit-${it.id}`} ref={ref} className="mif-row__edit" value={v} maxLength={200} onChange={(e) => setV(e.target.value)} onBlur={save}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); save(); }
          if (e.key === 'Escape') { done.current = true; onCancel(); }
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

