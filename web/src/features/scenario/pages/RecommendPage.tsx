/**
 * SC3R · 장면별 솔루션 추천(§4.8) — 장면마다 제품만 모습 · 근거(입력 인용 · 사례 수) · 추천 솔루션 동작 · 태그(꼭 필요 · 추천 · 선택) · 적용 토글,
 * 유형 전환 안내(WITHOUT → WITH 솔루션), 모두 적용, 제품만으로 생성 · 추천 적용 · 시나리오 생성(→ SC4G).
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx } from '@/ui';
import { useShellPage } from '@/shell';
import { ApiError, errMessage, scApi, type Recommendation, type Recommendations } from '../api';
import { qk, useInvalidate, useJobsPulse, useScenario } from '../hooks';
import { josa, route, SECTION, stepper, withJosa } from '../lib';
import { Btn, Card, Echo, Ico, Loading, NextButton, Note, P, Screen, W } from '../parts';

export default function RecommendPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const recs = useQuery({ queryKey: qk.recs(id), queryFn: () => scApi.recs(id), enabled: !!id, refetchInterval: (q) => (q.state.data?.status === 'computing' ? 1_500 : false) });
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  useJobsPulse([recs.data?.status === 'computing' ? recs.data.job_id : null], () => { void recs.refetch(); });

  // 처음 들어오면 추천을 계산한다(이미 있으면 그대로)
  useEffect(() => {
    if (!recs.data || started) return;
    if (recs.data.status === 'none' || recs.data.status === 'failed') {
      setStarted(true);
      scApi.computeRecs(id).then(() => recs.refetch()).catch((e) => setErr(errMessage(e)));
    }
  }, [recs.data, started, id]); // eslint-disable-line react-hooks/exhaustive-deps

  useShellPage({ section: SECTION, title: sc.data?.title ?? '', stepper: stepper(3), sidebarGroup: 'scenario' });
  if (sc.isLoading || recs.isLoading || !sc.data || !recs.data) return <Loading />;
  const s = sc.data;
  const r = recs.data;
  const computing = r.status === 'computing' || r.status === 'none';
  const items = r.items ?? [];
  const n = items.length || s.scene_count;
  const enteredWithout = (r.entered_with_type ?? s.type) === 'without';
  const ind = r.industry_name;
  const products = (s.product_picks ?? []).map((p) => (p.qty && p.qty > 1 ? `${p.label} ×${p.qty}` : p.label)).join(' · ');
  const required = r.required_nos ?? [];
  const reqList = required.length ? `장면 ${required.join(' · ')}` : '';
  const basis = ind ? `입력하신 시나리오 문장과 ${ind} 도입사례를 근거로` : '입력하신 시나리오 문장을 근거로';

  const setLocal = (next: Recommendations) => { recs.refetch(); return next; };
  const toggle = async (it: Recommendation) => {
    setErr(null);
    try { setLocal(await scApi.setRec(id, it.scene_id, !it.applied)); } catch (e) { setErr(errMessage(e)); }
  };
  const applyAll = async () => { try { setLocal(await scApi.applyAllRecs(id)); } catch (e) { setErr(errMessage(e)); } };
  const commit = async (mode: 'apply' | 'products_only') => {
    setBusy(mode); setErr(null);
    try {
      await scApi.commitRecs(id, mode);
      const g = await scApi.generate(id, 'all');
      await inv.sc(id);
      nav(route.generate(id, g.job_id));
    } catch (e) {
      if (e instanceof ApiError && e.code === 'GENERATION_IN_PROGRESS') {
        const fresh = await scApi.get(id).catch(() => null);
        if (fresh?.generation?.job_id) { nav(route.generate(id, fresh.generation.job_id)); return; }
      }
      setErr(errMessage(e)); setBusy(null);
    }
  };

  const applied = r.applied_count ?? 0;
  const sols = (r.applied_solutions ?? []).join(' · ');
  const off = r.off_nos ?? [];
  const willSwitch = enteredWithout && applied > 0;

  const dock = (
    <Card title="솔루션 · 제품" meta="3 / 4" testId="sc3r-card"
      right={(
        <div className="sc-row" style={{ gap: 8, whiteSpace: 'nowrap' }} data-testid="sc3r-type">
          <span className="sc-label">시나리오 유형</span>
          {willSwitch ? (
            <>
              <span className="sc-typepill sc-typepill--old">WITHOUT</span>
              <Ico d={P.arrow} size={14} sw={2.2} color="var(--wm-text-muted)" />
              <span className="sc-typepill">WITH 솔루션</span>
            </>
          ) : <span className={cx('sc-typepill', s.type === 'without' && applied === 0 && 'sc-typepill--plain')}>{s.type === 'with' || applied > 0 ? 'WITH 솔루션' : 'WITHOUT'}</span>}
        </div>
      )}>
      <div className="sc-card__sec">
        <div className="sc-infobox" data-testid="sc3r-info">
          <Ico d="M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 11v5 M12 8h.01" size={16} color="var(--wm-brand)" style={{ marginTop: 2 }} />
          {applied > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span>
                {enteredWithout ? <>적용하면 시나리오 유형이 <b>with 솔루션</b>으로 바뀌고 </> : '적용하면 '}
                {sols}{josa(sols, '이', '가')} 솔루션 칸에 들어가요.
              </span>
              <span style={{ color: 'var(--wm-text-muted)' }}>
                {off.length ? `${withJosa(`장면 ${off.join(' · ')}`, '은', '는')} 제품만 유지 · ` : ''}솔루션 장면은 결과에서 이야기 · 솔루션 동작 · 제품 활용으로 나뉩니다.
              </span>
            </div>
          ) : <span>제품만으로 만들어요</span>}
        </div>
      </div>
      {err && <div className="sc-card__sec"><Note tone="err" testId="sc3r-err">{err}</Note></div>}
      <div className="sc-card__foot sc-card__foot--split">
        <Link to={route.solutions(id)} className="sc-link" style={{ fontSize: 13, height: 36, padding: '0 8px' }} data-testid="sc3r-manual"><Ico d={P.pencil} size={14} sw={2.2} />솔루션 직접 고르기</Link>
        <div className="sc-row">
          <Btn to={s.via_timeline ? route.timeline(id) : route.input(id)} testId="sc3r-prev">이전</Btn>
          <Btn onClick={() => void commit('products_only')} disabled={!!busy || computing} testId="sc3r-products-only">제품만으로 생성</Btn>
          <NextButton onClick={() => void commit('apply')} busy={busy === 'apply'} disabled={computing || applied === 0} reason={computing ? '추천을 계산하는 중이에요' : '적용할 추천을 하나 이상 켜 주세요'}
            testId="sc3r-apply">추천 적용 · 시나리오 생성</NextButton>
        </div>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} tight testId="sc3r">
      <Echo testId="sc3r-echo"><b>{s.type_label}</b>{s.type === 'without' ? ' · 제품만' : ''}{products ? ` · ${products}` : ''}</Echo>
      <W testId="sc3r-w" extra={(
        <div className="sc-recs" data-testid="sc3r-list">
          <div className="sc-recs__head">
            <div style={{ fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap' }} data-testid="sc3r-head">
              장면별 솔루션 추천 <span style={{ color: 'var(--wm-text-muted)', fontWeight: 500 }}>· 적용 {applied} · 제품만 {r.product_only_count ?? 0}</span>
            </div>
            <div className="sc-row" style={{ gap: 10 }}>
              <span className="sc-label wm-ellipsis">근거 · 입력한 시나리오 문장{ind ? ` · ${ind} 도입사례` : ''}</span>
              <button type="button" className="sc-btn sc-btn--xs" onClick={() => void applyAll()} disabled={computing} data-testid="sc3r-apply-all">모두 적용</button>
            </div>
          </div>
          {computing && <div className="sc-recs__wait"><span className="wm-spinner" aria-hidden="true" />장면별로 어울리는 솔루션을 찾는 중이에요</div>}
          {!computing && items.map((it) => <RecRow key={it.scene_id} it={it} onToggle={() => void toggle(it)} />)}
        </div>
      )}>
        {s.type === 'with' && !enteredWithout
          ? '솔루션을 고르지 않아 장면별로 어울리는 솔루션을 추천합니다.'
          : reqList
            ? `제품만으로도 ${n}개 장면을 만들 수 있지만, ${withJosa(reqList, '은', '는')} 솔루션이 있어야 이야기가 완성돼요. ${basis} 장면별 솔루션을 추천합니다.`
            : `제품만으로도 ${n}개 장면을 만들 수 있어요. ${basis} 장면별 솔루션을 추천합니다.`}
      </W>
    </Screen>
  );
}

function RecRow({ it, onToggle }: { it: Recommendation; onToggle: () => void }) {
  const optional = it.tag === 'optional';
  const ev = it.evidence?.[0];
  return (
    <div className={cx('sc-rec', optional && !it.applied && 'sc-rec--off')} data-testid="sc3r-row" data-no={it.no} data-tag={it.tag}>
      <div style={{ width: 56, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span className="wm-num" style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--wm-brand)' }}>{it.time ?? ''}</span>
        <span style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>장면 {it.no}</span>
      </div>
      <div className="sc-rec__main">
        <div className="sc-rec__title">{it.title}</div>
        <div className="sc-rec__po">제품만 · {it.product_only_text}</div>
        <div className="sc-rec__ev" data-testid="sc3r-evidence">
          <b>근거</b>{' '}
          {ev?.kind === 'input_quote' && ev.text ? (
            <>입력 <span className="sc-quote">‘{ev.text}’</span>{ev.case_text ? ` ${ev.case_text}` : ''}</>
          ) : '제품만으로 장면이 완성돼요'}
        </div>
      </div>
      <div className="sc-rec__sol">
        <span className={cx('sc-solchip', !it.applied && 'sc-solchip--dash')} data-testid="sc3r-sol">{!it.applied ? `+ ${it.solution_label}` : it.solution_label}</span>
        <div className="sc-row" style={{ gap: 6, fontSize: 12, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>
          <span className={cx('sc-rtag', it.tag === 'required' && 'sc-rtag--req', optional && 'sc-rtag--opt')} data-testid="sc3r-tag">{it.tag_label}</span>
          <span className="wm-ellipsis">{optional ? '제품만으로 충분해요' : it.benefit}</span>
        </div>
      </div>
      <button type="button" className="sc-switch" aria-label={`장면 ${it.no} 추천 적용`} aria-pressed={it.applied} onClick={onToggle} data-testid="sc3r-toggle" />
    </div>
  );
}
