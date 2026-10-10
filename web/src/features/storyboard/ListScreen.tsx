/** SB0 — Storyboard · 작업 목록(§4.2). 탭 3(전체 · 진행 중 · 완료), 표(스토리보드 · 단계 · 수정), 행 버튼 이어서 · 보기 · 열기 */
import { useMemo } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router';
import { DataTable, FilterTabs, ListPage, NewButton, RowAction, TitleCell, type DataColumn } from '@/ui';
import { useShellPage } from '@/shell/ShellContext';
import { api, unwrap } from '@/api/client';
import { listTime, SECTION_NAME, type SbListItem } from './lib';
import './sb.css';

type Tab = 'all' | 'in_progress' | 'done';
const TABS: Tab[] = ['all', 'in_progress', 'done'];

export function ListScreen() {
  useShellPage({ section: SECTION_NAME, title: '작업 목록', hasTask: false, sidebarGroup: 'storyboard' });
  const [params, setParams] = useSearchParams();
  const tab: Tab = TABS.includes(params.get('tab') as Tab) ? (params.get('tab') as Tab) : 'all';
  const counts = useQuery({
    queryKey: ['storyboard', 'counts'],
    queryFn: async () => unwrap(await api.storyboard.GET('/v1/storyboards/counts')),
    refetchInterval: 15_000,
  });
  const list = useInfiniteQuery({
    queryKey: ['storyboard', 'list', tab],
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam }) => unwrap(await api.storyboard.GET('/v1/storyboards', {
      params: { query: { tab, limit: 20, cursor: pageParam ?? undefined } },
    })),
    getNextPageParam: (last) => last.next_cursor ?? null,
    // 목차 잡이 도는 행이 있으면 자주 다시 읽는다(`보기` → `이어서`)
    refetchInterval: (q) => (q.state.data?.pages.some((p) => p.items.some((it) => it.active_job)) ? 4000 : 20_000),
  });
  const rows = useMemo(() => list.data?.pages.flatMap((p) => p.items) ?? [], [list.data]);
  const now = new Date();
  const columns: Array<DataColumn<SbListItem>> = [
    { key: 'title', label: '스토리보드', width: 'minmax(0, 1fr)', render: (it) => <TitleCell title={it.title} sub={it.sub_line || undefined} to={it.route} /> },
    {
      key: 'step', label: '단계', width: '170px',
      render: (it) => <span className={`sb-steppill ${it.status === 'in_progress' ? 'sb-steppill--run' : 'sb-steppill--done'}`}>{it.step_label}</span>,
    },
    { key: 'when', label: '수정', width: '110px', render: (it) => <span className="sb-muted" style={{ fontSize: 13, whiteSpace: 'nowrap' }}>{listTime(it.updated_at, now)}</span> },
    {
      key: 'open', label: '', width: '96px', align: 'end',
      render: (it) => (it.cta === 'continue'
        ? <RowAction to={it.route} primary>이어서</RowAction>
        : <RowAction to={it.route}>{it.cta === 'view' ? '보기' : '열기'}</RowAction>),
    },
  ];
  const c = counts.data;
  return (
    <ListPage
      title="전략 수립 Storyboard"
      desc="요구사항 정의서로 기획 방향 → 목차 → 요구 추적 → 일정까지. 멈춘 단계에서 이어서 할 수 있어요."
      action={<NewButton to="/storyboard/legacy/new">새 스토리보드</NewButton>}
      toolbar={(
        <div className="wm-toolbar">
          <FilterTabs<Tab> value={tab} ariaLabel="상태" onChange={(v) => setParams(v === 'all' ? {} : { tab: v }, { replace: true })}
            items={[
              { value: 'all', label: '전체', count: c?.all },
              { value: 'in_progress', label: '진행 중', count: c?.in_progress },
              { value: 'done', label: '완료', count: c?.done },
            ]} />
        </div>
      )}
      table={(
        <DataTable rowKey={(it) => it.id} rows={rows} columns={columns} loading={list.isLoading} rowHeight={72}
          empty={list.isError ? '목록을 불러오지 못했어요.' : (
            <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
              <span>아직 스토리보드가 없어요</span>
              {tab === 'all' && <Link to="/storyboard/legacy/new" className="wm-btn wm-btn--primary wm-btn--h36">새 스토리보드</Link>}
            </span>
          )} />
      )}
      footer={list.hasNextPage ? (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button type="button" className="wm-btn wm-btn--h36" onClick={() => void list.fetchNextPage()} disabled={list.isFetchingNextPage}>더 보기</button>
        </div>
      ) : undefined}
    />
  );
}
