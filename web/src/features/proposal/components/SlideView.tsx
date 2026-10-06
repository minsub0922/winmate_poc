/**
 * 슬라이드 미리보기(PR7P · PR7C · PR7V · PRU4) — 시트 `display`(값 토큰을 표시 문자열로 바꾼 content, §5.3.1)를 16:9 로 그린다.
 * 보드 PR7P 실측(620×349): 위 6px 브랜드 띠 · eyebrow · 제목 19 · 부제 11 · 본문 · 아래 번호 · 제안서 이름.
 * 칸(slots) 값은 템플릿마다 모양이 달라 모양으로 그린다: 문자열 = 문단, {columns, rows} = 표, 이미지 객체 = 사진, 배열 = 카드 · 수치 · 목록 · 출처, 그 밖의 객체 = 작은 카드.
 * 요소 선택 → 점선 + 미니 툴바(「텍스트 수정」 · 「W로 다시 쓰기」 · 삭제). JSON pointer 경로(`/slots/table/rows/5`)를 그대로 PATCH 에 쓴다.
 */
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { fileUrl } from '@/api/client';
import { Icon, cx } from '@/ui';

export interface SlideCell { text?: string | null; mark?: 'full' | 'half' | 'none' | null }
export interface SlideRow { id?: string; label?: string | null; cells?: SlideCell[]; new?: boolean; recent?: boolean }
export interface SlideDoc { eyebrow?: string | null; title?: string | null; subtitle?: string | null; slots?: Record<string, unknown>; notes?: string | null; footnotes?: Array<{ text?: string }> }
export interface SlideSel { path: string; kind: 'row' | 'item' | 'title' | 'subtitle' | 'eyebrow' | 'image' | 'text' | 'obj'; label: string; deletable?: boolean }
type Obj = Record<string, unknown>;

/** 확정 필요 자리표시(「[00]시간」 · 「[확정 필요]」 · 「[확인 필요]」) */
export const PH_RE = /\[[^\]]{0,24}\]/;
export const hasPlaceholder = (t?: string | null) => !!t && PH_RE.test(t);

/** `[…]` 자리표시를 브랜드 굵게 */
export function PhText({ text }: { text?: string | number | null }) {
  if (text === null || text === undefined || text === '') return null;
  const parts = String(text).split(/(\[[^\]]{0,24}\])/g);
  return <>{parts.map((s, i) => (/^\[[^\]]*\]$/.test(s) ? <span key={i} className="pr-ph">{s}</span> : <span key={i}>{s}</span>))}</>;
}

function Dot({ mark, strong }: { mark?: SlideCell['mark']; strong?: boolean }) {
  if (!mark) return null;
  return <span className={cx('pr-sdot', `pr-sdot--${mark}`, strong && 'pr-sdot--strong')} aria-label={mark === 'full' ? '충족' : mark === 'half' ? '부분' : '미지원'} />;
}

const isObj = (v: unknown): v is Obj => !!v && typeof v === 'object' && !Array.isArray(v);
const str = (v: unknown) => (typeof v === 'string' || typeof v === 'number' ? String(v) : '');
const IMG_KINDS = ['kb_image', 'file', 'image_job', 'image', 'generated'];
export const isImage = (v: unknown): boolean => isObj(v) && ('caption_rule' in v || 'rights' in v || 'asset' in v || 'file_id' in v || (typeof v.kind === 'string' && IMG_KINDS.includes(v.kind) && !('rows' in v)));
export const isTable = (v: unknown): boolean => isObj(v) && (Array.isArray(v.rows) || Array.isArray(v.columns));

/** 이미지 칸 → 주소(파일 · KB 이미지 · 직접 url) */
export function assetUrl(v: unknown): string | null {
  if (!isObj(v)) return null;
  if (typeof v.url === 'string' && !/^https?:\/\/www\.samsung/.test(v.url)) return v.url;
  const a = isObj(v.asset) ? v.asset : v;
  if (typeof a.url === 'string' && a !== v) return a.url;
  if (typeof a.file_id === 'string') return fileUrl(a.file_id);
  if (a.kind === 'file' && typeof a.id === 'string') return fileUrl(a.id);
  if (a.kind === 'kb_image' && typeof a.id === 'string') return `/api/kb/v1/images/${a.id}/thumb`;
  return null;
}

/** JSON pointer 로 값 읽기 */
export function valueAt(doc: unknown, path: string): unknown {
  let cur: unknown = doc;
  for (const seg of path.split('/').slice(1)) {
    if (Array.isArray(cur)) cur = cur[Number(seg)];
    else if (isObj(cur)) cur = cur[seg];
    else return undefined;
  }
  return cur;
}

const KEY_LABEL: Record<string, string> = {
  title: '제목', body: '내용', text: '내용', label: '항목', value: '값', unit: '단위', tag: '태그', model: '모델', caption: '캡션', before: '전', after: '후',
  no: '번호', name: '이름', desc: '설명', note: '메모', customer: '고객사', details: '설명', chart_note: '도표 메모', qty: '수량', role: '역할',
};
const META_KEYS = new Set(['id', 'kind', 'rights', 'source_url', 'url', 'file_id', 'image_version_id', 'mark', 'caption_rule', 'fallback_level', 'source_ref', 'new', 'recent']);
export interface SlideField { path: string; label: string; value: string; wide?: boolean }

/** 선택 요소 → 편집 필드(표 행이면 열 이름이 라벨) */
export function fieldsAt(doc: SlideDoc | null, sel: SlideSel | null): SlideField[] {
  if (!doc || !sel) return [];
  const v = valueAt(doc, sel.path);
  if (sel.kind === 'row') {
    const table = valueAt(doc, sel.path.replace(/\/rows\/\d+$/, '')) as { columns?: string[] } | undefined;
    const cols = table?.columns ?? [];
    const row = v as SlideRow | undefined;
    if (!row) return [];
    return [
      { path: `${sel.path}/label`, label: cols[0] ?? '항목', value: row.label ?? '', wide: true },
      ...(row.cells ?? []).map((c, j) => ({ path: `${sel.path}/cells/${j}/text`, label: cols[j + 1] ?? `칸 ${j + 1}`, value: c.text ?? '', wide: j === 0 })),
    ];
  }
  if (typeof v === 'string' || typeof v === 'number') return [{ path: sel.path, label: sel.label, value: String(v), wide: true }];
  if (isObj(v)) {
    const fs = Object.entries(v).filter(([k, x]) => !META_KEYS.has(k) && (typeof x === 'string' || typeof x === 'number'))
      .map(([k, x]) => ({ path: `${sel.path}/${k}`, label: KEY_LABEL[k] ?? k, value: String(x), wide: ['title', 'body', 'text', 'label', 'caption', 'details', 'desc'].includes(k) }));
    return fs;
  }
  return [];
}

/** 선택한 요소 위 미니 툴바(보드: 검정 h30 · 「텍스트 수정」 「W로 다시 쓰기」 | 삭제) */
export function MiniToolbar({ onEdit, onRewrite, onDelete, label = '선택한 행', style }:
  { onEdit?: () => void; onRewrite?: () => void; onDelete?: () => void; label?: string; style?: CSSProperties }) {
  return (
    <div role="toolbar" aria-label={label} className="pr-minitool" style={style} onClick={(e) => e.stopPropagation()}>
      {onEdit && <button type="button" onClick={onEdit}>텍스트 수정</button>}
      {onRewrite && <button type="button" onClick={onRewrite}><svg width="11" height="11" viewBox="0 0 24 24" fill="var(--wm-brand-on-dark)" aria-hidden="true"><path d="M12 2l2.2 6.3L20.5 10l-6.3 2.2L12 18.5l-2.2-6.3L3.5 10l6.3-1.7z" /></svg>W로 다시 쓰기</button>}
      {onDelete && <><span className="pr-minitool__div" /><button type="button" aria-label={label === '선택한 행' ? '행 삭제' : '삭제'} className="pr-minitool__del" onClick={onDelete}><Icon name="trash" size={12} /></button></>}
    </div>
  );
}

export interface SlideViewProps {
  doc?: SlideDoc | null;
  no?: number | string | null;
  footer?: string | null;
  renderUrl?: string | null;
  sel?: string | null;
  onSelect?: (s: SlideSel | null) => void;
  toolbar?: ReactNode;
  /** 슬라이드 위에 덧그리기(코멘트 핀 · 비교 번호 상자) */
  overlay?: ReactNode;
  /** 줄 id 마다 표시(PRU4 변경 마커 등) */
  marks?: Record<string, 'keep' | 'update' | 'new' | 'drop' | string>;
  width?: number;
  className?: string;
  onSlideClick?: (x: number, y: number) => void;
  dim?: boolean;
}

const W0 = 620;
const H0 = 349;

export function SlideView({ doc, no, footer, renderUrl, sel, onSelect, toolbar, overlay, marks, width, className, onSlideClick, dim }: SlideViewProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(width ?? W0);
  useEffect(() => {
    if (width) { setW(width); return; }
    const el = ref.current?.parentElement;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => setW(Math.min(W0 * 1.4, el.clientWidth)));
    ro.observe(el);
    setW(Math.min(W0 * 1.4, el.clientWidth || W0));
    return () => ro.disconnect();
  }, [width]);
  const k = w / W0;
  const selectable = !!onSelect;
  const pick = (s: SlideSel) => (e: React.MouseEvent) => { if (!selectable) return; e.stopPropagation(); onSelect?.(sel === s.path ? null : s); };
  const on = (p: string) => sel === p;
  const S = (p: string, extra?: string) => cx(extra, selectable && 'pr-sel', on(p) && 'pr-sel--on');
  const mk = (id?: unknown) => (typeof id === 'string' && marks ? marks[id] : undefined);
  const slots = Object.entries(doc?.slots ?? {}).filter(([, v]) => v !== null && v !== undefined && v !== '');
  const empty = !doc || (!doc.title && slots.length === 0);
  const images = slots.filter(([, v]) => isImage(v));
  const rest = slots.filter(([, v]) => !isImage(v));

  const renderArray = (base: string, arr: unknown[], name: string) => {
    if (arr.every((x) => typeof x === 'string')) {
      return (
        <ul key={name} className="pr-sbullets">
          {(arr as string[]).map((t, i) => <li key={i} className={S(`${base}/${i}`)} onClick={pick({ path: `${base}/${i}`, kind: 'text', label: `목록 ${i + 1}줄`, deletable: true })}><PhText text={t} />{on(`${base}/${i}`) && toolbar}</li>)}
        </ul>
      );
    }
    const objs = arr.filter(isObj);
    if (objs.length && objs.every((o) => 'url' in o && 'label' in o && !('title' in o))) {
      return <div key={name} className="pr-ssources">출처 · {objs.map((o) => str(o.label)).join(' · ')}</div>;
    }
    if (objs.length && objs.every((o) => 'value' in o || 'after' in o)) {
      return (
        <div key={name} className="pr-snums">
          {objs.map((o, i) => {
            const p = `${base}/${i}`;
            return (
              <div key={str(o.id) || i} className={S(p, 'pr-snum')} onClick={pick({ path: p, kind: 'item', label: `수치 ${i + 1}`, deletable: true })}>
                <span className="pr-snum__val">{o.before ? <><span className="pr-subtle"><PhText text={str(o.before)} /></span> → </> : null}<b><PhText text={str(o.after ?? o.value)} /></b>{o.unit ? <small> {str(o.unit)}</small> : null}</span>
                <span className="pr-snum__label">{str(o.label)}</span>
                {on(p) && toolbar}
              </div>
            );
          })}
        </div>
      );
    }
    if (objs.length && objs.every((o) => 'text' in o && !('title' in o))) {
      return (
        <ul key={name} className="pr-sbullets">
          {objs.map((o, i) => {
            const p = `${base}/${i}`;
            return <li key={str(o.id) || i} className={cx(S(p), mk(o.id) && `pr-mark--${mk(o.id)}`)} onClick={pick({ path: p, kind: 'item', label: `목록 ${i + 1}줄`, deletable: true })} data-line={str(o.id) || undefined}><PhText text={str(o.text)} />{on(p) && toolbar}</li>;
          })}
        </ul>
      );
    }
    const cols = Math.min(Math.max(objs.length, 1), 4);
    return (
      <div key={name} className="pr-scards" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
        {objs.map((o, i) => {
          const p = `${base}/${i}`;
          const img = isImage(o.image) ? assetUrl(o.image) : null;
          return (
            <div key={str(o.id) || i} className={cx(S(p, 'pr-scard'), mk(o.id) && `pr-mark--${mk(o.id)}`)} onClick={pick({ path: p, kind: 'item', label: `${str(o.no) || i + 1}번 항목`, deletable: true })} data-line={str(o.id) || undefined}>
              {img && <img src={img} alt="" className="pr-scard__img" draggable={false} />}
              {o.no ? <span className="pr-scard__no pr-num">{str(o.no)}</span> : null}
              <b className="pr-scard__title"><PhText text={str(o.title ?? o.label ?? o.name ?? o.tag)} /></b>
              {(o.body ?? o.text ?? o.desc ?? o.model) ? <span className="pr-scard__body"><PhText text={str(o.body ?? o.text ?? o.desc ?? o.model)} /></span> : null}
              {on(p) && toolbar}
            </div>
          );
        })}
      </div>
    );
  };

  const renderSlot = (name: string, v: unknown) => {
    const base = `/slots/${name}`;
    if (typeof v === 'string' || typeof v === 'number') {
      return <div key={name} className={S(base, 'pr-stext')} onClick={pick({ path: base, kind: 'text', label: KEY_LABEL[name] ?? '문단' })}><PhText text={v} />{on(base) && toolbar}</div>;
    }
    if (Array.isArray(v)) return v.length ? renderArray(base, v, name) : null;
    if (!isObj(v)) return null;
    if (isTable(v)) {
      const cols = (v.columns as string[] | undefined) ?? [];
      const hl = typeof v.highlight_col === 'number' ? v.highlight_col : cols.findIndex((c) => /삼성/.test(c));
      const tpl = cols.length ? `29% repeat(${Math.max(1, cols.length - 1)}, minmax(0, 1fr))` : '1fr';
      return (
        <div key={name} className="pr-stable">
          {cols.length > 0 && <div className="pr-stable__head" style={{ gridTemplateColumns: tpl }}>{cols.map((c, j) => <div key={j} className={cx(j === hl && 'pr-stable__hl')}>{c}</div>)}</div>}
          {((v.rows as SlideRow[] | undefined) ?? []).map((r, i) => {
            const p = `${base}/rows/${i}`;
            return (
              <div key={r.id ?? i} className={cx(S(p, 'pr-stable__row'), mk(r.id) && `pr-mark--${mk(r.id)}`)} style={{ gridTemplateColumns: tpl }}
                onClick={pick({ path: p, kind: 'row', label: `표 ${i + 1}행`, deletable: true })} data-row={r.id}>
                <div className="pr-stable__label"><PhText text={r.label} /></div>
                {(r.cells ?? []).map((c, j) => (
                  <div key={j} className={cx('pr-stable__cell', j + 1 === hl && 'pr-stable__cell--hl')}>
                    <Dot mark={c.mark} strong={j + 1 === hl} /><span className="pr-ell"><PhText text={c.text} /></span>
                  </div>
                ))}
                {on(p) && toolbar}
              </div>
            );
          })}
        </div>
      );
    }
    if (isImage(v)) {
      const url = assetUrl(v);
      return (
        <div key={name} className={S(base, 'pr-simg')} onClick={pick({ path: base, kind: 'image', label: '이미지' })}>
          {url ? <img src={url} alt={str(v.label)} draggable={false} /> : <span className="pr-simg__ph"><Icon name="image" size={18} color="var(--wm-text-subtle)" />{str(v.label) || '이미지 자리'}</span>}
          {str(v.caption ?? v.caption_rule) ? <span className="pr-simg__cap">{str(v.caption ?? v.caption_rule)}</span> : null}
          {on(base) && toolbar}
        </div>
      );
    }
    if (Array.isArray(v.items)) return v.items.length ? renderArray(`${base}/items`, v.items, name) : null;
    if (typeof v.text === 'string') return <div key={name} className={S(`${base}/text`, 'pr-stext')} onClick={pick({ path: `${base}/text`, kind: 'text', label: '문단' })}><PhText text={v.text} />{on(`${base}/text`) && toolbar}</div>;
    // 그 밖의 객체(예 제품 { tag, title, model }) = 작은 카드
    return (
      <div key={name} className={S(base, 'pr-scard pr-scard--solo')} onClick={pick({ path: base, kind: 'obj', label: KEY_LABEL[name] ?? name })}>
        {v.tag ? <span className="pr-scard__tag">{str(v.tag)}</span> : null}
        <b className="pr-scard__title"><PhText text={str(v.title ?? v.name ?? v.label)} /></b>
        {(v.model || v.body || v.desc) ? <span className="pr-scard__body"><PhText text={str(v.model ?? v.body ?? v.desc)} /></span> : null}
        {on(base) && toolbar}
      </div>
    );
  };

  const body = (
    <div className={cx('pr-slide', dim && 'pr-slide--dim')} style={{ width: W0, height: H0, transform: `scale(${k})`, transformOrigin: 'top left' }}
      onClick={(e) => {
        if (onSlideClick) { const r = (e.currentTarget as HTMLDivElement).getBoundingClientRect(); onSlideClick((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height); }
        else if (selectable) onSelect?.(null);
      }}>
      <div className="pr-slide__bar" />
      {empty && renderUrl ? <img src={renderUrl} alt="" className="pr-slide__png" draggable={false} /> : empty ? (
        <div className="pr-slide__empty"><Icon name="file" size={22} color="var(--wm-text-subtle)" /><span>아직 내용이 없어요</span></div>
      ) : (
        <>
          {doc?.eyebrow && <div className={S('/eyebrow', 'pr-slide__eyebrow')} onClick={pick({ path: '/eyebrow', kind: 'eyebrow', label: '머리말' })}>{doc.eyebrow}{on('/eyebrow') && toolbar}</div>}
          {doc?.title && <div className={S('/title', 'pr-slide__title')} onClick={pick({ path: '/title', kind: 'title', label: '제목' })}><PhText text={doc.title} />{on('/title') && toolbar}</div>}
          {doc?.subtitle && <div className={S('/subtitle', 'pr-slide__sub')} onClick={pick({ path: '/subtitle', kind: 'subtitle', label: '부제' })}><PhText text={doc.subtitle} />{on('/subtitle') && toolbar}</div>}
          <div className={cx('pr-slide__body', images.length > 0 && rest.length > 0 && 'pr-slide__body--split')}>
            {images.length > 0 && rest.length > 0 ? (
              <>
                <div className="pr-slide__imgcol">{images.map(([n, v]) => renderSlot(n, v))}</div>
                <div className="pr-slide__restcol">{rest.map(([n, v]) => renderSlot(n, v))}</div>
              </>
            ) : slots.map(([n, v]) => renderSlot(n, v))}
          </div>
          {!!doc?.footnotes?.length && <div className="pr-slide__fn">{doc.footnotes.map((f) => f.text).filter(Boolean).join(' · ')}</div>}
        </>
      )}
      {no !== undefined && no !== null && <div className="pr-slide__no">{typeof no === 'number' ? String(no).padStart(2, '0') : no}</div>}
      {footer && <div className="pr-slide__foot">{footer}</div>}
      {overlay}
    </div>
  );
  return (
    <div ref={ref} className={cx('pr-slidebox', className)} style={{ width: W0 * k, height: H0 * k }}>
      {body}
    </div>
  );
}
