/**
 * PRU5 — 완성 · 원본 대비 변경 요약(§4.31, 보드 PRU5) — 파생 제안서의 PR7 자리. `/proposal/:id/reuse/summary`(`?export=1`).
 * 판정 5칸 · 섹션별 매핑(원본 n장 → 새 n장, 판정 칩) · 검토 필요(바로 고치기) · 원본에 남긴 흔적 · 완료 카드(미리보기 · 검토 요청 · PPTX 다운로드 → PR7X).
 */
import { Link, useParams } from 'react-router';
import { Icon, cx } from '@/ui';
import { useProposal, useReuseSummary } from '../api/proposal';
import { errText } from '../api/http';
import { Agent, Dock, ErrorBand, GhostButton, LoadingCard, MarkText, PrPage, Rich } from '../components/parts';
import { useExportParam } from '../components/ResultToolbar';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';
import { ExportModal } from '../pages/ExportModal';

const V_OF: Record<string, string> = { 유지: 'keep', 갱신: 'update', 재작성: 'rewrite', 신규: 'new', 제외: 'drop', 자동: 'auto' };
const vOf = (chip: string) => V_OF[chip.split(' ')[0]] ?? 'keep';

export function ReuseSummaryPage() {
  const { id } = useParams();
  const pq = useProposal(id);
  const p = pq.data;
  const sq = useReuseSummary(id);
  const s = sq.data;
  const ex = useExportParam();
  useProposalShell({ p, step: 6, complete: true });

  if (pq.isError) return <PrPage><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></PrPage>;
  if (!p || !id) return <PrPage><LoadingCard /></PrPage>;
  if (sq.isError) return <PrPage wide><ErrorBand message={errText(sq.error, '변경 요약을 불러오지 못했어요')} onRetry={() => void sq.refetch()} /><Link to={R.result(id)} className="pr-link">결과 화면으로</Link></PrPage>;
  if (!s) return <PrPage wide><LoadingCard lines={8} /></PrPage>;

  const counts = s.counts ?? [];
  const dock = (
    <Dock testId="pru5-dock" title={<span className="pr-row" style={{ gap: 8, display: 'inline-flex', verticalAlign: 'middle' }}><span className="pr-cficon pr-cficon--ok"><Icon name="check" size={11} strokeWidth={3} /></span>완료</span>}
      meta={s.footer_label?.replace(/^완료 · /, '') || `원본 대비 변경 ${s.changed_count}장 · 6 / 6`}
      right={<span className="pr-row" style={{ gap: 6 }}>{counts.map((c) => <span key={c.verdict} className={cx('pr-vchip', `pr-vchip--${c.verdict}`)}>{c.label} {c.n}장</span>)}</span>}
      hint={s.file_label ? `${s.file_label} · 원본 제안서는 바뀌지 않았어요.` : '원본 제안서는 바뀌지 않았어요.'}
      foot={<>
        <GhostButton to={R.preview(id)}>미리보기 · 시트 편집</GhostButton>
        <GhostButton to={R.review(id)}>검토 요청</GhostButton>
        <button type="button" className="pr-btn pr-btn--primary" onClick={() => ex.openExport()} data-testid="pru5-download"><Icon name="download" size={15} strokeWidth={2.2} />PPTX 다운로드</button>
      </>} />
  );

  return (
    <PrPage testId="pru5" dock={dock} wide gap={14} tight>
      <Agent text={<Rich text={s.intro} />} testId="pru5-agent" />
      <div className="pr-card pr-sumband" data-testid="pru5-counts">
        {counts.map((c) => (
          <div key={c.verdict} className="pr-sumcell">
            <b className={cx('pr-num', c.verdict === 'drop' && 'pr-subtle')} style={{ fontSize: 24 }}>{c.n}</b>
            <span className="pr-colflex" style={{ gap: 2, minWidth: 0 }}>
              <span className="pr-row" style={{ gap: 5 }}><i className={cx('pr-legdot', `pr-legdot--${c.verdict}`)} /><b style={{ fontSize: 13 }}>{c.label}</b></span>
              <span className="pr-ell pr-note" style={{ fontSize: 11.5 }}>{c.desc}</span>
            </span>
          </div>
        ))}
      </div>
      <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pru5-mapping">
        <div className="pr-cardhead" style={{ height: 40 }}>
          <b style={{ fontSize: 13 }}>섹션별 매핑</b>
          <span className="pr-note pr-ell" style={{ fontSize: 11.5 }}>{s.mapping_label}</span>
          <span className="pr-grow" />
          <span className="pr-row" style={{ gap: 4 }}>{['유지', '갱신', '재작성', '신규', '제외', '자동'].map((l) => <span key={l} className={cx('pr-vchip', `pr-vchip--${V_OF[l]}`)} style={{ height: 18, fontSize: 10.5 }}>{l}</span>)}</span>
          <span className="pr-brand" style={{ fontSize: 12, fontWeight: 700, marginLeft: 12 }}>새 제안서 {s.mapping.reduce((n, r) => n + r.new_count, 0)}장</span>
        </div>
        <div className="pr-colflex" style={{ padding: '8px 14px 10px', gap: 0 }}>
          {s.mapping.map((r) => {
            const gap = r.src_count === 0;
            const allDrop = r.new_count === 0;
            // 선 색 = 첫 「제외 아닌」 판정(보드: 갱신 주황 · 유지 파랑 · 재작성 검정 · 자동 남색 · 신규 초록 점선 · 제외 회색 점선)
            const lead = gap ? 'new' : allDrop ? 'drop' : (r.chips.map(vOf).find((x) => x !== 'drop') ?? 'keep');
            return (
              <div key={r.section} className={cx('pr-maprow2', gap && 'pr-maprow2--gap', allDrop && 'pr-maprow2--drop')} data-testid="pru5-row">
                <span className="pr-ell" style={{ fontSize: 12, fontWeight: 600 }}>{r.section}</span>
                <span className="pr-blocks">{Array.from({ length: Math.min(r.src_count, 5) }, (_, i) => <i key={i} />)}</span>
                <span className="pr-num pr-note" style={{ fontSize: 11.5 }}>{r.src_label ?? (gap ? '—' : `${r.src_count}장`)}</span>
                <span className={cx('pr-mapline', `pr-mapline--${lead}`)}><span className="pr-row" style={{ gap: 4 }}>{r.chips.map((c) => <span key={c} className={cx('pr-vchip', `pr-vchip--${vOf(c)}`)} style={{ height: 18, fontSize: 10.5 }}>{c}</span>)}</span></span>
                <span className="pr-subtle">›</span>
                <span className="pr-num" style={{ fontSize: 11.5, color: allDrop ? 'var(--wm-text-subtle)' : 'var(--wm-brand)', fontWeight: 700 }}>{r.new_label ?? `${r.new_count}장`}</span>
                <span className="pr-blocks pr-blocks--new">{Array.from({ length: Math.min(r.new_count, 5) }, (_, i) => <i key={i} className={`pr-block--${vOf(r.chips[Math.min(i, r.chips.length - 1)] ?? '유지')}`} />)}</span>
              </div>
            );
          })}
        </div>
      </div>
      <div className="pr-pru5bottom">
        <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pru5-review">
          <div className="pr-cardhead" style={{ height: 38 }}>
            <Icon name="info" size={13} color="var(--wm-brand)" /><b style={{ fontSize: 13 }}>검토 필요 {s.review_total}곳</b><span className="pr-note" style={{ fontSize: 11.5 }}>갱신한 수치 · 모델 · 원본과 달라진 곳</span>
            <span className="pr-grow" /><span className="pr-note" style={{ fontSize: 11 }}>확정하지 않은 곳은 PPTX에 표시가 남아요</span>
          </div>
          {s.review_items.map((it) => (
            <div key={it.id} className="pr-row" style={{ gap: 8, minHeight: 30, padding: '0 14px', borderBottom: '1px solid var(--wm-line-soft)' }}>
              <span className="pr-cfno pr-num">{it.sheet_no_label ?? '—'}</span>
              <span className="pr-ell pr-grow" style={{ fontSize: 12.5, fontWeight: 600 }}><MarkText t={it.text} cls="pr-sumark" /></span>
              <span className="pr-cftag">{it.tag}</span>
              <Link to={normalizeRoute(it.route) ?? R.confirm(id)} className="pr-mini">바로 고치기</Link>
            </div>
          ))}
          <div className="pr-row" style={{ padding: '8px 14px', gap: 8 }}>
            <span className="pr-note pr-ell pr-grow" style={{ fontSize: 11.5 }}>{s.review_more_label}</span>
            <Link to={R.confirm(id)} className="pr-link" style={{ fontSize: 12 }}>검토 필요 목록 전체<Icon name="chevronRight" size={11} strokeWidth={2.4} /></Link>
          </div>
        </div>
        <div className="pr-card" style={{ overflow: 'hidden' }} data-testid="pru5-traces">
          <div className="pr-cardhead" style={{ height: 38 }}>
            <Icon name="clock" size={13} color="var(--wm-brand)" /><b style={{ fontSize: 13 }}>원본에 남긴 흔적</b><span className="pr-grow" />
            <Link to={R.versions(id)} className="pr-link" style={{ fontSize: 12 }}>버전 · 변경 이력<Icon name="chevronRight" size={11} strokeWidth={2.4} /></Link>
          </div>
          <div className="pr-colflex" style={{ padding: '10px 14px', gap: 10 }}>
            {s.traces.map((t) => (
              <div key={t.title} className="pr-row" style={{ gap: 8, alignItems: 'flex-start' }}>
                <span className="pr-cficon" style={{ width: 16, height: 16, borderWidth: 1 }}><Icon name="check" size={9} strokeWidth={3} /></span>
                <span className="pr-colflex" style={{ gap: 1 }}><b style={{ fontSize: 12.5 }}>{t.title}</b><span className="pr-note" style={{ fontSize: 11.5 }}>{t.sub}</span></span>
              </div>
            ))}
          </div>
        </div>
      </div>
      {ex.open && <ExportModal proposalId={id} open onClose={ex.closeExport} initialLang={ex.lang} version={ex.version} />}
    </PrPage>
  );
}
