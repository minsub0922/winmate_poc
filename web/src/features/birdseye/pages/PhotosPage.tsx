/** BE1P — 현장 사진으로 입력(`/birdseye/:id/space/photos` · 새로 `/birdseye/new/photos`, §4.4): 촬영 가이드 · 찍은 방향 · QR · 사진 카드 · 천장 · 추정 요약. */
import { useRef, useState, type DragEvent } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Icon, Modal, toast } from '@/ui';
import { be, errText, qk, uploadAll, useBe, usePhotos, type Photo } from '../api';
import { Agent, BePage, Dock, DockLink, Echo, InfoChips, Loading, MainButton, PromptBar, SubButton, useBeShell } from '../ui';

const PHOTO_OK = /\.(png|jpe?g|heic|heif)$/i;
const ACCEPT = '.png,.jpg,.jpeg,.heic,.heif,image/png,image/jpeg,image/heic,image/heif';
const TYPE_MSG = 'JPG · PNG · HEIC만 올릴 수 있어요';

export default function PhotosPage() {
  const { id } = useParams();
  if (!id) return <NewPhotos />;
  return <Photos id={id} />;
}

function NewPhotos() {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useBeShell(null, 1);
  const onFiles = async (files: File[]) => {
    const ok = files.filter((f) => PHOTO_OK.test(f.name));
    if (ok.length !== files.length) setErr(TYPE_MSG);
    if (!ok.length) return;
    setBusy(true);
    try {
      const work = await be.create({});
      const up = await uploadAll(ok.slice(0, 12));
      for (const f of up) await be.addPhoto(work.id, f.id);
      nav(`/birdseye/${work.id}/space/photos`, { replace: true });
    } catch (e) { setErr(errText(e)); setBusy(false); }
  };
  return (
    <BePage testId="be1p-new" dock={<Dock title="현장 사진" meta="1 / 5" foot={<SubButton to="/birdseye/new">이전</SubButton>} />}>
      <Agent text="현장 사진을 올려 주세요. 사진마다 벽 · 창 · 문을 찾아 공간 구조를 잡아 드릴게요." busy={busy} />
      <PhotoDrop onFiles={onFiles} />
      {err && <div className="be-err" role="alert">{err}</div>}
    </BePage>
  );
}

function PhotoDrop({ onFiles, compact }: { onFiles: (f: File[]) => void; compact?: boolean }) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const drop = (e: DragEvent) => { e.preventDefault(); setOver(false); onFiles(Array.from(e.dataTransfer.files)); };
  return (
    <div className={over ? 'be-drop be-drop--over' : 'be-drop'} role="button" tabIndex={0} aria-label="사진 끌어 놓기" data-testid="be1p-drop"
      onClick={() => ref.current?.click()} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') ref.current?.click(); }}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={drop} style={compact ? { padding: 10 } : undefined}>
      <Icon name="upload" size={18} />
      <b>사진 끌어 놓기</b>
      <span>JPG · PNG · HEIC</span>
      <input ref={ref} type="file" accept={ACCEPT} multiple hidden data-testid="be1p-file" onChange={(e) => { onFiles(Array.from(e.target.files ?? [])); e.target.value = ''; }} />
    </div>
  );
}

export function QrCode({ rows, size = 96, label }: { rows: string[]; size?: number; label: string }) {
  const n = rows.length;
  const q = 2;
  const total = n + q * 2;
  let d = '';
  rows.forEach((r, y) => { for (let x = 0; x < r.length; x++) if (r[x] === '1') d += `M${x + q} ${y + q}h1v1h-1z`; });
  return (
    <svg className="be-qr" width={size} height={size} viewBox={`0 0 ${total} ${total}`} role="img" aria-label={label} shapeRendering="crispEdges">
      <rect width={total} height={total} fill="var(--wm-surface)" />
      <path d={d} fill="var(--wm-text)" />
    </svg>
  );
}

function Photos({ id }: { id: string }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const pq = usePhotos(id, true);
  const tq = useQuery({ queryKey: ['be', id, 'token'], queryFn: () => be.uploadToken(id), staleTime: 25 * 60_000, retry: 1 });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [replace, setReplace] = useState<string | null>(null);
  const [ceilingPick, setCeilingPick] = useState(false);
  const pickRef = useRef<HTMLInputElement>(null);
  useBeShell(bq.data, 1);
  const refresh = () => qc.invalidateQueries({ queryKey: qk.photos(id) });

  const upload = async (files: File[], o: { replace?: string; ceiling?: boolean } = {}) => {
    const ok = files.filter((f) => PHOTO_OK.test(f.name));
    setErr(ok.length !== files.length ? TYPE_MSG : null);
    if (!ok.length) return;
    try {
      const up = await uploadAll(o.replace || o.ceiling ? ok.slice(0, 1) : ok);
      for (const f of up) await be.addPhoto(id, f.id, o);
      await refresh();
    } catch (e) { setErr(errText(e)); }
  };
  const pick = (o: { replace?: string; ceiling?: boolean }) => { setReplace(o.replace ?? null); setCeilingPick(!!o.ceiling); pickRef.current?.click(); };
  const accept = async (p: Photo) => { try { await be.acceptPhoto(id, p.id); await refresh(); } catch (e) { toast(errText(e)); } };
  const again = async (p: Photo) => { try { await be.recognizePhoto(id, p.id); await refresh(); } catch (e) { toast(errText(e)); } };
  const proceed = async () => {
    setBusy(true);
    try { await be.analyze(id); await qc.invalidateQueries({ queryKey: qk.one(id) }); nav(`/birdseye/${id}/products`); }
    catch (e) { toast(errText(e)); setBusy(false); }
  };

  if (pq.isLoading || bq.isLoading) return <Loading />;
  const ps = pq.data;
  if (!ps) return <Loading />;
  const walls = ps.items.filter((p) => !p.is_ceiling);
  const ceiling = ps.items.find((p) => p.is_ceiling);
  const qr = tq.data;

  return (
    <BePage testId="be1p" dock={(
      <Dock title="현장 사진" meta={<>{ps.counts.total}장 · 1 / 5</>}
        right={(
          <>
            <DockLink onClick={() => setQrOpen(true)} icon={<Icon name="link" size={13} />}>휴대폰으로 올리기</DockLink>
            <DockLink to={`/birdseye/${id}/space/plan`} icon={<Icon name="file" size={13} />}>도면도 있어요</DockLink>
          </>
        )}
        foot={(
          <>
            <PromptBar label="사진에 없는 정보" placeholder="사진에 없는 정보 (예: 상황판 벽 폭 9m, 운영석 2열 12석)" testId="be1p-facts"
              onSend={async (t) => { try { await be.facts(id, t); await refresh(); } catch (e) { toast(errText(e)); return false; } }} />
            <SubButton to={`/birdseye/${id}/space`}>이전</SubButton>
            <MainButton onClick={proceed} busy={busy} disabled={!ps.can_continue} reason="인식 완료되거나 그대로 쓸 사진이 1장 이상 있어야 해요" testId="be1p-next">이 사진으로 계속</MainButton>
          </>
        )} />
    )}>
      <Echo text={ps.echo} />
      <Agent text={ps.w_message} busy={ps.counts.recognizing > 0}>
        <div className="be-guide">
          <div className="be-guide__card">
            <b>촬영 가이드</b>
            <div className="be-row" style={{ gap: 12, alignItems: 'flex-start' }}>
              <DirDiagram />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <span>· 모서리에 서서 맞은편 벽까지 담기</span>
                <span>· 가로로, 사람이 적을 때 찍기</span>
                <span>· 창이 있는 벽은 역광 피하기</span>
                <span>· 바닥에 A4 용지를 두면 치수 보정</span>
              </div>
            </div>
            <span data-testid="be1p-dirs"><b>찍은 방향</b> {ps.dir_label}{!ps.has_ceiling && ' · 천장 없음'}</span>
          </div>
          <div className="be-guide__card" style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            {qr?.qr ? <QrCode rows={qr.qr} label="휴대폰 올리기 QR" /> : <div className="be-qr" style={{ background: 'var(--wm-surface-3)', borderRadius: 8 }} />}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <b>휴대폰으로 QR을 찍으면</b>
              <span>이 작업에 바로 올라가요</span>
              {qr && <span className="be-small be-muted" style={{ wordBreak: 'break-all' }}>{qr.url}</span>}
            </div>
          </div>
        </div>
        <div className="be-canvas-head">
          <span><b>사진 {ps.counts.total}장</b> <span className="be-muted" data-testid="be1p-head">{ps.head}</span></span>
          <button type="button" className="be-btn be-btn--sm" onClick={() => pick({})}><Icon name="plus" size={13} />사진 추가</button>
        </div>
        <div className="be-photos" data-testid="be1p-photos">
          {walls.map((p) => <PhotoCard key={p.id} p={p} onRetake={() => pick({ replace: p.id })} onAccept={() => accept(p)} onAgain={() => again(p)} />)}
          <div className="be-photo">
            <div className="be-photo__img">{ceiling ? <img src={ceiling.thumb_url} alt="천장 사진" /> : null}</div>
            <div className="be-photo__body">
              <b>천장 사진</b>
              <span className="be-photo__st" data-testid="be1p-ceiling">{ps.ceiling_label}</span>
              {!ceiling && <button type="button" className="be-link" onClick={() => pick({ ceiling: true })}>+ 추가하기</button>}
            </div>
          </div>
        </div>
        <PhotoDrop onFiles={(f) => void upload(f)} compact />
        {err && <div className="be-err" role="alert" data-testid="be1p-err">{err}</div>}
        <div className="be-sec">
          <div className="be-sec__head"><b>지금까지 파악한 공간</b><span>· 사진 {ps.basis_count}장 기준</span></div>
          <InfoChips items={ps.summary_chips ?? []} testId="be1p-summary" />
        </div>
      </Agent>
      <input ref={pickRef} type="file" accept={ACCEPT} multiple={!replace && !ceilingPick} hidden
        onChange={(e) => { void upload(Array.from(e.target.files ?? []), { replace: replace ?? undefined, ceiling: ceilingPick }); e.target.value = ''; }} />
      <Modal open={qrOpen} onClose={() => setQrOpen(false)} title="휴대폰으로 올리기" width={420} variant="dialog">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: 8 }}>
          {qr?.qr ? <QrCode rows={qr.qr} size={180} label="휴대폰 올리기 QR" /> : <span className="be-muted">QR을 만들지 못했어요</span>}
          <span>휴대폰으로 QR을 찍으면 이 작업에 바로 올라가요</span>
          {qr && <span className="be-small be-muted" style={{ wordBreak: 'break-all' }}>{qr.url} · 30분 동안 쓸 수 있어요</span>}
          <span className="be-small be-muted">휴대폰이 이 PC 와 같은 사내망에 있어야 해요</span>
        </div>
      </Modal>
    </BePage>
  );
}

function PhotoCard({ p, onRetake, onAccept, onAgain }: { p: Photo; onRetake: () => void; onAccept: () => void; onAgain: () => void }) {
  const bad = p.status === 'backlit' || p.status === 'dark' || p.status === 'blurry';
  const st = p.status === 'recognized' || p.status === 'accepted' ? 'be-photo__st be-photo__st--ok' : bad || p.status === 'failed' ? 'be-photo__st be-photo__st--warn' : 'be-photo__st';
  return (
    <div className={bad || p.status === 'failed' ? 'be-photo be-photo--check' : 'be-photo'} data-testid={`be1p-photo-${p.n}`}>
      <div className="be-photo__img"><img src={p.thumb_url} alt={p.wall_label || `사진 ${p.n}`} /><span className="be-photo__n">{p.n}</span></div>
      <div className="be-photo__body">
        <b>{p.wall_label || `사진 ${p.n}`}</b>
        <span className={st}>{p.status_label}</span>
        {bad && (
          <div className="be-photo__acts">
            <button type="button" className="be-btn be-btn--sm" onClick={onRetake}>다시 찍기</button>
            <button type="button" className="be-btn be-btn--sm" onClick={onAccept}>그대로 사용</button>
          </div>
        )}
        {p.status === 'failed' && <button type="button" className="be-link" onClick={onAgain}>다시 인식</button>}
      </div>
    </div>
  );
}

/** 「위에서 본 모습」 방향 도식 — 1 정면 · 2 왼쪽 · 3 창 쪽 · 4 출입구 쪽 */
function DirDiagram() {
  return (
    <svg width="76" height="76" viewBox="0 0 76 76" role="img" aria-label="위에서 본 모습">
      <rect x="8" y="8" width="60" height="60" rx="4" fill="var(--wm-surface-2)" stroke="var(--wm-line-dashed)" strokeWidth="2" />
      {[[38, 14, '1'], [14, 38, '2'], [62, 38, '3'], [38, 62, '4']].map(([x, y, t]) => (
        <g key={String(t)}>
          <circle cx={Number(x)} cy={Number(y)} r="7" fill="var(--wm-brand)" />
          <text x={Number(x)} y={Number(y) + 3.5} textAnchor="middle" fontSize="9" fontWeight="700" fill="var(--wm-surface)">{t}</text>
        </g>
      ))}
      <circle cx="38" cy="38" r="3" fill="var(--wm-text-muted)" />
    </svg>
  );
}
