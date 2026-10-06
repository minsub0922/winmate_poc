/** BE5 — 3D 조감도 5/5(`/birdseye/:id/result?cut=`, §4.10): 완성 조감도 · 컷 썸네일 · 제품 칩 · 수정 요청(R8) · 저장 · 제안서에 넣기. */
import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useJob } from '@/api/jobs';
import { Icon, Modal, Spinner, toast } from '@/ui';
import { be, errText, qk, useBe, useCuts, useLayout, type Cut } from '../api';
import { Agent, BePage, Dock, DockLink, Loading, MainButton, PromptBar, SubButton, VIEW_PHRASE, useBeShell } from '../ui';
import { TONES } from './LayoutPage';

export function resultW(cut: Cut, tone: string, p: number, f: number): string {
  const phrase = (VIEW_PHRASE[cut.view.preset] ?? ((l: string) => l))(cut.view.label);
  const base = `3D 조감도가 완성되었습니다. ${tone} 톤, ${phrase} 시점이며 제품 ${p}종과 가구 ${f}종이 배치안대로 반영되었습니다.`;
  return cut.status === 'check' ? `${base} 일부 제품 위치가 배치안과 다를 수 있어요.` : base;
}

export default function ResultPage() {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const cq = useCuts(id);
  const lq = useLayout(id);
  const [zoom, setZoom] = useState(false);
  const [editJob, setEditJob] = useState<string | null>(null);
  const [ask, setAsk] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const refresh = () => Promise.all([qc.invalidateQueries({ queryKey: qk.cuts(id) }), qc.invalidateQueries({ queryKey: qk.one(id) })]);
  useJob(editJob, { onDone: () => { setEditJob(null); void refresh(); } });
  useBeShell(bq.data, 5, {}, false);
  if (bq.isLoading || cq.isLoading) return <Loading />;
  const b = bq.data!;
  const cuts = (cq.data ?? []).filter((c) => c.status !== 'canceled');
  const shown = cuts.filter((c) => ['done', 'check', 'draft', 'running', 'queued'].includes(c.status));
  const cut = cuts.find((c) => c.id === sp.get('cut')) ?? cuts.find((c) => c.id === b.primary_cut_id) ?? cuts.find((c) => ['done', 'check', 'draft'].includes(c.status));
  const lay = lq.data?.layout;
  const prodGroups = (lay?.groups ?? []).filter((g) => g.kind === 'product');
  const fKinds = new Set((lay?.groups ?? []).filter((g) => g.kind !== 'product').map((g) => g.ref)).size;
  const tone = TONES.find((t) => t.value === (cut?.tone ?? b.tone))?.label ?? '웜 우드';

  if (!cut) {
    return (
      <BePage testId="be5" dock={<Dock title="3D 조감도" meta="5 / 5" foot={<SubButton to={`/birdseye/${id}/layout`}>배치로 돌아가기</SubButton>} />}>
        <Agent text="아직 완성된 3D 조감도가 없어요. 배치안에서 「이 배치로 3D 생성」을 눌러 주세요." />
      </BePage>
    );
  }
  const running = cut.status === 'running' || cut.status === 'queued' || !!editJob;
  const save = async () => {
    setSaving(true);
    try { const r = await be.save(id); toast(`저장했어요 · v${r.version}`); await refresh(); } catch (e) { toast(errText(e)); } finally { setSaving(false); }
  };
  const request = async (text: string) => {
    setAsk(null);
    try {
      const r = await be.resultEdit(id, text, cut.id);
      if (r.route_hint === 'ask') { setAsk(r.question ?? '어떤 부분을 바꿀지 한 번만 더 알려 주세요.'); return false; }
      if (r.route_hint === 'render') { setEditJob(r.job_id ?? null); return; }
      await refresh();
      if (r.route) nav(r.route);
    } catch (e) { toast(errText(e)); return false; }
  };
  const complete = ['done', 'check', 'draft'].includes(cut.status);

  return (
    <BePage testId="be5" dock={(
      <Dock title="3D 조감도" meta={<>5 / 5 · {complete ? '완료' : '생성 중'}</>}
        right={(
          <>
            <DockLink to={`/birdseye/${id}/views`} icon={<Icon name="plus" size={13} />}>다른 시점 추가</DockLink>
            <DockLink to={`/birdseye/${id}/views?mode=tone`} icon={<Icon name="refresh" size={13} />}>톤 바꿔 재생성</DockLink>
            <DockLink to={`/birdseye/${id}/layout/edit`} icon={<Icon name="edit" size={13} />}>배치 수정</DockLink>
          </>
        )}
        foot={(
          <>
            <PromptBar label="수정 요청" placeholder="수정 요청 (예: 조명을 더 따뜻하게, 사람 실루엣 추가)" busy={!!editJob} initial={cut.edit_pending_text ?? undefined}
              onSend={request} testId="be5-edit" />
            <SubButton onClick={() => void save()} disabled={saving} testId="be5-save">저장</SubButton>
            <MainButton onClick={() => nav(`/birdseye/${id}/export`)} testId="be5-export">제안서에 넣기</MainButton>
          </>
        )} />
    )}>
      <Agent text={complete ? resultW(cut, tone, prodGroups.length, fKinds) : '조감도를 만들고 있어요.'}>
        {ask && <div className="be-notice" role="status">{ask}</div>}
        {cut.notice && <div className="be-notice" role="status">{cut.notice}</div>}
        <div className="be-hero" aria-label="3D 조감도 렌더 (생성 이미지 영역)" role="img" data-testid="be5-hero">
          {cut.image_url ? <img src={cut.display_url ?? cut.image_url} alt="3D 조감도 렌더 (생성 이미지 영역)" /> : cut.draft_url ? <img src={cut.draft_url} alt="초안" /> : null}
          <div className="be-hero__tags" data-testid="be5-tags"><span>{cut.view.label}</span><span>{tone}</span><span>{cut.resolution}</span></div>
          <div className="be-hero__btns">
            <button type="button" aria-label="확대" onClick={() => setZoom(true)}><Icon name="search" size={15} /></button>
            {cut.image_url && <a aria-label="다운로드" href={`${cut.image_url}?download=1`} download><Icon name="download" size={15} /></a>}
          </div>
          {cut.badge && <span className="be-hero__badge">{cut.badge}</span>}
          {cut.stale && <span className="be-hero__badge" style={{ left: cut.badge ? 96 : 12 }}>배치 변경 전</span>}
          {running && <div className="be-hero__busy"><Spinner label="진행 중" />{editJob ? '수정 요청을 반영하고 있어요' : `만드는 중 ${Math.round(cut.progress)}%`}</div>}
        </div>
        <div className="be-thumbs" data-testid="be5-thumbs">
          {shown.map((c) => (
            <button key={c.id} type="button" className={c.id === cut.id ? 'be-cutthumb be-cutthumb--on' : 'be-cutthumb'} aria-pressed={c.id === cut.id}
              onClick={() => setSp({ cut: c.id })}>
              {c.thumb_url ? <img src={c.thumb_url} alt="" /> : <span className="ph" />}
              <span>{c.thumb_label}</span>
              {c.stale && <em>배치 변경 전</em>}
              {(c.status === 'running' || c.status === 'queued') && <span className="pct">{c.status === 'queued' ? '대기' : `${Math.round(c.progress)}%`}</span>}
            </button>
          ))}
        </div>
        <div className="be-prodchips" data-testid="be5-chips">
          {prodGroups.map((g) => <span key={g.id} className="be-prodchip">{g.label}</span>)}
          {fKinds > 0 && <span className="be-prodchip be-prodchip--muted">가구 {fKinds}종</span>}
        </div>
        {running && cut.job_id && cut.status === 'running' && <Link className="be-link" to={`/birdseye/${id}/render/${cut.job_id}`}>진행 상황 보기</Link>}
      </Agent>
      <Modal open={zoom} onClose={() => setZoom(false)} title={cut.label} width={1100}>
        {cut.image_url && <img src={cut.image_url} alt="3D 조감도 렌더 (생성 이미지 영역)" style={{ width: '100%', borderRadius: 10 }} />}
      </Modal>
    </BePage>
  );
}
