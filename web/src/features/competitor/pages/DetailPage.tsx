/** CA4D — 경쟁사 상세(§4.13): 포지셔닝 · 항목 6 · 출처 요약 · `출처 · 근거 보기`(오른쪽 패널) · `이 경쟁사 더 찾기`. */
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useJob } from '@/api/jobs';
import { Button, Icon } from '@/ui';
import { errText, qk, research, useAnalysis, useDetail } from '../api';
import { useCaShell } from '../hooks';
import { Band, BigButton, CaPage, ErrorCol, FootBar, Letter, LoadingCol } from '../parts';
import { EvidencePanel } from './EvidencePanel';

const VS_CLASS: Record<string, string> = { better: 'ca-v ca-v--up ca-v--lg', similar: 'ca-v ca-v--eq ca-v--lg', worse: 'ca-v ca-v--dn ca-v--lg' };

export function DetailPage() {
  const { id: aid = '', cmp = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const aq = useAnalysis(aid);
  const dq = useDetail(aid, cmp);
  const d = dq.data;
  useCaShell({ aid, title: aq.data?.title, current: 4, added: aq.data?.added_refs });
  const [panel, setPanel] = useState<{ fact?: string | null } | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const runningJob = job ?? (d?.research?.running ? d.research.job_id ?? null : null);
  useJob(runningJob, {
    onDone: (j) => {
      setJob(null);
      if (j.status === 'failed') setErr(j.error?.message || '더 찾지 못했어요');
      void qc.invalidateQueries({ queryKey: ['ca'] });
    },
  });

  if (dq.isLoading || aq.isLoading) return <LoadingCol lines={6} />;
  if (dq.isError || !d) {
    return <ErrorCol message="이 경쟁사는 아직 분석 결과가 없어요" onRetry={() => nav(`/competitor/${aid}/result`)} />;
  }

  async function more() {
    setBusy(true);
    setErr(null);
    try {
      const r = await research(aid, cmp);
      setJob(r.job_id);
      void qc.invalidateQueries({ queryKey: qk.detail(aid, cmp) });
    } catch (e) {
      setErr(errText(e, '더 찾지 못했어요'));
    } finally {
      setBusy(false);
    }
  }

  const h = d.header;
  const running = !!runningJob;
  return (
    <CaPage>
      <div className="ca-head" style={{ gap: 8 }}>
        <Link to={`/competitor/${aid}/result`} className="ca-uplink"><Icon name="chevronLeft" size={12} strokeWidth={2.6} />한눈에</Link>
        <div className="ca-dhead">
          <Letter letter={h.letter} size={36} />
          <h1 className="ca-title">{h.display}</h1>
          {h.real_name && <span className="ca-real">{h.real_name}</span>}
          {h.kind && <span className="ca-kind" title={h.kind}>{h.kind}</span>}
          <nav aria-label="경쟁사 전환" className="ca-others">
            <span>다른 경쟁사</span>
            {(d.others ?? []).map((o) => (
              <Link key={o.id} to={`/competitor/${aid}/competitors/${o.id}`} aria-current={o.current ? 'true' : undefined} aria-label={`경쟁사 ${o.letter}`}>{o.letter}</Link>
            ))}
          </nav>
        </div>
        <span className="ca-pos">{d.positioning || '[확인 필요]'}</span>
      </div>
      {running && <Band>더 찾는 중 · {d.research?.eta_label || '약 40초'} · 이 경쟁사 사실만 다시 모아요</Band>}
      <div className="ca-list" role="list" aria-label="경쟁사 항목">
        {d.facts.map((f) => (
          <div key={f.key} className="ca-fact" role="listitem" data-fact={f.key}>
            <span className="ca-fact__k">{f.label}</span>
            <span className={`ca-fact__v${f.tbd ? ' ca-fact__v--tbd' : ''}`} title={f.text}>{f.text}</span>
            {f.sources_label && <button type="button" className="ca-fact__src" onClick={() => setPanel({ fact: f.key })}>{f.sources_label}</button>}
            {f.check && <span className="ca-tbd">확인 필요</span>}
          </div>
        ))}
        <div className="ca-fact" role="listitem" data-fact="vs">
          <span className="ca-fact__k">삼성 대비</span>
          <div className="ca-fact__chips">
            {d.vs_labels?.length ? d.vs_labels.map((c) => <span key={c.key} className={VS_CLASS[c.key] ?? 'ca-v ca-v--eq ca-v--lg'} title={c.label}>{c.label}</span>)
              : <span className="ca-fact__v ca-fact__v--tbd">[확인 필요]</span>}
          </div>
          {(d.vs_samsung?.unknown?.length ?? 0) > 0 && <span className="ca-tbd" title={d.vs_samsung!.unknown!.join(' · ')}>확인 필요 {d.vs_samsung!.unknown!.length}</span>}
        </div>
      </div>
      <div className="ca-dfoot">
        <span title={d.footer?.text}>{d.footer?.text}</span>
        <Button h={28} onClick={() => setPanel({})}>출처 · 근거 보기</Button>
      </div>
      {err && <Band tone="danger">{err}</Band>}
      <FootBar back={{ to: `/competitor/${aid}/result` }}>
        <Button h={48} className="ca-big2" onClick={more} loading={busy || running} disabled={running}
          icon={<Icon name="search" size={14} strokeWidth={2.2} color="var(--wm-text-muted)" />}>{running ? '더 찾는 중' : '이 경쟁사 더 찾기'}</Button>
        <BigButton onClick={() => nav(`/competitor/${aid}/send`)}>저장 · 보내기</BigButton>
      </FootBar>
      {panel && <EvidencePanel aid={aid} cmp={cmp} letter={h.letter} facts={d.facts} initialFact={panel.fact ?? null} onClose={() => setPanel(null)} />}
    </CaPage>
  );
}

export default DetailPage;
