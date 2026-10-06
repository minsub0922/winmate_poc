/** BE5Z — 존 포인트 지정(`/birdseye/:id/zones`, `?scenario=sc_…` 장면 연결 모드, §4.12): 번호 포인트 · 존 카드 · W 제안 · 시트 레이아웃 3. */
import { useEffect, useRef, useState, type PointerEvent as RPointerEvent } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import { useJob } from '@/api/jobs';
import { Icon, toast } from '@/ui';
import { be, errText, qk, useBe, useCuts, useZones, type S, type ZonePoint } from '../api';
import { Agent, BePage, Dock, FieldLabel, Loading, MainButton, Pill, PromptBar, SubButton, useBeShell } from '../ui';

const LAYOUTS = [{ code: 'ZP-A', label: '번호 콜아웃' }, { code: 'ZP-B', label: '존 확대 컷' }, { code: 'ZP-C', label: '고객 동선 따라가기' }] as const;

export default function ZonesPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const scenario = sp.get('scenario');
  const bq = useBe(id);
  const cq = useCuts(id);
  const b = bq.data;
  const cuts = (cq.data ?? []).filter((c) => ['done', 'check', 'draft'].includes(c.status) && !c.before);
  const cutId = sp.get('cut') ?? b?.primary_cut_id ?? cuts[0]?.id;
  const zq = useZones(id, cutId ?? undefined);
  const [openZ, setOpenZ] = useState<string | null>(null);
  const [autoJob, setAutoJob] = useState<string | null>(null);
  const [rwJob, setRwJob] = useState<string | null>(null);
  const started = useRef(false);
  const scenes = useQuery({
    queryKey: ['scenario', scenario, 'scenes'], enabled: !!scenario,
    queryFn: async () => unwrap(await api.scenario.GET('/v1/scenarios/{sc_id}/scenes', { params: { path: { sc_id: scenario! } } })),
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ['be', id, 'zones'] });
  useJob(autoJob ?? (zq.data?.running ? zq.data.job_id : null), { onDone: () => { setAutoJob(null); void refresh(); } });
  useJob(rwJob, { onDone: () => { setRwJob(null); void refresh(); } });
  useBeShell(b, 5);
  useEffect(() => {
    if (started.current || !zq.data || !cutId || zq.data.running) return;
    if (!zq.data.points.length && !(zq.data.suggestions ?? []).length) {
      started.current = true;
      be.zonesAuto(id, cutId).then((r) => setAutoJob(r.job_id)).catch((e) => toast(errText(e)));
    }
  }, [zq.data, cutId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (bq.isLoading || cq.isLoading || zq.isLoading) return <Loading />;
  const zv = zq.data;
  if (!zv || !cutId) {
    return <BePage><Agent text="존 포인트를 찍을 완성 컷이 아직 없어요." /><SubButton to={`/birdseye/${id}/result`}>결과로</SubButton></BePage>;
  }
  const points = zv.points;
  const patch = async (z: ZonePoint, body: S['ZonePatch']) => {
    try { await be.patchZone(z.id, { ...body, cut_id: cutId }); await refresh(); } catch (e) { toast(errText(e)); }
  };
  const add = async (u: number, v: number) => {
    try { const z = await be.addZone(id, { cut_id: cutId, u, v }); await refresh(); setOpenZ(z.id); } catch (e) { toast(errText(e)); }
  };
  const accept = async (sid: string) => { try { await be.addZone(id, { cut_id: cutId, from_suggestion: sid }); await refresh(); } catch (e) { toast(errText(e)); } };
  const skip = async (sid: string) => { try { await be.patchZone(sid, { status: 'dismissed', cut_id: cutId }); await refresh(); } catch (e) { toast(errText(e)); } };
  const renumber = async () => { try { await be.renumber(id, cutId); await refresh(); } catch (e) { toast(errText(e)); } };
  const setLayout = async (code: string) => { try { await be.patch(id, { zone_layout: code as never }); await refresh(); } catch (e) { toast(errText(e)); } };
  const opened = points.find((p) => p.id === openZ) ?? points[0];

  return (
    <BePage testId="be5z" dock={(
      <Dock title="존 포인트 지정" meta={<>{points.length}곳</>}
        foot={(
          <>
            <PromptBar label="포인트 문구 수정 요청" placeholder="문구 다듬기 (예: 4곳 모두 고객 관점의 한 문장으로)" busy={!!rwJob} testId="be5z-rewrite"
              onSend={async (t) => { try { const r = await be.rewrite(id, t, openZ ? [openZ] : undefined); setRwJob(r.job_id); } catch (e) { toast(errText(e)); return false; } }} />
            {scenario ? <SubButton to={`/scenario/${scenario}`}>시나리오로 돌아가기</SubButton> : <SubButton to={`/birdseye/${id}/result`}>결과로</SubButton>}
            <MainButton onClick={() => nav(`/birdseye/${id}/export?map=ZP`)} disabled={!points.length} testId="be5z-send">제안서 '존별 포인트'로</MainButton>
          </>
        )}>
        <div className="be-row">
          <FieldLabel>시트 레이아웃</FieldLabel>
          {LAYOUTS.map((l) => <Pill key={l.code} on={zv.preview.code === l.code} onClick={() => void setLayout(l.code)} testId={`be5z-layout-${l.code}`}>{l.label}</Pill>)}
        </div>
      </Dock>
    )}>
      <Agent text={zv.w_message} busy={zv.running || !!autoJob}>
        <ZoneImage url={zv.cut_url} label={zv.cut_label} points={points} selected={opened?.id} onSelect={setOpenZ}
          onMove={(z, u, v) => void patch(z, { u, v })} onAdd={(u, v) => void add(u, v)} />
        <div className="be-zprev" data-testid="be5z-preview">
          <span className="be-code">{zv.preview.code}</span>
          <div className="be-zprev__meta">
            <span>공간마다 무엇이 달라지나 · 제안서 미리보기</span>
            <b>조감도 · 존별 포인트 시트 {zv.preview.code}</b>
            <span>{zv.preview.layout_label} · 포인트 {zv.preview.count}곳</span>
            <span>{zv.proposal_label ?? '연결된 제안서 없음'}</span>
          </div>
        </div>
        <div className="be-canvas-head">
          <span><b>존 포인트</b> <span className="be-muted">· {points.length}</span></span>
          <span className="be-row">
            <button type="button" className="be-btn be-btn--sm" onClick={() => void renumber()} data-testid="be5z-renumber">동선 순서로 번호</button>
            <button type="button" className="be-btn be-btn--sm" aria-label="포인트 추가" onClick={() => void add(0.5, 0.5)}><Icon name="plus" size={14} /></button>
          </span>
        </div>
        <div className="be-zcards" data-testid="be5z-cards">
          {points.map((z) => (
            <ZoneCard key={z.id} z={z} open={opened?.id === z.id} onOpen={() => setOpenZ(z.id)} onPatch={(body) => void patch(z, body)}
              scenes={scenes.data?.items ?? []} />
          ))}
        </div>
        {(zv.suggestions ?? []).map((s) => (
          <div key={s.id} className="be-sugg" data-testid="be5z-sugg">
            <div><b>{s.title}</b>{s.question}</div>
            <button type="button" className="be-btn be-btn--sm" onClick={() => void accept(s.id)}>{s.add_label}</button>
            <button type="button" className="be-btn be-btn--sm" onClick={() => void skip(s.id)}>넘기기</button>
          </div>
        ))}
        {scenario && <Link className="be-link" to={`/scenario/${scenario}`}>시나리오 장면 {scenes.data?.items.length ?? 0}개와 연결 중</Link>}
      </Agent>
    </BePage>
  );
}

function ZoneImage({ url, label, points, selected, onSelect, onMove, onAdd }: {
  url?: string | null; label: string; points: ZonePoint[]; selected?: string; onSelect: (id: string) => void;
  onMove: (z: ZonePoint, u: number, v: number) => void; onAdd: (u: number, v: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<{ id: string; u: number; v: number; moved: boolean } | null>(null);
  const uv = (e: { clientX: number; clientY: number }) => {
    const r = ref.current!.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))] as const;
  };
  const down = (e: RPointerEvent, z: ZonePoint) => {
    e.stopPropagation();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    onSelect(z.id);
    setDrag({ id: z.id, u: z.u ?? 0.5, v: z.v ?? 0.5, moved: false });
  };
  return (
    <div className="be-sec">
      <div className="be-canvas-head">
        <span className="be-row"><span className="be-prodchip">{label}</span><button type="button" className="be-pill be-pill--on" aria-pressed>포인트</button></span>
        <span className="be-small be-muted">빈 곳을 눌러 추가 · 번호를 끌어 이동</span>
      </div>
      <div ref={ref} className="be-zimg" data-testid="be5z-image"
        onPointerMove={(e) => { if (drag) { const [u, v] = uv(e); setDrag({ ...drag, u, v, moved: true }); } }}
        onPointerUp={() => { if (drag) { const z = points.find((p) => p.id === drag.id); if (z && drag.moved) onMove(z, Math.round(drag.u * 1000) / 1000, Math.round(drag.v * 1000) / 1000); setDrag(null); } }}
        onClick={(e) => { if (!drag) { const [u, v] = uv(e); onAdd(Math.round(u * 1000) / 1000, Math.round(v * 1000) / 1000); } }}>
        {url ? <img src={url} alt="조감도 · 존 포인트 기준 컷" /> : null}
        {points.filter((z) => z.u != null && z.v != null).map((z) => {
          const u = drag?.id === z.id ? drag.u : z.u!;
          const v = drag?.id === z.id ? drag.v : z.v!;
          return (
            <span key={z.id} className={selected === z.id ? 'be-zpin be-zpin--sel' : 'be-zpin'} style={{ left: `${u * 100}%`, top: `${v * 100}%` }}
              role="button" aria-label={`${z.n}번 ${z.name}`} onPointerDown={(e) => down(e, z)} onClick={(e) => e.stopPropagation()} data-testid={`be5z-pin-${z.n}`}>
              {z.n}
            </span>
          );
        })}
      </div>
    </div>
  );
}

type SceneItem = { id: string; no: number; title?: string; short_title?: string };

function ZoneCard({ z, open, onOpen, onPatch, scenes }: { z: ZonePoint; open: boolean; onOpen: () => void; onPatch: (b: S['ZonePatch']) => void; scenes: SceneItem[] }) {
  const [name, setName] = useState(z.name);
  const [text, setText] = useState(z.text);
  useEffect(() => { setName(z.name); setText(z.text); }, [z.name, z.text]);
  const links = z.links ?? [];
  const removeLink = (i: number) => onPatch({ links: links.filter((_, k) => k !== i) });
  const addScene = (s: SceneItem) => onPatch({ links: [...links, { kind: 'scene', label: `장면 ${s.no}`, ref: s.id }] });
  return (
    <div className={open ? 'be-zcard be-zcard--open' : 'be-zcard'} data-testid={`be5z-card-${z.n}`}>
      <button type="button" className="be-zcard__row" onClick={onOpen} aria-expanded={open}>
        <span className="be-zcard__n">{z.n}</span><b>{z.name}</b>{!open && <span>{z.text}</span>}
      </button>
      {open && (
        <div className="be-zcard__body">
          <label className="be-field"><span>존 이름</span>
            <input value={name} maxLength={14} onChange={(e) => setName(e.target.value)} onBlur={() => name !== z.name && onPatch({ name })} />
          </label>
          <label className="be-field"><span>포인트 문구</span>
            <textarea value={text} maxLength={60} onChange={(e) => setText(e.target.value)} onBlur={() => text !== z.text && onPatch({ text })} />
          </label>
          <div className="be-zlinks">
            <span className="be-flabel">연결</span>
            {links.map((l, i) => (
              <span key={`${l.kind}-${i}`} className={l.kind === 'need' ? 'be-zlink be-zlink--need' : l.kind === 'scene' ? 'be-zlink be-zlink--scene' : 'be-zlink'}>
                {l.label}<button type="button" aria-label={`${l.label} 연결 빼기`} onClick={() => removeLink(i)}>×</button>
              </span>
            ))}
            {scenes.filter((s) => !links.some((l) => l.kind === 'scene' && l.ref === s.id)).slice(0, 6).map((s) => (
              <button key={s.id} type="button" className="be-pill" onClick={() => addScene(s)}>+ 장면 {s.no}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

