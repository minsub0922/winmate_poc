/** BE2 — 배치될 제품 2/5(`/birdseye/:id/products`, §4.5): 공간 W · 요약 칩 · 제품 검색(Enter 로 추가) · 제품 탐색 · 추가된 칩. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useOpenPopover } from '@/shell';
import { Icon, toast, useDropTarget } from '@/ui';
import { be, errText, qk, useBe, useProducts, type ProductItem, type S } from '../api';
import { Agent, BePage, Dock, DockLink, Echo, InfoChips, Loading, MainButton, SubButton, useBeShell } from '../ui';

type Hit = S['ProductSearchItem'];

export default function ProductsPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const pq = useProducts(id);
  const openPop = useOpenPopover();
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const items = pq.data?.items ?? [];
  const analyzing = !!pq.data?.analyzing;
  const refresh = () => qc.invalidateQueries({ queryKey: qk.products(id) });
  useEffect(() => {
    if (!analyzing) return;
    const t = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(t);
  }, [analyzing]); // eslint-disable-line react-hooks/exhaustive-deps

  /** 추가 · 제거는 차례대로(빠르게 연달아 넣어도 앞 요청을 덮지 않게 서버 목록을 다시 읽고 바꾼다) */
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const picks = (list: ProductItem[]) => list.map((p) => ({ family_id: p.family_id || null, model_code: p.model_code ?? null, ref: p.ref }));
  const mutate = <T,>(fn: (cur: ProductItem[]) => { next: Array<S['ProductPick']> | null; out: T }): Promise<T | null> => {
    const run = chain.current.then(async () => {
      setSaving(true);
      try {
        const cur = (await be.products(id)).items;
        const { next, out } = fn(cur);
        if (next) await be.putProducts(id, next);
        await refresh();
        return out;
      } catch (e) { toast(errText(e)); return null; } finally { setSaving(false); }
    });
    chain.current = run.catch(() => undefined);
    return run;
  };
  const addRefs = async (refs: string[], labels: Record<string, string> = {}) => {
    const r = await mutate((cur) => {
      const have = new Set(cur.map((p) => p.ref));
      const fresh = refs.filter((x) => !have.has(x) && !have.has(x.replace('kb:model:', 'kb:model:mdl_')));
      return { next: fresh.length ? [...picks(cur), ...fresh.map((x) => ({ ref: x, label: labels[x] ?? null }))] : null, out: fresh };
    });
    return r ?? [];
  };
  const remove = (p: ProductItem) => mutate((cur) => ({ next: picks(cur.filter((x) => x.id !== p.id)), out: true }));

  useBeShell(bq.data, 2, {
    accepts: ['product'], addable: ['product'], added: items.map((p) => p.ref),
    onAdd: async (_type, refs) => ({ added: await addRefs(refs) }),
  });
  const drop = useDropTarget({ accept: ['product'], onDrop: async (p) => { const a = await addRefs([p.ref], { [p.ref]: p.label }); return a.length ? true : false; } });

  const next = async () => {
    setBusy(true);
    try {
      await be.recommend(id, []);
      await qc.invalidateQueries({ queryKey: qk.furniture(id) });
      nav(`/birdseye/${id}/furniture`);
    } catch (e) { toast(errText(e)); setBusy(false); }
  };

  if (bq.isLoading || pq.isLoading) return <Loading />;
  const v = pq.data;
  return (
    <BePage testId="be2" dock={(
      <Dock title="배치될 제품" meta={<>{items.length}개 추가됨 · 2 / 5</>}
        right={<DockLink onClick={() => openPop('product')} icon={<Icon name="folder" size={13} />}>제품 탐색에서 고르기</DockLink>}
        foot={(
          <>
            <span className="be-note" style={{ flex: 1 }}>수량과 위치 메모는 4단계 배치 컨펌에서 조정합니다</span>
            <SubButton to={`/birdseye/${id}/space`}>이전</SubButton>
            <MainButton onClick={next} busy={busy} disabled={!items.length || analyzing} reason="배치할 제품을 1개 이상 추가해 주세요" testId="be2-next">가구 추천 받기</MainButton>
          </>
        )}>
        <div {...drop.props} data-state={drop.state} className={drop.over ? 'be-attach--over' : undefined} style={{ borderRadius: 12 }}>
          <ProductSearch items={items} onPick={(h) => void addRefs([h.ref], { [h.ref]: h.name })} onRemove={remove} busy={saving} />
        </div>
      </Dock>
    )}>
      <Echo text={v?.echo} files={v?.files?.map((f) => ({ name: f.name, to: f.route }))} />
      <Agent text={v?.w_message} busy={analyzing}>
        <InfoChips items={v?.chips ?? []} testId="be2-chips" />
      </Agent>
    </BePage>
  );
}

/** 제품명 입력 → 결과 패널(위로, 최대 5행) — 「"{q}" 검색 결과 · Enter로 추가」 · 포커스 행 「추가 ↵」 */
function ProductSearch({ items, onPick, onRemove, busy }: { items: ProductItem[]; onPick: (h: Hit) => void; onRemove: (p: ProductItem) => void; busy?: boolean }) {
  const [q, setQ] = useState('');
  const [dq, setDq] = useState('');
  const [hits, setHits] = useState<Hit[]>([]);
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const pendingEnter = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { const t = window.setTimeout(() => setDq(q.trim()), 150); return () => window.clearTimeout(t); }, [q]);
  useEffect(() => {
    if (!dq) { setHits([]); return; }
    let alive = true;
    setLoading(true);
    be.search(dq, 5).then((r) => {
      if (!alive) return;
      setHits(r.items); setActive(0); setLoading(false);
      if (pendingEnter.current && r.items.length) { pendingEnter.current = false; pick(r.items[0]); }
    }).catch(() => { if (alive) { setHits([]); setLoading(false); } });
    return () => { alive = false; };
  }, [dq]); // eslint-disable-line react-hooks/exhaustive-deps
  const pick = (h: Hit) => { onPick(h); setQ(''); setDq(''); setHits([]); inputRef.current?.focus(); };
  const added = useMemo(() => new Set(items.map((p) => p.ref)), [items]);
  const show = open && !!q.trim() && (hits.length > 0 || loading || !!dq);
  return (
    <div className="be-ps" data-testid="be2-search">
      {show && (
        <div className="be-ps__panel" role="listbox" aria-label="제품 검색 결과" onMouseDown={(e) => e.preventDefault()}>
          <div className="be-ps__head" data-testid="be2-results-head">"{q.trim()}" 검색 결과 · Enter로 추가</div>
          {loading && !hits.length && <div className="be-ps__head">찾는 중…</div>}
          {!loading && dq && !hits.length && <div className="be-ps__head">카탈로그에서 맞는 제품을 찾지 못했어요</div>}
          {hits.map((h, i) => (
            <button key={h.ref} type="button" role="option" aria-selected={i === active} className={i === active ? 'be-ps__row be-ps__row--on' : 'be-ps__row'}
              onMouseEnter={() => setActive(i)} onClick={() => pick(h)}>
              <span className="be-ps__thumb">{h.thumb_url ? <img src={h.thumb_url} alt="" /> : null}</span>
              <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0, flex: 1 }}>
                <span className="be-ps__name">{hl(h.name, h.name_match)}</span>
                <span className="be-ps__sub">{h.subline}</span>
              </span>
              {i === active && <span className="be-ps__cta">{added.has(h.ref) ? '이미 추가됨' : '추가 ↵'}</span>}
            </button>
          ))}
        </div>
      )}
      <div className="be-ps__box" onClick={() => inputRef.current?.focus()}>
        {items.map((p) => (
          <span key={p.id} className="be-tok" data-testid="be2-token">{p.display_name}
            <button type="button" aria-label="제거" onClick={() => onRemove(p)} disabled={busy}><Icon name="x" size={12} /></button>
          </span>
        ))}
        <label htmlFor="be2-q" className="wm-sr-only">제품명 입력</label>
        <input id="be2-q" ref={inputRef} value={q} placeholder={items.length ? '' : '제품명 입력'} autoComplete="off" role="combobox" aria-expanded={show}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
          onKeyDown={(e) => {
            if (e.nativeEvent.isComposing) return;
            if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, Math.max(0, hits.length - 1))); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
            else if (e.key === 'Enter') {
              e.preventDefault();
              if (dq === q.trim() && hits.length) pick(hits[Math.min(active, hits.length - 1)]);
              else if (q.trim()) { pendingEnter.current = true; setDq(q.trim()); }
            } else if (e.key === 'Escape') setOpen(false);
            else if (e.key === 'Backspace' && !q && items.length) onRemove(items[items.length - 1]);
          }} />
      </div>
    </div>
  );
}

function hl(name: string, m?: number[] | null) {
  if (!m || m.length !== 2 || m[0] >= m[1]) return name;
  return <>{name.slice(0, m[0])}<em>{name.slice(m[0], m[1])}</em>{name.slice(m[1])}</>;
}
