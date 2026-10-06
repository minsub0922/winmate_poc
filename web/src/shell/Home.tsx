/**
 * 홈(00-shell §5.1 HomeGrid) — 인사 · B2B 카드 · 기획·분석 6 · 공간·비주얼 3 · 최근 작업 3.
 * 카드 문구는 셸 카탈로그(§5.1.1 고정), 인사 이름은 workspace `/v1/me`, 최근 작업은 `/v1/items?limit=3`.
 */
import { useMemo } from 'react';
import { Link } from 'react-router';
import { Badge, Icon, Skeleton, greetingFor, relativeTime } from '@/ui';
import { PLAN_ORDER, VISUAL_ORDER, featureName, shellFeatureByCode, shellFeatures, type ShellFeature } from './catalog';
import { FeatureIcon } from './icons';
import { useShellPage } from './ShellContext';
import { useMe, useRecentItems } from './workspace';

const arrow = (size = 12, color = 'var(--wm-brand)', sw = 2.4) => <Icon name="arrowRight" size={size} color={color} strokeWidth={sw} />;

function PlanCard({ f }: { f: ShellFeature }) {
  const h = f.home;
  return (
    <Link to={f.newRoute} className={h.mark === 'new' ? 'hcard hcard--plan hcard--new' : 'hcard hcard--plan'} data-home-card={f.key}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, height: 32 }}>
        <span className="sh-ibox" style={{ width: 32, height: 32, borderRadius: 9 }}><FeatureIcon code={f.code} size={17} color="var(--wm-brand)" /></span>
        {h.mark === 'start' && <Badge tone="start">여기서 시작</Badge>}
        {h.mark === 'new' && <Badge tone="new">NEW</Badge>}
      </div>
      <span className="sh-ell" style={{ fontSize: 13.5, fontWeight: 600, lineHeight: '20px' }}>{h.title}</span>
      <div style={{ fontSize: 11.5, color: 'var(--wm-text-muted)', lineHeight: 1.5, height: 52, overflow: 'hidden' }}>{h.desc}</div>
      {h.feeds && <div className="sh-feeds">{arrow()}<span>{h.feeds}</span></div>}
    </Link>
  );
}

function VisualCard({ f }: { f: ShellFeature }) {
  const h = f.home;
  return (
    <Link to={f.newRoute} className="hcard hcard--visual" data-home-card={f.key}>
      <span className="sh-ibox" style={{ width: 34, height: 34, borderRadius: 10 }}><FeatureIcon code={f.code} size={18} color="var(--wm-brand)" /></span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0, flex: 1 }}>
        <span style={{ fontSize: 14.5, fontWeight: 600, whiteSpace: 'nowrap' }}>{h.title}</span>
        <span className="sh-ell" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>{h.desc}</span>
        {h.feeds && <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden' }}>{arrow()}{h.feeds}</span>}
      </span>
    </Link>
  );
}

export function Home() {
  // 홈 = 진행 중인 작업 없음(§5.1). section 을 두지 않아 브레드크럼은 `홈` 만.
  useShellPage({ hasTask: false });
  const me = useMe();
  const recent = useRecentItems(3);
  const now = useMemo(() => new Date(), []);
  const tz = me.data?.timezone || 'Asia/Seoul';
  const greeting = greetingFor(now, tz);
  const name = me.data?.given_name || me.data?.name;
  const hero = shellFeatures().find((f) => f.home.section === 'hero');
  const plan = PLAN_ORDER.map((c) => shellFeatureByCode(c)).filter((f): f is ShellFeature => !!f)
    .concat(shellFeatures().filter((f) => f.home.section === 'plan' && !PLAN_ORDER.includes(f.code)));
  const visual = VISUAL_ORDER.map((c) => shellFeatureByCode(c)).filter((f): f is ShellFeature => !!f)
    .concat(shellFeatures().filter((f) => f.home.section === 'visual' && !VISUAL_ORDER.includes(f.code)));
  const items = recent.data?.items ?? [];
  const showRecent = recent.isLoading || items.length > 0;

  return (
    <section className="sh-home" aria-label="홈">
      <div className="sh-home__inner">
        <div className="sh-home__head">
          <h1 className="sh-home__h1" data-greeting="">
            {me.isLoading ? <span style={{ visibility: 'hidden' }}>{greeting}, 님. 오늘은 무엇을 제안해 볼까요?</span>
              : name ? `${greeting}, ${name}님. 오늘은 무엇을 제안해 볼까요?` : `${greeting}. 오늘은 무엇을 제안해 볼까요?`}
          </h1>
          <p className="sh-home__sub">만들 콘텐츠를 고르면 바로 시작돼요. 고객 요구사항을 먼저 정리해 두면 이후 작업이 그 내용으로 자동으로 채워져요.</p>
        </div>

        {hero && (
          <Link to={hero.newRoute} className="hcard hcard--hero" data-home-card={hero.key}>
            <span style={{ width: 46, height: 46, flexShrink: 0, borderRadius: 13, background: 'var(--wm-brand)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FeatureIcon code={hero.code} size={23} color="#fff" />
            </span>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 17, fontWeight: 700 }}>{hero.home.title}</span>
                <Badge tone="core">핵심 기능</Badge>
              </span>
              <span className="sh-ell" style={{ fontSize: 13, color: 'var(--wm-text-muted)' }}>{hero.home.desc}</span>
            </span>
            <span className="wm-btn wm-btn--primary wm-btn--h40" style={{ pointerEvents: 'none' }}>바로 시작{arrow(15, 'currentColor', 2.2)}</span>
          </Link>
        )}

        <div className="sh-home__sechead"><b>기획 · 분석</b><span>제안서에 들어갈 재료를 만들어요. 결과는 해당 섹션으로 바로 보내져요.</span></div>
        <div className="sh-home__grid sh-home__grid--6" data-home-section="plan">{plan.map((f) => <PlanCard key={f.key} f={f} />)}</div>

        <div className="sh-home__sechead"><b>공간 · 비주얼</b><span>제안 공간을 보여 줄 이미지 · 조감도 · 장면을 만들어요.</span></div>
        <div className="sh-home__grid sh-home__grid--3" data-home-section="visual">{visual.map((f) => <VisualCard key={f.key} f={f} />)}</div>

        {showRecent && !recent.isError && (
          <>
            <div className="sh-home__sechead" style={{ justifyContent: 'space-between' }}>
              <span style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}><b>최근 작업</b><span>하던 작업을 바로 이어서 할 수 있어요.</span></span>
              <Link to="/requirements" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12.5, fontWeight: 600 }}>
                전체 작업 보기<Icon name="chevronRight" size={12} strokeWidth={2.4} />
              </Link>
            </div>
            <div className="sh-home__grid sh-home__grid--3" data-home-section="recent">
              {recent.isLoading
                ? [0, 1, 2].map((i) => <Skeleton key={i} h={64} r={14} />)
                : items.map((it) => (
                  <Link key={it.item_id} to={it.route} className="hcard hcard--recent" data-recent={it.item_id}>
                    <span style={{ width: 34, height: 34, flexShrink: 0, borderRadius: 10, background: 'var(--wm-surface-3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <FeatureIcon code={it.feature} size={17} color="var(--wm-text-muted)" />
                    </span>
                    <span style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0, flex: 1 }}>
                      <span className="sh-ell" style={{ fontSize: 13.5, fontWeight: 600 }} title={it.title}>{it.title}</span>
                      <span className="sh-ell" style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }}>{featureName(it.feature)} · {relativeTime(it.updated_at, now, tz)}</span>
                    </span>
                    <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" strokeWidth={2.2} />
                  </Link>
                ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
