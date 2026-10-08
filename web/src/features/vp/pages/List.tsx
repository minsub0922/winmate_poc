/**
 * VP0 — 작업 목록(`/vp`) · VPR 규칙 시트(`/vp/rules`) · 시작 방법 4(직접 · Storyboard · MI · 복제).
 */
import { useMemo, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useShellPage } from '@/shell/ShellContext';
import { Modal, SearchField, Empty, Skeleton, ErrorState, Icon, Button } from '@/ui';
import { api, unwrap } from '@/api/client';
import { cloneVp, collect, createVp, errText, usePacks, useVpList, type VPListItem } from '../api';
import { CodeChip, ICONS, PIcon, SECTION } from '../parts';
import { RulesSheet } from './Rules';

type Tab = '' | 'ask' | 'check' | 'run' | 'done';
const TABS: Array<{ v: Tab; label: string }> = [
  { v: '', label: '전체' }, { v: 'ask', label: '선택 필요' }, { v: 'check', label: '확인 권장' }, { v: 'run', label: '생성 중' }, { v: 'done', label: '완료' },
];

const STARTS = [
  { key: 'direct', title: '직접 입력으로', desc: '고객 · 과제를 적으면 나머지 재료는 찾아 와요', base: true, icon: ICONS.edit },
  { key: 'storyboard', title: 'Storyboard에서', desc: 'Key Message를 가치 기둥으로 바로 써요', base: false, icon: ICONS.sb },
  { key: 'mi', title: 'MI 결과에서', desc: '과제 · 사용자 · 삼성 강점을 근거로 써요', base: false, icon: ICONS.mi },
  { key: 'clone', title: '이전 가치 제안 복제', desc: '다른 고객에 맞게 업종 · 수치만 다시 골라요', base: false, icon: ICONS.clone },
] as const;

export function ListPage({ rules = false }: { rules?: boolean }) {
  useShellPage({ section: SECTION, title: '작업 목록', hasTask: false });
  const nav = useNavigate();
  const loc = useLocation();
  const [tab, setTab] = useState<Tab>('');
  const [q, setQ] = useState('');
  const [ind, setInd] = useState('');
  const [menu, setMenu] = useState(false);
  const [pick, setPick] = useState<null | 'storyboard' | 'mi' | 'clone'>(null);
  const all = useVpList({ q, industry: ind });
  const packs = usePacks();
  const items = all.data?.items ?? [];
  const counts = all.data?.counts;
  const rows = useMemo(() => items.filter((r) => !tab || r.ui_status === tab), [items, tab]);
  const waiting = (counts?.ask ?? 0) + (counts?.check ?? 0);
  const industries = packs.data?.items ?? [];
  const indName = ind === 'GEN' ? '범용' : industries.find((i) => i.code === ind)?.name;

  const start = (k: (typeof STARTS)[number]['key']) => {
    if (k === 'direct') nav('/vp/new');
    else setPick(k);
  };

  return (
    <div className="vp-list" data-testid="vp-list">
      <div className="vp-list__head">
        <div>
          <h1 className="vp-list__title">Value Proposition 작업</h1>
          <div className="vp-list__sub">가치 제안 {counts?.all ?? 0}건 · 답을 기다리는 작업 {waiting}건 · 생성 중 {counts?.run ?? 0}건</div>
        </div>
        <span style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {/* 새 흐름(2026-10-08 보드 webapp1 VP2) — 제품 · 솔루션마다 가치 여러 개 + 고객의 니즈 */}
          <Link to="/vp/values/new" className="wm-btn wm-btn--outline" style={{ height: 44, fontWeight: 700, fontSize: 14 }} data-testid="vp-values-new">가치 · 고객의 니즈</Link>
          <Link to="/vp/new" className="vp-new"><Icon name="plus" size={16} />새 가치 제안</Link>
        </span>
      </div>

      <div className="vp-starts">
        {STARTS.map((s) => (
          <button key={s.key} type="button" className="vp-start" onClick={() => start(s.key)}>
            <span className="vp-start__icon"><PIcon d={s.icon} size={17} /></span>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="vp-start__title">{s.title}</span>
                {s.base && <span className="vp-start__base">기본</span>}
              </span>
              <span className="vp-start__desc">{s.desc}</span>
            </span>
          </button>
        ))}
      </div>

      {packs.data?.banner && (
        <div className="vp-banner" id="packs">
          <Icon name="info" size={16} color="var(--wm-brand)" />
          <span className="vp-banner__text"><b>{packs.data.banner}</b> <span>{packs.data.banner_sub}</span></span>
          <Link to="/vp/rules">고르는 규칙 보기</Link>
        </div>
      )}

      <div className="vp-tools">
        <SearchField value={q} onChange={setQ} label="작업 검색" tone="white" width={280} placeholder="고객사 · 작업명 · 레이아웃 코드" clearable />
        <div className="vp-tabs" role="tablist" aria-label="상태 필터">
          {TABS.map((t) => {
            const n = t.v ? (counts?.[t.v] ?? 0) : (counts?.all ?? 0);
            return (
              <button key={t.label} role="tab" aria-selected={tab === t.v} className="vp-tab" onClick={() => setTab(t.v)}>{t.label}<span>{n}</span></button>
            );
          })}
        </div>
        <span className="vp-grow" />
        <div className="vp-menu">
          <button type="button" className="vp-menu__btn" aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu((x) => !x)}>
            {indName ? `업종: ${indName}` : '업종 전체'}<Icon name="chevronDown" size={14} />
          </button>
          {menu && (
            <div className="vp-menu__pop" role="menu" aria-label="업종">
              {[{ code: '', name: '업종 전체' }, ...industries.map((i) => ({ code: i.code, name: i.name })), { code: 'GEN', name: '범용' }].map((i) => (
                <button key={i.code || 'all'} role="menuitemradio" aria-checked={ind === i.code} className="vp-menu__item" onClick={() => { setInd(i.code); setMenu(false); }}>
                  {i.name}{ind === i.code && <Icon name="check" size={14} />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="vp-table" role="table" aria-label="Value Proposition 작업">
        <div className="vp-trow vp-trow--head" role="row"><span>작업</span><span>업종</span><span>레이아웃</span><span>상태</span><span>연결된 제안서</span><span /></div>
        {all.isLoading && [0, 1, 2].map((i) => <div key={i} className="vp-trow"><Skeleton w="60%" /><Skeleton w={60} /><Skeleton w={140} /><Skeleton w={80} /><Skeleton w={120} /><Skeleton w={50} /></div>)}
        {all.isError && <div style={{ padding: 16 }}><ErrorState message={errText(all.error)} onRetry={() => all.refetch()} /></div>}
        {!all.isLoading && !all.isError && rows.length === 0 && (
          <div style={{ padding: 24 }}><Empty size="sm" title={items.length ? '이 상태의 작업이 없어요' : '아직 가치 제안이 없어요'}>위의 시작 방법 중 하나로 시작해 보세요.</Empty></div>
        )}
        {rows.map((r) => <Row key={r.id} r={r} />)}
        <div className="vp-tfoot">
          <span>{all.data?.total_label || `작업 ${counts?.all ?? 0}개 · 최근 30일`}</span>
          <span>열면 마지막 단계에서 이어집니다 · 답이 없는 질문은 추천값으로 진행돼요</span>
        </div>
      </div>

      {pick && <WorkPicker kind={pick} onClose={() => setPick(null)} />}
      <Modal open={rules} onClose={() => nav(loc.state?.back ?? '/vp')} title="에이전트 라우팅 규칙" width={1200} ariaLabel="에이전트 라우팅 규칙">
        <RulesSheet />
      </Modal>
    </div>
  );
}

function Row({ r }: { r: VPListItem }) {
  const sub = `${r.owner_name || '나'} · ${r.when_label}`;
  return (
    <div className="vp-trow" role="row" data-testid="vp-row" data-status={r.ui_status}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <Link to={r.resume_route} className="vp-trow__title">{r.title}</Link>
        <span className="vp-trow__sub">{sub}</span>
      </div>
      <span className="vp-trow__ind">{r.industry?.name ?? '—'}</span>
      <div className="vp-trow__codes">{(r.layout_chips ?? []).map((c, i) => <CodeChip key={i} t={c.t} kind={c.kind} />)}</div>
      <span className={`vp-st vp-st--${r.ui_status}`}>{r.status_text}</span>
      <span className={r.linked_proposal ? 'vp-trow__prop' : 'vp-trow__prop vp-trow__prop--none'}>{r.linked_proposal ? String(r.linked_proposal.title ?? '') || '연결 안 됨' : '연결 안 됨'}</span>
      <Link to={r.resume_route} className={r.ui_status === 'ask' ? 'vp-act vp-act--primary' : 'vp-act'}>{r.action_label}</Link>
    </div>
  );
}

const PICK_FEATURE = { storyboard: 'SB', mi: 'MI', clone: 'VP' } as const;
const PICK_TITLE = { storyboard: 'Storyboard 고르기', mi: 'MI 결과 고르기', clone: '복제할 가치 제안 고르기' } as const;

/** 작업 고르기(Storyboard · MI · 이전 가치 제안) — 셸 대화상자가 없어 기능 쪽에서 만든다(docs/requests/workspace.md). */
function WorkPicker({ kind, onClose }: { kind: 'storyboard' | 'mi' | 'clone'; onClose: () => void }) {
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const [sel, setSel] = useState<{ id: string; title: string } | null>(null);
  const [customer, setCustomer] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const list = useQuery({
    queryKey: ['vp', 'pick', kind, q],
    queryFn: async () => unwrap(await api.workspace.GET('/v1/items', { params: { query: { feature: PICK_FEATURE[kind], q: q || undefined, limit: 20, owner: 'all' } } })),
  });
  const go = async () => {
    if (!sel) return;
    setBusy(true);
    setErr('');
    try {
      if (kind === 'clone') {
        const doc = await cloneVp(sel.id, { customer_name: customer.trim(), keep_pinned: true });
        nav(`/vp/${doc.id}/structure`);
      } else {
        const doc = await createVp({ start: kind, source_refs: [{ kind, ref_id: sel.id }] });
        await collect(doc.id);
        nav(`/vp/${doc.id}/materials`);
      }
    } catch (e) {
      setErr(errText(e));
      setBusy(false);
    }
  };
  const can = !!sel && (kind !== 'clone' || customer.trim().length > 0);
  return (
    <Modal open onClose={onClose} title={PICK_TITLE[kind]} width={560} ariaLabel={PICK_TITLE[kind]}
      footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center', width: '100%' }}>
        {err && <span className="vp-err" style={{ marginRight: 'auto' }}>{err}</span>}
        <Button h={38} onClick={onClose}>취소</Button>
        <Button h={38} variant="primary" onClick={go} disabled={!can} disabledReason={kind === 'clone' ? '원본과 고객사를 정해 주세요' : '작업을 골라 주세요'} loading={busy}>
          {kind === 'clone' ? '복제하기' : '이 자료로 시작'}
        </Button>
      </div>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <SearchField value={q} onChange={setQ} label="작업 검색" tone="gray" placeholder="작업 이름 · 고객사" autoFocus />
        <div role="listbox" aria-label="작업" style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 320, overflow: 'auto' }}>
          {list.isLoading && <Skeleton h={48} />}
          {!list.isLoading && (list.data?.items ?? []).length === 0 && <Empty size="sm" title="고를 수 있는 작업이 없어요">먼저 그 기능에서 작업을 만들어 주세요.</Empty>}
          {(list.data?.items ?? []).map((it) => (
            <button key={it.item_id} type="button" role="option" aria-selected={sel?.id === it.item_id} className="vp-pickrow" onClick={() => setSel({ id: it.item_id, title: it.title })}>
              <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
                <b>{it.title}</b>
                <span>{[it.summary, it.owner_name].filter(Boolean).join(' · ')}</span>
              </span>
              {sel?.id === it.item_id && <Icon name="check" size={16} color="var(--wm-brand)" />}
            </button>
          ))}
        </div>
        {kind === 'clone' && (
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span className="vp-form__label">새 고객사 <span>· 고정한 시트는 그대로 두고 나머지만 다시 골라요</span></span>
            <span className="vp-input"><input value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="예: K 베이커리" /></span>
          </label>
        )}
      </div>
    </Modal>
  );
}
