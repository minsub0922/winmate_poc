/**
 * PR1L — 기존 작업에서 시작(§4.9, 보드 PR1L, 1/6).
 * 같은 고객 작업(workspace 색인)을 체크로 연결 → 오른쪽 「연결하면 채워지는 것」(FillPreview: 고객 출처 · 추천 유형 · 섹션 8행)을 서버가 다시 계산.
 * 사이드바 작업을 목록에 끌어 놓아도 연결(on). `?check=<item_id>` = PR1 최근 Storyboard 카드에서 온 경우 그 작업을 켠 채로 연다.
 * 「연결 · 다음: 제안서 유형」 → `links:apply`(잡: 고객 정보 채움 · 섹션 연결) → stage=type → PR2.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, Modal, PathIcon, cx, toast, useDropTarget, type DragPayload } from '@/ui';
import { applyLinks, patchProposal, putLinks, qk, useProposal, useRelatedWorks } from '../api/proposal';
import { errText, isMissing, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { FillPreview, RelatedWork } from '../api/types';
import { Agent, Dock, ErrorBand, LoadingCard, NextButton, PrPage } from '../components/parts';
import { FEATURE_KEY, SRC_ICON } from '../lib/catalog';
import { isAhead, R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

const ICON_OF: Record<string, string> = { mi: 'mi', market: 'mi', storyboard: 'storyboard', birdseye: 'birdseye', scenario: 'scenario', image: 'image', spec: 'spec', vp: 'vp', competitor: 'competitor', requirements: 'requirements' };
const SIDEBAR_CODES = Object.keys(FEATURE_KEY).filter((c) => c !== 'PR');
const keyOf = (w: { feature: string; ref_id: string }) => `${w.feature}:${w.ref_id}`;

export function WorksPage() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const [scope, setScope] = useState<'customer' | 'all'>('customer');
  const [q, setQ] = useState('');
  const [qd, setQd] = useState('');
  useEffect(() => { const t = window.setTimeout(() => setQd(q.trim()), 300); return () => window.clearTimeout(t); }, [q]);
  const wq = useRelatedWorks(id, qd ? 'all' : scope, qd);
  const rw = wq.data;
  const [over, setOver] = useState<Record<string, boolean>>({});
  const [preview, setPreview] = useState<FillPreview | null>(null);
  const [onCount, setOnCount] = useState<number | null>(null);
  const [extra, setExtra] = useState<RelatedWork[]>([]);
  const [saving, setSaving] = useState(false);
  const [job, setJob] = useState<string | null>(null);
  const [help, setHelp] = useState(false);
  useProposalShell({ p, step: 1, oneClick: { from: 'customer' } });

  const ev = useJobEvents(job, {
    onDone: async (j) => {
      setJob(null);
      if (!id) return;
      if (j.status !== 'succeeded') { toast(jobErrText(j.error, '작업을 연결하지 못했어요. 다시 시도해 주세요')); return; }
      try { if (isAhead('type', p?.stage)) await patchProposal(id, { stage: 'type' }); } catch { /* 서버가 이미 옮겼으면 그대로 */ }
      void qc.invalidateQueries({ queryKey: qk.p(id) });
      nav(R.type(id));
    },
  });

  const works = useMemo(() => {
    const base = rw?.works ?? [];
    const seen = new Set(base.map(keyOf));
    return [...base, ...extra.filter((w) => !seen.has(keyOf(w)))];
  }, [rw, extra]);
  const isOn = (w: RelatedWork) => over[keyOf(w)] ?? w.on ?? w.default_on ?? false;
  const pv = preview ?? rw?.preview ?? null;
  const nOn = onCount ?? works.filter(isOn).length;

  const toggle = async (items: Array<{ feature: string; ref_id: string; on: boolean; title?: string | null }>) => {
    if (!id || !items.length) return;
    setOver((o) => { const n = { ...o }; items.forEach((it) => { n[keyOf(it)] = it.on; }); return n; });
    setSaving(true);
    try {
      const r = await putLinks(id, items.map((it) => ({ feature: it.feature, ref_id: it.ref_id, on: it.on })));
      if (r.preview) setPreview(r.preview);
      if (typeof r.on_count === 'number') setOnCount(r.on_count);
    } catch (e) {
      setOver((o) => { const n = { ...o }; items.forEach((it) => { delete n[keyOf(it)]; }); return n; });
      toast(errText(e));
    } finally { setSaving(false); }
  };

  // PR1 「채우기」에서 온 작업은 켠 채로
  const checked = useRef(false);
  useEffect(() => {
    const c = sp.get('check');
    if (!c || !rw || checked.current) return;
    checked.current = true;
    const w = works.find((x) => x.ref_id === c);
    if (w && !isOn(w)) void toggle([{ feature: w.feature, ref_id: w.ref_id, on: true }]);
    else if (!w) void toggle([{ feature: 'storyboard', ref_id: c, on: true }]).then(() => void wq.refetch());
    setSp((cur) => { const x = new URLSearchParams(cur); x.delete('check'); return x; }, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rw]);

  const drop = useDropTarget({
    accept: ['work_item'], acceptWork: SIDEBAR_CODES,
    onDrop: async (pl: DragPayload) => {
      const ref = pl.ref.replace(/^ws:item:/, '');
      const feature = FEATURE_KEY[pl.feature ?? ''] ?? (pl.feature ?? '').toLowerCase();
      const w = works.find((x) => x.ref_id === ref);
      if (!w) setExtra((xs) => [...xs, { feature, ref_id: ref, title: pl.label, tool_label: pl.sub.replace(/^사이드바 · /, ''), meta: '끌어 놓음', on: true, target_label: '' } as RelatedWork]);
      await toggle([{ feature: w?.feature ?? feature, ref_id: ref, on: true }]);
      void wq.refetch();
      return { note: '연결했어요' };
    },
    disabled: !!job,
  });

  const next = async () => {
    if (!id) return;
    try { const r = await applyLinks(id); setJob(r.job_id); }
    catch (e) {
      if (isMissing(e)) { toast(errText(e)); return; }
      toast(errText(e));
    }
  };

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p) return <PrPage><LoadingCard /></PrPage>;
  const customer = rw?.customer_name || p.customer?.name || '';
  const intro = rw?.intro || (customer
    ? `${customer}와 이어진 작업 ${rw?.work_count ?? works.length}건을 찾았어요. 연결하면 고객 정보는 Storyboard에서 채우고, 각 작업 결과는 맞는 섹션에 미리 넣어 둡니다. 연결은 섹션 작성 중에도 바꿀 수 있어요.`
    : `최근 작업 ${rw?.work_count ?? works.length}건을 찾았어요. 연결하면 고객 정보는 Storyboard에서 채우고, 각 작업 결과는 맞는 섹션에 미리 넣어 둡니다. 연결은 섹션 작성 중에도 바꿀 수 있어요.`);
  const counts = pv?.counts;
  const countsLabel = pv?.counts_label || (counts ? `채움 ${counts.full ?? 0} · 일부 ${counts.partial ?? 0} · 새로 작성 ${counts.new ?? 0}` : '');

  const dock = (
    <Dock testId="pr1l-dock" title="기존 작업에서 시작" meta={rw?.footer_label?.replace(/^기존 작업에서 시작 · /, '') || `작업 ${nOn}건 연결 · 1 / 6`}
      right={countsLabel ? <span className="pr-note" data-testid="pr1l-counts">{countsLabel}</span> : null}>
      <div className="pr-row" style={{ gap: 10, paddingBottom: 14 }}>
        <label htmlFor="pr1l-find" className="wm-sr-only">작업 찾기</label>
        <div className="pr-search pr-grow" style={{ height: 44, borderRadius: 12, background: 'var(--wm-bg)', width: 'auto' }}>
          <Icon name="search" size={15} color="var(--wm-text-muted)" />
          <input id="pr1l-find" placeholder="다른 작업 찾기 (작업 이름 · 고객사)" value={q} onChange={(e) => setQ(e.target.value)} data-testid="pr1l-find" />
        </div>
        <button type="button" className="pr-btn" onClick={() => nav(R.customer(p.id))} data-testid="pr1l-manual">직접 입력으로</button>
        <NextButton onClick={() => void next()} busy={!!job} disabled={nOn === 0 || saving} disabledReason="연결할 작업을 하나 이상 골라 주세요" testId="pr1l-next">연결 · 다음: 제안서 유형</NextButton>
      </div>
    </Dock>
  );

  return (
    <PrPage testId="pr1l" dock={dock} gap={14} tight>
      <Agent text={intro} testId="pr1l-agent">
        {job && <div className="pr-band pr-band--muted" data-testid="pr1l-applying">작업을 연결하고 고객 정보를 채우는 중이에요 · {Math.round(ev.progress)}%</div>}
        <div className="pr-works">
          <div role="group" aria-label="연결할 작업" className={cx('pr-workbox', drop.dragging && 'pr-workbox--drag', drop.over && 'pr-workbox--over')} {...drop.props} data-testid="pr1l-works">
            <div className="pr-workbox__head">
              <span style={{ fontSize: 12.5, fontWeight: 700 }}>연결할 작업 <span className="pr-brand pr-num" style={{ fontWeight: 800 }}>{nOn}</span><span className="pr-muted" style={{ fontWeight: 500 }}> / {rw?.work_count ?? works.length}</span></span>
              <div role="radiogroup" aria-label="고객 범위" className="pr-miniseg">
                <button type="button" role="radio" aria-checked={scope === 'customer' && !qd} onClick={() => setScope('customer')} data-testid="pr1l-scope-customer">{customer ? `${customer} 작업` : '이 고객 작업'}</button>
                <button type="button" role="radio" aria-checked={scope === 'all' || !!qd} onClick={() => setScope('all')} data-testid="pr1l-scope-all">모든 고객</button>
              </div>
            </div>
            {wq.isError ? <div style={{ padding: 14 }}><ErrorBand message={errText(wq.error)} onRetry={() => void wq.refetch()} /></div>
              : !rw ? <div style={{ padding: 14 }}><LoadingCard lines={4} /></div>
                : works.length === 0 ? <div className="pr-empty" style={{ padding: '28px 14px' }}>{qd ? `「${qd}」 작업을 찾지 못했어요` : '이어진 작업이 없어요. 「모든 고객」에서 찾거나 사이드바 작업을 끌어 놓아 주세요.'}</div>
                  : works.map((w) => {
                    const on = isOn(w);
                    return (
                      <label key={keyOf(w)} className={cx('pr-workrow', !on && 'pr-workrow--off')} data-testid="pr1l-work" data-on={on || undefined}>
                        <input type="checkbox" checked={on} aria-label={w.title} onChange={(e) => void toggle([{ feature: w.feature, ref_id: w.ref_id, on: e.target.checked }])} disabled={!!job} />
                        <span className={cx('pr-workrow__icon', on && 'pr-workrow__icon--on')}><PathIcon d={SRC_ICON[ICON_OF[w.feature] ?? 'file'] ?? SRC_ICON.file} size={15} color={on ? 'var(--wm-brand)' : 'var(--wm-text-muted)'} strokeWidth={2} /></span>
                        <span className="pr-colflex pr-grow" style={{ gap: 1 }}>
                          <span className="pr-ell" style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>{[w.tool_label, w.meta].filter(Boolean).join(' · ')}</span>
                          <span className="pr-ell pr-workrow__title">{w.title}</span>
                        </span>
                        <span className="pr-workrow__to">
                          <span style={{ fontSize: 10.5, color: 'var(--wm-text-subtle)' }}>넣을 곳</span>
                          {w.target_label ? <span className={cx('pr-tochip', !on && 'pr-tochip--off')}>{w.target_label}</span> : <span className="pr-subtle" style={{ fontSize: 11 }}>—</span>}
                        </span>
                      </label>
                    );
                  })}
            <div className="pr-workbox__foot">
              <Icon name="upload" size={13} color="var(--wm-text-muted)" />
              <span className="pr-grow">{drop.dragging ? '여기에 놓으면 연결돼요' : '사이드바의 작업을 이 목록에 끌어 놓아도 연결돼요'}</span>
              <button type="button" className="pr-link" style={{ fontSize: 12 }} onClick={() => setHelp(true)}>끌어 놓기 보기</button>
            </div>
          </div>
          <div className="pr-fillcard" data-testid="pr1l-preview">
            <span style={{ fontSize: 12.5, fontWeight: 700 }}>연결하면 채워지는 것</span>
            {!pv ? <LoadingCard lines={3} /> : (
              <>
                <div className="pr-fillcard__cust">
                  <span style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>고객 · 프로젝트{pv.customer_from ? ` · ${pv.customer_from.label}에서` : ''}</span>
                  <span style={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.5 }}>{pv.customer_summary || '연결한 작업에 고객 정보가 없어요'}</span>
                </div>
                {pv.recommended_type && (
                  <>
                    <div className="pr-fillcard__type" data-testid="pr1l-rec"><span style={{ fontSize: 11, color: 'var(--wm-text-muted)', flexShrink: 0 }}>추천 유형</span><b>{pv.recommended_type.name}</b></div>
                    <span style={{ fontSize: 11, color: 'var(--wm-text-muted)', lineHeight: 1.45 }}>{pv.recommended_type.reason}</span>
                  </>
                )}
                <div className="pr-colflex" style={{ gap: 0 }}>
                  {pv.sections.map((s) => (
                    <div key={s.key} className="pr-fillrow" data-state={s.state}>
                      <span className={cx('pr-filldot', `pr-filldot--${s.state}`)} />
                      <span className="pr-ell pr-grow" style={{ fontSize: 12 }}>{s.name}</span>
                      <span className={cx('pr-fillrow__src', s.state === 'new' && 'pr-subtle')}>{s.source_label || s.state_label}</span>
                    </div>
                  ))}
                </div>
                <div className="pr-row" style={{ gap: 10, fontSize: 11, color: 'var(--wm-text-muted)' }}>
                  <span className="pr-row" style={{ gap: 4 }}><span className="pr-filldot pr-filldot--full" />채움</span>
                  <span className="pr-row" style={{ gap: 4 }}><span className="pr-filldot pr-filldot--partial" />일부</span>
                  <span className="pr-row" style={{ gap: 4 }}><span className="pr-filldot pr-filldot--new" />새로 작성</span>
                </div>
              </>
            )}
          </div>
        </div>
      </Agent>
      <Modal open={help} onClose={() => setHelp(false)} title="작업 끌어 놓기" width={520}>
        <div className="pr-colflex" style={{ gap: 10, fontSize: 13.5, lineHeight: 1.65 }}>
          <span>왼쪽 사이드바 「작업 내역」에서 작업을 잡아 이 목록 위에 놓으면 그 작업이 연결돼요.</span>
          <span>섹션 작성 중에는 섹션 아래 드롭 영역에 놓으면, 그 섹션에 필요한 내용만 뽑아서 시트별로 어디에 넣을지 먼저 보여 드려요.</span>
          <span className="pr-muted" style={{ fontSize: 12.5 }}>제품 · 솔루션 · 이미지 · 사례는 상단 「제품 탐색」 같은 팝업에서 ⠿ 손잡이를 잡아 끌어 놓을 수 있어요.</span>
        </div>
      </Modal>
    </PrPage>
  );
}
