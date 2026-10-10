/** SP0 — 이전 흐름 작업 목록(`/spec/legacy`, 06-spec §4.2 — 새 흐름 목록은 `/spec` = flow/FlowPages.tsx) */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import { Button, ErrorState, Icon, Input, Modal, PathIcon, Skeleton, cx, toast } from '@/ui';
import { archiveSheet, cloneSheet, errText, patchSheet, useSheetCache, useSheetList, type SheetListItem } from './api';
import { SECTION, StatusIcon, TYPE_ICON } from './ui';

const STARTS = [
  { title: '모델명으로 입력', desc: '모델명을 넣으면 카탈로그 스펙을 바로 가져와요', to: '/spec/legacy/new', base: true, icon: 'M4 7h16M4 12h10M4 17h7 M17 14l3 3-3 3' },
  { title: '제품 탐색에서 고르기', desc: '시리즈 폴더에서 여러 크기를 한 번에 담아요', to: '/spec/legacy/new?pop=product', icon: 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z' },
  { title: '조건으로 모델 찾기', desc: '크기 · 밝기 · 용도 · 설치 조건으로 후보를 비교해요', to: '/spec/legacy/new/find', icon: 'M4 5h16l-6 7v6l-4 2v-8L4 5z' },
  { title: '고객 요구 스펙으로 시작', desc: '규격서를 올리면 요구사항 대응표를 만들어요', to: '/spec/legacy/new/requirements', icon: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13l2 2 4-4' },
];
const TABS = [['all', '전체'], ['draft', '작성 중'], ['check', '확인 필요'], ['done', '완료']] as const;
const SORTS = [['updated_desc', '최근 수정순'], ['title', '이름순'], ['status', '상태순']] as const;
type Tab = (typeof TABS)[number][0];
type Sort = (typeof SORTS)[number][0];

export default function ListPage() {
  useShellPage({ section: SECTION, title: '작업 목록', hasTask: false });
  const [sp, setSp] = useSearchParams();
  const archived = sp.get('archived') === '1';
  const [tab, setTab] = useState<Tab>('all');
  const [q, setQ] = useState(sp.get('q') ?? '');
  const [dq, setDq] = useState(q);
  const [linked, setLinked] = useState(false);
  const [sort, setSort] = useState<Sort>('updated_desc');
  const [sortOpen, setSortOpen] = useState(false);
  useEffect(() => { const t = window.setTimeout(() => setDq(q.trim()), 300); return () => window.clearTimeout(t); }, [q]);
  const list = useSheetList({ tab, q: dq, linked, archived, sort });
  const nav = useNavigate();
  const data = list.data;
  const counts = data?.counts ?? { all: 0, draft: 0, check: 0, done: 0 };

  return (
    <div className="sp-list" data-testid="sp0">
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, letterSpacing: '-0.01em' }}>{archived ? '보관된 Spec 시트' : 'Spec 시트 작업'}</h1>
          <p style={{ margin: 0, fontSize: 13.5, color: 'var(--wm-text-muted)' }}>제품 스펙 비교표와 단일 제품 시트를 만들고, 제안서 '제품 스펙'으로 보냅니다.</p>
        </div>
        <Button h={40} variant="primary" icon={<Icon name="plus" size={15} strokeWidth={2.4} />} onClick={() => nav('/spec/legacy/new')}>새 Spec 시트</Button>
      </div>

      {!archived && (
        <div className="sp-starts" role="list" aria-label="시작 방법">
          {STARTS.map((s) => (
            <Link key={s.title} to={s.to} className="sp-start" role="listitem">
              <span className="sp-start__ic"><PathIcon d={s.icon} size={18} /></span>
              <span style={{ minWidth: 0 }}>
                <span className="sp-start__title">{s.title}{s.base && <span style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--wm-brand)', background: 'var(--wm-brand-50)', borderRadius: 999, padding: '1px 7px' }}>기본</span>}</span>
                <span className="sp-start__desc" style={{ display: 'block' }}>{s.desc}</span>
              </span>
            </Link>
          ))}
        </div>
      )}

      {data?.banner && !archived && (
        <div className="sp-banner" role="status" data-testid="sp0-banner">
          <Icon name="info" size={16} color="var(--wm-brand)" />
          <span className="sp-banner__text">{data.banner.text}</span>
          {data.banner.route && (
            <Link to={data.banner.route} className="sp-link" style={{ fontSize: 13 }}>변경 내용 보기<Icon name="chevronRight" size={13} strokeWidth={2.2} /></Link>
          )}
        </div>
      )}

      <div className="sp-tools">
        <div className="sp-prompt" style={{ flex: 'none', width: 280, height: 36, background: 'var(--wm-surface)', borderRadius: 10, padding: '0 12px' }}>
          <Icon name="search" size={15} color="var(--wm-text-subtle)" />
          <label htmlFor="sp0-q" className="wm-sr-only">작업 검색</label>
          <input id="sp0-q" value={q} placeholder="작업명 · 모델명 · 고객사 검색" onChange={(e) => setQ(e.target.value)} style={{ fontSize: 13 }} />
        </div>
        <div className="sp-chiprow" role="group" aria-label="상태">
          {TABS.map(([v, label]) => (
            <button key={v} type="button" className="sp-chip" aria-pressed={tab === v} onClick={() => setTab(v)}>
              {label}<span className="wm-num" style={{ fontWeight: 700 }}>{counts[v]}</span>
            </button>
          ))}
        </div>
        <span style={{ flex: 1 }} />
        <button type="button" className="sp-chip" aria-pressed={linked} onClick={() => setLinked((v) => !v)}>
          <PathIcon d="M3 4h18v12H3z M8 20h8 M12 16v4" size={13} />제안서에 쓴 시트만
        </button>
        <div style={{ position: 'relative' }}>
          <button type="button" className="sp-chip" style={{ borderRadius: 8 }} aria-haspopup="menu" aria-expanded={sortOpen} onClick={() => setSortOpen((v) => !v)}>
            <PathIcon d="M7 4v16M3 16l4 4 4-4M17 20V4M13 8l4-4 4 4" size={13} />{SORTS.find((s) => s[0] === sort)?.[1]}
          </button>
          {sortOpen && (
            <div className="sp-menu" role="menu" style={{ right: 0, top: 36 }}>
              {SORTS.map(([v, label]) => (
                <button key={v} type="button" role="menuitem" onClick={() => { setSort(v); setSortOpen(false); }}>{label}</button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="sp-tbl" role="table" aria-label="Spec 시트 작업">
        <div className="sp-tbl__head" role="row">
          <span role="columnheader">작업</span><span role="columnheader">제품</span><span role="columnheader">출력</span><span role="columnheader">상태</span>
          <span role="columnheader">연결된 제안서</span><span role="columnheader">수정</span><span />
        </div>
        {list.isLoading && Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="sp-tbl__row" style={{ cursor: 'default' }}><Skeleton h={20} /><Skeleton h={20} /><Skeleton h={16} /><Skeleton h={16} /><Skeleton h={16} /><Skeleton h={16} /><span /></div>
        ))}
        {list.isError && <div style={{ padding: 20 }}><ErrorState message="작업 목록을 불러오지 못했어요." onRetry={() => void list.refetch()} /></div>}
        {data && data.items.length === 0 && (
          <div style={{ padding: '28px 16px', textAlign: 'center', fontSize: 13, color: 'var(--wm-text-muted)', borderTop: '1px solid var(--wm-line)' }}>
            {dq ? `‘${dq}’에 맞는 작업이 없어요.` : '아직 Spec 시트 작업이 없어요. 위에서 시작 방법을 골라 주세요.'}
          </div>
        )}
        {data?.items.map((r) => <ListRow key={r.id} r={r} onChanged={() => void list.refetch()} />)}
        <div className="sp-tbl__foot">
          <span>{archived ? `보관된 작업 ${data?.total ?? 0}개` : `작업 ${counts.all}개 · 최근 30일`}</span>
          <span style={{ flex: 1 }} />
          <span>열면 마지막 단계에서 이어집니다</span>
          {archived
            ? <button type="button" className="sp-link" onClick={() => setSp({})}>작업 목록으로</button>
            : <button type="button" className="sp-link" onClick={() => setSp({ archived: '1' })}>보관된 작업 {data?.archived_count ?? 0}</button>}
        </div>
      </div>
    </div>
  );
}

function ListRow({ r, onChanged }: { r: SheetListItem; onChanged: () => void }) {
  const nav = useNavigate();
  const [menu, setMenu] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(r.title);
  const ref = useRef<HTMLDivElement>(null);
  const cache = useSheetCache();
  useEffect(() => {
    if (!menu) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setMenu(false); };
    window.addEventListener('mousedown', close);
    return () => window.removeEventListener('mousedown', close);
  }, [menu]);
  const open = () => nav(r.resume_route);
  const clone = async () => {
    try {
      const s = await cloneSheet(r.id);
      cache.put(s);
      nav(`/spec/${s.id}/products`);
    } catch (e) { toast(errText(e)); }
  };
  const archive = async () => {
    try { await archiveSheet(r.id); onChanged(); toast('보관했어요.'); } catch (e) { toast(errText(e)); }
  };
  const rename = async () => {
    try { await patchSheet(r.id, { title: name }); setRenaming(false); onChanged(); } catch (e) { toast(errText(e)); }
  };
  return (
    <div className="sp-tbl__row" role="row" tabIndex={0} data-testid="sp0-row" data-id={r.id} onClick={open}
      onKeyDown={(e) => { if (e.key === 'Enter') open(); }}>
      <div className="sp-tbl__title" role="cell">
        <span className="sp-tbl__ic" data-type={r.type_icon}><PathIcon d={TYPE_ICON[r.type_icon]} size={16} strokeWidth={1.9} /></span>
        <span style={{ minWidth: 0 }}>
          <div className="sp-tbl__name">{r.title}</div>
          <div className="sp-tbl__sub">{r.sub_line}</div>
        </span>
      </div>
      <div role="cell" style={{ display: 'flex', alignItems: 'center', minWidth: 0, overflow: 'hidden' }}>
        {r.model_chips.map((m) => <span key={m} className="sp-mchip wm-num">{m}</span>)}
        {(r.more_models ?? 0) > 0 && <span className="sp-mchip wm-num">+{r.more_models}</span>}
      </div>
      <span role="cell" className={cx(r.output_label === '정하지 않음' ? 'sp-muted' : '')} style={r.output_label === '정하지 않음' ? undefined : { color: 'var(--wm-text-2)' }}>{r.output_label}</span>
      <span role="cell"><StatusIcon ui={r.ui_status} text={r.status_text} /></span>
      <span role="cell" className={cx('wm-ellipsis', r.proposal_label === '연결 안 됨' && 'sp-muted')}>{r.proposal_label}</span>
      <span role="cell" style={{ fontSize: 12, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>{r.when_label}</span>
      <div role="cell" ref={ref} style={{ position: 'relative' }} onClick={(e) => e.stopPropagation()}>
        <button type="button" className="sp-icbtn" aria-label="더 보기" aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu((v) => !v)}
          style={{ color: 'var(--wm-text-subtle)' }}>
          <Icon name="more" size={14} />
        </button>
        {menu && (
          <div className="sp-menu" role="menu" style={{ right: 0, top: 30 }}>
            <button type="button" role="menuitem" onClick={open}>열기</button>
            <button type="button" role="menuitem" onClick={() => void clone()}>복제해서 새 버전</button>
            <button type="button" role="menuitem" onClick={() => { setMenu(false); setRenaming(true); }}>이름 바꾸기</button>
            <button type="button" role="menuitem" onClick={() => void archive()}>보관</button>
          </div>
        )}
        <Modal open={renaming} onClose={() => setRenaming(false)} title="이름 바꾸기" variant="dialog" width={420}
          footer={<><Button onClick={() => setRenaming(false)}>취소</Button><Button variant="primary" onClick={() => void rename()} disabled={!name.trim()}>저장</Button></>}>
          <Input value={name} onChange={(e) => setName(e.target.value)} aria-label="작업 이름" autoFocus />
        </Modal>
      </div>
    </div>
  );
}
