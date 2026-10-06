/**
 * SC0 · 작업 목록(§4.1) — 머리 · 시작 카드 3 · 조감도 변경 알림 · 상태 탭(개수) · 검색 · 시작 방식 · 정렬 · 표 · 꼬리.
 * IMG4 「공간 시나리오 장면으로」가 `/scenario?image_version=&request=` 로 보내면 그 장면에 붙이고 SC4E 로 간다.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { ErrorState, Icon, Skeleton, useConfirm } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi, type ScenarioRow } from '../api';
import { qk, useDebounced, useInvalidate, useJobsPulse } from '../hooks';
import { route, SECTION, TYPE_ROW, whenLabel } from '../lib';
import { Dropdown, Ico, MoreMenu, Note, P, StatusIcon } from '../parts';

type Tab = 'all' | 'draft' | 'generating' | 'done';
type Mode = 'all' | 'blank' | 'template' | 'birdseye';
type Sort = 'updated' | 'created' | 'title';
const LIMIT = 20;
const MODE_LABEL: Record<Mode, string> = { all: '전체', blank: '직접 입력', template: '업종 템플릿', birdseye: '조감도' };
const SORT_LABEL: Record<Sort, string> = { updated: '최근 수정순', created: '최근 만든 순', title: '이름순' };

export default function ListPage() {
  const nav = useNavigate();
  const inv = useInvalidate();
  const [sp, setSp] = useSearchParams();
  const [tab, setTab] = useState<Tab>('all');
  const [mode, setMode] = useState<Mode>('all');
  const [sort, setSort] = useState<Sort>('updated');
  const [q, setQ] = useState('');
  const dq = useDebounced(q, 250);
  const [cursors, setCursors] = useState<string[]>([]);
  const [msg, setMsg] = useState<{ text: string; tone: 'ok' | 'err' } | null>(null);
  const { confirm, dialog } = useConfirm();
  const cursor = cursors[cursors.length - 1];
  useEffect(() => { setCursors([]); }, [tab, mode, sort, dq]);

  useShellPage({ section: SECTION, title: '작업 목록', hasTask: false, sidebarGroup: 'scenario' });

  // IMG4 → 장면 이미지 돌려받기
  const retVersion = sp.get('image_version');
  const retRequest = sp.get('request');
  useEffect(() => {
    if (!retVersion || !retRequest) return;
    let off = false;
    scApi.imageReturn(retRequest, retVersion)
      .then((r) => { if (!off) nav(r.route, { replace: true }); })
      .catch((e) => { if (!off) { setMsg({ text: `장면에 이미지를 붙이지 못했어요 · ${errMessage(e)}`, tone: 'err' }); setSp({}, { replace: true }); } });
    return () => { off = true; };
  }, [retVersion, retRequest, nav, setSp]);

  const params = { status: tab, start_mode: mode, q: dq, sort, cursor };
  const list = useQuery({
    queryKey: qk.list(params),
    queryFn: () => scApi.list({ status: tab, start_mode: mode, q: dq, sort, limit: LIMIT, cursor }),
    refetchInterval: 10_000,
  });
  const rows = list.data?.items ?? [];
  const counts = list.data?.counts;
  const alert = list.data?.alert;
  // 생성 중인 행은 잡 SSE 로 바로 갱신
  const genJobs = rows.filter((r) => r.status === 'generating').map((r) => r.route.split('/generate/')[1]).filter(Boolean);
  useJobsPulse(genJobs, () => { void list.refetch(); });

  const dismiss = async () => {
    if (!alert?.scenario_ids.length) return;
    try { await scApi.dismissAlert(alert.scenario_ids[0]); await list.refetch(); } catch (e) { setMsg({ text: errMessage(e), tone: 'err' }); }
  };
  const clone = async (r: ScenarioRow) => {
    try { const c = await scApi.clone(r.id); await inv.all(); nav(c.route); } catch (e) { setMsg({ text: errMessage(e), tone: 'err' }); }
  };
  const remove = async (r: ScenarioRow) => {
    const yes = await confirm({ title: `「${r.title}」을 지울까요?`, message: '지운 시나리오는 되돌릴 수 없어요.', tone: 'danger', confirmLabel: '지우기' });
    if (!yes) return;
    try { await scApi.remove(r.id); await list.refetch(); setMsg({ text: `「${r.title}」을 지웠어요`, tone: 'ok' }); } catch (e) { setMsg({ text: errMessage(e), tone: 'err' }); }
  };

  const page = cursors.length;
  const a = rows.length ? page * LIMIT + 1 : 0;
  const b = page * LIMIT + rows.length;
  const total = list.data?.total ?? 0;
  const filtered = tab !== 'all' || mode !== 'all' || !!dq;
  const tabs: Array<{ value: Tab; label: string; n?: number }> = [
    { value: 'all', label: '전체', n: counts?.all }, { value: 'draft', label: '작성 중', n: counts?.draft },
    { value: 'generating', label: '생성 중', n: counts?.generating }, { value: 'done', label: '완료', n: counts?.done },
  ];

  return (
    <section className="sc-list" data-testid="sc0">
      <div className="sc-list__in">
        <div className="sc-list__head">
          <div style={{ minWidth: 0 }}>
            <h1 className="sc-list__title">공간 시나리오</h1>
            <div className="sc-list__desc">고객 공간의 하루 · 동선을 장면으로 풀고, 장면마다 삼성 제품 · 솔루션 활용을 넣습니다.</div>
          </div>
          <Link to={route.newType()} className="sc-btn sc-btn--primary" data-testid="sc0-new"><Ico d={P.plus} size={16} sw={2.4} />새 시나리오</Link>
        </div>
        <StartCards />
        {alert && (
          <div className="sc-alert" role="status" data-testid="sc0-alert">
            <Ico d={P.warn} size={16} sw={2.2} color="var(--wm-text)" />
            <span className="sc-alert__main"><b>{alert.title}</b> 조감도가 {alert.changed_label}에 바뀌었어요.</span>
            <span className="sc-alert__sub">연결된 시나리오 {alert.scenario_ids.length}개의 공간 · 제품을 다시 맞출까요?</span>
            <Link to={route.resync(alert.scenario_ids[0])} className="sc-link" data-testid="sc0-alert-apply">변경 반영하기</Link>
            <button type="button" className="sc-iconbtn" aria-label="닫기" onClick={() => void dismiss()} data-testid="sc0-alert-close"><Icon name="x" size={12} strokeWidth={2.6} /></button>
          </div>
        )}
        {msg && <div style={{ marginTop: 12 }}><Note tone={msg.tone} onClose={() => setMsg(null)}>{msg.text}</Note></div>}
        <div className="sc-tabs">
          <div className="sc-tabs__list" role="tablist" aria-label="상태">
            {tabs.map((t) => (
              <button key={t.value} type="button" role="tab" aria-selected={tab === t.value} className="sc-tab" onClick={() => setTab(t.value)} data-testid={`sc0-tab-${t.value}`}>
                {t.label}<span>{t.n ?? 0}</span>
              </button>
            ))}
          </div>
          <div className="sc-tabs__tools">
            <div className="sc-search" style={{ width: 260 }}>
              <Ico d="M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14 M20 20l-4-4" size={13} sw={2.2} color="var(--wm-text-subtle)" />
              <label htmlFor="sc0-q" className="wm-sr-only">시나리오 검색</label>
              <input id="sc0-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="시나리오 · 고객 · 공간 검색" autoComplete="off" />
            </div>
            <Dropdown label={`시작 방식 · ${MODE_LABEL[mode]}`} value={mode} onChange={setMode} testId="sc0-mode"
              options={(Object.keys(MODE_LABEL) as Mode[]).map((m) => ({ value: m, label: MODE_LABEL[m] }))} />
            <Dropdown label={SORT_LABEL[sort]} value={sort} onChange={setSort} testId="sc0-sort"
              options={(Object.keys(SORT_LABEL) as Sort[]).map((s) => ({ value: s, label: SORT_LABEL[s] }))} />
          </div>
        </div>
        <div className="sc-table" role="table" aria-label="시나리오 목록" data-testid="sc0-table">
          <div className="sc-table__head" role="row">
            {['시나리오 · 고객', '시작 방식', '유형', '장면', '상태', '수정', ''].map((h, i) => <span key={i} role="columnheader">{h}</span>)}
          </div>
          {list.isLoading && [0, 1, 2].map((i) => (
            <div key={i} className="sc-table__row" role="row"><Skeleton h={16} w="70%" /><Skeleton h={12} w="60%" /><Skeleton h={12} w={60} /><span /><Skeleton h={12} w="60%" /><span /><span /></div>
          ))}
          {list.isError && <div style={{ padding: 18 }}><ErrorState message="목록을 불러오지 못했어요" onRetry={() => list.refetch()} /></div>}
          {!list.isLoading && !list.isError && rows.length === 0 && (
            <div className="sc-empty" data-testid="sc0-empty">
              {filtered ? <><b>맞는 시나리오가 없어요</b><span>검색어나 필터를 바꿔 보세요</span></> : <><b>아직 시나리오가 없어요</b><span>위 시작 카드에서 첫 시나리오를 만들어 보세요</span></>}
            </div>
          )}
          {rows.map((r) => <Row key={r.id} r={r} onClone={() => void clone(r)} onRemove={() => void remove(r)} />)}
        </div>
        <div className="sc-list__foot">
          <span className="sc-row" data-testid="sc0-range">
            {total}개 중 {a}–{b}
            {(page > 0 || list.data?.next_cursor) && (
              <>
                <button type="button" className="sc-iconbtn" aria-label="이전 쪽" disabled={page === 0} onClick={() => setCursors(cursors.slice(0, -1))}><Icon name="chevronLeft" size={13} /></button>
                <button type="button" className="sc-iconbtn" aria-label="다음 쪽" disabled={!list.data?.next_cursor} onClick={() => list.data?.next_cursor && setCursors([...cursors, list.data.next_cursor])}><Icon name="chevronRight" size={13} /></button>
              </>
            )}
          </span>
          <span>완료된 시나리오는 보내기 아이콘으로 제안서 · PDF로 바로 넘길 수 있어요</span>
        </div>
      </div>
      {dialog}
    </section>
  );
}

export function StartCards() {
  const cards = [
    { to: route.newType(), icon: P.play, name: '빈 시나리오로 시작', sub: '유형 → 공간 시나리오 → 솔루션 · 제품 → 생성', id: 'blank' },
    { to: route.template(), icon: P.grid, name: '업종 템플릿으로 시작', sub: '16개 업종 · 대표 공간 · 장면 프리셋', id: 'template' },
    { to: route.fromBirdseye(), icon: P.cube, name: '조감도에서 이어 만들기', sub: '조감도 존과 배치 제품을 공간으로 가져오기', id: 'birdseye' },
  ];
  return (
    <div className="sc-starts">
      {cards.map((c) => (
        <Link key={c.id} to={c.to} className="sc-start" data-testid={`sc0-start-${c.id}`}>
          <span className="sc-start__icon"><Ico d={c.icon} size={18} /></span>
          <span style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: 1, minWidth: 0 }}>
            <span className="sc-start__name">{c.name}</span>
            <span className="sc-start__sub">{c.sub}</span>
          </span>
          <Ico d={P.arrow} size={16} sw={2.2} color="var(--wm-brand)" />
        </Link>
      ))}
    </div>
  );
}

const START_ICON: Record<string, string> = { blank: P.pencil, template: P.grid, birdseye: P.cube };

function Row({ r, onClone, onRemove }: { r: ScenarioRow; onClone: () => void; onRemove: () => void }) {
  const nav = useNavigate();
  const kind = r.status === 'done' ? 'done' : r.status === 'generating' ? 'gen' : r.status === 'failed' ? 'failed' : 'draft';
  const subCls = r.status === 'done' && r.in_proposal ? 'sc-cell-status__sub sc-cell-status__sub--brand'
    : r.birdseye_changed && r.status === 'draft' ? 'sc-cell-status__sub sc-cell-status__sub--strong' : 'sc-cell-status__sub';
  return (
    <div className="sc-table__row" role="row" data-testid="sc0-row" data-id={r.id} data-status={r.status}>
      <div className="sc-cell-title" role="cell">
        <Link to={r.route} data-testid="sc0-row-title">{r.title}</Link>
        <span>{r.customer_line}</span>
      </div>
      <div className="sc-cell-start" role="cell" data-testid="sc0-row-start">
        <Ico d={START_ICON[r.start_mode] ?? P.pencil} size={13} color="var(--wm-text-muted)" />
        <span className="wm-ellipsis">{r.start_label}</span>
      </div>
      <div role="cell" style={{ display: 'flex' }}><span className={r.type === 'with' ? 'sc-typetag' : 'sc-typetag sc-typetag--without'}>{TYPE_ROW[r.type]}</span></div>
      <div role="cell" className="sc-cell-num">{r.scene_count}</div>
      <div role="cell" className="sc-cell-status" data-testid="sc0-row-status">
        <StatusIcon kind={kind} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
          <span className="sc-cell-status__main">{r.status_label}</span>
          {r.status_action ? (
            <Link to={r.route} className="sc-cell-status__sub sc-cell-status__sub--brand">{r.status_sub}</Link>
          ) : (
            <span className={subCls}>{r.birdseye_changed && r.status === 'draft' && <Ico d={P.warn} size={12} sw={2.4} />}{r.status_sub}</span>
          )}
        </div>
      </div>
      <div role="cell" className="sc-cell-when">{whenLabel(r.updated_at)}</div>
      <div role="cell" className="sc-cell-act">
        {r.status === 'done'
          ? <Link to={route.send(r.id)} className="sc-iconbtn sc-iconbtn--line" aria-label="제안서로 보내기" title="제안서로 보내기 · 내보내기" data-testid="sc0-send"><Ico d={P.send} size={13} sw={2.2} /></Link>
          : <span style={{ width: 28, height: 28 }} />}
        <MoreMenu testId="sc0-more" items={[
          { label: '열기', onClick: () => nav(r.route) },
          { label: '복제', onClick: onClone },
          { label: '삭제', onClick: onRemove, danger: true },
        ]} />
      </div>
    </div>
  );
}
