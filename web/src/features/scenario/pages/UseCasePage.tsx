/**
 * UC_SC · 유스케이스 맵(§3.2 · §4.0, 런타임 화면 아님 — 개발용 `/scenario/uc`). 레인 5 · 카드 17 · 화면 안 상태 4 · 받아오는 것 · 넘겨주는 것.
 * 카드를 누르면 그 화면으로 간다(시나리오가 필요한 화면은 가장 최근 완료 시나리오, 없으면 목록).
 */
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx } from '@/ui';
import { useShellPage } from '@/shell';
import { scApi } from '../api';
import { route, SECTION } from '../lib';

type Kind = 'flow' | 'extra' | 'other';
interface UcCard { code: string; kind: Kind; title: string; desc: string; next: string; to: (id: string | null) => string }
interface Lane { no: string; title: string; sub: string; cards: UcCard[] }

const withId = (f: (id: string) => string) => (id: string | null) => (id ? f(id) : route.list());
const LANES: Lane[] = [
  { no: '01', title: '들어오는 길', sub: '어디서 시나리오를 시작하나', cards: [
    { code: 'HOME', kind: 'other', title: '홈 · 공간 시나리오 생성', desc: '홈 화면 기능 버튼으로 바로 시작', next: 'SC1', to: () => '/' },
    { code: 'SC0', kind: 'extra', title: '시나리오 작업 목록', desc: '최근 작업 · 상태 · 검색 · 이어서 작성', next: 'SC1 · SC1T · SC1B · SC4', to: () => route.list() },
    { code: 'SC1T', kind: 'extra', title: '업종 템플릿에서 시작', desc: '16개 업종 · 대표 공간 · 장면 프리셋', next: 'SC2E', to: () => route.template() },
    { code: 'SC1B', kind: 'extra', title: '조감도에서 이어 만들기', desc: '조감도 존 · 배치 제품을 공간으로', next: 'SC2E', to: () => route.fromBirdseye() },
    { code: 'BE6', kind: 'other', title: '조감도 결과에서 보내기', desc: '공간 조감도 → 시나리오로 보내기', next: 'SC1B', to: () => '/birdseye' },
  ] },
  { no: '02', title: '입력 방식', sub: '무엇을 어떻게 넣나', cards: [
    { code: 'SC1', kind: 'flow', title: '시나리오 유형', desc: 'with / without · 조감도 추가(선택)', next: 'SC2', to: () => route.newType() },
    { code: 'SC2', kind: 'flow', title: '공간 시나리오 입력', desc: '텍스트 · 예시 골격 · 등장인물', next: 'SC3 · SC2E', to: withId((id) => `/scenario/${id}/input`) },
    { code: 'SC3', kind: 'flow', title: '솔루션 · 제품 입력', desc: '솔루션을 고르면 연관 제품 추천', next: 'SC4G · SC3R', to: withId((id) => route.solutions(id)) },
    { code: 'SC3R', kind: 'extra', title: '장면별 솔루션 추천', desc: 'without → with 전환 · 추천 근거', next: 'SC4G', to: withId((id) => `/scenario/${id}/solutions/recommend`) },
  ] },
  { no: '03', title: '진행 · 확인 상태', sub: '생성 · 대기 · 결과 확인', cards: [
    { code: 'SC4G', kind: 'extra', title: '시나리오 생성 중', desc: '장면 단위 진행 · 중지 · 미리보기', next: 'SC4', to: () => route.list() },
    { code: 'SC4', kind: 'flow', title: '시나리오 생성 결과', desc: '장면별 이야기 · 솔루션 · 제품', next: 'PRX3 · SC4E · SC5', to: withId((id) => route.result(id)) },
  ] },
  { no: '04', title: '편집 · 버전', sub: '구조와 장면 고치기', cards: [
    { code: 'SC2E', kind: 'extra', title: '타임라인 · 페르소나 편집', desc: '시간대 · 역할 레인 · 장면 이동', next: 'SC3', to: withId((id) => route.timeline(id)) },
    { code: 'SC4E', kind: 'extra', title: '장면 편집 · 재생성', desc: '장면 고치기 · 장면 이미지 만들기', next: 'SC4 · IMG2', to: withId((id) => route.result(id)) },
  ] },
  { no: '05', title: '결과 활용', sub: '제안서 · 이미지 · 내보내기', cards: [
    { code: 'SC5', kind: 'extra', title: '제안서로 보내기 · 내보내기', desc: '공간별 가치 제공 시나리오 · PDF', next: 'PRX3 · PR1L', to: withId((id) => `/scenario/${id}/send`) },
    { code: 'PRX3', kind: 'other', title: '제안서 · 공간별 가치 제공 시나리오', desc: 'B2B 제안서 섹션에 장면이 들어감', next: 'PRX4', to: () => '/proposal' },
    { code: 'IMG2', kind: 'other', title: '이미지 생성 · 장면 이미지', desc: '장면 설명으로 이미지 조건 채움', next: 'IMG3', to: () => '/image' },
    { code: 'PR1L', kind: 'other', title: '제안서 시작 · 기존 작업 연결', desc: '제안서 생성에서 이 시나리오 선택', next: 'PR2', to: () => '/proposal/new' },
  ] },
];
const STATES = ['생성이 멈추면 → SC4G 다시 시도', '장면이 너무 많으면 → SC2E 합치기', '조감도가 바뀌면 → SC0 알림 → SC1B', '솔루션을 못 고르면 → SC3R 추천'];
const IN = ['조감도 존 · 배치 제품 ← 공간 조감도', '고객 · 공간 정보 ← Storyboard · 사이드바에서 끌어오기', '업종별 공간 · 장면 프리셋 ← 도입사례 기준 템플릿'];
const OUT = ["장면 · 솔루션 · 제품 → 제안서 '공간별 가치 제공 시나리오'", '장면 설명 · 등장 제품 → 이미지 생성 조건', '시나리오 보드 → PDF · 이미지 내보내기'];
const KIND_LABEL: Record<Kind, string> = { flow: '기본 흐름', extra: '추가 화면', other: '다른 기능' };

export default function UseCasePage() {
  useShellPage({ section: SECTION, title: '유스케이스 맵', hasTask: false, sidebarGroup: 'scenario' });
  const latest = useQuery({ queryKey: ['scenario', 'uc-latest'], queryFn: () => scApi.list({ status: 'done', limit: 1 }), staleTime: 30_000, retry: 0 });
  const id = latest.data?.items?.[0]?.id ?? null;
  const count = (k: Kind) => LANES.reduce((n, l) => n + l.cards.filter((c) => c.kind === k).length, 0);
  return (
    <section className="sc-uc" data-testid="sc-uc">
      <header className="sc-uc__head">
        <div className="sc-uc__titles">
          <span className="sc-uc__eyebrow">WINMATE · USE-CASE MAP</span>
          <h1 className="sc-uc__title">공간 시나리오 생성 — 유스케이스 맵</h1>
          <p className="sc-uc__desc">들어오는 길부터 결과 활용까지, 시나리오 기능의 화면 12개와 이어지는 다른 기능. 카드를 누르면 그 화면으로 이동합니다.</p>
        </div>
        <div className="sc-uc__legend" aria-label="범례">
          <span><i className="sc-uc__arrow" />기본 흐름</span>
          <span><i className="sc-uc__arrow sc-uc__arrow--alt" />다른 길</span>
          <span className="sc-uc__sep" />
          <span><i className="sc-uc__sw sc-uc__sw--flow" />기본 흐름 화면</span>
          <span><i className="sc-uc__sw" />추가 화면</span>
          <span><i className="sc-uc__sw sc-uc__sw--other" />다른 기능</span>
        </div>
      </header>
      <div className="sc-uc__lanes">
        {LANES.map((l) => (
          <div key={l.no} className="sc-uc__lane" data-testid="sc-uc-lane">
            <div className="sc-uc__lanehead">
              <span className="sc-row" style={{ justifyContent: 'space-between' }}>
                <span className="sc-row" style={{ gap: 8, alignItems: 'baseline' }}><b className="sc-uc__no">{l.no}</b><b style={{ fontSize: 15 }}>{l.title}</b></span>
                <span className="sc-uc__muted">화면 {l.cards.length}</span>
              </span>
              <span className="sc-uc__muted" style={{ fontSize: 12 }}>{l.sub}</span>
            </div>
            {l.cards.map((c) => (
              <Link key={c.code} to={c.to(id)} className={cx('sc-uc__card', `sc-uc__card--${c.kind}`)} data-testid="sc-uc-card">
                <span className="sc-row" style={{ justifyContent: 'space-between' }}>
                  <b className="sc-uc__code">{c.code}</b><span className="sc-uc__kind">{KIND_LABEL[c.kind]}</span>
                </span>
                <span className="sc-uc__ctitle">{c.title}</span>
                <span className="sc-uc__cdesc">{c.desc}</span>
                <span className="sc-uc__next">다음 {c.next}</span>
              </Link>
            ))}
          </div>
        ))}
      </div>
      <div className="sc-uc__foot">
        <div className="sc-uc__box"><b>화면 안에서 생기는 상태</b>{STATES.map((s) => <span key={s}>{s}</span>)}</div>
        <div className="sc-uc__box"><b>받아오는 것</b>{IN.map((s) => <span key={s}>{s}</span>)}</div>
        <div className="sc-uc__box"><b>넘겨주는 것</b>{OUT.map((s) => <span key={s}>{s}</span>)}</div>
      </div>
      <p className="sc-uc__muted" style={{ margin: 0, fontSize: 12 }}>
        카드 아래 '다음'은 그 화면에서 이어지는 곳입니다. SC1T · SC1B는 타임라인 편집(SC2E)으로 바로 이어집니다. · 기본 흐름 {count('flow')} · 추가 화면 {count('extra')} · 다른 기능 {count('other')}
      </p>
    </section>
  );
}
