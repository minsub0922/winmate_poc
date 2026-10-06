/** BE0 — 조감도 작업 목록(`/birdseye`, §4.1): 시작 카드 3 · 상태 필터 · 작업 표 · 행 메뉴 · 팀 공유 조감도. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useShellPage } from '@/shell/ShellContext';
import { Icon, Modal, SearchField, Toggle, toast, useConfirm } from '@/ui';
import { be, errText, qk, useList, type Row } from '../api';
import { PlanCanvas } from '../PlanCanvas';
import { SECTION, whenLabel } from '../ui';

type Filter = 'all' | 'in_progress' | 'needs_check' | 'done';

export default function ListPage() {
  useShellPage({ section: SECTION, title: '작업 목록', hasTask: false, sidebarGroup: 'birdseye' });
  const nav = useNavigate();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>('all');
  const [inProposal, setInProposal] = useState(false);
  const [q, setQ] = useState('');
  const [dq, setDq] = useState('');
  useEffect(() => { const t = window.setTimeout(() => setDq(q.trim()), 200); return () => window.clearTimeout(t); }, [q]);
  const list = useList({ filter, in_proposal: inProposal, q: dq });
  const all = useList({ filter: 'all' });
  const team = useList({ scope: 'team', limit: 20 });
  const [menu, setMenu] = useState<string | null>(null);
  const [preview, setPreview] = useState<Row | null>(null);
  const [showAllShared, setShowAllShared] = useState(false);
  const { confirm, dialog } = useConfirm();
  const counts = list.data?.counts ?? all.data?.counts ?? { all: 0, in_progress: 0, needs_check: 0, done: 0 };
  const rows = list.data?.items ?? [];
  const total = all.data?.counts.all ?? counts.all;

  const refresh = () => qc.invalidateQueries({ queryKey: ['be', 'list'] });
  const clone = async (r: Row) => {
    try {
      const out = await be.clone(r.id);
      await refresh();
      nav(out.route);
    } catch (e) { toast(errText(e)); }
  };
  const remove = async (r: Row) => {
    setMenu(null);
    if (await confirm({ title: '이 조감도를 삭제할까요?', message: '제안서 · 시나리오에 이미 넣은 이미지는 그대로 남아요.', tone: 'danger', confirmLabel: '삭제' })) {
      try { await be.remove(r.id); await refresh(); } catch (e) { toast(errText(e)); }
    }
  };

  const tabs: Array<{ value: Filter; label: string; n: number }> = [
    { value: 'all', label: '전체', n: counts.all }, { value: 'in_progress', label: '진행 중', n: counts.in_progress },
    { value: 'needs_check', label: '확인 필요', n: counts.needs_check }, { value: 'done', label: '완료', n: counts.done },
  ];
  const shared = (team.data?.items ?? []).filter((r) => r.shared_scope === 'team');
  const empty = !list.isLoading && total === 0;

  return (
    <div className="be-list" data-testid="be0">
      <div className="be-list__head">
        <div>
          <h1>조감도 작업 <span className="wm-num" data-testid="be0-total">{total}</span></h1>
          <p>진행 중인 작업을 이어서 하거나, 공간 설명 · 도면 · 현장 사진으로 새 조감도를 시작하세요.</p>
        </div>
        <Link to="/birdseye/new" className="be-btn be-btn--primary"><Icon name="plus" size={16} />새 조감도 만들기</Link>
      </div>
      <div className="be-starts">
        <Link className="be-start" to="/birdseye/new"><span className="be-start__ico"><Icon name="edit" size={18} /></span>
          <span><b>공간 설명으로 시작</b><span>용도 · 면적 · 층고를 적으면 바로 시작</span></span></Link>
        <Link className="be-start" to="/birdseye/new/plan"><span className="be-start__ico"><Icon name="file" size={18} /></span>
          <span><b>도면 올려서 시작</b><span>PDF · 이미지 도면에서 벽 · 창 · 문 인식</span></span></Link>
        <Link className="be-start" to="/birdseye/new/photos"><span className="be-start__ico"><Icon name="image" size={18} /></span>
          <span><b>현장 사진으로 시작</b><span>여러 장을 올리면 사진마다 구조를 인식</span></span></Link>
      </div>
      {empty ? (
        <div className="be-card be-center" data-testid="be0-empty"><b>아직 조감도 작업이 없어요</b></div>
      ) : (
        <>
          <div className="be-toolbar">
            <div className="be-tabs" role="tablist" aria-label="상태">
              {tabs.map((t) => (
                <button key={t.value} type="button" role="tab" aria-selected={filter === t.value} className={filter === t.value ? 'be-pill be-pill--on' : 'be-pill'}
                  onClick={() => setFilter(t.value)} data-testid={`be0-tab-${t.value}`}>
                  {t.label} <span className="wm-num">{t.n}</span>
                </button>
              ))}
            </div>
            <Toggle checked={inProposal} onChange={setInProposal}>제안서에 쓰인 것만</Toggle>
            <div style={{ flex: 1 }} />
            <SearchField value={q} onChange={setQ} label="작업 검색" placeholder="작업 · 고객사 · 공간 검색" tone="white" width={240} clearable />
            <span className="be-small be-muted">최근 수정순</span>
          </div>
          <div className="be-table" role="table" aria-label="조감도 작업">
            <div className="be-tr be-tr--head" role="row">
              <span>작업</span><span>입력</span><span>진행 상태</span><span>쓰인 곳</span><span>수정</span><span />
            </div>
            {rows.map((r) => (
              <div className="be-tr" role="row" key={r.id} data-testid={`be0-row-${r.id}`}>
                <div className="be-work">
                  {r.thumb_url ? <img className="be-thumb" src={r.thumb_url} alt="" /> : <span className="be-thumb" />}
                  <div style={{ minWidth: 0 }}>
                    <Link className="be-work__title" to={r.route}>{r.title}</Link>
                    <div className="be-work__sub">{r.subtitle}</div>
                  </div>
                </div>
                <div className="be-row">{(r.input_chips ?? []).map((c) => <span key={c} className="be-mini">{c}</span>)}</div>
                <div className="be-status" data-testid="be0-status">
                  <b className={r.status === 'done' ? 'done' : r.status === 'needs_check' ? 'check' : r.status === 'failed' ? 'fail' : undefined}>{r.status_title}</b>
                  {r.status_line && <span>{r.status_line}</span>}
                  {r.running && <Link to={r.running.route}>{r.running.label}</Link>}
                </div>
                <div className="be-uses">
                  {r.usages?.length ? r.usages.map((u) => (
                    <Link key={`${u.service}-${u.ref}`} to={u.route || (u.service === 'proposal' ? `/proposal/${u.ref}` : `/scenario/${u.ref}`)}>
                      {u.service === 'proposal' ? '제안서' : '시나리오'} · {u.label}
                    </Link>
                  )) : <span className="none">아직 없음</span>}
                </div>
                <span className="be-small be-muted">{whenLabel(r.updated_at)}</span>
                <div className="be-act">
                  <Link className={r.action.label === '열기' ? 'be-btn be-btn--sm' : 'be-btn be-btn--sm'} to={r.action.route}>{r.action.label}</Link>
                  <button type="button" className="be-btn be-btn--sm" aria-label="작업 메뉴" aria-haspopup="menu" aria-expanded={menu === r.id}
                    onClick={() => setMenu(menu === r.id ? null : r.id)}><Icon name="more" size={16} /></button>
                </div>
                {menu === r.id && <RowMenu r={r} onClose={() => setMenu(null)} onClone={() => clone(r)} onDelete={() => remove(r)} />}
              </div>
            ))}
            {!rows.length && !list.isLoading && <div className="be-tr"><span className="be-muted">조건에 맞는 작업이 없어요</span></div>}
          </div>
        </>
      )}
      {shared.length > 0 && (
        <section className="be-sec" aria-label="팀에서 공유한 조감도" data-testid="be0-shared">
          <div className="be-sec__head" style={{ justifyContent: 'space-between' }}>
            <span><b>팀에서 공유한 조감도</b> <span>복제하면 배치안부터 내 작업으로 이어집니다</span></span>
            <button type="button" className="be-link" onClick={() => setShowAllShared(true)}>전체 보기</button>
          </div>
          <div className="be-shared">
            {shared.slice(0, 2).map((r) => <SharedCard key={r.id} r={r} onClone={() => clone(r)} onPreview={() => setPreview(r)} />)}
          </div>
        </section>
      )}
      <Modal open={showAllShared} onClose={() => setShowAllShared(false)} title="팀에서 공유한 조감도" width={720}>
        <div className="be-shared" style={{ gridTemplateColumns: '1fr' }}>
          {shared.map((r) => <SharedCard key={r.id} r={r} onClone={() => clone(r)} onPreview={() => setPreview(r)} />)}
        </div>
      </Modal>
      <Modal open={!!preview} onClose={() => setPreview(null)} title={preview?.title} width={820}>
        {preview && <Preview r={preview} />}
      </Modal>
      {dialog}
    </div>
  );
}

function RowMenu({ r, onClose, onClone, onDelete }: { r: Row; onClose: () => void; onClone: () => void; onDelete: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const nav = useNavigate();
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.setTimeout(() => document.addEventListener('mousedown', h), 0);
    document.addEventListener('keydown', k);
    return () => { document.removeEventListener('mousedown', h); document.removeEventListener('keydown', k); };
  }, [onClose]);
  const done = r.done;
  const go = (to: string) => () => { onClose(); nav(to); };
  const off = '3D 조감도가 완성된 뒤에 쓸 수 있어요';
  return (
    <div className="be-menu" role="menu" ref={ref} aria-label="작업 메뉴">
      <button role="menuitem" type="button" disabled={!done} title={done ? undefined : off} onClick={go(`/birdseye/${r.id}/result`)}>열기</button>
      <button role="menuitem" type="button" disabled={r.layout_version < 1} onClick={go(`/birdseye/${r.id}/layout/edit`)}>배치 직접 수정</button>
      <button role="menuitem" type="button" disabled={!done} title={done ? undefined : off} onClick={go(`/birdseye/${r.id}/views`)}>시점 · 조명 바꾸기</button>
      <button role="menuitem" type="button" disabled={!done} title={done ? undefined : off} onClick={go(`/birdseye/${r.id}/zones`)}>존 포인트 지정</button>
      <button role="menuitem" type="button" disabled={r.layout_version < 1} onClick={() => { onClose(); onClone(); }}>복제해서 새 시안</button>
      <button role="menuitem" type="button" disabled={!done} title={done ? undefined : off} onClick={go(`/birdseye/${r.id}/export`)}>내보내기 · 제안서로 보내기</button>
      <button role="menuitem" type="button" disabled={!done} title={done ? undefined : off} onClick={go(`/scenario/new/birdseye?birdseye=${r.id}`)}>시나리오로 이어 만들기</button>
      <button role="menuitem" type="button" className="danger" onClick={onDelete}>삭제</button>
    </div>
  );
}

function SharedCard({ r, onClone, onPreview }: { r: Row; onClone: () => void; onPreview: () => void }) {
  return (
    <div className="be-shared__card" data-testid={`be0-shared-${r.id}`}>
      {r.thumb_url ? <img className="be-thumb" src={r.thumb_url} alt="" /> : <span className="be-thumb" />}
      <div className="be-shared__meta">
        <b>{r.title}</b>
        <span>{r.team_meta}</span>
        <span>{r.products_line}</span>
        <div className="be-row" style={{ marginTop: 4 }}>
          <button type="button" className="be-btn be-btn--sm" onClick={onClone}>복제해서 시작</button>
          <button type="button" className="be-btn be-btn--sm" onClick={onPreview}>미리보기</button>
        </div>
      </div>
    </div>
  );
}

function Preview({ r }: { r: Row }) {
  const [lay, setLay] = useState<Awaited<ReturnType<typeof be.layout>> | null>(null);
  useEffect(() => { be.layout(r.id).then(setLay).catch(() => setLay(null)); }, [r.id]);
  const plan = useMemo(() => lay?.plan, [lay]);
  return (
    <div className="be-lightbox">
      {r.primary_cut_url ? <img src={r.primary_cut_url} alt={`${r.title} 주 컷`} /> : <div className="be-muted">아직 3D 조감도가 없어요</div>}
      {plan && <PlanCanvas plan={plan} items={lay?.layout?.items} groups={lay?.layout?.groups} width={760} height={300} />}
    </div>
  );
}
