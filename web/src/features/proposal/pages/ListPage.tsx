/**
 * PR0 — 제안서 목록(§4.6, 보드 PR0). `GET /proposals?tab&q&owner&type&sort` → 요약 줄 · 상태 탭 · 표 · 행 버튼.
 * 쿼리: `?focus=CM&competitor=` (IMG3X 「Why Samsung 비교표로 보내기」) → 이어서 작성이 Why Samsung 섹션으로.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Icon, PathIcon } from '@/ui';
import { useShellPage } from '@/shell';
import { useProposalList, type ListParams } from '../api/proposal';
import { errText } from '../api/http';
import type { ProposalRow } from '../api/types';
import { ErrorBand, Segs } from '../components/parts';
import { normalizeRoute, R } from '../lib/routes';
import { rowView } from '../lib/format';
import { SECTION_NAME } from '../lib/useProposalShell';

const ICON = {
  blank: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M12 11v6 M9 14h6',
  rfp: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M12 18v-6 M9.5 14.5L12 12l2.5 2.5',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  copy: 'M8 8h12v12H8z M4 16V4h12',
  draft: 'M4 20h4L19 9l-4-4L4 16v4z',
  review: 'M4 5h16v11H9l-5 4V5z',
  done: 'M5 12l5 5L20 7',
};
const STARTS: Array<{ title: string; desc: string; icon: string; to: string; main?: boolean; testId: string }> = [
  { title: '빈 제안서', desc: '고객 정보부터 직접 입력', icon: ICON.blank, to: R.create(), main: true, testId: 'pr0-start-blank' },
  { title: 'RFP로 시작', desc: '파일을 올리면 고객 · 요구 · 일정 자동 채움', icon: ICON.rfp, to: R.create({ start: 'rfp' }), testId: 'pr0-start-rfp' },
  { title: '기존 작업에서 시작', desc: 'Storyboard · MI · 조감도 · 시나리오 연결', icon: ICON.link, to: R.create({ start: 'works' }), testId: 'pr0-start-works' },
  { title: '이전 제안서 복제', desc: '가져올 섹션만 골라 다시 쓰기', icon: ICON.copy, to: R.create({ start: 'reuse' }), testId: 'pr0-start-reuse' },
];
type Tab = 'all' | 'draft' | 'review' | 'done';
const TABS: Array<{ v: Tab; label: string }> = [{ v: 'all', label: '전체' }, { v: 'draft', label: '작성 중' }, { v: 'review', label: '검토 중' }, { v: 'done', label: '완료' }];
const OWNER = [{ v: 'all', label: '전체' }, { v: 'me', label: '나' }];
const TYPE = [{ v: '', label: '전체' }, { v: 'standard', label: '표준' }, { v: 'quickwin', label: '퀵윈(제품)' }, { v: 'solution', label: 'Solution형' }];
const SORT = [{ v: 'due_asc', label: '마감 임박순' }, { v: 'updated_desc', label: '최근 수정순' }];

function Filter({ k, value, options, onChange, testId }: { k: string; value: string; options: Array<{ v: string; label: string }>; onChange: (v: string) => void; testId: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);
  const cur = options.find((o) => o.v === value) ?? options[0];
  return (
    <div className="pr-filter" ref={ref}>
      <button type="button" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)} data-testid={testId}>
        <span className="pr-filter__k">{k}</span><span className="pr-filter__v">{cur.label}</span>
        <Icon name="chevronDown" size={12} color="var(--wm-text-muted)" strokeWidth={2.4} />
      </button>
      {open && (
        <div className="pr-menu" role="listbox" aria-label={k}>
          {options.map((o) => (
            <button key={o.v} type="button" role="option" aria-selected={o.v === value} onClick={() => { onChange(o.v); setOpen(false); }}>{o.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function actionOf(r: ProposalRow, focus: string | null): { label: string; to: string } {
  const route = normalizeRoute(r.action?.route || r.route);
  const label = r.action?.label ?? (r.status === 'done' ? '복제해서 시작' : r.status === 'review' ? '버전 보기' : '이어서 작성');
  if (focus === 'CM' && r.status !== 'done') return { label: '이어서 작성', to: R.section(r.id, 'why') };
  if (route) return { label, to: route };
  if (r.status === 'done') return { label, to: R.create({ start: 'reuse', source: r.id }) };
  if (r.status === 'review') return { label, to: R.versions(r.id) };
  return { label, to: R.open(r.id) };
}

export function ListPage() {
  const [sp] = useSearchParams();
  const focus = sp.get('focus');
  const competitor = sp.get('competitor');
  useShellPage({ section: SECTION_NAME, title: '제안서 목록', hasTask: false });
  const [tab, setTab] = useState<Tab>('all');
  const [q, setQ] = useState('');
  const [dq, setDq] = useState('');
  const [owner, setOwner] = useState('all');
  const [type, setType] = useState('');
  const [sort, setSort] = useState('due_asc');
  useEffect(() => { const t = window.setTimeout(() => setDq(q.trim()), 300); return () => window.clearTimeout(t); }, [q]);
  const params: ListParams = { tab, q: dq || undefined, owner: owner === 'all' ? undefined : owner, type: type || undefined, sort };
  const list = useProposalList(params);
  const rows = list.data?.items ?? [];
  const counts = list.data?.counts;
  const total = list.data?.total ?? counts?.all ?? rows.length;
  // 강조 행: 가장 최근에 연 제안서(제안) — 첫 「이어서 작성」 행
  const hl = rows.find((r) => r.status === 'draft')?.id;

  return (
    <div className="pr-list" data-testid="pr0">
      <div className="pr-list__head">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <h1 className="pr-list__h1">제안서</h1>
          <span className="pr-list__sum" data-testid="pr0-summary">
            {list.data?.summary_label || `전체 ${total}건 · 2주 안에 마감 ${list.data?.due_within_14d ?? 0}건 · 내 검토 차례 ${list.data?.my_review_turn ?? 0}건`}
          </span>
        </div>
        <Link to={R.create()} className="pr-new" data-testid="pr0-new"><Icon name="plus" size={16} strokeWidth={2.2} /><span>새 제안서</span></Link>
      </div>

      {focus === 'CM' && (
        <div className="pr-band" data-testid="pr0-focus">
          <Icon name="info" size={15} color="var(--wm-brand)" />
          <span className="pr-grow">{competitor ? `「${competitor}」 ` : ''}비교를 넣을 제안서를 고르세요 — 「이어서 작성」을 누르면 Why Samsung 섹션이 열려요.</span>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <span className="pr-label">시작하는 방법</span>
        <div className="pr-starts">
          {STARTS.map((s) => (
            <Link key={s.title} to={s.to} className={s.main ? 'pr-start pr-start--main' : 'pr-start'} data-testid={s.testId}>
              <span className="pr-start__icon"><PathIcon d={s.icon} size={17} /></span>
              <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
                <span className="pr-start__title">{s.title}</span>
                <span className="pr-start__desc">{s.desc}</span>
              </span>
              <Icon name="chevronRight" size={14} color="var(--wm-text-subtle)" strokeWidth={2.2} />
            </Link>
          ))}
        </div>
      </div>

      <div className="pr-row pr-row--between" style={{ height: 36 }}>
        <div className="pr-tabs" role="tablist" aria-label="상태">
          {TABS.map((t) => (
            <button key={t.v} type="button" role="tab" aria-selected={tab === t.v} onClick={() => setTab(t.v)} data-testid={`pr0-tab-${t.v}`}>
              {t.label}<span>{counts ? counts[t.v] ?? 0 : t.v === 'all' ? rows.length : '·'}</span>
            </button>
          ))}
        </div>
        <div className="pr-row">
          <label htmlFor="pr0-q" className="wm-sr-only">제안서 검색</label>
          <div className="pr-search">
            <Icon name="search" size={14} color="var(--wm-text-muted)" />
            <input id="pr0-q" placeholder="제안서 · 고객사 검색" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Filter k="담당" value={owner} options={OWNER} onChange={setOwner} testId="pr0-owner" />
          <Filter k="유형" value={type} options={TYPE} onChange={setType} testId="pr0-type" />
          <Filter k="정렬" value={sort} options={SORT} onChange={setSort} testId="pr0-sort" />
        </div>
      </div>

      {list.isError ? <ErrorBand message={errText(list.error)} onRetry={() => void list.refetch()} /> : (
        <div className="pr-table" data-testid="pr0-table">
          <div className="pr-trow pr-trow--head"><span>제안서</span><span>유형</span><span>진행</span><span>상태</span><span>마감</span><span>담당</span><span /></div>
          {list.isLoading && <div className="pr-empty">불러오는 중…</div>}
          {!list.isLoading && rows.length === 0 && <div className="pr-empty">{dq ? '검색 결과가 없어요' : '아직 제안서가 없어요. 「새 제안서」로 시작하세요.'}</div>}
          {rows.map((r) => {
            const v = rowView(r);
            const act = actionOf(r, focus);
            const primary = r.id === hl;
            return (
              <div key={r.id} className={primary ? 'pr-trow pr-trow--hl' : 'pr-trow'} data-testid="pr0-row" data-id={r.id}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                  <Link to={act.to} className="pr-trow__title">{v.title}</Link>
                  <div className="pr-row" style={{ gap: 6, minWidth: 0 }}>
                    <span className="pr-trow__sub">{v.sub}</span>
                    {r.badge?.label && <span className="pr-note-badge" data-testid="pr0-badge">{r.badge.label}</span>}
                  </div>
                </div>
                <span style={{ fontSize: 12.5, color: 'var(--wm-text-2)', whiteSpace: 'nowrap' }}>{v.type}</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
                  <Segs done={v.done} cur={v.cur} />
                  <span className="pr-trow__sub" style={{ fontSize: 11.5 }}>{v.progress}</span>
                </div>
                <span className={`pr-status pr-status--${r.status}`}>
                  <PathIcon d={ICON[r.status]} size={11} strokeWidth={2.4} />{v.statusLabel}
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span className="pr-due">{v.due}</span>
                  <span className={v.urgent ? 'pr-dday pr-dday--urgent' : 'pr-dday'}>{v.dday}</span>
                </div>
                <div className="pr-row" style={{ minWidth: 0 }}>
                  <span className="pr-owner">{v.initial}</span>
                  <span className="pr-ell" style={{ fontSize: 12.5 }}>{v.owner}</span>
                </div>
                <Link to={act.to} className={primary ? 'pr-act pr-act--primary' : 'pr-act'} data-testid="pr0-action">{act.label}</Link>
              </div>
            );
          })}
        </div>
      )}

      <div className="pr-list__foot">
        <span className="pr-row" style={{ gap: 6 }}><PathIcon d={ICON.copy} size={13} color="var(--wm-brand)" />완료한 제안서는 &apos;복제해서 시작&apos;으로 필요한 섹션만 골라 다시 쓸 수 있어요.</span>
        <span className="pr-num" style={{ fontWeight: 700 }}>{list.data?.range_label || (rows.length ? `1–${rows.length} / ${total}` : `0 / ${total}`)}</span>
      </div>
    </div>
  );
}
