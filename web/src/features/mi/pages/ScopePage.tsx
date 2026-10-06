/** MI2 — 분석 범위 `/mi/:id/scope` (§4.6) */
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { cx, toast } from '@/ui';
import type { JobEvent } from '@/api/jobs';
import {
  AREAS, addCompetitor, errText, patchAnalysis, patchCompetitor, qk, startDesign, startRun, useAnalysis, useCompetitors, useDesign, useSegments, type Area,
} from '../api';
import { useJobWatch, useLastScreen } from '../hooks';
import { SCOPE_TITLE, runLabel } from '../lib';
import { Agent, BigButton, Dock, MiPage, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';

function descFor(area: Area, a: { customer_name?: string | null; scope_desc?: Record<string, string> }, comps: string[]): string {
  const d = a.scope_desc?.[area];
  if (d) return d;
  const cust = a.customer_name || '고객사';
  if (area === 'market') return '국내 업종 시장 규모·성장률, 도입 트렌드, 규제';
  if (area === 'customer') return `${cust}의 매장 전략, 최근 투자·확장 계획, 운영 구조(직영/가맹)`;
  if (area === 'user') return '현장 사용자 · 운영자 · 손님의 페르소나와 동선, 현재 불편 지점';
  return `요구사항 관련 경쟁사(${comps.join(' · ') || '자동 선정'}) 제품·솔루션 비교 후 삼성의 차별 강점 도출`;
}

export function ScopePage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 2);
  useLastScreen(aid, 'scope');
  const comps = useCompetitors(aid);
  const segs = useSegments();
  const d = useDesign(aid);
  const [areas, setAreas] = useState<Area[] | null>(null);
  const [designJob, setDesignJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const quiet = useRef(false);

  // 설계가 아직 범위를 안 정했으면(빈 범위 · 고정 아님) 기본값 4개 모두를 보여 준다 — 사람이 바꾸면 그때 고정(pin)
  useEffect(() => {
    if (!a.data || areas !== null) return;
    const sc = a.data.scope;
    setAreas(sc?.areas?.length || sc?.mode === 'pin' ? (sc.areas as Area[]) : [...AREAS]);
  }, [a.data, areas]);

  // MI1I 에서 왔으면 업종 · 요구는 고정 — 설계의 나머지는 조용히 채운다(묻지 않는다)
  useEffect(() => {
    if (!aid || !d.data || quiet.current) return;
    if (d.data.status === 'none' || (d.data.status === 'running' && d.data.job_id)) {
      quiet.current = true;
      if (d.data.status === 'running' && d.data.job_id) { setDesignJob(d.data.job_id); return; }
      startDesign(aid).then((r) => setDesignJob(r.job_id)).catch(() => undefined);
    }
  }, [aid, d.data]);
  useJobWatch(designJob, {
    onEvent: (e: JobEvent) => { if (e.type === 'awaiting_input') nav(`/mi/${aid}/design/industry`); },
    onDone: () => {
      setDesignJob(null);
      void qc.invalidateQueries({ queryKey: qk.analysis(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.competitors(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.criteria(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.design(aid ?? '') });
      setAreas(null);
    },
  });

  async function save(next: Area[]) {
    setAreas(next);
    if (!aid) return;
    try {
      const res = await patchAnalysis(aid, { scope: { areas: next, mode: 'pin' } });
      qc.setQueryData([...qk.analysis(aid), null], res);
      void qc.invalidateQueries({ queryKey: qk.design(aid) });
    } catch (e) { toast(errText(e)); }
  }
  const toggle = (x: Area) => {
    const cur = areas ?? [];
    void save(cur.includes(x) ? cur.filter((y) => y !== x) : AREAS.filter((y) => cur.includes(y) || y === x));
  };

  async function addComp(e: KeyboardEvent<HTMLInputElement>) {
    if (e.nativeEvent.isComposing || e.key !== 'Enter' || !aid) return;
    const n = name.trim();
    if (!n) return;
    e.preventDefault();
    try {
      await addCompetitor(aid, n);
      setName('');
      void qc.invalidateQueries({ queryKey: qk.competitors(aid) });
    } catch (err) { toast(errText(err)); }
  }
  async function removeComp(id: string) {
    if (!aid) return;
    try {
      await patchCompetitor(aid, id, { removed: true });
      void qc.invalidateQueries({ queryKey: qk.competitors(aid) });
    } catch (e) { toast(errText(e)); }
  }

  async function run() {
    if (!aid) return;
    setBusy(true);
    try {
      await startRun(aid, { mode: 'full' });
      nav(`/mi/${aid}/run`);
    } catch (e) {
      if ((e as { code?: string }).code === 'RUN_IN_PROGRESS') nav(`/mi/${aid}/run`);
      else toast(errText(e));
    } finally { setBusy(false); }
  }

  const sel = areas ?? [];
  const live = comps.data?.items ?? [];
  const segCode = a.data?.segment?.code;
  const segShort = segCode ? (segCode === 'GEN' ? '범용' : segs.data?.items.find((s) => s.code === segCode)?.short ?? segCode) : null;
  const designing = !!designJob;
  return (
    <MiPage gap22 dock={
      <Dock title="분석 범위" meta={`복수 선택 · ${sel.length}개 선택됨 · 2 / 3`}
        right={<button type="button" className="mi-link" style={{ height: 28, padding: '0 10px' }} onClick={() => void save(sel.length ? [] : [...AREAS])}>
          {sel.length ? '모두 해제' : '모두 선택'}</button>}>
        <div className="mi-scope">
          {AREAS.map((x) => {
            const on = sel.includes(x);
            return (
              <label key={x} className={cx('mi-scope__card', on && 'mi-scope__card--on')} data-area={x}>
                <input type="checkbox" checked={on} onChange={() => toggle(x)} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div className="mi-scope__title">{SCOPE_TITLE[x]}</div>
                  <div className="mi-scope__desc">{a.data ? descFor(x, a.data, live.map((c) => c.export_display || c.display)) : ''}</div>
                </div>
              </label>
            );
          })}
        </div>
        {sel.includes('competitor') && (
          <div className="mi-compchips">
            <button type="button" className="mi-compchips__label" onClick={() => nav(`/mi/${aid}/competitors`)}>경쟁사 지정</button>
            {live.map((c) => (
              <span key={c.id} className="mi-compchip">{c.export_display || c.display}
                <button type="button" aria-label={`경쟁사 ${c.letter} 빼기`} onClick={() => void removeComp(c.id)}>×</button>
              </span>
            ))}
            {designing && <Spin size={14} />}
            <label htmlFor="mi-comp" className="wm-sr-only">경쟁사 추가</label>
            <input id="mi-comp" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => void addComp(e)} placeholder="경쟁사 추가…" />
          </div>
        )}
        <div className="mi-dock__row mi-dock__row--end">
          <SecButton to={`/mi/${aid}/input`}>이전</SecButton>
          <BigButton onClick={() => void run()} busy={busy} disabled={!sel.length || designing} testId="mi2-run"
            reason={!sel.length ? '분석할 범위를 하나 이상 골라 주세요' : '설계를 마치는 중이에요'}>{runLabel(sel.length || 1)}</BigButton>
        </div>
      </Dock>
    }>
      {a.data && (a.data.customer_name || segShort || a.data.req_summary) && (
        <UserBubble>
          <b>{[a.data.customer_name, segShort].filter(Boolean).join(' · ')}</b>
          {a.data.req_summary ? ` · ${a.data.req_summary}` : ''}
        </UserBubble>
      )}
      <Agent text="분석할 범위를 골라주세요. 4개 모두 선택하면 약 3~4분이 걸리고, 결과는 탭으로 나뉘어 제안서 근거 자료로 바로 쓸 수 있습니다." />
    </MiPage>
  );
}
