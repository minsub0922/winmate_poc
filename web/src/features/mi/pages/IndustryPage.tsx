/** MI1I — 업종 인사이트 프리셋 `/mi/new/industry?segment=` · `/mi/:id/industry` (§4.8) */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PathIcon, toast } from '@/ui';
import { createAnalysis, detectSegment, errText, patchAnalysis, qk, useAnalysis, useInsights, useSegments, type SegmentItem } from '../api';
import { useLastScreen } from '../hooks';
import { Agent, BigButton, Dock, Ic, MiPage, P, useMiShell } from '../parts';

const DEFAULT_ON = 4;

export function IndustryPage() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(id);
  useMiShell(a.data, 1);
  useLastScreen(id, 'industry');
  const segs = useSegments();
  const detect = useQuery({
    queryKey: ['mi', 'detect', id ?? ''],
    queryFn: () => detectSegment('', id),
    enabled: !!id,
    staleTime: 60_000,
  });
  const [sel, setSel] = useState<string | null>(sp.get('segment')?.toUpperCase() ?? null);
  const [q, setQ] = useState('');
  const [off, setOff] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);

  const items = segs.data?.items ?? [];
  // 처음 선택: ?segment= → (고정된 업종) → 감지 업종 → 첫 타일(FB)
  useEffect(() => {
    if (sel || !items.length) return;
    const pinned = a.data?.segment?.mode === 'pin' ? a.data.segment.code : null;
    const top = pinned || (id ? detect.data?.top : null);
    if (id && !pinned && detect.isLoading) return;
    setSel(top && items.some((s) => s.code === top) ? top : (items[0]?.code ?? 'FB'));
  }, [items, detect.data, detect.isLoading, a.data, id, sel]);

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return items;
    return items.filter((s) => [s.full, s.short, ...(s.aliases ?? [])].some((x) => x.toLowerCase().includes(t)));
  }, [items, q]);

  const ins = useInsights(sel);
  const reqs = (ins.data?.req_types ?? []).slice(0, 6);
  const on = (i: number) => (i < DEFAULT_ON) !== !!off[`${sel}:${i}`];
  const checked = reqs.filter((_, i) => on(i));
  const selItem: SegmentItem | undefined = items.find((s) => s.code === sel);
  const allCases = segs.data?.case_total ?? items.reduce((s, x) => s + (x.case_count ?? 0), 0);

  async function apply() {
    if (!sel) return;
    setBusy(true);
    const preset = { segment: sel, req_items: checked.map((r) => r.label) };
    try {
      let aid = id;
      if (!aid) {
        const created = await createAnalysis({ segment_pin: sel, preset });
        aid = created.id;
        qc.setQueryData([...qk.analysis(aid), null], created);
      } else {
        const res = await patchAnalysis(aid, { segment: { code: sel, mode: 'pin' }, preset });
        qc.setQueryData([...qk.analysis(aid), null], res);
      }
      void qc.invalidateQueries({ queryKey: qk.criteria(aid) });
      nav(`/mi/${aid}/scope`);
    } catch (e) {
      toast(errText(e));
    } finally {
      setBusy(false);
    }
  }

  const back = id ? `/mi/${id}/input` : '/mi/new';
  const det = detect.data;
  const detName = det?.top ? items.find((s) => s.code === det.top)?.full : null;
  const cust = det?.customer_name || a.data?.customer_name;
  return (
    <MiPage dock={
      <Dock title="업종 인사이트 프리셋" meta={`삼성 도입사례 ${allCases}건 · ${items.length}개 업종 · 1 / 3`}
        right={<Link to={back} className="mi-link" style={{ height: 28, padding: '0 10px' }}>직접 입력으로</Link>}>
        <div className="mi-preset">
          <div className="mi-preset__left">
            <div className="mi-searchsm">
              <Ic d={P.search} size={14} w={2} />
              <label htmlFor="mi-indq" className="wm-sr-only">업종 검색</label>
              <input id="mi-indq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="업종 검색 (예: 호텔, 무인 매장)" />
            </div>
            <div className="mi-tiles" role="radiogroup" aria-label="업종">
              {filtered.map((s) => (
                <button key={s.code} type="button" role="radio" aria-checked={s.code === sel} title={s.full} className="mi-tile"
                  onClick={() => { setSel(s.code); setOff({}); }}>
                  <span>{s.short}</span><b>{s.mapping === false && !s.case_count ? '준비 중' : `${s.case_count}건`}</b>
                </button>
              ))}
              {!filtered.length && <div className="mi-tiles__empty">맞는 업종이 없어요 · 범용으로 분석해요</div>}
            </div>
          </div>
          <div className="mi-ins" aria-live="polite">
            <div className="mi-ins__head">
              <span className="mi-ins__name">{ins.data?.full ?? selItem?.full ?? '—'}</span>
              <span className="mi-ins__badge">도입사례 {ins.data?.cases ?? selItem?.case_count ?? 0}건 기준</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div className="mi-ins__sec"><b>이 업종 고객이 요구한 것</b><span>분석에 넣을 항목 {checked.length}개</span></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {reqs.map((r, i) => {
                  const pct = ins.data?.cases ? Math.round((r.n / ins.data.cases) * 100) : 0;
                  return (
                    <button key={r.code + i} type="button" role="checkbox" aria-checked={on(i)} className="mi-req"
                      onClick={() => setOff((o) => ({ ...o, [`${sel}:${i}`]: !o[`${sel}:${i}`] }))}>
                      <span className="mi-req__box">{on(i) && <PathIcon d={P.check} size={9} strokeWidth={3.6} />}</span>
                      <span className="mi-req__label" title={r.label}>{r.label}</span>
                      <span className="mi-req__bar"><span style={{ width: `${pct}%` }} /></span>
                      <span className="mi-req__n">{r.n}건</span>
                    </button>
                  );
                })}
                {ins.isSuccess && !reqs.length && <span className="mi-note">사례 집계 준비 중</span>}
              </div>
            </div>
            <div className="mi-ins__lists">
              <div className="mi-ins__list">
                <b>많이 쓰인 제품</b>
                {(ins.data?.products ?? []).slice(0, 4).map((p) => <div key={p.name} className="mi-ins__item"><span>{p.name}</span><b>{p.n}건</b></div>)}
              </div>
              <div className="mi-ins__list">
                <b>많이 쓰인 솔루션</b>
                {(ins.data?.solutions ?? []).slice(0, 4).map((p) => <div key={p.name} className="mi-ins__item mi-ins__item--sol"><span>{p.name}</span><b>{p.n}건</b></div>)}
                {ins.isSuccess && !(ins.data?.solutions ?? []).length && <span className="mi-note">솔루션 없이 제품만 도입</span>}
              </div>
            </div>
          </div>
        </div>
        <div className="mi-apply">
          <div className="mi-apply__box">
            <b>적용하면</b>
            <span className="mi-apply__chip">고객 요구사항 ← 요구 {checked.length}개</span>
            <span className="mi-apply__chip">경쟁 비교 기준 ← 같은 {checked.length}개</span>
            <span className="mi-apply__chip">제안서 MI 레이아웃 ←<b>MI-{sel ?? 'XX'}-A · B · C</b></span>
          </div>
        </div>
        <div className="mi-dock__row mi-dock__row--between" style={{ gap: 12 }}>
          <span className="mi-note">사례 수는 도입사례 본문을 자동 분류한 값이에요. 업종 하나에 사례 하나씩 셉니다.</span>
          <div className="mi-row" style={{ gap: 8, flexShrink: 0 }}>
            <Link to={back} className="mi-btn">직접 입력</Link>
            <BigButton onClick={() => void apply()} busy={busy} disabled={!sel} testId="mi1i-apply">이 프리셋으로 분석 범위 선택</BigButton>
          </div>
        </div>
      </Dock>
    }>
      <Agent text="업종을 고르면 삼성 도입사례에서 그 업종 고객이 요구한 것과 많이 쓰인 제품 · 솔루션을 분석 출발점으로 채워 드려요. 고객사만의 요구사항은 다음 단계에서 더하거나 뺄 수 있어요.">
        {id && det?.top && detName && (
          <div className="mi-detect" data-testid="mi1i-detect">
            <span className="mi-detect__tag">업종 감지</span>
            <span className="mi-ell">{cust ? `${cust} → ` : ''}<b>{detName}</b>{det.basis ? ` · ${det.basis}` : ''}</span>
          </div>
        )}
      </Agent>
    </MiPage>
  );
}
