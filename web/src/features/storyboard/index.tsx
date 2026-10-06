/**
 * 전략 수립 Storyboard(SB) 기능 모듈 — 소유: storyboard 서비스 세션. 수용 기준: docs/scenarios/02-storyboard.md
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts). 라우트(§2 화면 목록):
 *   /storyboard(SB0) · /storyboard/new(SB1 만들기) · /storyboard/:sbId → 지금 화면(route)
 *   1 source · settings · planning/:i — 2 direction · direction/messages — 3 outline(SB3G·SB3) · outline/part2 · outline/all ·
 *   spaces/:spcId/q · spaces/:spcId/done · revise · revise/:revId · versions — 4 trace · trace/resolve/:i · trace/resolved ·
 *   trace/all · trace/extensions — 5 schedule · saved · export
 */
import { Navigate, useParams } from 'react-router';
import { feature } from '@/shell/feature';
import { useSb, useSbShell } from './lib';
import { Gate } from './parts';
import { ListScreen } from './ListScreen';
import { NewScreen, PlanningScreen, SettingsScreen, SourceScreen } from './StageLoad';
import { DirectionScreen, MessagesScreen } from './StageDirection';
import { OutlineAllScreen, OutlineScreen, Part2Screen } from './StageOutline';
import { SpaceDoneScreen, SpaceQScreen } from './StageSpaces';
import { ReviseScreen, RevisionScreen, VersionsScreen } from './StageRevise';
import { ExtensionsScreen, ResolvedScreen, ResolveScreen, TraceAllScreen, TraceScreen } from './StageTrace';
import { ExportScreen, SavedScreen, ScheduleScreen } from './StageShare';

/** `/storyboard/:sbId` — 사이드바 · 목록이 주는 지금 화면으로 */
function CurrentScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  useSbShell(q.data, null);
  if (!q.data) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;
  return <Navigate to={q.data.route} replace />;
}

export default feature({
  code: 'SB',
  key: 'storyboard',
  name: '전략 수립 Storyboard',
  order: 2,
  home: { section: 'plan', title: '전략 수립 Storyboard', desc: '기획 질문 · 5단 목차 · 요구사항 추적' },
  routes: [
    { index: true, element: <ListScreen /> },
    { path: 'new', element: <NewScreen /> },
    { path: ':sbId', element: <CurrentScreen /> },
    { path: ':sbId/source', element: <SourceScreen /> },
    { path: ':sbId/settings', element: <SettingsScreen /> },
    { path: ':sbId/planning/:i', element: <PlanningScreen /> },
    { path: ':sbId/direction', element: <DirectionScreen /> },
    { path: ':sbId/direction/messages', element: <MessagesScreen /> },
    { path: ':sbId/outline', element: <OutlineScreen /> },
    { path: ':sbId/outline/part2', element: <Part2Screen /> },
    { path: ':sbId/outline/all', element: <OutlineAllScreen /> },
    { path: ':sbId/spaces/:spcId/q', element: <SpaceQScreen /> },
    { path: ':sbId/spaces/:spcId/done', element: <SpaceDoneScreen /> },
    { path: ':sbId/revise', element: <ReviseScreen /> },
    { path: ':sbId/revise/:revId', element: <RevisionScreen /> },
    { path: ':sbId/versions', element: <VersionsScreen /> },
    { path: ':sbId/trace', element: <TraceScreen /> },
    { path: ':sbId/trace/resolve/:i', element: <ResolveScreen /> },
    { path: ':sbId/trace/resolved', element: <ResolvedScreen /> },
    { path: ':sbId/trace/all', element: <TraceAllScreen /> },
    { path: ':sbId/trace/extensions', element: <ExtensionsScreen /> },
    { path: ':sbId/schedule', element: <ScheduleScreen /> },
    { path: ':sbId/saved', element: <SavedScreen /> },
    { path: ':sbId/export', element: <ExportScreen /> },
  ],
});
