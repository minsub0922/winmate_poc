/** RQ0 — 요구사항 목록 `/requirements?tab=all|in_progress|saved&q=` */
import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useShellPage } from '@/shell';
import { FilterTabs, NewButton, PageHeader, SearchField, Skeleton } from '@/ui';
import { rqApi, type RequirementListItem, type Tab } from '../api';
import { rqTime } from '../lib/format';

const TABS: Array<{ value: Tab; label: string }> = [
  { value: 'all', label: '전체' }, { value: 'in_progress', label: '진행 중' }, { value: 'saved', label: '저장됨' },
];

export function ListPage() {
  useShellPage({ section: '고객 요구사항', hasTask: false });
  const [sp, setSp] = useSearchParams();
  const tab = (TABS.find((t) => t.value === sp.get('tab'))?.value ?? 'all') as Tab;
  const q = sp.get('q') ?? '';
  const [text, setText] = useState(q);
  useEffect(() => { setText(q); }, [q]);
  useEffect(() => {
    if (text === q) return;
    const t = window.setTimeout(() => {
      const next = new URLSearchParams(sp);
      if (text) next.set('q', text); else next.delete('q');
      setSp(next, { replace: true });
    }, 300);
    return () => window.clearTimeout(t);
  }, [text, q, sp, setSp]);

  const counts = useQuery({ queryKey: ['rq-list', 'counts', q], queryFn: () => rqApi.counts(q), staleTime: 5_000 });
  const list = useInfiniteQuery({
    queryKey: ['rq-list', tab, q],
    queryFn: ({ pageParam }) => rqApi.list({ tab, q, limit: 20, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor ?? null,
    staleTime: 5_000,
  });
  const rows = list.data?.pages.flatMap((p) => p.items) ?? [];
  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const io = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting) && list.hasNextPage && !list.isFetchingNextPage) void list.fetchNextPage();
    });
    io.observe(el);
    return () => io.disconnect();
  }, [list]);

  const setTab = (t: Tab) => {
    const next = new URLSearchParams(sp);
    if (t === 'all') next.delete('tab'); else next.set('tab', t);
    setSp(next, { replace: true });
  };

  return (
    <div className="rq-root">
      <section className="rq-list">
        <PageHeader title="고객 요구사항" actions={<NewButton to="/requirements/new">새 요구사항</NewButton>} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <FilterTabs value={tab} onChange={setTab} ariaLabel="상태"
            items={TABS.map((t) => ({ ...t, count: counts.data ? counts.data[t.value] : undefined }))} />
          <span style={{ flex: 1 }} />
          <SearchField tone="white" width={280} value={text} onChange={setText} placeholder="찾기" label="요구사항 검색" clearable />
        </div>
        <div className="rq-table" role="table" aria-label="요구사항 목록" aria-busy={list.isLoading}>
          <div className="rq-table__head" role="row">
            <span role="columnheader">고객 · 사업</span><span role="columnheader">상태</span><span role="columnheader">수정</span><span role="columnheader" />
          </div>
          {list.isLoading && Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="rq-table__row" role="row" aria-hidden="true">
              <span><Skeleton w="60%" h={16} /><Skeleton w="30%" h={12} style={{ marginTop: 6 }} /></span>
              <Skeleton w={110} h={24} r={12} /><Skeleton w={60} h={14} /><span />
            </div>
          ))}
          {!list.isLoading && rows.length === 0 && (
            <div className="rq-table__empty">
              {q ? '찾는 요구사항이 없어요' : <>아직 요구사항이 없어요<NewButton to="/requirements/new">새 요구사항</NewButton></>}
            </div>
          )}
          {rows.map((r) => <Row key={r.id} r={r} />)}
        </div>
        <div ref={sentinel} style={{ height: 1 }} />
      </section>
    </div>
  );
}

function Row({ r }: { r: RequirementListItem }) {
  const saved = r.list_state === 'saved';
  return (
    <div className="rq-table__row" role="row" data-state={r.list_state}>
      <div role="cell" style={{ minWidth: 0 }}>
        <Link to={r.route} className="rq-table__title wm-ellipsis" style={{ display: 'block' }}>{r.title || '새 요구사항'}</Link>
        <div className="rq-table__sub">키맨 {r.keyman_count} · 요구사항 {r.item_count}</div>
      </div>
      <div role="cell"><span className={`rq-pill ${saved ? 'rq-pill--saved' : 'rq-pill--prog'}`}>{r.state_label}</span></div>
      <div role="cell" className="rq-table__when">{rqTime(r.updated_at)}</div>
      <div role="cell" style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Link to={r.route} className={`wm-btn wm-btn--h32 ${saved ? '' : 'wm-btn--primary'}`} style={{ padding: '0 14px' }}>{saved ? '열기' : '이어서'}</Link>
      </div>
    </div>
  );
}
