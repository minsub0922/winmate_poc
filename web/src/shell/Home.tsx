/**
 * 홈 — 보드 webapp1 v58 HomeGrid(콘텐츠 흐름 중심). 문구 · px 는 보드 그대로.
 */
import { Fragment, useMemo } from 'react';
import { Link } from 'react-router';
import { Icon, PathIcon, Skeleton, greetingFor, relativeTime } from '@/ui';
import { featureName } from './catalog';
import { useShellPage } from './ShellContext';
import { useMe, useRecentItems } from './workspace';

/** 보드 HomeGrid 아이콘(웹앱 ① v58) — 카드마다 보드 path 그대로 */
const ICON = {
  rq: 'M9 4h6v3H9z M7 5.5H5V21h14V5.5h-2 M8.5 12h7 M8.5 16h5',
  sb: 'M4 5h16v14H4z M4 11h16 M10 11v8',
  dss: 'M3 21h18 M5 21V9l7-5 7 5v12 M9 21v-6h6v6',
  mi: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2',
  ca: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z M12 11a1 1 0 1 0 0 2 1 1 0 0 0 0-2z',
  vp: 'M6 4h12l3 5-9 11L3 9l3-5z M3 9h18 M9.5 9L12 20l2.5-11',
  sp: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7',
  sc: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  img: 'M4 5h16v14H4z M9 10.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z M20 15l-5-5-8 8',
  be: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 12l8-4.5 M12 12v9 M12 12L4 7.5',
  pr: 'M3 4h18v12H3z M8 20h8 M12 16v4 M7 12l3-3 2 2 4-4',
};

/** 시작 · 흐름(요구사항 → Storyboard(자동) → DSS) — 요구사항은 새로 쓰기, Storyboard · DSS 는 목록(보드 RQ1 · SB0 · DS0) */
const FLOW = [
  { key: 'requirements', to: '/requirements/new', icon: ICON.rq, title: '고객 요구사항', desc: '요청서 · 회의록을 넣거나 폼에 적어요. 저장하면 Storyboard가 생겨요.', rel: '사전 없음 · 후속 DSS', start: true },
  { key: 'storyboard', to: '/storyboard', icon: ICON.sb, title: '전략 수립 Storyboard', desc: '제안 흐름 전체 context. 어디까지 됐는지 보고, 요약본과 Key message를 다듬어요.', rel: '사전 요구사항 · 후속 PPT 제작', start: false },
  { key: 'dss', to: '/dss', icon: ICON.dss, title: '공간별 제품 매칭 DSS', desc: '업종 · 공간을 정하고 공간마다 제품 · 솔루션을 골라요.', rel: '사전 Storyboard · 후속 시나리오 · Spec', start: false },
];
/** Storyboard 로 만드는 콘텐츠(사전 작업 = DSS까지 된 Storyboard) — 목록(보드 MI0 · CA0 · VP0 · SP0 · SC0) */
const AFTER = [
  { key: 'mi', to: '/mi', icon: ICON.mi, title: 'Market Intelligence', desc: '시장 · 고객사 · 사용자를 웹에서 모아 정리' },
  { key: 'competitor', to: '/competitor', icon: ICON.ca, title: '경쟁사 분석', desc: '제품군 · 공간이 겹치는 경쟁사 리스트업' },
  { key: 'vp', to: '/vp', icon: ICON.vp, title: 'Value Proposition', desc: '제품 · 솔루션마다 고객 가치 추출' },
  { key: 'spec', to: '/spec', icon: ICON.sp, title: 'Spec 시트', desc: 'DSS 제품의 스펙 시트' },
  { key: 'scenario', to: '/scenario', icon: ICON.sc, title: '공간 시나리오', desc: '공간마다 사용자 시나리오' },
];
const VISUAL = [
  { key: 'image', to: '/image/new', icon: ICON.img, title: '이미지 생성', desc: '공간 · 배경 · 장면 이미지' },
  { key: 'birdseye', to: '/birdseye/new', icon: ICON.be, title: '공간 조감도', desc: '2D 수치 · 3D 개략' },
];

/**
 * 홈(보드 webapp1 v58 HomeGrid 1180×836) — 인사 · B2B 제안서(PPT) · 시작 · 흐름 3 · Storyboard 로 만드는 콘텐츠 5 · 비주얼 2 · 최근 작업 2.
 * 인사 이름은 workspace `/v1/me`, 최근 작업은 `/v1/items?limit=2`(없으면 그 칸을 그리지 않는다).
 */
export function Home() {
  // 홈 = 진행 중인 작업 없음(§5.1). section 을 두지 않아 브레드크럼은 `홈` 만.
  useShellPage({ hasTask: false });
  const me = useMe();
  const recent = useRecentItems(2);
  const now = useMemo(() => new Date(), []);
  const tz = me.data?.timezone || 'Asia/Seoul';
  const greeting = greetingFor(now, tz);
  const name = me.data?.given_name || me.data?.name;
  const items = recent.data?.items ?? [];
  const showRecent = !recent.isError && (recent.isLoading || items.length > 0);

  return (
    <section className="sh-home" aria-label="홈">
      <div className="sh-home__inner">
        <div className="sh-home__head">
          <h1 className="sh-home__h1" data-greeting="">
            {me.isLoading ? <span style={{ visibility: 'hidden' }}>{greeting}, 님. 오늘은 무엇을 제안해 볼까요?</span>
              : name ? `${greeting}, ${name}님. 오늘은 무엇을 제안해 볼까요?` : `${greeting}. 오늘은 무엇을 제안해 볼까요?`}
          </h1>
          <p className="sh-home__sub">고객 요구사항에서 시작하면 Storyboard가 생기고, 모든 콘텐츠가 그 Storyboard에 차곡차곡 쌓여요.</p>
        </div>

        <Link to="/proposal/new" className="hcard hcard--hero" data-home-card="proposal">
          <span className="sh-home__heroic"><PathIcon d={ICON.pr} size={22} color="#fff" /></span>
          <span className="sh-home__herotxt"><b>B2B 제안서 만들기 · PPT</b><span>Storyboard의 후속 작업이에요. Storyboard를 고르면 연결된 콘텐츠로 PPTX까지 만들어요.</span></span>
          <span className="sh-home__herobtn">바로 시작</span>
        </Link>

        <div className="sh-home__sechead"><b>시작 · 흐름</b><span>요구사항 → Storyboard(자동) → DSS 순서로 쌓여요.</span></div>
        <div className="sh-home__flow" data-home-section="flow">
          {FLOW.map((c, i) => (
            <Fragment key={c.key}>
              <Link to={c.to} className={c.start ? 'hcard hcard--flow hcard--start' : 'hcard hcard--flow'} data-home-card={c.key}>
                <span className="sh-home__flowtop">
                  <span className="sh-home__ic34"><PathIcon d={c.icon} size={18} color="var(--wm-brand)" /></span>
                  <b>{c.title}</b>
                  {c.start && <span className="sh-home__startpill">여기서 시작</span>}
                </span>
                <span className="sh-home__flowdesc">{c.desc}</span>
                <span className="sh-home__flowrel">{c.rel}</span>
              </Link>
              {i < FLOW.length - 1 && <span className="sh-home__arrow" aria-hidden><Icon name="arrowRight" size={16} color="var(--wm-text-subtle)" strokeWidth={2.2} /></span>}
            </Fragment>
          ))}
        </div>

        <div className="sh-home__sechead"><b>Storyboard로 만드는 콘텐츠</b><span>사전 작업 · DSS까지 된 Storyboard</span></div>
        <div className="sh-home__after" data-home-section="after">
          {AFTER.map((c) => (
            <Link key={c.key} to={c.to} className="hcard hcard--after" data-home-card={c.key}>
              <span className="sh-home__ic32"><PathIcon d={c.icon} size={17} color="var(--wm-brand)" /></span>
              <b>{c.title}</b>
              <span>{c.desc}</span>
            </Link>
          ))}
        </div>

        <div className="sh-home__bottom">
          <div className="sh-home__col">
            <span className="sh-home__colh"><b>비주얼</b></span>
            <div className="sh-home__rows" data-home-section="visual">
              {VISUAL.map((c) => (
                <Link key={c.key} to={c.to} className="hcard hcard--row" data-home-card={c.key}>
                  <PathIcon d={c.icon} size={18} color="var(--wm-brand)" />
                  <b>{c.title}</b>
                  <span className="sh-ell">{c.desc}</span>
                </Link>
              ))}
            </div>
          </div>
          {showRecent && (
            <div className="sh-home__col">
              <span className="sh-home__colh"><b>최근 작업</b><Link to="/storyboard">Storyboard 전체</Link></span>
              <div className="sh-home__rows" data-home-section="recent">
                {recent.isLoading
                  ? [0, 1].map((i) => <Skeleton key={i} h={56} r={12} />)
                  : items.map((it) => (
                    <Link key={it.item_id} to={it.route} className="hcard hcard--row hcard--recent" data-recent={it.item_id}>
                      <span className="sh-home__rectxt"><b className="sh-ell" title={it.title}>{it.title}</b><span className="sh-ell">{featureName(it.feature)} · {relativeTime(it.updated_at, now, tz)}</span></span>
                      <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" strokeWidth={2.2} />
                    </Link>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
