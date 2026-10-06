/**
 * `/scenario/:id` — 사이드바 항목 · 공유 링크로 들어오면 그 시나리오의 현재 화면(`route`)으로 보낸다(§1 진입점 1).
 */
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import { ErrorState } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage } from '../api';
import { useScenario } from '../hooks';
import { route, SECTION } from '../lib';
import { Loading } from '../parts';

export default function OpenPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const sc = useScenario(id);
  useShellPage({ section: SECTION, title: sc.data?.title ?? '' });
  useEffect(() => { if (sc.data) nav(sc.data.route, { replace: true }); }, [sc.data, nav]);
  if (sc.isError) {
    return <div style={{ padding: 40 }}><ErrorState message={`시나리오를 열지 못했어요 · ${errMessage(sc.error)}`} onRetry={() => nav(route.list())} /></div>;
  }
  return <Loading />;
}
