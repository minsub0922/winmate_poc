/**
 * DnD_MIExtract — 사이드바 작업을 놓은 뒤 추출 결과 확인(§4.15). `GET …/imports/{impId}` → 체크 목록 → 「이대로 반영」 = `POST …:apply {keys}`(202).
 * 추출 중이면 잡 진행을 보여 준다. 「원본 채팅 보기」 = 원 작업 화면(source_route).
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { applyImport, useImport } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import { Bar, ErrorBand, LoadingCard, SpinIcon, SrcIcon } from '../components/parts';
import { FEATURE_LABEL } from '../lib/catalog';
import { normalizeRoute } from '../lib/routes';

export function ExtractPanel({ proposalId, importId, sectionName, onApplied }: { proposalId: string; importId: string; sectionName: string; onApplied: () => void }) {
  const iq = useImport(proposalId, importId, false);
  const imp = iq.data;
  const [checked, setChecked] = useState<Record<string, boolean> | null>(null);
  const [applyJob, setApplyJob] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const extracting = imp?.status === 'extracting';
  const ex = useJobEvents(extracting ? imp?.job_id : null, { onDone: () => void iq.refetch() });
  const ap = useJobEvents(applyJob, {
    onDone: (j) => { if (j.status === 'succeeded') onApplied(); else { setApplyJob(null); setErr(jobErrText(j.error)); } },
  });
  useEffect(() => { if (imp?.items && !checked) setChecked(Object.fromEntries(imp.items.map((i) => [i.key, i.checked]))); }, [imp?.items, checked]);
  useEffect(() => { if (imp?.status === 'applied') onApplied(); }, [imp?.status, onApplied]);
  // 추출 잡 이벤트가 오지 않는 경우를 대비해 가볍게 다시 읽는다
  useEffect(() => { if (!extracting) return; const t = window.setInterval(() => void iq.refetch(), 2500); return () => window.clearInterval(t); }, [extracting, iq]);

  if (iq.isError) return <ErrorBand message={errText(iq.error)} onRetry={() => void iq.refetch()} />;
  if (!imp) return <LoadingCard lines={4} />;
  const src = (imp.source ?? {}) as { feature?: string; title?: string; ref_id?: string };
  const feature = String(src.feature ?? 'mi').toLowerCase();
  const items = imp.items ?? [];
  const keys = items.filter((i) => checked?.[i.key]).map((i) => i.key);
  const route = normalizeRoute(imp.source_route) ?? (feature === 'mi' && src.ref_id ? `/mi/${src.ref_id}/result` : null);
  const title = imp.panel_title ?? `${FEATURE_LABEL[feature] ?? feature} · ${src.title ?? imp.label ?? ''}`;
  const [tHead, ...tRest] = title.split(' · ');

  const apply = async () => {
    setErr(null);
    try {
      const r = await applyImport(proposalId, importId, keys);
      if (r?.job_id) setApplyJob(r.job_id); else onApplied();
    } catch (e) { setErr(errText(e)); }
  };

  return (
    <div className="pr-extract" data-testid="pr-extract">
      <div className="pr-extract__head">
        <SrcIcon kind={feature} size={16} />
        <div style={{ fontSize: 13, flex: 1, minWidth: 0 }} className="pr-ell"><span className="pr-muted">{tHead} ·</span> <span style={{ fontWeight: 600 }}>{tRest.join(' · ')}</span></div>
        {!extracting && <span className="pr-badge pr-badge--soft" style={{ height: 22, fontSize: 11.5, padding: '0 9px' }} data-testid="pr-extract-count">{imp.ex_count ?? items.length}개 항목 추출됨</span>}
      </div>
      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {extracting ? (
          <div className="pr-colflex">
            <div className="pr-row" style={{ fontSize: 13 }}><SpinIcon /> {sectionName} 섹션에 쓸 내용을 뽑는 중이에요</div>
            <Bar value={ex.progress} label="추출 진행률" />
          </div>
        ) : imp.status === 'failed' ? (
          <ErrorBand message={jobErrText((imp.error as { code?: string; message?: string } | null) ?? ex.error ?? null, '내용을 뽑지 못했어요. 다시 놓아 주세요')} />
        ) : (
          <>
            <div style={{ fontSize: 13, color: 'var(--wm-text-muted)' }}>{imp.question || '이 섹션의 시트에 이렇게 넣을까요? 필요한 것만 남겨 주세요.'}</div>
            {items.map((it) => {
              const on = !!checked?.[it.key];
              return (
                <label key={it.key} className="pr-extract__row" data-testid="pr-extract-row">
                  <input type="checkbox" checked={on} onChange={() => setChecked({ ...(checked ?? {}), [it.key]: !on })} aria-label={it.what} />
                  <span style={{ fontWeight: 600, flexShrink: 0 }}>{it.what}</span>
                  <span className={it.in_section ? 'pr-extract__to' : 'pr-extract__to pr-extract__to--off'}>{it.line_label}</span>
                </label>
              );
            })}
            {err && <ErrorBand message={err} />}
            <div className="pr-row" style={{ justifyContent: 'flex-end', paddingTop: 2 }}>
              {route && <Link to={route} className="pr-btn pr-btn--sm">원본 채팅 보기</Link>}
              <button type="button" className="pr-btn pr-btn--sm pr-btn--primary" style={{ fontSize: 12.5, padding: '0 14px' }} disabled={!keys.length || !!applyJob}
                onClick={() => void apply()} data-testid="pr-extract-apply">{applyJob ? <SpinIcon color="currentColor" /> : null}이대로 반영</button>
            </div>
            {applyJob && <Bar value={ap.progress} label="반영 진행률" />}
          </>
        )}
      </div>
    </div>
  );
}
