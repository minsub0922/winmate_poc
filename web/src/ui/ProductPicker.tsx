/**
 * 제품 · 솔루션 고르기 대화상자(보드 webapp1 ProdPicker · VP2_Pick · SC2_Pick) — 760×640.
 * 묶음(DSS 제품 · DSS 솔루션 …)의 2열 체크 행 + 아래 `+ 카탈로그에서 찾기`(kb 제품 검색 · 솔루션 카탈로그) + 발 `n개 골랐어요 · 완료`.
 * 고른 것은 이름으로 센다(같은 이름 = 같은 항목). min 보다 적으면 발 문구가 주황.
 */
import { useEffect, useState } from 'react';
import { cx } from './controls';
import { Modal } from './overlay';
import { searchProducts, productName } from './ProductInput';

export interface PickItem { name: string; kind: 'product' | 'solution'; ref?: string | null; where?: string }
export interface PickGroup { label: string; items: PickItem[] }

interface SolRow { id: string; name: string; domain?: string; kb_id?: string | null }

function useCatalog(q: string) {
  const [rows, setRows] = useState<PickItem[]>([]);
  useEffect(() => {
    const t = q.trim();
    if (t.length < 1) { setRows([]); return; }
    const ac = new AbortController();
    const h = setTimeout(async () => {
      try {
        const [prods, sols] = await Promise.all([
          searchProducts(t, { limit: 6, kinds: 'family', signal: ac.signal }).catch(() => []),
          fetch(`/api/kb/v1/solutions?q=${encodeURIComponent(t)}`, { credentials: 'same-origin', signal: ac.signal })
            .then((r) => (r.ok ? r.json() : { items: [] })).then((b: { items?: SolRow[] }) => b.items ?? []).catch(() => [] as SolRow[]),
        ]);
        setRows([
          ...prods.map((p) => ({ name: productName(p), kind: 'product' as const, ref: `kb:${p.kind}:${p.id}`, where: `카탈로그 · ${(p.category_path ?? []).slice(-1)[0] ?? '제품'}` })),
          ...sols.map((s) => ({ name: s.name, kind: 'solution' as const, ref: s.kb_id ? `kb:solution:${s.kb_id}` : `kb:solution:${s.id}`, where: `카탈로그 · ${s.domain || '솔루션'}` })),
        ]);
      } catch { /* 검색 실패는 빈 결과 */ }
    }, 250);
    return () => { clearTimeout(h); ac.abort(); };
  }, [q]);
  return rows;
}

function Row({ it, on, onToggle }: { it: PickItem; on: boolean; onToggle: () => void }) {
  return (
    <button type="button" role="checkbox" aria-checked={on} className={cx('wm-pick__row', on && 'wm-pick__row--on')} onClick={onToggle}>
      <span className={cx('wm-pick__box', on && 'wm-pick__box--on')} aria-hidden>
        {on && <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>}
      </span>
      <span className="wm-pick__txt"><span className="wm-pick__name">{it.name}</span>{it.where && <span className="wm-pick__where">{it.where}</span>}</span>
      <span className={cx('wm-kindtag', it.kind === 'solution' && 'wm-kindtag--sol')}>{it.kind === 'solution' ? '솔루션' : '제품'}</span>
    </button>
  );
}

export function ProductPickerDialog({ open, title = '제품 · 솔루션 고르기', sub, groups, picked, onToggle, onClose, min = 0 }: {
  open: boolean; title?: string; sub?: string; groups: PickGroup[]; picked: string[]; onToggle: (it: PickItem) => void; onClose: () => void; min?: number;
}) {
  const [q, setQ] = useState('');
  const found = useCatalog(q);
  const known = new Set(groups.flatMap((g) => g.items.map((i) => i.name)));
  const pickedOutside = picked.filter((n) => !known.has(n));
  const short = picked.length < min;
  return (
    <Modal open={open} onClose={onClose} width={760} height={640} ariaLabel={title}
      title={<span style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '6px 0' }}><span style={{ fontSize: 18, fontWeight: 700 }}>{title}</span>{sub && <span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', fontWeight: 400, lineHeight: 1.5 }}>{sub}</span>}</span>}
      bodyStyle={{ padding: '14px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}
      footer={<div style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}>
        <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: short ? 'var(--wm-amber)' : 'var(--wm-text-muted)' }}>{short ? '하나 이상 골라야 해요' : `${picked.length}개 골랐어요`}</span>
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h40" onClick={onClose} style={{ fontSize: 13.5, fontWeight: 700, padding: '0 20px' }}>완료</button>
      </div>}>
      {groups.map((g) => (
        <div key={g.label} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span className="wm-pick__group">{g.label}</span>
          <div className="wm-pick__grid">{g.items.map((it) => <Row key={it.name} it={it} on={picked.includes(it.name)} onToggle={() => onToggle(it)} />)}</div>
        </div>
      ))}
      {!!pickedOutside.length && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span className="wm-pick__group">고른 카탈로그 항목</span>
          <div className="wm-pick__grid">{pickedOutside.map((n) => <Row key={n} it={{ name: n, kind: 'product', where: '카탈로그' }} on onToggle={() => onToggle({ name: n, kind: 'product' })} />)}</div>
        </div>
      )}
      <label className="wm-sr" htmlFor="wm-pick-search">카탈로그에서 찾기</label>
      <input id="wm-pick-search" className="wm-pick__search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="+ 카탈로그에서 제품 · 솔루션 찾기 (DSS 밖)" />
      {(!!found.length || !!q.trim()) && (
        <div className="wm-pick__grid">
          {found.filter((f) => !known.has(f.name)).map((it) => <Row key={`${it.kind}:${it.name}`} it={it} on={picked.includes(it.name)} onToggle={() => onToggle(it)} />)}
          {!!q.trim() && !known.has(q.trim()) && !found.some((f) => f.name === q.trim()) && (
            <Row it={{ name: q.trim(), kind: 'product', ref: null, where: '직접 추가 · KB 에 없음 · 확인 필요' }} on={picked.includes(q.trim())}
              onToggle={() => onToggle({ name: q.trim(), kind: 'product', ref: null })} />
          )}
        </div>
      )}
    </Modal>
  );
}
