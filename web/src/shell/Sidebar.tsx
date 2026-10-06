/**
 * 사이드바(00-shell §6) — 로고 · 새 작업 · 작업 내역(기능 10, 개수 · 펼친 그룹 항목 최대 5) · 사용자 카드.
 * 데이터: workspace `/v1/me` · `/v1/items/counts` · `/v1/items?feature=&limit=5`.
 * 작업 항목은 현재 화면이 그 기능 작업을 받을 때(accepts 'work_item' + acceptsWork) 끌 수 있다(§6.3 · §5.7).
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Avatar, Icon, Skeleton, useActiveDrag, useDragSource } from '@/ui';
import { shellFeatures, type ShellFeature } from './catalog';
import { FEATURE_ICON, FeatureIcon } from './icons';
import { useShellRuntime } from './runtime';
import { UserMenu } from './UserMenu';
import { markNotificationsRead, useFeatureItems, useItemCounts, useMe, useNotificationCounts, type WsItem } from './workspace';
import type { FeatureCode } from './types';

function pathOf(route: string) {
  try { return new URL(route, 'http://x').pathname.replace(/\/$/, ''); } catch { return route; }
}

function WorkItem({ it, f, current, draggable, unread = 0 }: { it: WsItem; f: ShellFeature; current: boolean; draggable: boolean; unread?: number }) {
  const active = useActiveDrag();
  const r = `ws:item:${it.item_id}`;
  const drag = useDragSource(draggable ? { type: 'work_item', ref: r, label: it.title, sub: `사이드바 · ${f.name}`, feature: f.code, icon: FEATURE_ICON[f.code] } : null);
  return (
    <Link to={it.route} title={unread ? `${it.title} · 새 알림 ${unread}건` : it.title} aria-current={current ? 'page' : undefined} draggable={draggable} {...drag}
      className={['sh-item', current && 'sh-item--cur', draggable && 'sh-item--drag', active?.ref === r && 'sh-item--dragging'].filter(Boolean).join(' ')}>
      <span>{it.title}</span>
      {unread > 0 && <span className="sh-item__new wm-num" data-unread={unread}>{unread}<span className="wm-sr-only">건 새 알림</span></span>}
    </Link>
  );
}

/** 지금 화면이 알림이 있는 작업물이면(경로에 항목 id) 그 항목 알림을 읽음으로 */
function useMarkVisitedRead(pathname: string) {
  const counts = useNotificationCounts();
  const qc = useQueryClient();
  const done = useRef(new Set<string>());
  useEffect(() => {
    const segs = pathname.split('/');
    for (const it of counts.data?.items ?? []) {
      if (!it.unread || !segs.includes(it.item_id)) continue;
      const k = `${pathname}|${it.item_id}|${it.unread}`;
      if (done.current.has(k)) continue;
      done.current.add(k);
      void markNotificationsRead({ item_id: it.item_id }).then(() => qc.invalidateQueries({ queryKey: ['ws', 'notifications'] })).catch(() => undefined);
    }
  }, [pathname, counts.data, qc]);
  return counts;
}

function GroupItems({ f, pathname, dragOk, unreadOf }: { f: ShellFeature; pathname: string; dragOk: boolean; unreadOf: (id: string) => number }) {
  const items = useFeatureItems(f.code as FeatureCode, 5);
  if (items.isLoading) {
    return <div className="sh-items" aria-busy="true">{[0, 1, 2].map((i) => <Skeleton key={i} h={32} r={8} />)}</div>;
  }
  if (items.isError) return <div className="sh-items" />;
  const list = items.data?.items ?? [];
  return (
    <div className="sh-items">
      {list.map((it) => {
        const p = pathOf(it.route);
        const cur = pathname === p || pathname.startsWith(`${p}/`);
        return <WorkItem key={it.item_id} it={it} f={f} current={cur} draggable={dragOk} unread={cur ? 0 : unreadOf(it.item_id)} />;
      })}
    </div>
  );
}

export function Sidebar() {
  const loc = useLocation();
  const rt = useShellRuntime();
  const first = loc.pathname.split('/')[1] ?? '';
  const routeGroup = shellFeatures().find((f) => f.key === first)?.key ?? null;
  const [manual, setManual] = useState<{ path: string; key: string | null } | null>(null);
  useEffect(() => { setManual(null); }, [loc.pathname]);
  const expanded = manual && manual.path === loc.pathname ? manual.key : (rt.page.sidebarGroup ?? routeGroup);
  const counts = useItemCounts();
  const me = useMe();
  const noti = useMarkVisitedRead(loc.pathname);
  const unreadOf = (id: string) => noti.data?.items.find((x) => x.item_id === id)?.unread ?? 0;
  const groupUnread = (code: string) => (noti.data?.items ?? []).filter((x) => x.feature === code).reduce((a, x) => a + x.unread, 0);
  const countOf = (code: string) => counts.data?.items.find((c) => c.feature === code)?.count ?? (counts.isLoading ? '·' : 0);
  const acceptWork = rt.canDrag('work_item');
  const workOk = (code: string) => acceptWork && (!rt.page.acceptsWork?.length || rt.page.acceptsWork.includes(code as FeatureCode));

  return (
    <aside className="sh-sidebar" aria-label="사이드바">
      <Link to="/" className="sh-logo" aria-label="winmate 홈">
        <span className="sh-logo__w" aria-hidden="true">W</span>
        <span className="sh-logo__name">winmate</span>
      </Link>
      <Link to="/" className="sh-newbtn">
        <Icon name="plus" size={16} strokeWidth={2.2} />
        <span>새 작업</span>
      </Link>
      <div className="sh-overline">작업 내역</div>
      <nav className="sh-groups" aria-label="작업 내역">
        {shellFeatures().map((f) => {
          const open = expanded === f.key;
          const gu = groupUnread(f.code);
          return (
            <div key={f.key} data-group={f.key}>
              <div className={['sh-group__row', open && 'sh-group__row--open'].filter(Boolean).join(' ')}>
                <Link to={f.listRoute} className="sh-group__link" aria-expanded={open}>
                  <FeatureIcon code={f.code} color={open ? 'var(--wm-brand)' : 'var(--wm-text-muted)'} strokeWidth={1.9} />
                  <span className="sh-group__name">{f.name}</span>
                  {gu > 0 && <span className="sh-group__dot" title={`새 알림 ${gu}건`} data-unread={gu}><span className="wm-sr-only">새 알림 {gu}건</span></span>}
                  <span className="wm-count" aria-label={`작업 ${countOf(f.code)}건`}>{countOf(f.code)}</span>
                </Link>
                <button type="button" className="sh-group__chev" aria-label={`${f.name} ${open ? '접기' : '펼치기'}`}
                  onClick={() => setManual({ path: loc.pathname, key: open ? null : f.key })}>
                  <Icon name={open ? 'chevronDown' : 'chevronRight'} size={12} color="var(--wm-text-subtle)" strokeWidth={2.2} />
                </button>
              </div>
              {open && <GroupItems f={f} pathname={loc.pathname} dragOk={workOk(f.code)} unreadOf={unreadOf} />}
            </div>
          );
        })}
      </nav>
      <div style={{ flex: 1 }} />
      <div className="sh-user">
        <Avatar initial={me.data?.initial ?? me.data?.name?.slice(0, 1) ?? '·'} />
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
          <div className="sh-user__name">{me.data?.name ?? ''}</div>
          <div className="sh-user__org">{me.data?.org ?? ''}</div>
        </div>
        <UserMenu />
      </div>
    </aside>
  );
}
