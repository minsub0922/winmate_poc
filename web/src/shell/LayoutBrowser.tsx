/**
 * PPT 레이아웃 브라우저 `/layouts` [제안 — 보드 없음] — export 카탈로그(430종)를 섹션별로 훑고 코드 · 이름 · 쓰는 때로 찾는다.
 * 사이드바 「PPT 레이아웃 브라우저」(작업 내역 위)로 연다.
 *
 * 데이터: export `GET /v1/templates?limit=1000&include_slots=false`(한 번 받아 브라우저에서 거른다) ·
 *         `GET /v1/templates/{code}`(상세 · 칸) · `/templates/{code}/board.jpg`(원본 보드 그림) · `/thumbnail.png`(와이어프레임).
 * URL: `?find=` 검색어 · `sec=` 섹션 · `st=all` 제작 중 포함 · `layout=` 열린 상세(코드) — 링크로 그대로 공유된다.
 */
import { useMemo, useRef, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import type { components } from '@/api/gen/export';
import {
  Badge, Button, Chip, Empty, ErrorState, MetaRows, NeutralTag, SearchField, Segmented, SideSheet, Skeleton, StatusBadge, Tag, templateThumbUrl, toast,
} from '@/ui';
import { useShellPage } from './ShellContext';

type Tpl = components['schemas']['TemplateSummary'];

const SECTION_ORDER = ['common', 'mi', 'vp', 'birdseye', 'space_products', 'solution', 'space_scenario', 'cases', 'why', 'spec', 'appendix'];
const KIND_LABEL: Record<string, string> = {
  common: '공통', generic: '범용', industry: '업종판', product: '제품', dedicated: '전용', industry_solution: '솔루션 업종판',
};
const PTYPE_LABEL: Record<string, string> = { standard: '표준', quickwin: '퀵윈', solution: 'Solution형' };
const STATUS_LABEL: Record<string, string> = { ready: '사용 가능', in_production: '제작 중', internal: '내부' };

export const boardImageUrl = (code: string) => `/api/export/v1/templates/${encodeURIComponent(code)}/board.jpg`;
const wireUrl = (code: string, w: number) => `${templateThumbUrl(code)}?w=${w}`;

const norm = (s: string) => s.toLowerCase();
const compact = (s: string) => norm(s).replace(/[\s\-·_./()]+/g, '');

function haystack(t: Tpl): { full: string; tight: string } {
  const parts = [t.code, t.display_code, t.name, t.description, t.when, t.section_name, t.role_name, t.sheet_role, t.archetype,
    t.industry_name, t.industry_code, t.solution_name, t.solution_code, KIND_LABEL[t.kind] ?? t.kind, t.variant]
    .filter((x): x is string => typeof x === 'string' && x.length > 0);
  const full = norm(parts.join(' \u0001 '));
  return { full, tight: compact(parts.join('')) };
}

function matches(h: { full: string; tight: string }, words: string[]) {
  return words.every((w) => h.full.includes(norm(w)) || (compact(w).length > 0 && h.tight.includes(compact(w))));
}

/** 이름 안 검색어를 굵게 */
function Hl({ text, words }: { text: string; words: string[] }) {
  const ws = words.map(norm).filter(Boolean);
  if (!ws.length) return <>{text}</>;
  const low = norm(text);
  const marks: Array<[number, number]> = [];
  for (const w of ws) {
    let i = low.indexOf(w);
    while (i >= 0) { marks.push([i, i + w.length]); i = low.indexOf(w, i + w.length); }
  }
  if (!marks.length) return <>{text}</>;
  marks.sort((a, b) => a[0] - b[0]);
  const out: ReactNode[] = [];
  let at = 0;
  for (const [s, e] of marks) {
    if (e <= at) continue;
    const from = Math.max(s, at);
    if (from > at) out.push(text.slice(at, from));
    out.push(<mark key={from} className="lb-mark">{text.slice(from, e)}</mark>);
    at = e;
  }
  out.push(text.slice(at));
  return <>{out}</>;
}

/** 원본 보드 그림 → 없으면 와이어프레임 */
function LayoutImage({ code, w, alt, eager }: { code: string; w: number; alt: string; eager?: boolean }) {
  const [src, setSrc] = useState(boardImageUrl(code));
  const [wire, setWire] = useState(false);
  return (
    <img className={wire ? 'lb-img lb-img--wire' : 'lb-img'} src={src} alt={alt} loading={eager ? 'eager' : 'lazy'} decoding="async" draggable={false}
      onError={() => { if (!wire) { setWire(true); setSrc(wireUrl(code, w)); } }} />
  );
}

function useTemplates() {
  return useQuery({
    queryKey: ['export', 'templates', 'all'],
    queryFn: async () => unwrap(await api.export.GET('/v1/templates', { params: { query: { limit: 1000, include_slots: false } } })),
    staleTime: 10 * 60_000,
  });
}

function useTemplate(code: string | null) {
  return useQuery({
    queryKey: ['export', 'template', code],
    queryFn: async () => unwrap(await api.export.GET('/v1/templates/{code}', { params: { path: { code: code! } } })),
    enabled: !!code,
    staleTime: 10 * 60_000,
  });
}

function Card({ t, words, onOpen }: { t: Tpl; words: string[]; onOpen: () => void }) {
  const dim = t.status !== 'ready';
  return (
    <button type="button" className={dim ? 'lb-card lb-card--dim' : 'lb-card'} onClick={onOpen} data-code={t.code}
      aria-label={`${t.display_code} ${t.name} 자세히 보기`}>
      <span className="lb-card__img"><LayoutImage code={t.code} w={480} alt="" /></span>
      <span className="lb-card__body">
        <span className="lb-card__top">
          <span className="lb-code wm-num"><Hl text={t.display_code} words={words} /></span>
          {t.status !== 'ready' && <StatusBadge tone="warn">{STATUS_LABEL[t.status] ?? t.status}</StatusBadge>}
          {t.industry_name && <NeutralTag>{t.industry_name}</NeutralTag>}
          {t.solution_name && !t.industry_name && <NeutralTag>{t.solution_name}</NeutralTag>}
        </span>
        <span className="lb-card__name"><Hl text={t.name} words={words} /></span>
        {t.when && <span className="lb-card__when"><Hl text={t.when} words={words} /></span>}
      </span>
    </button>
  );
}

function Detail({ code, onClose }: { code: string; onClose: () => void }) {
  const d = useTemplate(code);
  const [view, setView] = useState<'board' | 'wire'>('board');
  const t = d.data;
  const copy = async () => {
    try { await navigator.clipboard.writeText(t?.display_code ?? code); toast(`「${t?.display_code ?? code}」 코드를 복사했어요`); }
    catch { toast('복사하지 못했어요'); }
  };
  const slots = (t?.slots ?? []) as Array<Record<string, unknown>>;
  const source = (t?.source ?? null) as { canvas?: string; board?: string; title?: string; path?: string } | null;
  return (
    <SideSheet open onClose={onClose} width={720} title={t ? <span><span className="lb-code wm-num">{t.display_code}</span> · {t.name}</span> : code}
      footer={<><Button h={38} onClick={copy}>코드 복사</Button><Button h={38} variant="primary" onClick={onClose}>닫기</Button></>}>
      {d.isLoading && <div className="lb-detail"><Skeleton h={360} r={12} /><Skeleton h={18} /><Skeleton h={18} /></div>}
      {d.isError && <ErrorState message="레이아웃을 불러오지 못했어요" onRetry={() => d.refetch()} />}
      {t && (
        <div className="lb-detail" data-testid="layout-detail">
          <div className="lb-detail__stage">
            {view === 'board'
              ? <LayoutImage key={`b-${code}`} code={t.code} w={1280} alt={`${t.display_code} 원본 보드`} eager />
              : <img className="lb-img lb-img--wire" src={wireUrl(t.code, 1280)} alt={`${t.display_code} 와이어프레임`} />}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Segmented<'board' | 'wire'> value={view} onChange={setView} ariaLabel="그림 종류"
              items={[{ value: 'board', label: '원본 보드' }, { value: 'wire', label: '와이어프레임' }]} />
            <span style={{ flex: 1 }} />
            <Badge tone={t.status === 'ready' ? 'ok' : 'warn'}>{STATUS_LABEL[t.status] ?? t.status}</Badge>
          </div>
          {t.when && <p className="lb-detail__when"><b>쓰는 때</b> {t.when}</p>}
          {t.description && t.description !== t.when && <p className="lb-detail__desc">{t.description}</p>}
          <MetaRows variant="sheet" rows={[
            { k: '섹션', v: t.section_name || t.section },
            { k: '시트 역할', v: `${t.sheet_role} · ${t.role_name}` },
            { k: '종류', v: KIND_LABEL[t.kind] ?? t.kind },
            { k: '원형', v: t.archetype },
            ...(t.industry_name ? [{ k: '업종', v: t.industry_name }] : []),
            ...(t.solution_name ? [{ k: '솔루션', v: t.solution_name }] : []),
            ...(t.proposal_types?.length ? [{ k: '제안서 유형', v: t.proposal_types.map((p) => PTYPE_LABEL[p] ?? p).join(' · ') }] : []),
            { k: '칸', v: `${t.slot_count}개` },
            ...(source?.board ? [{ k: '원본 보드', v: `${source.canvas}/${source.board}` }] : []),
          ]} />
          {slots.length > 0 && (
            <section>
              <h3 className="lb-h3">칸(slots) {slots.length}</h3>
              <ul className="lb-slots">
                {slots.map((s) => (
                  <li key={String(s.key)}>
                    <code className="lb-slot__key">{String(s.key)}</code>
                    <Tag tone="neutral">{String(s.type)}</Tag>
                    {s.required === true && <Tag tone="warn">필수</Tag>}
                    <span className="lb-slot__label">{String(s.label ?? '')}</span>
                    {typeof s.max_chars === 'number' && <span className="lb-slot__cap wm-num">≤{s.max_chars}자</span>}
                    {typeof s.count === 'number' && <span className="lb-slot__cap wm-num">×{s.count}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </SideSheet>
  );
}

export default function LayoutBrowser() {
  useShellPage({ section: 'PPT 레이아웃', title: '브라우저', hasTask: false });
  const [sp, setSp] = useSearchParams();
  const find = sp.get('find') ?? '';
  const sec = sp.get('sec') ?? 'all';
  const st = sp.get('st') === 'all' ? 'all' : 'ready';
  const open = sp.get('layout');
  const set = (patch: Record<string, string | null>) => setSp((prev) => {
    const n = new URLSearchParams(prev);
    for (const [k, v] of Object.entries(patch)) { if (v === null || v === '') n.delete(k); else n.set(k, v); }
    return n;
  }, { replace: true });
  const searchRef = useRef<HTMLInputElement>(null);
  const q = useTemplates();

  const words = useMemo(() => find.trim().split(/\s+/).filter(Boolean), [find]);
  const all = useMemo(() => (q.data?.items ?? []).map((t) => ({ t, h: haystack(t) })), [q.data]);
  const byStatus = useMemo(() => all.filter(({ t }) => st === 'all' || t.status === 'ready'), [all, st]);
  const hits = useMemo(() => byStatus.filter(({ h }) => matches(h, words)).map(({ t }) => t), [byStatus, words]);
  const sectionNames = useMemo(() => {
    const m = new Map<string, string>();
    for (const { t } of all) if (!m.has(t.section)) m.set(t.section, t.section_name || t.section);
    return m;
  }, [all]);
  const sections = useMemo(() => {
    const rank = (k: string) => { const i = SECTION_ORDER.indexOf(k); return i < 0 ? 99 : i; };
    const keys = [...sectionNames.keys()].sort((a, b) => rank(a) - rank(b));
    return keys.map((k) => ({ key: k, name: sectionNames.get(k)!, count: hits.filter((t) => t.section === k).length }));
  }, [sectionNames, hits]);
  const shown = sec === 'all' ? hits : hits.filter((t) => t.section === sec);
  const groups = sections.filter((s) => sec === 'all' || s.key === sec)
    .map((s) => ({ ...s, items: shown.filter((t) => t.section === s.key) })).filter((g) => g.items.length);

  return (
    <section className="wm-listpage lb-page" data-testid="layout-browser"
      onKeyDown={(e) => {
        const tag = (e.target as HTMLElement).tagName;
        if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') { e.preventDefault(); searchRef.current?.focus(); }
      }}>
      <div className="wm-pagehead">
        <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <h1 className="wm-pagehead__title">PPT 레이아웃 브라우저</h1>
          <div className="wm-pagehead__desc">
            제안서 슬라이드 레이아웃 {q.data ? <b className="wm-num">{q.data.total}</b> : '…'}종 — 코드(MS-A) · 이름 · 쓰는 때 · 업종 · 솔루션으로 찾고, 눌러서 원본 보드와 칸을 봅니다.
          </div>
        </div>
      </div>

      <div className="lb-toolbar">
        <SearchField tone="white" width={420} value={find} onChange={(v) => set({ find: v })} inputRef={searchRef} autoFocus clearable
          label="레이아웃 검색" placeholder="예: MS-A · 핵심 수치 · 경쟁 비교 · 리테일 · MagicINFO  ( / )" />
        <span className="lb-total wm-num" aria-live="polite">{q.data ? `${shown.length}개` : ''}</span>
        <span style={{ flex: 1 }} />
        <Segmented<'ready' | 'all'> value={st} onChange={(v) => set({ st: v === 'all' ? 'all' : null })} ariaLabel="상태"
          items={[{ value: 'ready', label: '사용 가능' }, { value: 'all', label: '제작 중 포함' }]} />
      </div>
      <div className="lb-chips" role="group" aria-label="섹션">
        <Chip on={sec === 'all'} onClick={() => set({ sec: null })} count={hits.length}>전체</Chip>
        {sections.map((s) => (
          <Chip key={s.key} on={sec === s.key} onClick={() => set({ sec: sec === s.key ? null : s.key })} count={s.count} disabled={!s.count && sec !== s.key}>
            {s.name}
          </Chip>
        ))}
      </div>

      {q.isLoading && <div className="lb-grid">{Array.from({ length: 12 }, (_, i) => <Skeleton key={i} h={230} r={12} />)}</div>}
      {q.isError && <ErrorState message="레이아웃 목록을 불러오지 못했어요" onRetry={() => q.refetch()} />}
      {q.data && !groups.length && (
        <Empty title={`「${find}」에 맞는 레이아웃이 없어요`}
          action={<Button h={36} onClick={() => set({ find: null, sec: null, st: 'all' })}>조건 지우고 전부 보기</Button>} />
      )}
      {groups.map((g) => (
        <section key={g.key} className="lb-group" aria-label={g.name}>
          <h2 className="lb-group__title">{g.name}<span className="wm-num">{g.items.length}</span></h2>
          <div className="lb-grid">
            {g.items.map((t) => <Card key={t.code} t={t} words={words} onOpen={() => set({ layout: t.code })} />)}
          </div>
        </section>
      ))}

      {open && <Detail code={open} onClose={() => set({ layout: null })} />}
    </section>
  );
}
