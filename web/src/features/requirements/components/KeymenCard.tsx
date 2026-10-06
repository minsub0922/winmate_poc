/**
 * 키맨별 요구사항 카드 — RQ1(입력형: 빈 키맨 1개) · RQ1G(채우는 중 스켈레톤) · RQ2(목록형: 가중치 · 스테퍼 · 출처 배지).
 * 레이아웃 전환(§4.6): 키맨이 없거나 이름 · 항목이 모두 빈 키맨 1개뿐이면 입력형, 그 밖에는 목록형.
 */
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Icon } from '@/ui';
import type { DraftOp, Keyman, ReqItem, Requirement } from '../api';
import { newId } from '../lib/ids';
import { stepWeights } from '../lib/weights';
import { KmAvatar, Shim, SrcBadge, WeightBar } from './bits';
import { LiveInput } from './LiveInput';

type Edit = (op: DraftOp | DraftOp[]) => void;

export function isInputStyle(rq: Requirement): boolean {
  const ks = rq.form.keymen;
  if (ks.length === 0) return true;
  return ks.length === 1 && !(ks[0].name ?? '').trim() && ks[0].items.every((i) => !(i.text ?? '').trim());
}

export function KeymenCard({ rq, edit, filling, fillJobId }: { rq: Requirement; edit: Edit; filling: boolean; fillJobId?: string | null }) {
  const ks = rq.form.keymen;
  const [focusKm, setFocusKm] = useState<string | null>(null);
  // 입력형 카드에서 타이핑하는 동안은 목록형으로 바꾸지 않는다(포커스가 카드를 떠나면 규칙대로)
  const [sticky, setSticky] = useState(false);
  const addKeyman = () => {
    setSticky(false);
    const id = newId('km');
    edit({ op: 'add_keyman', keyman_id: id, name: '' });
    setFocusKm(id);
  };
  if ((isInputStyle(rq) || (sticky && ks.length <= 1)) && !filling) {
    return (
      <div className="rq-rightcard" data-layout="input" onFocus={() => setSticky(true)}
        onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setSticky(false); }}>
        <div className="rq-km-head" style={{ marginTop: 6 }}><span className="rq-km-head__title">키맨별 요구사항</span></div>
        <InputKeyman km={ks[0]} edit={edit} />
        <button type="button" className="rq-addkm" onClick={addKeyman}>+ 키맨 추가</button>
      </div>
    );
  }
  const multi = ks.length >= 2;
  const weights = ks.map((k) => k.weight ?? 0);
  const commitWeights = (vals: number[]) => edit({ op: 'set_weights', weights: Object.fromEntries(ks.map((k, i) => [k.id, vals[i]])) });
  return (
    <div className="rq-rightcard" data-layout="list">
      <div className="rq-km-head">
        <span className="rq-km-head__title">키맨별 요구사항</span>
        <span className="rq-km-head__n" data-testid="km-count">{ks.length}명</span>
        <span style={{ flex: 1 }} />
        <button type="button" className="wm-btn wm-btn--h32" style={{ color: 'var(--wm-brand)', fontSize: 12.5 }} onClick={addKeyman}>+ 키맨</button>
      </div>
      {multi && (
        <div className="rq-wrow">
          <span className="rq-wrow__label">가중치</span>
          <WeightBar keymen={ks} onCommit={commitWeights} />
          {rq.form.weights_mode === 'equal_default' && <span className="rq-dash" data-testid="equal-badge">균등</span>}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {ks.map((k, i) => (
          <KeymanBlock key={k.id} km={k} multi={multi} edit={edit} filling={filling} fillJobId={fillJobId} autoFocusName={focusKm === k.id}
            onStep={(dir) => commitWeights(stepWeights(weights, i, dir))} />
        ))}
        {filling && ks.length === 0 && (
          <div className="rq-kmcard" aria-busy="true">
            <div className="rq-kmcard__head"><Shim w="40%" /></div>
            <div className="rq-item"><Shim w="62%" /></div>
            <div className="rq-item"><Shim w="44%" /></div>
          </div>
        )}
      </div>
    </div>
  );
}

/** RQ1 입력형 키맨 카드 */
function InputKeyman({ km, edit }: { km?: Keyman; edit: Edit }) {
  const [rows, setRows] = useState(0);
  const refs = useRef<Array<HTMLInputElement | null>>([]);
  const [focusRow, setFocusRow] = useState<number | null>(null);
  const items = km?.items ?? [];
  const total = Math.max(1, items.length + rows);
  useEffect(() => { if (focusRow !== null) { refs.current[focusRow]?.focus(); setFocusRow(null); } }, [focusRow, total]);
  const ensureKm = (ops: DraftOp[]): string => {
    if (km) return km.id;
    const id = newId('km');
    ops.push({ op: 'add_keyman', keyman_id: id, name: '' });
    return id;
  };
  const setName = (name: string) => {
    if (km) edit({ op: 'update_keyman', keyman_id: km.id, name });
    else edit({ op: 'add_keyman', keyman_id: newId('km'), name });
  };
  const setRow = (j: number, text: string) => {
    const it = items[j];
    if (it) { edit({ op: 'update_item', item_id: it.id, text }); return; }
    if (!text) return;
    const ops: DraftOp[] = [];
    const kid = ensureKm(ops);
    ops.push({ op: 'add_item', keyman_id: kid, item_id: newId('ri'), text });
    setRows((r) => Math.max(0, r - 1));
    edit(ops);
  };
  const addRow = () => { setRows((r) => r + 1); setFocusRow(total); };
  return (
    <div className="rq-input-km">
      <span className="rq-input-km__av" aria-hidden="true" />
      <div className="rq-input-km__body">
        <label className="wm-sr-only" htmlFor="km1">키맨</label>
        <LiveInput id="km1" className="rq-input rq-input-sm" placeholder="키맨 (예: 대표이사)" maxLength={40} value={km?.name ?? ''}
          onText={setName} />
        {Array.from({ length: total }, (_, j) => (
          <div key={items[j]?.id ?? `new-${j}`}>
            <label className="wm-sr-only" htmlFor={`km1r${j + 1}`}>요구사항 {j + 1}</label>
            <LiveInput id={`km1r${j + 1}`} ref={(el) => { refs.current[j] = el; }} className="rq-input rq-input-sm" placeholder="요구사항" maxLength={200}
              value={items[j]?.text ?? ''} onText={(t) => setRow(j, t)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); addRow(); } }} />
          </div>
        ))}
        <div><button type="button" className="rq-link-btn" style={{ paddingLeft: 0 }} onClick={addRow}>+ 요구사항</button></div>
      </div>
    </div>
  );
}

/** RQ2 목록형 키맨 묶음 */
function KeymanBlock({ km, multi, edit, filling, fillJobId, autoFocusName, onStep }: {
  km: Keyman; multi: boolean; edit: Edit; filling: boolean; fillJobId?: string | null; autoFocusName: boolean; onStep: (dir: 1 | -1) => void;
}) {
  const [editingName, setEditingName] = useState(autoFocusName || !(km.name ?? '').trim());
  const [name, setName] = useState(km.name ?? '');
  const [adding, setAdding] = useState<number>(0);
  const [menu, setMenu] = useState(false);
  useEffect(() => { if (!editingName) setName(km.name ?? ''); }, [km.name, editingName]);
  const commitName = () => {
    const v = name.trim();
    if (v !== (km.name ?? '')) edit({ op: 'update_keyman', keyman_id: km.id, name: v });
    if (v) setEditingName(false);
  };
  const label = km.name || '키맨';
  return (
    <div className="rq-kmcard" data-keyman={km.name}>
      <div className="rq-kmcard__head">
        <KmAvatar name={km.name} colorIndex={km.color_index} />
        {editingName ? (
          <input className="rq-kmcard__nameinput" aria-label="키맨 이름" placeholder="키맨 (예: 대표이사)" maxLength={40} value={name} autoFocus={autoFocusName}
            onChange={(e) => setName(e.target.value)} onBlur={commitName}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) commitName(); if (e.key === 'Escape') { setName(km.name ?? ''); if (km.name) setEditingName(false); } }} />
        ) : (
          <button type="button" className="rq-kmcard__name" title="이름 고치기" onClick={() => setEditingName(true)}>{km.name}</button>
        )}
        {multi && (
          <span className="rq-stepper" data-testid={`stepper-${km.name}`}>
            <button type="button" aria-label={`${label} 가중치 낮추기`} onClick={() => onStep(-1)}>−</button>
            <span className="wm-num">{km.weight ?? 0}%</span>
            <button type="button" aria-label={`${label} 가중치 높이기`} onClick={() => onStep(1)}>+</button>
          </span>
        )}
        <button type="button" className="rq-link-btn" onClick={() => setAdding((a) => a + 1)}>+ 요구사항</button>
        <span style={{ position: 'relative' }}>
          <button type="button" className="rq-iconx" aria-label={`${label} 메뉴`} aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu((m) => !m)}>
            <Icon name="more" size={14} />
          </button>
          {menu && (
            <span role="menu" className="rq-vermenu" style={{ left: 'auto', right: 0, top: 26, minWidth: 120 }} onMouseLeave={() => setMenu(false)}>
              <button type="button" role="menuitem" className="rq-vermenu__row" style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--wm-danger)' }}
                onClick={() => { setMenu(false); edit({ op: 'remove_keyman', keyman_id: km.id }); }}>키맨 삭제</button>
            </span>
          )}
        </span>
      </div>
      {km.items.map((it, j) => <ItemRow key={it.id} it={it} n={j + 1} edit={edit} fill={!!fillJobId && it.source?.job_id === fillJobId} />)}
      {Array.from({ length: adding }, (_, j) => (
        <NewItemRow key={`n${j}`} n={km.items.length + j + 1}
          onDone={(text) => { if (text) edit({ op: 'add_item', keyman_id: km.id, item_id: newId('ri'), text }); setAdding((a) => Math.max(0, a - 1)); }}
          onMore={() => setAdding((a) => a + 1)} />
      ))}
      {filling && <div className="rq-item" aria-busy="true"><span className="rq-item__n" /><Shim w={km.items.length % 2 ? '44%' : '62%'} /></div>}
    </div>
  );
}

function ItemRow({ it, n, edit, fill }: { it: ReqItem; n: number; edit: Edit; fill: boolean }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(it.text);
  useEffect(() => { if (!editing) setText(it.text); }, [it.text, editing]);
  const commit = () => {
    const v = text.trim();
    setEditing(false);
    if (!v) edit({ op: 'remove_item', item_id: it.id });
    else if (v !== it.text) edit({ op: 'update_item', item_id: it.id, text: v });
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing) commit();
    if (e.key === 'Escape') { setText(it.text); setEditing(false); }
  };
  return (
    <div className={`rq-item ${fill ? 'rq-item--fill' : ''}`} data-item={it.text}>
      <span className="rq-item__n">{n}</span>
      {editing ? (
        <input className="rq-item__input" aria-label={`요구사항 ${n}`} value={text} maxLength={200} autoFocus onChange={(e) => setText(e.target.value)} onBlur={commit} onKeyDown={onKey} />
      ) : (
        <button type="button" className="rq-item__text" title={it.text} onClick={() => setEditing(true)}>{it.text}</button>
      )}
      <SrcBadge source={it.source} />
      <button type="button" className="rq-iconx rq-item__del" aria-label="요구사항 삭제" onClick={() => edit({ op: 'remove_item', item_id: it.id })}>
        <Icon name="x" size={11} strokeWidth={2.4} />
      </button>
    </div>
  );
}

function NewItemRow({ n, onDone, onMore }: { n: number; onDone: (text: string) => void; onMore: () => void }) {
  const [text, setText] = useState('');
  const done = useRef(false);
  const finish = (t: string) => { if (done.current) return; done.current = true; onDone(t.trim()); };
  return (
    <div className="rq-item">
      <span className="rq-item__n">{n}</span>
      <input className="rq-item__input" aria-label={`요구사항 ${n}`} placeholder="요구사항" value={text} maxLength={200} autoFocus
        onChange={(e) => setText(e.target.value)} onBlur={() => finish(text)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); const t = text; finish(t); if (t.trim()) onMore(); }
          if (e.key === 'Escape') finish('');
        }} />
    </div>
  );
}
