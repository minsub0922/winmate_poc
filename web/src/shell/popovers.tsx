/**
 * 상단바 팝오버 4종(00-shell §5.2~5.6) — 제품 탐색 · 솔루션 탐색 · 이미지 검색 · 유관 사례 검색.
 * 데이터는 kb 서비스(/api/kb/v1/...), 고른 항목은 화면 맥락의 onAdd 로 넘긴다. 구현은 ./pop/*.
 */
import { CasePopover } from './pop/CasePopover';
import { ImagePopover } from './pop/ImagePopover';
import { ProductPopover } from './pop/ProductPopover';
import { SolutionPopover } from './pop/SolutionPopover';
import type { PopoverKind } from './urlState';

export type { PopoverKind } from './urlState';

export function Popovers({ kind, onClose, hidden }: { kind: PopoverKind; onClose: () => void; hidden?: boolean }) {
  if (kind === 'product') return <ProductPopover onClose={onClose} hidden={hidden} />;
  if (kind === 'solution') return <SolutionPopover onClose={onClose} hidden={hidden} />;
  if (kind === 'image') return <ImagePopover onClose={onClose} hidden={hidden} />;
  return <CasePopover onClose={onClose} hidden={hidden} />;
}
