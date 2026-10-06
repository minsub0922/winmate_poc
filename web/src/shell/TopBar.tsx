/**
 * 상단 액션바(00-shell §5.2) — 브레드크럼 + 알약 버튼 4개(제품 탐색 · 솔루션 탐색 · 이미지 검색 · 유관 사례 검색).
 * 팝오버는 버튼 오른쪽 끝에 붙어 탭처럼 열리고(한 번에 하나), URL `pop` 으로 상태를 둔다.
 */
import { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { getActiveDrag } from '@/ui';
import { TopBarIcon } from './icons';
import { Popovers } from './popovers';
import { useShellRuntime } from './runtime';
import { useShellUrl, type PopoverKind } from './urlState';

export const TOPBAR_BUTTONS: Array<{ kind: PopoverKind; label: string }> = [
  { kind: 'product', label: '제품 탐색' },
  { kind: 'solution', label: '솔루션 탐색' },
  { kind: 'image', label: '이미지 검색' },
  { kind: 'case', label: '유관 사례 검색' },
];

export function TopBar({ section, title }: { section?: string; title?: string }) {
  const url = useShellUrl();
  const rt = useShellRuntime();
  const { pop, detail, update } = url;
  const wrapRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const open = (k: PopoverKind) => {
    const mem = rt.recall<{ q?: string; node?: string | null }>(k);
    update({ pop: k, q: mem?.q || null, node: k === 'product' ? mem?.node ?? null : null });
  };
  const close = () => update({ pop: null, q: null, node: null });
  const toggle = (k: PopoverKind) => (pop === k ? close() : open(k));

  // 바깥 클릭으로 닫기(끌기 중 · 상세 시트가 열린 동안은 아님)
  const closeRef = useRef(close);
  closeRef.current = close;
  useEffect(() => {
    if (!pop || detail) return;
    const h = (e: MouseEvent) => {
      if (getActiveDrag()) return;
      const w = wrapRefs.current[pop];
      const t = e.target as Node | null;
      if (w && t && w.contains(t)) return;
      if (t instanceof Element && t.closest('[data-shell-keep-popover]')) return;
      closeRef.current();
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [pop, detail]);

  return (
    <header className="sh-topbar">
      <nav className="sh-crumbs" aria-label="현재 위치">
        <Link to="/">홈</Link>
        {section && <><span aria-hidden="true">/</span><span className="sh-crumbs__sec">{section}</span></>}
        {title && <><span aria-hidden="true">/</span><span className="sh-crumbs__cur" aria-current="page">{title}</span></>}
      </nav>
      <div className="sh-pills">
        {TOPBAR_BUTTONS.map((b) => {
          const on = pop === b.kind;
          return (
            <div key={b.kind} className="sh-pillwrap" ref={(el) => { wrapRefs.current[b.kind] = el; }}>
              <button type="button" className={on ? 'sh-pill sh-pill--on' : 'sh-pill'} aria-expanded={on} aria-haspopup="dialog"
                aria-controls={on ? `sh-pop-${b.kind}` : undefined} onClick={() => toggle(b.kind)} data-pill={b.kind}>
                <TopBarIcon kind={b.kind} />
                <span>{b.label}</span>
              </button>
              {on && <Popovers kind={b.kind} onClose={close} hidden={!!detail} />}
            </div>
          );
        })}
      </div>
    </header>
  );
}
