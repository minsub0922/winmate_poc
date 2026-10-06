/**
 * IMG0 · 작업 목록 · 갤러리(§4.1) — 시작 버튼 3 · 작업 목록(최근 수정순 · 검색 · 상태 배지) · 다른 기능에서 요청한 이미지 ·
 * 갤러리(내 생성 이미지 · 유형 칩 · 고객사 · 비율 · 제안서 사용 · 생성 중 타일 · 다중 선택 바).
 * 진행 갱신: 진행 중 run 의 jobs SSE + 15초 폴링.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx, ErrorState, Icon, Img, Skeleton, Spinner } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, img, type ImageTile } from '../api';
import { CountPill, Dropdown, Ico, PATH, StatusPill } from '../components';
import { useInvalidate, useJobsPulse } from '../hooks';
import { route, SECTION } from '../lib';

const TYPE_CHIPS: Array<{ value: string; label: string }> = [
  { value: '', label: '전체' }, { value: 'space', label: '공간' }, { value: 'background', label: '배경' }, { value: 'scenario', label: '시나리오' }, { value: 'composite', label: '제품 합성' },
];
const RUNNING = new Set(['waiting', 'composing', 'rendering', 'qc']);

export default function ListPage() {
  const nav = useNavigate();
  const inv = useInvalidate();
  const [wq, setWq] = useState('');
  const [dwq, setDwq] = useState('');
  const [gq, setGq] = useState('');
  const [dgq, setDgq] = useState('');
  const [kind, setKind] = useState('');
  const [customer, setCustomer] = useState('');
  const [aspect, setAspect] = useState('');
  const [usage, setUsage] = useState<'' | 'yes' | 'no'>('');
  const [sel, setSel] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  useEffect(() => { const t = window.setTimeout(() => setDwq(wq), 250); return () => window.clearTimeout(t); }, [wq]);
  useEffect(() => { const t = window.setTimeout(() => setDgq(gq), 250); return () => window.clearTimeout(t); }, [gq]);

  const works = useQuery({ queryKey: ['image', 'works', dwq], queryFn: () => img.works(dwq), refetchInterval: 15_000 });
  const filters = { kind: kind || undefined, customer: customer || undefined, aspect: aspect || undefined, in_proposal: usage ? usage === 'yes' : undefined, q: dgq || undefined };
  const gallery = useQuery({ queryKey: ['image', 'gallery', filters], queryFn: () => img.images({ ...filters, limit: 60 }), refetchInterval: 15_000 });
  const allTiles = useQuery({ queryKey: ['image', 'gallery', 'all'], queryFn: () => img.images({ limit: 100 }), staleTime: 30_000 });
  const reqs = useQuery({ queryKey: ['image', 'requests'], queryFn: img.requests, staleTime: 15_000 });
  const assets = useQuery({ queryKey: ['image', 'assets-count'], queryFn: () => img.refSearch({ tab: 'kb', limit: 1 }), staleTime: 300_000, retry: 0 });
  const jobIds = (works.data?.items ?? []).map((w) => w.run?.job_id).filter(Boolean);
  useJobsPulse(jobIds, () => { void works.refetch(); void gallery.refetch(); });

  useShellPage({
    section: SECTION, title: '작업 목록 · 갤러리', hasTask: false, sidebarGroup: 'image',
    onAttach: (images) => {
      const refs = images.map((i) => String(i.ref ?? '')).filter(Boolean).slice(0, 3);
      nav(refs.length ? `/image/new/references?refs=${encodeURIComponent(refs.join(','))}` : '/image/new/references');
    },
  });

  const tiles = gallery.data?.items ?? [];
  const customers = useMemo(() => Array.from(new Set((allTiles.data?.items ?? []).map((t) => t.customer_short).filter(Boolean) as string[])), [allTiles.data]);
  const selTiles = tiles.filter((t) => sel.includes(t.id));
  const toggle = (t: ImageTile) => setSel(sel.includes(t.id) ? sel.filter((x) => x !== t.id) : [...sel, t.id]);

  const bulkDownload = async () => {
    const vids = selTiles.map((t) => t.current_version_id).filter(Boolean) as string[];
    if (!vids.length) return;
    setBusy('dl'); setMsg({ text: '선택한 시안을 묶는 중이에요', ok: true });
    try {
      let out = await img.bulkExport(vids);
      for (let i = 0; i < 90 && out.status !== 'done' && out.status !== 'failed'; i++) {
        await new Promise((r) => setTimeout(r, 1_000));
        out = await img.exportStatus(out.export_id);
      }
      if (out.status === 'done' && out.download_url) { window.location.assign(out.download_url); setMsg({ text: `${out.filename} 파일을 만들었어요`, ok: true }); }
      else setMsg({ text: '파일을 만들지 못했어요 · 다시 시도해 주세요', ok: false });
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const bulkVariants = async () => {
    if (!selTiles.length) return;
    setBusy('var'); setMsg(null);
    try {
      for (const t of selTiles) await img.variants(t.id, { count: 4, axis: 'any' });
      const first = selTiles[0];
      nav(route.variants(first.work_id, first.id));
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const toProposal = () => {
    const [first, ...rest] = selTiles;
    if (!first) return;
    nav(`${route.exportTo(first.work_id, first.id)}${rest.length ? `?also=${rest.map((t) => t.id).join(',')}` : ''}`);
  };
  const startRequest = async (id: string) => {
    setBusy(`req:${id}`);
    try { const st = await img.startRequest(id); void inv.works(); nav(st.route); } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };

  const totals = works.data?.totals;
  const wrows = works.data?.items ?? [];
  const requests = reqs.data?.items ?? [];
  const nothing = !works.isLoading && !gallery.isLoading && wrows.length === 0 && tiles.length === 0 && !dgq && !kind && !customer && !aspect && !usage;
  const startButtons = (
    <>
      <Link to="/image/new/composite" className="img-startbtn"><Ico d={PATH.camera} size={16} color="var(--wm-text-muted)" />현장 사진에 제품 합성</Link>
      <Link to="/image/new/references" className="img-startbtn"><Icon name="image" size={16} color="var(--wm-text-muted)" />참조 이미지로 시작</Link>
      <Link to="/image/new" className="img-startbtn img-startbtn--primary"><Icon name="plus" size={16} strokeWidth={2.2} />새 이미지 만들기</Link>
    </>
  );
  return (
    <section className="img-list" data-testid="img0">
      <div className="img-list__head">
        <div style={{ minWidth: 0 }}>
          <h1 className="img-list__title">이미지 생성</h1>
          <div className="img-list__desc" data-testid="img0-totals">
            내 작업 <b>{totals?.works ?? 0}</b>개 · 생성 이미지 <b>{totals?.images ?? 0}</b>장 · 결과를 다시 고치거나 제안서에 바로 넣을 수 있어요
          </div>
        </div>
        <div className="img-row">{startButtons}</div>
      </div>
      <div className="img-list__body">
        <div className="img-works">
          <div className="img-works__head">
            <span className="img-works__title">작업 목록 <CountPill n={totals?.works ?? 0} /></span>
            <span className="img-sort">최근 수정순<Icon name="chevronDown" size={12} strokeWidth={2.4} /></span>
          </div>
          <div style={{ padding: '0 16px 10px 16px' }}>
            <div className="wm-search" style={{ height: 36 }}>
              <label htmlFor="img-wq" className="wm-sr-only">작업 검색</label>
              <Icon name="search" size={14} color="var(--wm-text-muted)" />
              <input id="img-wq" value={wq} onChange={(e) => setWq(e.target.value)} placeholder="작업 · 고객사 검색" autoComplete="off" />
            </div>
          </div>
          <div className="img-works__list" data-testid="img0-works">
            {works.isLoading && [0, 1, 2, 3].map((i) => <div key={i} className="img-workrow"><Skeleton w={64} h={48} /><div style={{ flex: 1 }}><Skeleton h={14} w="70%" /><Skeleton h={12} w="50%" style={{ marginTop: 6 }} /></div></div>)}
            {works.isError && <ErrorState message="목록을 불러오지 못했어요" onRetry={() => works.refetch()} />}
            {!works.isLoading && !works.isError && wrows.length === 0 && <div className="img-hint" style={{ padding: '18px 16px' }}>{dwq ? '맞는 작업이 없어요' : '아직 작업이 없어요'}</div>}
            {wrows.map((w) => (
              <Link key={w.id} to={w.route} className="img-workrow" data-testid="img0-work">
                <span className="img-workrow__thumb">
                  {w.thumb_url ? <Img src={w.thumb_url} alt={w.title} /> : w.run ? <Spinner label="생성 중" /> : <Icon name="image" size={18} color="var(--wm-text-subtle)" />}
                </span>
                <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span className="img-row"><span className="img-workrow__title">{w.title}</span><span className="img-workrow__time">{w.time}</span></span>
                  <span className="img-workrow__meta">{w.meta}</span>
                  <span style={{ display: 'flex', marginTop: 2 }}><StatusPill badge={w.status} /></span>
                </span>
              </Link>
            ))}
          </div>
          {requests.length > 0 && (
            <div className="img-reqs" data-testid="img0-requests">
              <div className="img-row" style={{ justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12.5, fontWeight: 700 }}>다른 기능에서 요청한 이미지</span>
                <CountPill n={requests.length} brand />
              </div>
              {requests.map((r) => (
                <div key={r.id} className="img-req" data-testid="img0-request">
                  <span className="img-req__icon"><Ico d={r.from_service === 'scenario' ? PATH.play : PATH.present} size={14} /></span>
                  <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                    <span className="wm-ellipsis" style={{ fontSize: 12.5, fontWeight: 600, lineHeight: '17px' }}>{r.title}</span>
                    <span className="wm-ellipsis" style={{ fontSize: 11, lineHeight: '15px', color: 'var(--wm-text-muted)' }}>{r.from_label}</span>
                  </span>
                  <button type="button" className="img-req__make" disabled={busy === `req:${r.id}`} onClick={() => void startRequest(r.id)}>
                    {r.status === 'in_progress' && r.work_id ? '이어서' : '만들기'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="img-gal">
          <div className="img-gal__tabs">
            <div role="tablist" aria-label="이미지 출처" style={{ display: 'flex', gap: 4, height: 48 }}>
              <button type="button" role="tab" aria-selected className="img-gal__tab">내 생성 이미지 <span data-testid="img0-mine-count">{gallery.data?.total ?? 0}</span></button>
              <button type="button" role="tab" aria-selected={false} className="img-gal__tab" onClick={() => nav('/image/new/references')}>
                사내 자산{assets.data ? <span>{assets.data.total}</span> : null}
              </button>
            </div>
            <div className="wm-search" style={{ width: 230, flex: '0 0 230px', height: 32 }}>
              <label htmlFor="img-gq" className="wm-sr-only">이미지 검색</label>
              <Icon name="search" size={13} color="var(--wm-text-muted)" />
              <input id="img-gq" value={gq} onChange={(e) => setGq(e.target.value)} placeholder="이미지 · 고객사 검색" autoComplete="off" />
            </div>
          </div>
          <div className="img-gal__filters">
            <div className="img-row" role="group" aria-label="유형" style={{ gap: 6 }}>
              {TYPE_CHIPS.map((c) => (
                <button key={c.value} type="button" className={cx('img-pill', kind === c.value && 'img-pill--on')} aria-pressed={kind === c.value} onClick={() => setKind(c.value)}>{c.label}</button>
              ))}
            </div>
            <span className="img-vsep" style={{ height: 18 }} />
            <Dropdown label="고객사 전체" value={customer} onChange={setCustomer} options={[{ value: '', label: '고객사 전체' }, ...customers.map((c) => ({ value: c, label: c }))]} />
            <Dropdown label="비율" value={aspect} onChange={setAspect} options={[{ value: '', label: '비율 전체' }, ...['16:9', '4:3', '1:1', '9:16'].map((a) => ({ value: a, label: a }))]} />
            <Dropdown label="제안서 사용" value={usage} onChange={(v) => setUsage(v as '' | 'yes' | 'no')} options={[{ value: '', label: '제안서 사용 전체' }, { value: 'yes', label: '제안서 사용 중' }, { value: 'no', label: '사용 안 함' }]} />
            <span style={{ flex: 1 }} />
            <span className="img-sort">최근 생성순<Icon name="chevronDown" size={11} strokeWidth={2.4} /></span>
          </div>
          {gallery.isError ? (
            <div className="img-center"><ErrorState message="목록을 불러오지 못했어요" onRetry={() => gallery.refetch()} /></div>
          ) : nothing ? (
            <div className="img-center" style={{ flexDirection: 'column', gap: 14 }} data-testid="img0-empty">
              <strong>아직 만든 이미지가 없어요</strong>
              <div className="img-row">{startButtons}</div>
            </div>
          ) : (
            <div className="img-gal__grid" data-testid="img0-gallery">
              {gallery.isLoading && Array.from({ length: 9 }).map((_, i) => <div key={i} className="img-tile"><Skeleton h={120} r={10} /><Skeleton h={13} w="60%" /></div>)}
              {!gallery.isLoading && tiles.length === 0 && <div className="img-hint" style={{ gridColumn: '1 / -1', padding: 20, textAlign: 'center' }}>맞는 이미지가 없어요</div>}
              {tiles.map((t) => <Tile key={t.id} t={t} selected={sel.includes(t.id)} onToggle={() => toggle(t)} />)}
            </div>
          )}
          {msg && <div className={cx('img-askline', !msg.ok && 'img-err')} style={{ padding: '6px 18px' }} role="status">{busy === 'dl' ? <Spinner /> : <Icon name={msg.ok ? 'check' : 'info'} size={13} />}{msg.text}</div>}
          {sel.length > 0 && (
            <div className="img-selbar" data-testid="img0-selbar">
              <span className="img-tile__check" aria-hidden style={{ position: 'static', background: 'var(--wm-brand)', borderColor: 'var(--wm-brand)' }}><Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} /></span>
              <span style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap' }}><span className="wm-num">{sel.length}</span>장 선택됨</span>
              <button type="button" className="img-sort" style={{ border: 'none', background: 'transparent' }} onClick={() => setSel([])}>선택 해제</button>
              <span style={{ flex: 1 }} />
              <button type="button" className="wm-btn wm-btn--h36" disabled={!!busy} onClick={() => void bulkDownload()}><Icon name="download" size={14} />다운로드</button>
              <button type="button" className="wm-btn wm-btn--h36" disabled={!!busy} onClick={() => void bulkVariants()}>변형 만들기</button>
              <button type="button" className="wm-btn wm-btn--h36 wm-btn--primary" onClick={toProposal}>제안서에 넣기<Icon name="arrowRight" size={14} strokeWidth={2.2} /></button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function Tile({ t, selected, onToggle }: { t: ImageTile; selected: boolean; onToggle: () => void }) {
  const gen = RUNNING.has(t.status) && !!t.run_route;
  const done = t.progress_done ?? 0; const total = t.progress_total ?? 0;
  return (
    <div className={cx('img-tile', selected && 'img-tile--sel', gen && 'img-tile--gen')} data-testid="img0-tile" data-state={gen ? 'running' : t.status}>
      <div className="img-tile__frame">
        {gen ? (
          <Link to={t.run_route!} className="img-tile__gen" data-testid="img0-tile-gen">
            <b>생성 중 <span className="wm-num">{done} / {total}</span></b>
            <span className="img-bar"><span style={{ width: `${total ? (done / total) * 100 : 0}%` }} /></span>
            <em>진행 보기</em>
          </Link>
        ) : (
          <>
            <Img src={t.thumb_url} alt={t.title} />
            <Link to={t.route} className="img-tile__open" aria-label={`${t.title} 열기`} />
            <button type="button" role="checkbox" aria-checked={selected} aria-label={`${t.title} 선택`} className="img-tile__check" onClick={onToggle}>
              {selected && <Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} />}
            </button>
            {t.used_in_count > 0 && <span className="img-tile__badge"><Ico d={PATH.present} size={10} sw={2.6} />제안서 사용 중</span>}
            <div className="img-tile__hover">
              <Link to={route.edit(t.work_id, t.id)} className="img-tile__act">부분 수정</Link>
              <Link to={route.variants(t.work_id, t.id)} className="img-tile__act">변형</Link>
              <Link to={route.exportTo(t.work_id, t.id)} className="img-tile__act">내보내기</Link>
            </div>
          </>
        )}
      </div>
      <Link to={gen ? t.run_route! : t.route} className="img-tile__title">{t.title}</Link>
      <div className="img-tile__meta">{t.meta}</div>
    </div>
  );
}
