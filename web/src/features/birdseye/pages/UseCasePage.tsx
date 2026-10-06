/** UC_BE — 공간 조감도 생성 유스케이스 맵(`/birdseye/uc`, §4.0 · 개발용). 화면 코드를 누르면 그 화면(작업이 필요한 화면은 목록)으로 간다. */
import { Link } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import { SECTION } from '../ui';

type N = { code: string; label: string; to: string; kind?: 'new' | 'other' };
const FLOW: N[] = [
  { code: 'BE1', label: '공간 입력', to: '/birdseye/new' }, { code: 'BE2', label: '배치될 제품', to: '/birdseye' }, { code: 'BE3', label: '가구 추천', to: '/birdseye' },
  { code: 'BE4', label: '배치 컨펌', to: '/birdseye' }, { code: 'BE5G', label: '생성 중', to: '/birdseye' }, { code: 'BE5', label: '3D 조감도', to: '/birdseye' },
  { code: 'BE6', label: '내보내기', to: '/birdseye' }, { code: 'PRS3', label: '제안서에 넣기', to: '/proposal', kind: 'other' },
];
const LANES: Array<{ title: string; nodes: N[] }> = [
  { title: '01 들어오는 길', nodes: [{ code: 'Main', label: '홈 · 새 작업', to: '/', kind: 'other' }, { code: 'BE0', label: '작업 목록', to: '/birdseye' },
    { code: 'PRS3', label: '조감도 새로 만들기', to: '/proposal', kind: 'other' }] },
  { title: '02 입력 방식', nodes: [{ code: 'BE1', label: '공간 입력', to: '/birdseye/new' }, { code: 'BE1D', label: '도면 인식 확인', to: '/birdseye/new/plan', kind: 'new' },
    { code: 'BE1P', label: '현장 사진', to: '/birdseye/new/photos', kind: 'new' }, { code: 'BE2', label: '배치될 제품', to: '/birdseye' }, { code: 'BE3', label: '가구 추천', to: '/birdseye' }] },
  { title: '03 진행 · 확인 상태', nodes: [{ code: 'BE4', label: '배치 컨펌', to: '/birdseye' }, { code: 'BE5G', label: '생성 중', to: '/birdseye' },
    { code: 'BE5', label: '3D 조감도', to: '/birdseye' }] },
  { title: '04 편집 · 버전', nodes: [{ code: 'BE4E', label: '배치 직접 수정', to: '/birdseye', kind: 'new' }, { code: 'BE5V', label: '시점 · 조명', to: '/birdseye', kind: 'new' },
    { code: 'BE5Z', label: '존 포인트', to: '/birdseye', kind: 'new' }, { code: 'BE0', label: '복제', to: '/birdseye' }] },
  { title: '05 결과 활용', nodes: [{ code: 'BE6', label: '내보내기 · 보내기', to: '/birdseye', kind: 'new' }, { code: 'PRS3', label: '존별 포인트', to: '/proposal', kind: 'other' },
    { code: 'PRS4', label: '공간 맵 · 구성', to: '/proposal', kind: 'other' }, { code: 'SC1B', label: '공간 시나리오', to: '/scenario', kind: 'other' },
    { code: 'PR1L', label: '새 제안서 연결', to: '/proposal', kind: 'other' }] },
];

export default function UseCasePage() {
  useShellPage({ section: SECTION, title: '유스케이스 맵', hasTask: false, sidebarGroup: 'birdseye' });
  const node = (n: N, i: number) => (
    <Link key={`${n.code}-${i}`} to={n.to} className={n.kind === 'new' ? 'be-uc__node be-uc__node--new' : n.kind === 'other' ? 'be-uc__node be-uc__node--other' : 'be-uc__node'}>
      <b>{n.code}</b>{n.label}
    </Link>
  );
  return (
    <div className="be-uc" data-testid="be-uc">
      <div className="be-small be-muted">WINMATE · USE CASE MAP</div>
      <h1 style={{ margin: 0, fontSize: 22 }}>공간 조감도 생성 — 유스케이스 맵</h1>
      <p className="be-muted" style={{ margin: 0 }}>들어오는 길부터 결과 활용까지 화면 13개를 한 장에 모았습니다. 화면 코드를 누르면 그 화면으로 이동합니다.</p>
      <div className="be-row be-small be-muted"><span className="be-uc__node" style={{ minWidth: 0 }}>기본 흐름 (기존 화면)</span>
        <span className="be-uc__node be-uc__node--new" style={{ minWidth: 0 }}>새 화면</span><span className="be-uc__node be-uc__node--other" style={{ minWidth: 0 }}>다른 기능 화면</span></div>
      <div className="be-sec"><b>기본 흐름</b><div className="be-uc__flow">{FLOW.map(node)}</div></div>
      {LANES.map((l) => <div key={l.title} className="be-uc__lane"><h3>{l.title}</h3><div className="be-uc__flow">{l.nodes.map(node)}</div></div>)}
      <div className="be-assume"><i>!</i>확인이 필요할 때 · BE1D 도면 인식 확인 필요 · 치수 보정 / BE1P 사진 다시 찍기 · 천장 사진 없음 / BE4E 시야각 · 동선 · 전원 위치 경고 / BE0 목록의 '확인 필요' 필터</div>
    </div>
  );
}
