/**
 * `/proposal/new` — 시작 방식이 정해지는 순간 제안서를 만든다(§3.1 · AC-002) → 그 시작 화면으로.
 *   ?start=rfp|works|reuse(&source=pr_…)  PR0 「시작하는 방법」 · 「복제해서 시작」
 *   ?handoff=sho_…(SP4) · ?handoff=vho_…(VP4) · ?handoff=hof_…&link=mi_…|ca_…(MI4 · CA5 — hof_ 는 분석 id 필요, 기능은 분석 id 접두사로) · ?sb=sb_…&rq=rq_…(SB4) · ?image_version=imv_…(IMG4)
 *   · ?link=<id>&feature=<서비스>  → start_mode=handoff → PR1
 * `/proposal/:id` — 제안서가 지금 있는 화면(「이어서 작성」 · 사이드바 항목, E2)으로.
 */
import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { createProposal, getProposal, qk, type Loose } from '../api/proposal';
import type { ProposalCreate } from '../api/types';

type CreateBody = Loose<ProposalCreate>;
import { errText } from '../api/http';
import { ErrorBand, LoadingCard, PrPage } from '../components/parts';
import { currentRoute, featureOfRef, handoffFeature, normalizeRoute, R } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

// 같은 주소로 두 번 만들지 않는다(StrictMode · 뒤로 가기)
const inflight = new Map<string, Promise<string>>();

function bodyFrom(sp: URLSearchParams): { body: CreateBody; next: 'customer' | 'rfp' | 'works' | 'reuse' } {
  const start = sp.get('start');
  if (start === 'rfp') return { body: { start_mode: 'rfp' }, next: 'rfp' };
  if (start === 'works') return { body: { start_mode: 'works' }, next: 'works' };
  if (start === 'reuse') return { body: { start_mode: 'reuse', source_proposal_id: sp.get('source') ?? undefined }, next: 'reuse' };
  const links: NonNullable<ProposalCreate['links']> = [];
  const handoff = sp.get('handoff');
  const link = sp.get('link');
  // 넘김 id 만으로 원본을 찾는 건 spec(sho_) · vp(vho_) 뿐 — mi · competitor(hof_)는 분석 id(?link=)를 같은 연결에 함께 보낸다([backend] 3차 요청 3)
  // 기능 = feature → 작업 id 접두사(ca_ · mi_ · be_ · sc_ …) → 넘김 id 접두사(hof_ 는 mi · competitor 공통 — 작업 id 로 가른다)
  if (handoff) links.push({ feature: handoffFeature(sp), ref_id: sp.get('ref') ?? link ?? '', handoff_id: handoff });
  else if (link) links.push({ feature: sp.get('feature') ?? featureOfRef(link) ?? link.split('_')[0], ref_id: link });
  const sb = sp.get('sb');
  if (sb) links.push({ feature: 'storyboard', ref_id: sb });
  const rq = sp.get('rq');
  const imv = sp.get('image_version');
  if (links.length || rq || imv) {
    return { body: { start_mode: 'handoff', links, rq_ref: rq ? { rq_id: rq } : undefined, image_version: imv ?? undefined }, next: 'customer' };
  }
  return { body: { start_mode: 'blank' }, next: 'customer' };
}

export function NewPage() {
  const [sp] = useSearchParams();
  const loc = useLocation();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useProposalShell({ title: '새 제안서', step: 1 });
  useEffect(() => {
    const key = `${loc.key}:${loc.search}:${tick}`;
    const { body, next } = bodyFrom(sp);
    let p = inflight.get(key);
    if (!p) {
      p = createProposal(body).then((pr) => { qc.setQueryData(qk.p(pr.id), pr); void qc.invalidateQueries({ queryKey: ['pr', 'list'] }); return pr.id; });
      inflight.set(key, p);
    }
    let alive = true;
    p.then((id) => {
      if (!alive) return;
      const src = sp.get('source');
      const to = next === 'rfp' ? R.rfp(id) : next === 'works' ? R.works(id) : next === 'reuse' ? `${R.reuse(id)}${src ? `?source=${encodeURIComponent(src)}` : ''}` : R.customer(id);
      nav(to, { replace: true });
    }).catch((e) => { inflight.delete(key); if (alive) setErr(errText(e)); });
    return () => { alive = false; };
  }, [loc.key, loc.search, sp, nav, qc, tick]);
  return <PrPage>{err ? <ErrorBand message={err} onRetry={() => { setErr(null); setTick((t) => t + 1); }} /> : <LoadingCard lines={3} />}</PrPage>;
}

export function OpenPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);
  useProposalShell({});
  useEffect(() => {
    if (!id) return;
    getProposal(id).then((p) => {
      const server = normalizeRoute(p.route);
      nav(server && server !== R.open(id) ? server : currentRoute(p), { replace: true });
    }).catch((e) => setErr(errText(e, '제안서를 찾을 수 없어요')));
  }, [id, nav]);
  return <PrPage>{err ? <ErrorBand message={err} onRetry={() => nav(R.list())} /> : <LoadingCard lines={4} />}</PrPage>;
}
