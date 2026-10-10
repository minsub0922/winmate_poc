/**
 * 전략 수립 · Key message 팝업(보드 webapp1 StrategyPopup 1100×700 · SB1_Strat · SB1_StratAI).
 * 한 줄 메시지 + 받쳐 줄 메시지 3(근거 = 연결된 콘텐츠 코드). 「연결된 콘텐츠로 수립」 → AI 후보 3안(오른쪽 360, 점선) → 「이 안 쓰기」 → 저장해야 들어간다
 * (`PATCH /v1/flows/{id}` key_message · key_message_by='ai-accepted' · key_pillars). 저장하면 요약본 Key message 절이 바로 바뀐다.
 */
import { useEffect, useRef, useState } from 'react';
import { patchFlow, suggestKeyMessage, type FlowDoc } from '@/shell';
import { Icon, Modal, Skeleton, cx, josa, toast } from '@/ui';

interface Pillar { text: string; evidence: string[] }
interface Cand { id?: string | null; text: string; basis?: string | null; pillars?: Pillar[] }
type KM = { text?: string; by?: string; pillars?: Pillar[] } | null | undefined;

const SPARK = 'M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z M19 15l.9 2.1 2.1.9-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z';
const pad3 = (ps: Pillar[] | undefined): Pillar[] => [0, 1, 2].map((i) => ({ text: ps?.[i]?.text ?? '', evidence: [...(ps?.[i]?.evidence ?? [])] }));

function Evidence({ p, refs, onChange }: { p: Pillar; refs: string[]; onChange: (ev: string[]) => void }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', off);
    return () => document.removeEventListener('mousedown', off);
  }, [open]);
  const left = refs.filter((r) => !p.evidence.includes(r));
  return (
    <div className="sbk-evs" ref={box}>
      <small>근거</small>
      {p.evidence.map((e) => (
        <button key={e} type="button" className="sbk-ev" title="누르면 빼요" aria-label={`근거 ${e} 빼기`} onClick={() => onChange(p.evidence.filter((x) => x !== e))}>{e}</button>
      ))}
      <button type="button" className="sbk-addev" aria-expanded={open} onClick={() => setOpen((v) => !v)}>+ 근거</button>
      {open && (
        <div className="sbk-evmenu" role="menu" aria-label="근거 고르기">
          {left.length ? left.map((r) => <button key={r} type="button" role="menuitem" onClick={() => { onChange([...p.evidence, r]); setOpen(false); }}>{r}</button>)
            : <span style={{ padding: '8px 10px', fontSize: 12, color: 'var(--wm-text-subtle)' }}>더 고를 콘텐츠가 없어요</span>}
        </div>
      )}
    </div>
  );
}

export function StrategyPopup({ flow, onClose, onSaved }: { flow: FlowDoc; onClose: () => void; onSaved: (d: FlowDoc) => void }) {
  const km0 = flow.key_message as KM;
  const [km, setKm] = useState(km0?.text ?? '');
  const [pills, setPills] = useState<Pillar[]>(() => pad3(km0?.pillars));
  const [ai, setAi] = useState(false);
  const [cands, setCands] = useState<Cand[] | null>(null);
  const [mode, setMode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [used, setUsed] = useState(-1);
  const [saving, setSaving] = useState(false);
  const done = flow.cells.filter((c) => c.state === 'done' && c.key !== 'ppt');
  const srcs = done.map((c) => (c.key === 'rq' ? `요구사항 ${c.ref} v${c.ver}` : `${c.ref} v${c.ver}`));
  const refs = done.map((c) => c.ref!).filter(Boolean);
  const read = refs.join(' · ');
  const picked = used >= 0 && cands?.[used] && km.trim() === cands[used].text.trim();

  const openAi = async () => {
    setAi(true);
    if (cands || loading) return;
    setLoading(true);
    try {
      const r = await suggestKeyMessage(flow.id);
      setCands((r.candidates ?? []) as Cand[]);
      setMode(r.mode);
    } catch (e) { toast((e as Error).message || 'AI 후보를 만들지 못했어요'); setAi(false); } finally { setLoading(false); }
  };
  const use = (i: number) => {
    const c = cands![i];
    setUsed(i);
    setKm(c.text);
    setPills(pad3(c.pillars));
  };
  const save = async () => {
    if (saving) return;
    setSaving(true);
    try {
      const doc = await patchFlow(flow.id, {
        key_message: km.trim(), key_message_by: picked ? 'ai-accepted' : 'manual',
        key_pillars: pills.filter((p) => p.text.trim()).map((p) => ({ text: p.text.trim(), evidence: p.evidence })), expected_version: flow.version,
      });
      onSaved(doc);
      toast(km.trim() ? 'Key message를 저장했어요 · 요약본에 반영됐어요' : 'Key message를 비웠어요');
      onClose();
    } catch (e) { toast((e as Error).message || '저장하지 못했어요'); } finally { setSaving(false); }
  };
  const setPill = (i: number, p: Partial<Pillar>) => setPills((xs) => xs.map((x, j) => (j === i ? { ...x, ...p } : x)));

  return (
    <Modal open onClose={onClose} width={1100} height={700} ariaLabel="전략 수립 · Key message" bodyStyle={{ padding: 0, display: 'flex', overflow: 'hidden' }}>
      <div className="sbk">
        <div className="sbk-main">
          <div className="sbk-head">
            <div className="sbk-titles"><small>{flow.name} · 전략 수립</small><b>Key message</b></div>
            {!ai && (
              <button type="button" className="sbk-ai" onClick={openAi} disabled={!refs.length}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d={SPARK} /></svg>연결된 콘텐츠로 수립
              </button>
            )}
            <button type="button" className="sbk-x" aria-label="닫기" onClick={onClose}><Icon name="x" size={16} strokeWidth={2.2} /></button>
          </div>
          <div className="sbk-body">
            <div className="sbk-srcs">
              <small>근거로 쓸 콘텐츠</small>
              {srcs.map((c) => <span key={c} className="sbk-src"><i />{c}</span>)}
            </div>
            <div className={cx('sbk-kmbox', picked && 'sbk-kmbox--ai')}>
              <label htmlFor="sbk-km">한 줄 메시지{picked && <span className="sbf-kmby">AI 후보에서 고름</span>}</label>
              <input id="sbk-km" value={km} placeholder="제안 전체를 한 줄로" onChange={(e) => setKm(e.target.value)} autoComplete="off" />
            </div>
            <span className="sbk-h">받쳐 줄 메시지 3</span>
            {pills.map((p, i) => (
              <div key={i} className="sbk-pill">
                <div className="sbk-pillrow">
                  <span className="sbk-n" aria-hidden>{i + 1}</span>
                  <input aria-label={`메시지 ${i + 1}`} value={p.text} placeholder="메시지를 적어 주세요" onChange={(e) => setPill(i, { text: e.target.value })} autoComplete="off" />
                </div>
                <Evidence p={p} refs={refs} onChange={(ev) => setPill(i, { evidence: ev })} />
              </div>
            ))}
          </div>
          <div className="sbk-foot">
            <span>저장하면 요약본의 Key message 섹션이 바로 바뀌어요</span>
            <button type="button" className="sbk-btn" onClick={onClose}>취소</button>
            <button type="button" className="sbk-btn sbk-btn--primary" onClick={save} disabled={saving} aria-busy={saving || undefined}>{saving ? '저장 중…' : '저장'}</button>
          </div>
        </div>
        {ai && (
          <aside className="sbk-aside" aria-label="AI Key message 후보">
            <div className="sbk-asidehead">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="var(--wm-brand)" aria-hidden><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z" /></svg>
              <b>AI 후보 3안</b>
              <button type="button" className="sbk-x sbk-x--sm" aria-label="후보 닫기" onClick={() => setAi(false)}><Icon name="x" size={13} strokeWidth={2.2} /></button>
            </div>
            <div className="sbk-asidebody" aria-busy={loading || undefined}>
              {loading && <><small>{read}{josa(read, '을', '를')} 읽는 중…</small><Skeleton h={130} r={12} /><Skeleton h={130} r={12} /><Skeleton h={130} r={12} /></>}
              {!loading && cands && (
                <small>{mode === 'rule' ? `${read}의 문장으로 골랐어요 · 모델 없이 만든 후보예요` : `${read}${josa(read, '을', '를')} 읽고 만들었어요`}</small>
              )}
              {!loading && cands && !cands.length && <small>후보를 만들 문장이 아직 없어요 · 연결된 콘텐츠를 더 저장해 주세요</small>}
              {!loading && cands?.map((c, i) => {
                const on = used === i && picked;
                return (
                  <div key={i} className={cx('sbk-cand', on && 'sbk-cand--on')} data-testid="sb-km-cand">
                    <span className="sbk-candhead"><em>{c.id ?? 'ABC'[i]}</em><b>{c.text}</b></span>
                    {(c.pillars ?? []).map((p, j) => <span key={j}>· {p.text}</span>)}
                    <button type="button" className={cx('sbk-use', on && 'sbk-use--on')} onClick={() => use(i)} aria-pressed={!!on}>{on ? '쓰는 중' : '이 안 쓰기'}</button>
                  </div>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </Modal>
  );
}
