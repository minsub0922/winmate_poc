/**
 * SC4 · 시나리오 생성 결과(§4.10) — 장면 카드(이야기 · 솔루션 동작(파랑) · 제품(회색) · 이미지 / 「이미지 생성」),
 * 장면 추가 · 더 짧게 · 장면별 이미지 모두 생성 · 조감도 추가, 수정 요청(영향 장면만 다시 쓰기), 저장(v{n}), 제안서에 넣기(SC5).
 * 열 때 image 요청 결과를 확인해 붙인다(images:sync).
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx, Img, toast } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi, type SceneOut } from '../api';
import { qk, useInvalidate, useJobsPulse, useScenario } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Ask, Card, Ico, Loading, Marked, NextButton, Note, P, Screen, StatusIcon, useOutside } from '../parts';
import { AerialPicker } from './aerial';

export default function ResultPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [aerialOpen, setAerialOpen] = useState(false);
  const aerialRef = useOutside<HTMLDivElement>(aerialOpen, () => setAerialOpen(false));
  const scenes = useQuery({
    queryKey: qk.scenes(id), queryFn: () => scApi.scenes(id), enabled: !!id,
    refetchInterval: (q) => ((q.state.data?.items ?? []).some((s) => s.rewriting || s.image_job?.status === 'queued' || s.image_job?.status === 'running') ? 2_000 : false),
  });
  const s = sc.data;
  const jobId = s?.active_job?.job_id ?? (s?.images_job as { job_id?: string } | null | undefined)?.job_id ?? null;
  useJobsPulse([jobId], () => { void scenes.refetch(); void inv.sc(id); });

  // image 요청이 충족됐으면 붙인다(IMG 에서 돌아왔을 때)
  useEffect(() => {
    if (!id) return;
    scApi.syncImages(id).then((r) => { if (r.attached?.length) void scenes.refetch(); }).catch(() => undefined);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  // 생성 중이면 SC4G 로
  useEffect(() => {
    if (s && (s.status === 'generating' || s.status === 'failed') && s.generation?.job_id) nav(route.generate(id, s.generation.job_id), { replace: true });
  }, [s?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  useShellPage({ section: SECTION, title: s?.title ?? '', stepper: stepper(4), sidebarGroup: 'scenario' });
  if (sc.isLoading || !s || scenes.isLoading) return <Loading />;

  const items = scenes.data?.items ?? [];
  const isWith = s.type === 'with';
  const missing = items.filter((x) => !x.image && !(x.image_job && ['queued', 'running'].includes(x.image_job.status)));
  const imagesRunning = items.some((x) => x.image_job && ['queued', 'running'].includes(x.image_job.status));
  const jobRunning = !!s.active_job;
  const link = s.birdseye_link?.birdseye_id || s.aerial?.birdseye_id;

  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key); setErr(null);
    try { await fn(); await inv.sc(id); await scenes.refetch(); } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const makeImage = async (scene: SceneOut) => {
    setBusy(`img:${scene.id}`); setErr(null);
    try { const r = await scApi.imageRequest(scene.id); nav(r.image_route); } catch (e) { setErr(errMessage(e)); setBusy(null); }
  };
  const save = () => run('save', async () => { const r = await scApi.save(id); toast(`저장했어요 · v${r.version}`); });

  const dock = (
    <Card title="시나리오" meta="4 / 4 · 완료" testId="sc4-card"
      right={(
        <div className="sc-row" style={{ gap: 6 }}>
          <Link to={route.timeline(id)} className="sc-pill sc-pill--h30" data-testid="sc4-add-scene">장면 추가</Link>
          <button type="button" className="sc-pill sc-pill--h30" disabled={jobRunning || busy === 'short'} onClick={() => void run('short', () => scApi.shorten(id))} data-testid="sc4-shorter"
            title={jobRunning ? '다른 작업이 끝나면 할 수 있어요' : undefined}>더 짧게</button>
          <button type="button" className="sc-pill sc-pill--h30" disabled={missing.length === 0 || imagesRunning || busy === 'imgs'} data-testid="sc4-images-all"
            title={missing.length === 0 ? (imagesRunning ? '이미지를 만드는 중이에요' : '모든 장면에 이미지가 있어요') : undefined}
            onClick={() => void run('imgs', () => scApi.generateMissing(id))}>장면별 이미지 모두 생성</button>
          {link ? (
            <Link to={`/birdseye/${link}/zones?scenario=${id}`} className="sc-pill sc-pill--h30" data-testid="sc4-aerial"><Ico d={P.cube} size={13} color="var(--wm-brand)" />조감도 추가</Link>
          ) : (
            <div className="sc-menuwrap" ref={aerialRef}>
              <button type="button" className="sc-pill sc-pill--h30" aria-haspopup="dialog" aria-expanded={aerialOpen} onClick={() => setAerialOpen(!aerialOpen)} data-testid="sc4-aerial">
                <Ico d={P.cube} size={13} color="var(--wm-brand)" />조감도 추가
              </button>
              {aerialOpen && (
                <div className="sc-pop" role="dialog" aria-label="조감도 연결" data-testid="sc4-aerial-pop">
                  <div className="sc-pop__title">조감도 연결</div>
                  <AerialPicker scenarioId={id} onDone={(beId, created) => { setAerialOpen(false); void inv.sc(id); nav(created ? `/birdseye/${beId}/space` : `/birdseye/${beId}/zones?scenario=${id}`); }} />
                </div>
              )}
            </div>
          )}
        </div>
      )}>
      {err && <div className="sc-card__sec"><Note tone="err" testId="sc4-err">{err}</Note></div>}
      <div className="sc-card__foot" style={{ gap: 10 }}>
        <Ask id="sc4-edit" label="수정 요청" placeholder="수정 요청 (예: 장면 2에 점장이 태블릿으로 재고 확인하는 장면 추가)" testId="sc4-edit" disabled={jobRunning}
          onSubmit={async (t) => { await run('edit', () => scApi.edit(id, t)); }} />
        <button type="button" className="sc-btn" onClick={() => void save()} disabled={busy === 'save'} data-testid="sc4-save">저장</button>
        <NextButton to={route.send(id)} testId="sc4-send">제안서에 넣기</NextButton>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} tight testId="sc4">
      <div className="sc-w">
        <span className="sc-w__logo" aria-hidden="true">W</span>
        <div className="sc-w__body">
          <div className="sc-w__text" data-testid="sc4-w">
            {isWith
              ? `${items.length}개 장면으로 시나리오를 구성했습니다. 각 장면은 이야기 · 솔루션 동작 · 제품 활용으로 나뉘며, 장면별 이미지는 '이미지 생성'으로 바로 만들 수 있습니다.`
              : `${items.length}개 장면으로 시나리오를 구성했습니다. 각 장면은 이야기 · 제품 활용으로 나뉘며, 장면별 이미지는 '이미지 생성'으로 바로 만들 수 있습니다.`}
          </div>
          {s.anonymized && <div className="sc-w__note"><Ico d={P.warn} size={13} />고객 정보를 가리고 쓴 뒤 원래 이름으로 되돌렸어요</div>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="sc4-scenes">
            {items.map((x) => <SceneCard key={x.id} id={id} s={x} busy={busy === `img:${x.id}`} onImage={() => void makeImage(x)} />)}
          </div>
        </div>
      </div>
    </Screen>
  );
}

function SceneCard({ id, s, onImage, busy }: { id: string; s: SceneOut; onImage: () => void; busy: boolean }) {
  const nav = useNavigate();
  const img = s.image;
  const ij = s.image_job;
  const open = () => nav(route.scene(id, s.id));
  return (
    <div className={cx('sc-scard', s.rewriting && 'sc-scard--busy')} role="link" tabIndex={0} onClick={(e) => { if (!(e.target as HTMLElement).closest('button,a')) open(); }}
      onKeyDown={(e) => { if (e.key === 'Enter' && e.target === e.currentTarget) open(); }} data-testid="sc4-scene" data-no={s.no}>
      <div style={{ width: 54, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span className="wm-num" style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-brand)' }}>{s.time ?? ''}</span>
        <span style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>장면 {s.no}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, flex: 1, minWidth: 0 }}>
        {s.rewriting && <span className="sc-scard__busy" data-testid="sc4-rewriting"><StatusIcon kind="gen" size={12} />장면 {s.no} 다시 쓰는 중</span>}
        <div className="sc-scard__title" data-testid="sc4-scene-title"><Marked text={s.title} /></div>
        <div className="sc-scard__story" data-testid="sc4-scene-story"><Marked text={s.story} /></div>
        <div className="sc-row sc-wrap" style={{ gap: 6 }}>
          {(s.solution_chips ?? []).map((c) => <span key={c} className="sc-mini sc-mini--brand" data-testid="sc4-sol-chip">{c}</span>)}
          {(s.products ?? []).map((p) => <span key={(p.ref ?? '') + p.short} className="sc-mini" data-testid="sc4-prod-chip">{p.qty && p.qty > 1 ? `${p.short} ×${p.qty}` : p.short}</span>)}
          {s.locked && <span className="sc-mini" title="직접 고친 장면은 「나머지 장면 다시 생성」에서 빠져요">직접 고침</span>}
        </div>
      </div>
      {img ? (
        <Link to={route.scene(id, s.id)} className="sc-scard__thumb" aria-label={`장면 ${s.no} 이미지`} data-testid="sc4-thumb">
          <Img src={img.thumb_url || img.url || ''} alt={`장면 ${s.no} · ${s.label}`} />
          {s.image_stale && <span className="sc-scard__stale" title="이야기가 바뀌어 이미지와 다를 수 있어요"><Ico d={P.warn} size={11} sw={2.4} /></span>}
        </Link>
      ) : ij && ['queued', 'running'].includes(ij.status) ? (
        <span className="sc-scard__img sc-scard__img--run" data-testid="sc4-img-running"><StatusIcon kind="gen" size={14} />이미지 만드는 중</span>
      ) : ij?.status === 'failed' ? (
        <button type="button" className="sc-scard__img sc-scard__img--fail" onClick={onImage} data-testid="sc4-img-failed">이미지를 만들지 못했어요 · 다시</button>
      ) : (
        <button type="button" className="sc-scard__img" onClick={onImage} disabled={busy} data-testid="sc4-img-make">{busy ? <span className="wm-spinner" aria-hidden="true" /> : '이미지 생성'}</button>
      )}
    </div>
  );
}
