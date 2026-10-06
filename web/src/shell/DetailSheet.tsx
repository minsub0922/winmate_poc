/**
 * 제품·솔루션 상세 시트(00-shell §5.8~5.9) — URL `?detail=product:<모델코드>|solution:<id>&tab=` 로 열린다.
 * 열려 있는 동안 상단바 팝오버는 숨기고(pop 유지), 닫으면 연 곳(팝오버)으로 돌아간다.
 */
import { useCallback } from 'react';
import { ProductSheet } from './sheets/ProductSheet';
import { SolutionSheet } from './sheets/SolutionSheet';
import { detailSearch, useShellUrl, type DetailKind } from './urlState';

export function DetailSheetHost() {
  const { detail, update } = useShellUrl();
  const close = useCallback(() => update({ detail: null, tab: null, img: null }), [update]);
  if (!detail) return null;
  return detail.kind === 'product'
    ? <ProductSheet key={`p:${detail.id}`} code={detail.id} onClose={close} />
    : <SolutionSheet key={`s:${detail.id}`} id={detail.id} onClose={close} />;
}

/** 상세 시트를 여는 URL 조각(현재 쿼리 유지) — `<Link to={detailHref('product', 'LH55QMCEBGCXKR')}>` */
export const detailHref = (kind: DetailKind, id: string, tab?: string) => detailSearch(kind, id, tab);

/** 기능 화면에서 상세 시트 열기: `const open = useOpenDetail(); open('product', 'LH55QMCEBGCXKR')` */
export function useOpenDetail() {
  const { update } = useShellUrl();
  return useCallback((kind: DetailKind, id: string, tab?: string) => update({ detail: `${kind}:${id}`, tab: tab ?? null, img: null }), [update]);
}

/** 기능 화면에서 팝오버 열기: `const pop = useOpenPopover(); pop('product')` */
export function useOpenPopover() {
  const { update } = useShellUrl();
  return useCallback((kind: 'product' | 'solution' | 'image' | 'case', q?: string) => update({ pop: kind, q: q ?? null, node: null }), [update]);
}
