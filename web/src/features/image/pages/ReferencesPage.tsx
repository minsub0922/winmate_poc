/**
 * IMG2R · 참조 이미지 고르기(§4.4) — 탭 4(사내 자산 · 내 생성 이미지 · 유관 사례 · 내 파일 올리기) · 검색 · 업종/스타일 필터 · 결과 8.
 * 고른 참조(최대 3)마다 따를 요소(다중) · 강도(약 · 중 · 강, 업로드는 중까지)를 정하고 「참조 n장 적용」(PUT) → IMG2.
 */
import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Button, cx, ErrorState, Icon, Img, Skeleton, useDropTarget } from '@/ui';
import { ApiError, errMessage, img, uploadFile, type Reference, type RefSearchItem } from '../api';
import { Echo, Loading, Pill, Screen, useImgShell, WSay } from '../components';
import { useInvalidate, useWork } from '../hooks';
import { checkUpload, refKind, route, UPLOAD_ACCEPT } from '../lib';

type Tab = 'kb' | 'mine' | 'cases' | 'upload';
type AspectKey = 'color_light' | 'composition' | 'placement' | 'material';
type Strength = 'low' | 'mid' | 'high';
const ASPECTS: Array<{ key: AspectKey; label: string }> = [
  { key: 'color_light', label: '색감 · 조명' }, { key: 'composition', label: '구도' }, { key: 'placement', label: '제품 배치' }, { key: 'material', label: '소재' },
];
const ASPECT_LABEL = Object.fromEntries(ASPECTS.map((a) => [a.key, a.label])) as Record<AspectKey, string>;
const LEVELS: Array<{ key: Strength; label: string }> = [{ key: 'low', label: '약' }, { key: 'mid', label: '중' }, { key: 'high', label: '강' }];

interface Picked {
  key: string;
  source_kind: Reference['source_kind'];
  source_ref?: string | null;
  file_id?: string | null;
  thumb_url?: string | null;
  label: string;
  source_label: string;
  aspects: AspectKey[];
  strength: Strength;
  upload: boolean;
  via?: 'picker' | 'topbar' | 'drop' | 'upload';
}

const fromRef = (r: Reference): Picked => ({
  key: r.source_ref ?? r.file_id ?? r.id, source_kind: r.source_kind, source_ref: r.source_ref, file_id: r.file_id, thumb_url: r.thumb_url, label: r.label,
  source_label: r.source_label, aspects: r.aspects as AspectKey[], strength: r.strength as Strength, upload: r.origin_kind === 'upload', via: r.via,
});
const fromItem = (it: RefSearchItem): Picked => ({
  key: it.source_ref, source_kind: it.source_kind, source_ref: it.source_ref, file_id: it.file_id, thumb_url: it.thumb_url, label: it.label,
  source_label: it.source_label, aspects: it.source_kind === 'kb_asset' ? ['composition'] : ['color_light'], strength: 'mid', upload: it.source_kind === 'upload',
});
const sameKey = (a: string, b: string) => a.replace(/^(kb|img):image:/, '') === b.replace(/^(kb|img):image:/, '');

export default function ReferencesPage() {
  const { workId = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const wq = useWork(workId);
  const w = wq.data;
  const [tab, setTab] = useState<Tab>('kb');
  const [q, setQ] = useState<string | null>(null);
  const [dq, setDq] = useState<string | null>(null);
  const [industry, setIndustry] = useState<string | null | undefined>(undefined);
  const [style, setStyle] = useState<'all' | 'photo' | 'illustration'>('all');
  const [picked, setPicked] = useState<Picked[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<'apply' | 'run' | 'upload' | null>(null);
  const [over, setOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (w && picked === null) setPicked((w.references ?? []).map(fromRef)); }, [w, picked]);
  useEffect(() => { if (w && industry === undefined) setIndustry(w.prefill?.industry ? (w.prefill.industry_chips?.[0] ?? null) : null); }, [w, industry]);
  useEffect(() => { const t = window.setTimeout(() => setDq(q), 300); return () => window.clearTimeout(t); }, [q]);

  const searchTab = tab === 'upload' ? null : tab;
  const res = useQuery({
    queryKey: ['image', 'refsearch', workId, searchTab, dq, industry ?? null, style],
    queryFn: () => img.refSearch({ tab: searchTab!, q: dq ?? undefined, industry: searchTab === 'kb' ? industry : null, style, work_id: workId, limit: 8 }),
    enabled: !!searchTab && !!w && industry !== undefined, staleTime: 60_000, placeholderData: (prev) => prev,
  });
  useEffect(() => { if (q === null && res.data && searchTab === 'kb') setQ(res.data.query); }, [res.data, q, searchTab]);

  const list = picked ?? [];
  const toggle = (it: Picked) => {
    setMsg(null);
    const has = list.some((p) => sameKey(p.key, it.key));
    if (has) { setPicked(list.filter((p) => !sameKey(p.key, it.key))); return; }
    if (list.length >= 3) { setMsg('참조는 3장까지 고를 수 있어요'); return; }
    setPicked([...list, it]);
  };
  const update = (key: string, patch: Partial<Picked>) => setPicked(list.map((p) => (p.key === key ? { ...p, ...patch } : p)));

  const addShellImages = async (refs: string[]) => {
    const out: string[] = [];
    let cur = [...list];
    for (const r of refs) {
      if (cur.length >= 3) { setMsg('참조는 3장까지 고를 수 있어요'); break; }
      if (cur.some((p) => sameKey(p.key, r))) continue;
      const k = refKind(r);
      let label = '이미지 검색에서 고른 이미지';
      let thumb: string | null = null;
      let source = '이미지 검색';
      try {
        if (k.ns === 'kb') {
          const meta = await fetch(`/api/kb/v1/images/${encodeURIComponent(k.id)}`, { credentials: 'same-origin' }).then((x) => (x.ok ? x.json() : null));
          label = meta?.title || meta?.alt || label;
          thumb = meta?.thumb_url ?? `/api/kb/v1/images/${k.id}/thumb`;
          source = '사내 자산 · 이미지 검색';
        } else if (k.ns === 'img') {
          const d = await img.image(k.id);
          label = d.title; thumb = d.thumb_url ?? null; source = '내 생성 이미지 · AI 생성';
        }
      } catch { /* 이름 없이도 넣는다 */ }
      cur = [...cur, { key: r, source_kind: 'topbar', source_ref: r, thumb_url: thumb, label, source_label: source, aspects: k.ns === 'kb' ? ['composition'] : ['color_light'], strength: 'mid', upload: false, via: 'topbar' }];
      out.push(r);
    }
    setPicked(cur);
    return out;
  };
  const onFiles = async (files: FileList | File[]) => {
    const f = Array.from(files)[0];
    if (!f) return;
    const bad = checkUpload(f);
    if (bad) { setMsg(bad); return; }
    if (list.length >= 3) { setMsg('참조는 3장까지 고를 수 있어요'); return; }
    setBusy('upload'); setMsg(null);
    try {
      const up = await uploadFile(f, { confidential: true, purpose: 'image_reference' });
      setPicked([...list, { key: up.id, source_kind: 'upload', file_id: up.id, source_ref: null, thumb_url: `/api/files/v1/files/${up.id}/thumbnail?w=320`,
        label: f.name.replace(/\.[^.]+$/, '') || '올린 사진', source_label: '내 파일 · 업로드', aspects: ['color_light'], strength: 'mid', upload: true, via: 'upload' }]);
    } catch (e) { setMsg(`올리지 못했어요 · ${errMessage(e)}`); } finally { setBusy(null); }
  };

  const apply = async (andRun: boolean) => {
    if (!w) return;
    setBusy(andRun ? 'run' : 'apply'); setMsg(null);
    try {
      await img.setReferences(w.id, list.map((p) => ({
        source_kind: p.source_kind, source_ref: p.source_ref ?? undefined, file_id: p.file_id ?? undefined, aspects: p.aspects, strength: p.strength, label: p.label,
        via: p.via ?? (p.upload ? 'upload' : 'picker'),
      })), 'picker');
      await inv.work(w.id);
      if (andRun) {
        const acc = await img.startRun(w.id, { kind: 'initial', count: w.conditions.count });
        void inv.gallery();
        nav(route.run(w.id, acc.run_id));
      } else nav(route.conditions(w.id));
    } catch (e) {
      if (e instanceof ApiError && e.code === 'RUN_IN_PROGRESS' && typeof e.details.run_id === 'string') nav(route.run(w.id, e.details.run_id));
      else setMsg(errMessage(e));
    } finally { setBusy(null); }
  };

  useImgShell({
    title: w?.title ?? '새 작업', step: 2, accepts: ['image'], addable: ['image'], added: list.map((p) => p.source_ref ?? '').filter(Boolean),
    onAdd: async (_t, refs) => ({ added: await addShellImages(refs) }),
  });
  const drop = useDropTarget({ accept: ['image'], onDrop: async (p) => (await addShellImages([p.ref])).length > 0 });

  const items = res.data?.items ?? [];
  const roleOf = useMemo(() => (key: string) => {
    const i = list.findIndex((p) => sameKey(p.key, key));
    return i < 0 ? null : { n: i + 1, role: list[i].aspects.map((a) => ASPECT_LABEL[a]).join(' · ') };
  }, [list]);

  if (wq.isLoading) return <Loading />;
  if (!w) return <div className="img-center"><ErrorState message="작업을 불러오지 못했어요" onRetry={() => wq.refetch()} /></div>;
  const count = w.conditions.count;
  const TABS: Array<{ key: Tab; label: string }> = [
    { key: 'kb', label: '사내 자산' }, { key: 'mine', label: '내 생성 이미지' }, { key: 'cases', label: '유관 사례' }, { key: 'upload', label: '내 파일 올리기' },
  ];
  const onDragFiles = (e: DragEvent) => { if (e.dataTransfer?.types?.includes('Files')) { e.preventDefault(); setOver(true); } };
  return (
    <Screen testid="img2r" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span>참조 이미지 {list.length}장 · 무엇을 따를지<small> · 2 / 3</small></span>
            <span className="img-row img-hint img-hint--sm" style={{ gap: 6 }}><Icon name="info" size={13} />참조 속 사람 얼굴 · 타사 로고는 따라 그리지 않아요</span>
          </div>
          {list.length > 0 && (
            <div style={{ padding: '10px 18px 0 18px', display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="img2r-picked">
              {list.map((p, i) => (
                <div key={p.key} className="img-picked" data-testid="img2r-pick">
                  <span className="img-picked__thumb"><Img src={p.thumb_url} alt={p.label} /><span className="img-picked__num">{i + 1}</span></span>
                  <span className="img-picked__name"><b title={p.label}>{p.label}</b><span>{p.source_label}</span></span>
                  <span className="img-row img-grow" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-label={`${p.label} 따를 요소`}>
                    {ASPECTS.map((a) => (
                      <Pill key={a.key} h={26} on={p.aspects.includes(a.key)}
                        onClick={() => update(p.key, { aspects: p.aspects.includes(a.key) ? (p.aspects.length > 1 ? p.aspects.filter((x) => x !== a.key) : p.aspects) : [...p.aspects, a.key] })}>
                        {a.label}
                      </Pill>
                    ))}
                  </span>
                  <span className="img-label" style={{ flexShrink: 0 }}>강도</span>
                  <span className="img-segb img-segb--sm" role="group" aria-label={`${p.label} 강도`}>
                    {LEVELS.map((l) => (
                      <button key={l.key} type="button" aria-pressed={p.strength === l.key} disabled={p.upload && l.key === 'high'}
                        title={p.upload && l.key === 'high' ? '올린 사진은 ‘중’까지 따를 수 있어요' : undefined} onClick={() => update(p.key, { strength: l.key })}>{l.label}</button>
                    ))}
                  </span>
                  <button type="button" className="img-xbtn" aria-label="참조 빼기" onClick={() => toggle(p)}><Icon name="x" size={14} /></button>
                </div>
              ))}
            </div>
          )}
          <div className="wm-composer__foot" style={{ justifyContent: 'space-between' }}>
            <span className={cx('img-hint', msg && 'img-err')} role={msg ? 'alert' : undefined} data-testid="img2r-msg">{msg ?? '적용하면 상세 조건의 참조 이미지로 들어갑니다'}</span>
            <div className="img-row">
              <Button h={44} onClick={() => nav(route.conditions(w.id))}>취소</Button>
              <Button h={44} loading={busy === 'run'} disabled={!!busy || (list.length === 0 && w.description.trim().length < 2)} onClick={() => void apply(true)}
                disabledReason="참조를 고르거나 장면 설명을 적어 주세요">적용하고 바로 {count}장 생성</Button>
              <Button h={44} variant="primary" loading={busy === 'apply'} disabled={!!busy} onClick={() => void apply(false)} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>
                참조 {list.length}장 적용
              </Button>
            </div>
          </div>
        </div>
      </div>
    }>
      <Echo head={w.kind_label} text={w.description || null} />
      <WSay text="참조할 이미지를 골라 주세요. 사내 자산은 브랜드 검수를 마친 이미지라 색감과 구도를 그대로 따라도 됩니다. 고른 이미지마다 무엇을 따를지 정할 수 있어요.">
        <div className="img-card" {...drop.props} style={drop.dragging ? { borderColor: 'var(--wm-brand)', boxShadow: 'var(--wm-ring-drop)' } : undefined}>
          <div className="img-card__bar" style={{ justifyContent: 'space-between', padding: '0 14px' }}>
            <div role="tablist" aria-label="참조 이미지 출처" style={{ display: 'flex', gap: 2, height: 44 }}>
              {TABS.map((t) => (
                <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} className="img-rtab" onClick={() => { setTab(t.key); setMsg(null); }}>
                  {t.key === 'upload' && <Icon name="upload" size={13} />}{t.label}
                </button>
              ))}
            </div>
            {tab !== 'upload' && (
              <div className="img-rsearch">
                <label htmlFor="img-rq" className="wm-sr-only">참조 이미지 검색</label>
                <Icon name="search" size={13} color="var(--wm-text-muted)" />
                <input id="img-rq" value={q ?? ''} onChange={(e) => setQ(e.target.value)} placeholder="참조 이미지 검색" autoComplete="off" />
              </div>
            )}
          </div>
          {tab === 'upload' ? (
            <div className={cx('img-upload', over && 'img-upload--over')} role="button" tabIndex={0} data-testid="img2r-upload"
              onClick={() => fileRef.current?.click()} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileRef.current?.click(); } }}
              onDragEnter={onDragFiles} onDragOver={onDragFiles} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); if (e.dataTransfer.files?.length) void onFiles(e.dataTransfer.files); }}>
              <Icon name="upload" size={22} />
              <b style={{ color: 'var(--wm-text)' }}>{busy === 'upload' ? '올리는 중…' : '참조할 사진을 끌어 놓거나 눌러서 올려 주세요'}</b>
              <span className="img-hint img-hint--sm">JPG · PNG · HEIC · 20MB 이하 · 올린 사진은 강도 ‘중’까지 따를 수 있어요</span>
              <input ref={fileRef} type="file" accept={UPLOAD_ACCEPT} hidden onChange={(e) => { if (e.target.files) void onFiles(e.target.files); e.target.value = ''; }} />
            </div>
          ) : (
            <>
              <div className="img-rfilters">
                {tab === 'kb' && (
                  <>
                    <span className="img-label" style={{ marginRight: 2 }}>업종</span>
                    {(res.data?.industry_chips ?? w.prefill?.industry_chips ?? []).map((c) => (
                      <Pill key={c} h={28} on={industry === c} onClick={() => setIndustry(industry === c ? null : c)}>{c}</Pill>
                    ))}
                    <span className="img-vsep" style={{ height: 16 }} />
                  </>
                )}
                <span className="img-label" style={{ marginRight: 2 }}>스타일</span>
                {([['all', '전체'], ['photo', '실사'], ['illustration', '일러스트']] as const).map(([k, l]) => (
                  <Pill key={k} h={28} on={style === k} onClick={() => setStyle(k)}>{l}</Pill>
                ))}
                <span style={{ flex: 1 }} />
                <span className="img-hint img-hint--sm" data-testid="img2r-head">
                  {res.data ? <><b className="wm-num" style={{ color: 'var(--wm-text)' }}>{res.data.total}</b>{res.data.head.replace(/^\d+\s*/, '')}</> : ' '}
                </span>
              </div>
              {res.isError && <ErrorState message="이미지를 불러오지 못했어요" onRetry={() => res.refetch()} />}
              {!res.isError && (
                <div className="img-rgrid" data-testid="img2r-grid">
                  {res.isLoading && Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} h={100} r={10} />)}
                  {!res.isLoading && items.length === 0 && (
                    <div className="img-hint" style={{ gridColumn: '1 / -1', padding: '18px 0', textAlign: 'center' }}>
                      {tab === 'mine' ? '아직 저장한 생성 이미지가 없어요' : '맞는 이미지가 없어요'}
                      {industry && tab === 'kb' && <> · <button type="button" className="wm-btn wm-btn--h28" onClick={() => setIndustry(null)}>업종 필터 풀기</button></>}
                    </div>
                  )}
                  {items.map((it) => {
                    const role = roleOf(it.source_ref);
                    return (
                      <button key={it.source_ref} type="button" className="img-rtile" aria-pressed={!!role} aria-label={it.label} title={`${it.label} · ${it.source_label}`}
                        onClick={() => toggle(fromItem(it))} data-rights={it.rights}>
                        <Img src={it.thumb_url} alt={it.alt ?? it.label} />
                        {role && <><span className="img-rtile__num">{role.n}</span><span className="img-rtile__role">{role.role}</span></>}
                        <span className="img-rtile__label">{it.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </WSay>
    </Screen>
  );
}
