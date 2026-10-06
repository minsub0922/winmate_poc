/**
 * SC5 · 제안서로 보내기 · 내보내기(§4.12) — 보낼 곳(제안서 고르기 · 새 제안서로 시작), 시트 계획 미리보기(§7.9),
 * 함께 넘어가는 것, 이미지 없는 장면 안내, 파일로 받기 4(export 잡 → 다운로드), 다른 기능으로 2, 팀에 공유, 제안서에 넣기.
 */
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx, Icon, Img, toast } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, proposal, scApi, type ProposalPick, type SceneOut, type Sheet } from '../api';
import { qk, useInvalidate, useScenario, waitJob } from '../hooks';
import { agoLabel, route, SECTION, stepper } from '../lib';
import { Btn, Card, Echo, Ico, Loading, NextButton, Note, P, Screen, useOutside, W } from '../parts';
import { AerialPicker } from './aerial';

type Kind = 'pptx' | 'pdf' | 'docx' | 'zip';
const normalize = (r?: string | null) => (r ? r.replace(/^\/proposals\//, '/proposal/') : null);

export default function SendPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const plan = useQuery({ queryKey: qk.plan(id), queryFn: () => scApi.sheetPlan(id), enabled: !!id });
  const scenes = useQuery({ queryKey: qk.scenes(id), queryFn: () => scApi.scenes(id), enabled: !!id });
  const props = useQuery({ queryKey: ['scenario', 'proposals', sc.data?.project_id ?? ''], queryFn: () => proposal.list(sc.data?.project_id), enabled: !!sc.data, retry: 0 });
  const [pickId, setPickId] = useState<string | null>(null);
  const [pickOpen, setPickOpen] = useState(false);
  const pickRef = useOutside<HTMLDivElement>(pickOpen, () => setPickOpen(false));
  const [aerialOpen, setAerialOpen] = useState(false);
  const aerialRef = useOutside<HTMLDivElement>(aerialOpen, () => setAerialOpen(false));
  const [exporting, setExporting] = useState<Partial<Record<Kind, 'run' | 'err'>>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<{ title: string; route: string | null; k: number } | null>(null);

  useShellPage({ section: SECTION, title: sc.data?.title ?? '', stepper: stepper(4, true), sidebarGroup: 'scenario' });
  if (sc.isLoading || plan.isLoading || !sc.data || !plan.data) return <Loading />;
  const s = sc.data;
  const pl = plan.data;
  const sheets = pl.sheets;
  const k = sheets.length;
  const items = scenes.data?.items ?? [];
  const n = items.length || s.scene_count;
  const proposals = props.data?.items ?? [];
  const target: ProposalPick | undefined = proposals.find((p) => p.id === pickId) ?? proposals[0];
  const link = s.birdseye_link?.birdseye_id || s.aerial?.birdseye_id;
  const carry = pl.carry;
  const carryLine = `장면 텍스트 ${carry.scenes ?? 0} · 솔루션 ${carry.solutions ?? 0} · 제품 ${carry.products ?? 0} · 이미지 ${carry.images ?? 0} · 확정 필요 ${carry.confirm ?? 0}`;

  const doExport = async (kind: Kind) => {
    setExporting((e) => ({ ...e, [kind]: 'run' })); setErr(null);
    try {
      const acc = await scApi.exportStart(id, kind);
      const r = await waitJob(acc.job_id, { timeoutMs: 180_000 });
      const out = await scApi.exportGet(id, acc.export_id);
      if (r.status !== 'succeeded' || out.status !== 'done' || !out.url) throw new Error(out.error || r.error?.message || '파일을 만들지 못했어요');
      const a = document.createElement('a');
      a.href = out.url; a.download = out.file_name ?? ''; a.rel = 'noopener';
      document.body.appendChild(a); a.click(); a.remove();
      setExporting((e) => ({ ...e, [kind]: undefined }));
    } catch (e) { setExporting((x) => ({ ...x, [kind]: 'err' })); setErr(`파일을 만들지 못했어요 · ${errMessage(e)}`); }
  };
  const share = async () => {
    setBusy('share'); setErr(null);
    try {
      const r = await scApi.share(id);
      try { await navigator.clipboard.writeText(r.url); toast('공유 링크를 복사했어요'); } catch { toast(`공유 링크 · ${r.url}`); }
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const send = async () => {
    if (!target) return;
    setBusy('send'); setErr(null);
    try {
      const keys = sheets.map((sh) => `${sh.code}:${sh.n}`);
      const r = await proposal.importScenario(target.id, { id, version: s.version, title: s.title }, keys);
      // 보낸 섹션은 제안서가 정한다(표준 · 퀵윈엔 「공간별 가치 제공 시나리오」가 없어 솔루션 섹션 등으로, 09-scenario §11 Q4) — 응답 section_key 로 연다
      const sec = 'section_key' in r && r.section_key ? r.section_key : null;
      const to = normalize('route' in r ? r.route : null) ?? (sec ? `/proposal/${target.id}/sections/${sec}` : `/proposal/${target.id}`);
      setDone({ title: target.title, route: to, k });
      toast(`${target.title}에 시트 ${k}장을 넣었어요`, { action: { label: '열기', onClick: () => nav(to) } });
      void inv.sc(id);
    } catch (e) { setErr(`제안서에 넣지 못했어요 · ${errMessage(e)}`); } finally { setBusy(null); }
  };
  const makeImage = async () => {
    const first = items.find((x) => !x.image) ?? items[0];
    if (!first) return;
    setBusy('img'); setErr(null);
    try { const r = await scApi.imageRequest(first.id); nav(r.image_route); } catch (e) { setErr(errMessage(e)); setBusy(null); }
  };

  const dock = (
    <Card title="보내기 · 내보내기" meta={`시나리오 완료 · 장면 ${n}`} testId="sc5-card"
      right={<span className="sc-label" data-testid="sc5-saved">마지막 저장 {agoLabel(s.last_saved_at || s.updated_at) || '—'}</span>}>
      <div className="sc-card__sec" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="sc-row" style={{ gap: 6 }} data-testid="sc5-files">
          <span className="sc-label" style={{ width: 84, flexShrink: 0 }}>파일로 받기</span>
          <ExportBtn kind="pptx" state={exporting.pptx} onClick={doExport} icon>PPTX · 시트 {k}장</ExportBtn>
          <ExportBtn kind="pdf" state={exporting.pdf} onClick={doExport}>PDF</ExportBtn>
          <ExportBtn kind="docx" state={exporting.docx} onClick={doExport}>장면 스크립트 DOCX</ExportBtn>
          <ExportBtn kind="zip" state={exporting.zip} onClick={doExport} disabled={(carry.images ?? 0) === 0} reason="장면 이미지가 아직 없어요">장면 이미지 ZIP</ExportBtn>
        </div>
        <div className="sc-row" style={{ gap: 6 }} data-testid="sc5-others">
          <span className="sc-label" style={{ width: 84, flexShrink: 0 }}>다른 기능으로</span>
          <button type="button" className="sc-btn sc-btn--sm" onClick={() => void makeImage()} disabled={busy === 'img' || items.length === 0} data-testid="sc5-make-image">
            <Ico d={P.image} size={13} color="var(--wm-brand)" />장면 이미지 만들기
          </button>
          {link ? (
            <Link to={`/birdseye/${link}/zones?scenario=${id}`} className="sc-btn sc-btn--sm" data-testid="sc5-aerial"><Ico d={P.cube} size={13} color="var(--wm-brand)" />조감도 존에 장면 연결</Link>
          ) : (
            <div className="sc-menuwrap" ref={aerialRef}>
              <button type="button" className="sc-btn sc-btn--sm" aria-haspopup="dialog" aria-expanded={aerialOpen} onClick={() => setAerialOpen(!aerialOpen)} data-testid="sc5-aerial">
                <Ico d={P.cube} size={13} color="var(--wm-brand)" />조감도 존에 장면 연결
              </button>
              {aerialOpen && (
                <div className="sc-pop" style={{ left: 0, right: 'auto' }} role="dialog" aria-label="조감도 연결">
                  <div className="sc-pop__title">조감도 연결</div>
                  <AerialPicker scenarioId={id} onDone={(beId, created) => { setAerialOpen(false); void inv.sc(id); nav(created ? `/birdseye/${beId}/space` : `/birdseye/${beId}/zones?scenario=${id}`); }} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {err && <div className="sc-card__sec"><Note tone="err" testId="sc5-err">{err}</Note></div>}
      <div className="sc-card__foot">
        <Btn to={route.result(id)} testId="sc5-prev">이전</Btn>
        <button type="button" className="sc-btn" onClick={() => void share()} disabled={busy === 'share'} data-testid="sc5-share"><Ico d={P.share} size={14} />팀에 공유</button>
        <NextButton onClick={() => void send()} busy={busy === 'send'} disabled={!target} testId="sc5-send"
          reason={props.data?.available === false ? '제안서 서비스에 연결할 수 없어요' : '보낼 제안서가 없어요 · 새 제안서로 시작하세요'}>제안서에 넣기 · 시트 {k}장</NextButton>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} tight testId="sc5">
      <Echo>제안서에 넣기</Echo>
      <W testId="sc5-w" extra={(
        <>
          <div className="sc-send" data-testid="sc5-plan">
            <div className="sc-send__to">
              <span className="sc-label">보낼 곳</span>
              <div className="sc-menuwrap" ref={pickRef} style={{ flex: 1, minWidth: 0 }}>
                <button type="button" className="sc-send__pick" aria-haspopup="listbox" aria-expanded={pickOpen} onClick={() => setPickOpen(!pickOpen)} disabled={proposals.length === 0}
                  data-testid="sc5-target">
                  <Ico d="M3 4h18v12H3z M8 20h8 M12 16v4 M7 12l3-3 2 2 4-4" size={15} color="var(--wm-brand)" />
                  <span className="wm-ellipsis" style={{ flex: 1, fontSize: 13 }}>
                    {target ? <><b style={{ fontWeight: 600 }}>{target.title}</b><span style={{ color: 'var(--wm-text-muted)' }}> · 공간별 가치 제공 시나리오</span></>
                      : <span style={{ color: 'var(--wm-text-muted)' }}>{props.isLoading ? '제안서를 찾는 중…' : '진행 중인 제안서가 없어요'}</span>}
                  </span>
                  {target && <span className="sc-tag">{target.status_label}</span>}
                  <Ico d={P.down} size={13} sw={2.2} color="var(--wm-text-muted)" />
                </button>
                {pickOpen && (
                  <div className="sc-menu sc-menu--left" role="listbox" style={{ right: 0, maxHeight: 260, overflow: 'auto' }}>
                    {proposals.map((p) => (
                      <button key={p.id} type="button" role="option" aria-checked={p.id === target?.id} aria-selected={p.id === target?.id}
                        onClick={() => { setPickId(p.id); setPickOpen(false); }}>
                        <span className="wm-ellipsis" style={{ flex: 1 }}>{p.title}</span><span className="sc-tag">{p.status_label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Link to={`/proposal/new?link=${id}&feature=scenario`} className="sc-btn sc-btn--sm" style={{ height: 36 }} data-testid="sc5-new-proposal"><Ico d={P.plus} size={12} sw={2.6} />새 제안서로 시작</Link>
            </div>
            <div className="sc-sheets">
              {sheets.map((sh) => <SheetPreview key={sh.n} sh={sh} scenes={items} />)}
            </div>
            <div className="sc-send__carry">
              <span className="wm-ellipsis" data-testid="sc5-carry"><b>함께 넘어가는 것</b> {carryLine}</span>
              {target ? <Link to={`/proposal/${target.id}/sections/spaceScenario`} className="sc-btn sc-btn--xs">시트 구성 바꾸기</Link>
                : <button type="button" className="sc-btn sc-btn--xs" disabled title="보낼 제안서를 먼저 고르세요">시트 구성 바꾸기</button>}
            </div>
          </div>
          {pl.images_missing > 0 && (
            <div className="sc-row" style={{ fontSize: 12.5, color: 'var(--wm-text-2)' }} data-testid="sc5-missing">
              <Icon name="info" size={15} color="var(--wm-text-muted)" />
              <span>이미지가 없는 장면 {pl.images_missing}개는 시트에 이미지 자리만 남겨요.</span>
              {pl.first_missing_scene_id && <Link to={route.scene(id, pl.first_missing_scene_id)} className="sc-link">장면 이미지 먼저 만들기</Link>}
            </div>
          )}
          {done && (
            <Note tone="ok" testId="sc5-done">{done.title}에 시트 {done.k}장을 넣었어요 · {done.route && <Link to={done.route} className="sc-link">열기</Link>}</Note>
          )}
        </>
      )}>
        시나리오를 제안서 '공간별 가치 제공 시나리오' 섹션에 넣을게요. 장면 {n}개를 공간 기준으로 묶어 시트 {k}장으로 나눴어요. 넣기 전에 어떻게 들어가는지 확인하세요.
      </W>
    </Screen>
  );
}

function ExportBtn({ kind, state, onClick, children, icon, disabled, reason }:
  { kind: Kind; state?: 'run' | 'err'; onClick: (k: Kind) => void; children: React.ReactNode; icon?: boolean; disabled?: boolean; reason?: string }) {
  return (
    <button type="button" className="sc-btn sc-btn--sm" onClick={() => onClick(kind)} disabled={disabled || state === 'run'} title={disabled ? reason : undefined}
      data-testid={`sc5-export-${kind}`} aria-busy={state === 'run' || undefined}>
      {state === 'run' ? <span className="wm-spinner" aria-hidden="true" style={{ width: 12, height: 12 }} /> : icon && <Ico d={P.download} size={13} sw={2.2} />}
      {state === 'run' ? <>만드는 중 · {children}</> : children}
    </button>
  );
}

const SHEET_LINES: Record<string, (sh: Sheet) => [string, string]> = {
  'VM-A': (sh) => [String(sh.detail?.grid ?? ''), '칸마다 장면 한 줄 요약'],
  'VM-B': () => ['공간 3개 한 장', '공간마다 장면 한 줄 요약'],
  'VM-C': () => ['조감도 위 솔루션 핀', '존 번호마다 장면 요약'],
  'VM-D': (sh) => [String(sh.detail?.grid ?? ''), '하루 타임라인 × 공간'],
  'SS-A': (sh) => [String(sh.detail?.line ?? ''), String(sh.detail?.sub ?? '')],
  'SS-B': (sh) => [String(sh.detail?.chain ?? ''), String(sh.detail?.sub ?? '')],
  'SS-C': () => ['이 공간 도입 전 → 후', '전 · 후 이미지 비교'],
};

function SheetPreview({ sh, scenes }: { sh: Sheet; scenes: SceneOut[] }) {
  const lines = (SHEET_LINES[sh.code] ?? (() => ['', '']))(sh);
  const byId = new Map(scenes.map((x) => [x.id, x]));
  const group = sh.scene_ids.map((x) => byId.get(x)).filter(Boolean) as SceneOut[];
  return (
    <div className="sc-sheet" data-testid="sc5-sheet" data-code={sh.code}>
      <div className="sc-sheet__art" aria-hidden="true">
        <span className="sc-sheet__bar" /><span className="sc-sheet__h" />
        {sh.code === 'VM-A' || sh.code === 'VM-D' ? <MapArt sh={sh} /> : sh.code === 'SS-B' ? <ChainArt sh={sh} /> : (
          <div className="sc-sheet__cells">
            {group.slice(0, 3).map((x) => (
              <div key={x.id} className="sc-sheet__cell">
                {x.image ? <div className="sc-sheet__img"><Img src={x.image.thumb_url || x.image.url || ''} alt={`장면 ${x.no} 이미지`} /></div>
                  : <div className="sc-sheet__img sc-sheet__img--empty"><Ico d={P.image} size={14} color="var(--wm-line-dashed)" /></div>}
                <span className="wm-num" style={{ fontSize: 8.5, fontWeight: 700, color: 'var(--wm-brand)' }}>{x.time ?? `장면 ${x.no}`}</span>
                <span className="sc-sheet__ln" /><span className="sc-sheet__ln" style={{ width: '70%' }} />
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="sc-row" style={{ justifyContent: 'space-between', gap: 6 }}>
        <span className="wm-ellipsis" style={{ fontSize: 12.5, fontWeight: 600 }}>시트 {sh.n} · {sh.title}</span>
        <span className="wm-num" style={{ fontSize: 11, fontWeight: 700, color: 'var(--wm-text-subtle)', flexShrink: 0 }}>{sh.code}</span>
      </div>
      <div className="sc-row sc-wrap" style={{ gap: 4 }}>
        {sh.kind === 'map' ? <span className="sc-schip">{sh.summary}</span> : sh.scene_nos.map((no) => <span key={no} className="sc-schip">장면 {no}</span>)}
        {sh.confirm_count > 0 && sh.kind !== 'map' && <span className="sc-schip sc-schip--warn"><Ico d={P.warn} size={10} sw={2.6} />확정 필요 {sh.confirm_count}</span>}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 1, fontSize: 12, lineHeight: 1.5, color: 'var(--wm-text-muted)' }}>
        <span className="wm-ellipsis">{lines[0]}</span><span className="wm-ellipsis">{lines[1]}</span>
      </div>
    </div>
  );
}

function MapArt({ sh }: { sh: Sheet }) {
  const rows = ((sh.detail?.rows as string[] | undefined) ?? []).slice(0, 3);
  const cols = ((sh.detail?.cols as string[] | undefined) ?? []).slice(0, 3);
  const cells = (sh.detail?.cells as string[][][] | undefined) ?? [];
  return (
    <div className="sc-sheet__grid" style={{ gridTemplateColumns: `54px repeat(${Math.max(1, cols.length)}, minmax(0, 1fr))`, gridTemplateRows: `18px repeat(${Math.max(1, rows.length)}, minmax(0, 1fr))` }}>
      <div />
      {cols.map((c) => <div key={c} className="sc-sheet__colh">{c}</div>)}
      {rows.map((r, i) => (
        <div key={r} style={{ display: 'contents' }}>
          <div className="sc-sheet__rowh">{r}</div>
          {cols.map((c, j) => {
            const k = (cells[i]?.[j] ?? []).length;
            return <div key={c} className={cx('sc-sheet__dot', !k && 'sc-sheet__dot--empty')}>{Array.from({ length: Math.min(3, k) }, (_, x) => <span key={x} />)}</div>;
          })}
        </div>
      ))}
    </div>
  );
}

function ChainArt({ sh }: { sh: Sheet }) {
  const parts = String(sh.detail?.chain ?? '').split(' → ');
  return (
    <div className="sc-sheet__chain">
      <div className="sc-sheet__node sc-sheet__node--brand"><b>{parts[0] ?? ''}</b><span /><span style={{ width: '70%' }} /></div>
      <Ico d={P.arrow} size={10} sw={2.6} color="var(--wm-text-muted)" />
      <div className="sc-sheet__node"><b>{parts[1] ?? ''}</b><span /><span style={{ width: '70%' }} /></div>
      <Ico d={P.arrow} size={10} sw={2.6} color="var(--wm-text-muted)" />
      <div className="sc-sheet__node sc-sheet__node--value"><b>가치</b><em className="wm-num">[00]</em></div>
    </div>
  );
}
