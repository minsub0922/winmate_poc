/**
 * SC4E · 장면 편집(§4.11) — 왼쪽 장면 목록(상태 · 장면 추가 · 나머지 장면 다시 생성), 버전 · 되돌리기 · 삭제,
 * 제목 · 이야기(바뀐 곳 강조) · 등장인물 · 솔루션 동작 · 제품 활용(「새로」), 장면 이미지(stale 경고 · 넘어가는 것 · 다시 만들기 · 고르기),
 * 이 장면만 다시 쓰기(더 짧게 · {역할} 시점으로 · 솔루션 동작 더 구체적으로 · 지시문), 취소 · 변경 저장(locked).
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx, Icon, Img, useConfirm } from '@/ui';
import { useOpenPopover, useShellPage } from '@/shell';
import { errMessage, scApi, type SceneOut, type SceneProduct, type SceneSolution } from '../api';
import { qk, useInvalidate, useScenario, waitJob } from '../hooks';
import { route, SECTION, stepper, withJosa } from '../lib';
import { Ask, Ico, Loading, Note, P, StatusIcon, useOutside } from '../parts';

interface Draft { title: string; story: string; characters: Array<{ role_id: string; name: string; is_new: boolean }>; solutions: SceneSolution[]; products: SceneProduct[] }
const draftOf = (s: SceneOut): Draft => ({
  title: s.title ?? '', story: s.story ?? '', characters: (s.characters ?? []).map((c) => ({ role_id: c.role_id, name: c.name ?? '', is_new: !!c.is_new })),
  solutions: (s.solutions ?? []).map((x) => ({ ...x })), products: (s.products ?? []).map((x) => ({ ...x })),
});

export default function ScenePage() {
  const { id = '', sceneId = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const scenes = useQuery({ queryKey: qk.scenes(id), queryFn: () => scApi.scenes(id), enabled: !!id });
  const scene = useQuery({ queryKey: qk.scene(sceneId), queryFn: () => scApi.scene(sceneId), enabled: !!sceneId });
  const tl = useQuery({ queryKey: qk.timeline(id), queryFn: () => scApi.timeline(id), enabled: !!id, staleTime: 10_000 });
  const prefill = useQuery({ queryKey: ['scenario', 'prefill', sceneId, scene.data?.version], queryFn: () => scApi.imagePrefill(sceneId), enabled: !!scene.data });
  const actions = useQuery({ queryKey: ['scenario', 'actions', (sc.data?.solution_picks ?? []).map((x) => x.solution_id).join(',')],
    queryFn: () => scApi.actions((sc.data?.solution_picks ?? []).map((x) => x.solution_id)), enabled: !!sc.data && sc.data.type === 'with' });
  const [draft, setDraft] = useState<Draft | null>(null);
  const [editStory, setEditStory] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [menu, setMenu] = useState<'char' | 'sol' | 'prod' | null>(null);
  const menuRef = useOutside<HTMLDivElement>(!!menu, () => setMenu(null));
  const { confirm, dialog } = useConfirm();
  const openPop = useOpenPopover();

  useEffect(() => { if (scene.data) setDraft(draftOf(scene.data)); setEditStory(false); }, [scene.data?.id, scene.data?.version]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!id) return;
    scApi.syncImages(id).then((r) => { if (r.attached?.length) { void scene.refetch(); void scenes.refetch(); } }).catch(() => undefined);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const s = scene.data;
  const dirty = useMemo(() => !!(s && draft && JSON.stringify(draftOf(s)) !== JSON.stringify(draft)), [s, draft]);
  useShellPage({
    section: SECTION, title: sc.data?.title ?? '', stepper: stepper(4), sidebarGroup: 'scenario',
    addable: ['image'], accepts: [],
    onAdd: async (type, refs) => {
      if (type !== 'image' || !refs.length) return { added: [] };
      try {
        await scApi.attachImage(sceneId, { image_ref: refs[0], source: 'picked' });
        await scene.refetch(); await scenes.refetch();
        return { added: [refs[0]] };
      } catch (e) { setErr(errMessage(e)); return { added: [] }; }
    },
  });
  if (sc.isLoading || scene.isLoading || !sc.data || !s || !draft) return <Loading />;
  const scenario = sc.data;
  const items = scenes.data?.items ?? [];
  const locked = scenes.data?.locked_nos ?? [];
  const isWith = scenario.type === 'with';
  const roles = tl.data?.roles ?? [];

  const go = async (to: string) => {
    if (dirty && !(await confirm({ title: '저장하지 않은 변경이 있어요', message: '이 장면에서 고친 내용을 버리고 이동할까요?', confirmLabel: '버리고 이동' }))) return;
    nav(to);
  };
  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key); setErr(null);
    try { await fn(); } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const save = () => run('save', async () => {
    const orig = draftOf(s);
    const body: Parameters<typeof scApi.patchScene>[1] = { if_version: s.version };
    if (draft.title !== orig.title) body.title = draft.title;
    if (draft.story !== orig.story) body.story = draft.story;
    if (JSON.stringify(draft.characters) !== JSON.stringify(orig.characters)) body.characters = draft.characters.map((c) => c.role_id);
    if (JSON.stringify(draft.solutions) !== JSON.stringify(orig.solutions)) body.solutions = draft.solutions;
    if (JSON.stringify(draft.products) !== JSON.stringify(orig.products)) body.products = draft.products;
    if (Object.keys(body).length > 1) await scApi.patchScene(sceneId, body);
    await inv.scenes(id); await inv.sc(id);
    nav(route.result(id));
  });
  const rewrite = (key: string, body: Parameters<typeof scApi.rewrite>[1]) => run(key, async () => {
    const acc = await scApi.rewrite(sceneId, body);
    const r = await waitJob(acc.job_id, { timeoutMs: 120_000 });
    if (r.status !== 'succeeded') throw new Error(r.error?.message || '이 장면을 다시 쓰지 못했어요');
    await scene.refetch(); await scenes.refetch();
  });
  const restore = () => run('restore', async () => { await scApi.restoreScene(sceneId, s.version - 1); await scene.refetch(); await scenes.refetch(); });
  const remove = async () => {
    const yes = await confirm({ title: `${withJosa(`장면 ${s.no}`, '을', '를')} 지울까요? 번호가 다시 매겨져요.`, tone: 'danger', confirmLabel: '지우기' });
    if (!yes) return;
    await run('del', async () => { await scApi.deleteScene(sceneId); await inv.scenes(id); await inv.sc(id); nav(route.result(id)); });
  };
  const addScene = () => run('add', async () => { const n = await scApi.addScene(id, sceneId); await inv.scenes(id); nav(route.scene(id, n.id)); });
  const regen = () => run('regen', async () => { const g = await scApi.generate(id, 'unlocked'); await inv.sc(id); nav(route.generate(id, g.job_id)); });
  const makeImage = () => run('img', async () => { const r = await scApi.imageRequest(sceneId); nav(r.image_route); });

  const img = s.image;
  const stale = s.image_stale as { missing?: string[] } | null | undefined;
  const pov = (s.pov_role_ids ?? []).map((rid) => draft.characters.find((c) => c.role_id === rid)?.name ?? roles.find((r) => r.id === rid)?.name).filter(Boolean) as string[];
  const changed = s.changed_sentences ?? [];
  const charOptions = roles.filter((r) => !draft.characters.some((c) => c.role_id === r.id));
  const solOptions = (actions.data?.items ?? []).filter((a) => !draft.solutions.some((x) => x.solution_id === a.solution_id && x.action_code === a.action_code));
  const prodOptions = (scenario.product_picks ?? []).filter((p) => !draft.products.some((x) => (x.ref && x.ref === p.ref) || x.short === p.short));
  const lockedLine = locked.length ? `직접 고친 ${withJosa(`장면 ${locked.join(' · ')}`, '은', '는')} 그대로 둡니다` : '';

  return (
    <section className="sc-screen" data-testid="sc4e">
      <div className="sc-edit">
        <aside className="sc-elist" data-testid="sc4e-list">
          <div className="sc-row" style={{ justifyContent: 'space-between', padding: '0 2px 4px 2px' }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>장면 <span className="wm-num" style={{ color: 'var(--wm-text-muted)', fontWeight: 600 }}>{items.length}</span></div>
            <button type="button" className="sc-link" style={{ fontSize: 12 }} onClick={() => void go(route.timeline(id))} data-testid="sc4e-timeline">
              <Ico d="M4 6h16M4 12h10M4 18h6" size={12} sw={2.2} />타임라인 편집
            </button>
          </div>
          <div className="sc-elist__items">
            {items.map((x) => {
              const on = x.id === sceneId;
              const stat = on ? '편집 중' : x.image_stale ? '이미지 확인' : !x.image ? '이미지 없음' : '';
              return (
                <button key={x.id} type="button" className={cx('sc-erow', on && 'sc-erow--on')} onClick={() => !on && void go(route.scene(id, x.id))} data-testid="sc4e-row" aria-current={on || undefined}>
                  <span className="sc-row" style={{ gap: 7 }}>
                    <svg width="10" height="14" viewBox="0 0 10 14" aria-hidden="true" style={{ flexShrink: 0 }}>{[[2.5, 2.5], [7.5, 2.5], [2.5, 7], [7.5, 7], [2.5, 11.5], [7.5, 11.5]].map(([cx_, cy]) => <circle key={`${cx_}${cy}`} cx={cx_} cy={cy} r="1.3" className="sc-art-mid" />)}</svg>
                    <span className="wm-num" style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-brand)' }}>{x.time ?? ''}</span>
                    <span style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>장면 {x.no}</span>
                    <span style={{ flex: 1 }} />
                    {stat && <span className={cx('sc-erow__stat', on && 'sc-erow__stat--on', stat === '이미지 확인' && 'sc-erow__stat--warn')} data-testid="sc4e-row-stat">{stat}</span>}
                  </span>
                  <span className="sc-erow__title">{x.short_title || x.title}</span>
                  {(x.solution_chips ?? [])[0] && <span style={{ display: 'flex' }}><span className="sc-erow__sol">{x.solution_chips?.[0]}</span></span>}
                </button>
              );
            })}
            <button type="button" className="sc-eadd" onClick={() => void addScene()} disabled={busy === 'add'} data-testid="sc4e-add"><Ico d={P.plus} size={12} sw={2.6} />장면 추가</button>
          </div>
          <div className="sc-elist__foot">
            <button type="button" className="sc-btn sc-btn--sm" style={{ height: 38, width: '100%' }} onClick={() => void regen()} disabled={busy === 'regen' || locked.length === items.length}
              title={locked.length === items.length ? '모든 장면을 직접 고쳤어요' : undefined} data-testid="sc4e-regen">
              <Ico d={P.refresh} size={13} sw={2.2} />나머지 장면 다시 생성
            </button>
            {lockedLine && <span className="sc-hint sc-hint--sm" style={{ textAlign: 'center' }} data-testid="sc4e-locked">{lockedLine}</span>}
          </div>
        </aside>
        <div className="sc-emain">
          <div className="sc-eform" data-testid="sc4e-editor">
            <div className="sc-ehead">
              <div className="sc-row" style={{ gap: 10, minWidth: 0 }}>
                {s.time && <span className="sc-etime wm-num">{s.time}</span>}
                <span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>장면 {s.no}</span>
                <span style={{ fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap' }}>{s.label}</span>
                {s.rewriting || busy?.startsWith('rw') ? <span className="sc-scard__busy"><StatusIcon kind="gen" size={12} />이 장면을 다시 쓰는 중</span> : null}
              </div>
              <div className="sc-row" style={{ gap: 8, flexShrink: 0 }}>
                {s.version > 0 && <span className="sc-vbadge" data-testid="sc4e-version"><b className="wm-num">v{s.version}</b>{s.reason ? `· ${s.reason}` : ''}</span>}
                {s.version >= 2 && (
                  <button type="button" className="sc-btn sc-btn--xs" style={{ height: 30 }} onClick={() => void restore()} disabled={busy === 'restore'} data-testid="sc4e-restore">
                    <Ico d={P.undo} size={13} sw={2.2} />v{s.version - 1}로 되돌리기
                  </button>
                )}
                <button type="button" className="sc-iconbtn" style={{ width: 30, height: 30, border: '1px solid var(--wm-line)' }} aria-label="장면 삭제" onClick={() => void remove()} data-testid="sc4e-delete">
                  <Ico d={P.trash} size={14} />
                </button>
              </div>
            </div>
            <div className="sc-ebody">
              <div className="sc-efields">
                <div className="sc-efield">
                  <label htmlFor="sc4e-title">장면 제목</label>
                  <input id="sc4e-title" className="sc-einput" value={draft.title} maxLength={80} onChange={(e) => setDraft({ ...draft, title: e.target.value })} data-testid="sc4e-title" />
                </div>
                <div className="sc-efield">
                  <div className="sc-row" style={{ justifyContent: 'space-between' }}>
                    <label htmlFor="sc4e-story">이야기</label>
                    {changed.length > 0 && <span className="sc-changed" data-testid="sc4e-changed"><span className="sc-changed__sw" />바뀐 곳 {changed.length}</span>}
                  </div>
                  {editStory ? (
                    <textarea id="sc4e-story" className="sc-estory sc-estory--edit" value={draft.story} maxLength={400} autoFocus onChange={(e) => setDraft({ ...draft, story: e.target.value })}
                      onBlur={() => setEditStory(false)} data-testid="sc4e-story" />
                  ) : (
                    <div id="sc4e-story" className="sc-estory" role="textbox" tabIndex={0} aria-label="이야기" onClick={() => setEditStory(true)} onFocus={() => setEditStory(true)} data-testid="sc4e-story-view">
                      <Story text={draft.story} changed={changed} />
                    </div>
                  )}
                </div>
                <ChipField label="등장인물" testId="sc4e-chars" items={draft.characters.map((c) => ({ key: c.role_id, label: c.name, isNew: c.is_new }))}
                  onRemove={(k) => setDraft({ ...draft, characters: draft.characters.filter((c) => c.role_id !== k) })}
                  addLabel="+ 추가" open={menu === 'char'} onOpen={() => setMenu(menu === 'char' ? null : 'char')} menuRef={menu === 'char' ? menuRef : undefined}
                  options={charOptions.map((r) => ({ key: r.id, label: r.name }))}
                  onPick={(k) => { const r = roles.find((x) => x.id === k); if (r) setDraft({ ...draft, characters: [...draft.characters, { role_id: r.id, name: r.name, is_new: true }] }); setMenu(null); }} />
                {isWith && (
                  <ChipField label="솔루션 동작" testId="sc4e-sols" items={draft.solutions.map((x) => ({ key: `${x.solution_id}:${x.action_code}`, label: x.label || x.action_code, isNew: x.is_new }))}
                    onRemove={(k) => setDraft({ ...draft, solutions: draft.solutions.filter((x) => `${x.solution_id}:${x.action_code}` !== k) })}
                    addLabel="+ 솔루션" open={menu === 'sol'} onOpen={() => setMenu(menu === 'sol' ? null : 'sol')} menuRef={menu === 'sol' ? menuRef : undefined}
                    options={solOptions.map((a) => ({ key: `${a.solution_id}:${a.action_code}`, label: `${a.solution_name} · ${a.label}`, sub: a.benefit }))}
                    onPick={(k) => {
                      const a = solOptions.find((x) => `${x.solution_id}:${x.action_code}` === k);
                      if (a) setDraft({ ...draft, solutions: [...draft.solutions, { solution_id: a.solution_id, action_code: a.action_code, label: `${a.solution_name} · ${a.label}`, is_new: true }] });
                      setMenu(null);
                    }} />
                )}
                <ChipField label="제품 활용" gray testId="sc4e-prods" items={draft.products.map((p, i) => ({ key: `${i}:${p.short}`, label: p.qty && p.qty > 1 ? `${p.short} ×${p.qty}` : p.short, isNew: p.is_new }))}
                  onRemove={(k) => setDraft({ ...draft, products: draft.products.filter((p, i) => `${i}:${p.short}` !== k) })}
                  addLabel="+ 제품" open={menu === 'prod'} onOpen={() => setMenu(menu === 'prod' ? null : 'prod')} menuRef={menu === 'prod' ? menuRef : undefined}
                  options={prodOptions.map((p) => ({ key: p.ref || p.label, label: p.label }))}
                  onPick={(k) => {
                    const p = prodOptions.find((x) => (x.ref || x.label) === k);
                    if (p) setDraft({ ...draft, products: [...draft.products, { ref: p.ref, family_id: p.family_id, model_code: p.model_code, short: p.short, label: p.label, qty: null, is_new: true }] });
                    setMenu(null);
                  }} />
              </div>
              <div className="sc-eimg" data-testid="sc4e-image">
                <div className="sc-row" style={{ justifyContent: 'space-between' }}>
                  <span className="sc-label">장면 이미지</span>
                  {img && <span style={{ fontSize: 11.5, color: 'var(--wm-text-subtle)' }} data-testid="sc4e-image-label">{img.label}</span>}
                </div>
                {img ? (
                  <div className="sc-eimg__frame">
                    <Img src={img.url || img.thumb_url || ''} alt={`장면 ${s.no} · ${s.label} 이미지`} />
                    <span className="sc-eimg__badge">{img.aspect || '16:9'}</span>
                  </div>
                ) : (
                  <div className="sc-eimg__frame sc-eimg__frame--empty" data-testid="sc4e-image-empty">아직 이미지가 없어요</div>
                )}
                {img && stale && (
                  <div className="sc-row" style={{ alignItems: 'flex-start', gap: 6, fontSize: 12, lineHeight: 1.5, color: 'var(--wm-text-2)' }} data-testid="sc4e-stale">
                    <Ico d={P.warn} size={14} color="var(--wm-text)" style={{ marginTop: 2 }} />
                    <span>이야기가 바뀌어 이미지와 다를 수 있어요{stale.missing?.length ? ` (${stale.missing.join(' · ')} 장면 없음)` : ''}</span>
                  </div>
                )}
                <button type="button" className="sc-btn sc-btn--brandline" onClick={() => void makeImage()} disabled={busy === 'img'} data-testid="sc4e-make-image">
                  <Ico d={P.image} size={14} />{img ? '이미지 생성에서 다시 만들기' : '이미지 생성에서 만들기'}
                </button>
                {prefill.data && (
                  <div className="sc-carry" data-testid="sc4e-prefill">
                    <span className="sc-carry__head">이미지 생성으로 넘어가는 것</span>
                    <CarryRow k="공간" v={prefill.data.space} />
                    <CarryRow k="장면" v={prefill.data.scene} />
                    <CarryRow k="제품" v={prefill.data.product_line} testId="sc4e-prefill-products" />
                    <CarryRow k="비율" v={prefill.data.aspect_label ?? '16:9 · 제안서 시트용'} />
                  </div>
                )}
                <button type="button" className="sc-link" style={{ alignSelf: 'center', height: 26, fontSize: 12 }} onClick={() => openPop('image')} data-testid="sc4e-pick">사내 자산 · 내 이미지에서 고르기</button>
              </div>
            </div>
          </div>
          <div className="sc-card" style={{ width: '100%' }} data-testid="sc4e-rewrite">
            <div className="sc-card__head">
              <div className="sc-card__title">이 장면만 다시 쓰기<small> · 다른 장면은 그대로</small></div>
              <div className="sc-row" style={{ gap: 6 }}>
                <button type="button" className="sc-pill sc-pill--h30" disabled={!!busy} onClick={() => void rewrite('rw-short', { preset: 'shorter' })} data-testid="sc4e-shorter">더 짧게</button>
                {pov.slice(0, 2).map((name, i) => (
                  <button key={name} type="button" className="sc-pill sc-pill--h30" disabled={!!busy} data-testid="sc4e-pov"
                    onClick={() => void rewrite(`rw-pov${i}`, { preset: 'pov', pov_role_id: s.pov_role_ids?.[i] ?? null })}>{name} 시점으로</button>
                ))}
                {isWith && <button type="button" className="sc-pill sc-pill--h30" disabled={!!busy} onClick={() => void rewrite('rw-sol', { preset: 'solution_detail' })} data-testid="sc4e-sol-detail">솔루션 동작 더 구체적으로</button>}
              </div>
            </div>
            {err && <div className="sc-card__sec"><Note tone="err" testId="sc4e-err" onClose={() => setErr(null)}>{err}</Note></div>}
            <div className="sc-card__foot" style={{ gap: 10 }}>
              <Ask id="sc4e-fix" label="이 장면 수정 지시" placeholder="지시문 (예: 키오스크 대기 줄이 줄어드는 순간을 강조)" sendLabel="이 장면 다시 쓰기" disabled={!!busy && busy !== 'rw-ins'}
                busy={busy === 'rw-ins'} testId="sc4e-fix" onSubmit={(text) => rewrite('rw-ins', { instruction: text })} />
              <Link to={route.result(id)} className="sc-btn" data-testid="sc4e-cancel">취소</Link>
              <button type="button" className="sc-btn sc-btn--primary" onClick={() => void save()} disabled={busy === 'save'} data-testid="sc4e-save">
                <Ico d={P.check} size={16} sw={2.2} />변경 저장
              </button>
            </div>
          </div>
        </div>
      </div>
      {dialog}
    </section>
  );
}

function Story({ text, changed }: { text: string; changed: string[] }) {
  if (!changed.length) return <>{text}</>;
  const parts: Array<{ t: string; on: boolean }> = [];
  let rest = text;
  for (const c of changed) {
    const i = rest.indexOf(c);
    if (i < 0) continue;
    if (i > 0) parts.push({ t: rest.slice(0, i), on: false });
    parts.push({ t: c, on: true });
    rest = rest.slice(i + c.length);
  }
  if (rest) parts.push({ t: rest, on: false });
  return <>{parts.map((p, i) => (p.on ? <mark key={i} className="sc-hl">{p.t}</mark> : <span key={i}>{p.t}</span>))}</>;
}

function ChipField({ label, items, onRemove, addLabel, options, onPick, open, onOpen, menuRef, gray, testId }:
  { label: string; items: Array<{ key: string; label: string; isNew?: boolean }>; onRemove: (k: string) => void; addLabel: string;
    options: Array<{ key: string; label: string; sub?: string }>; onPick: (k: string) => void; open: boolean; onOpen: () => void;
    menuRef?: React.Ref<HTMLDivElement>; gray?: boolean; testId: string }) {
  return (
    <div className="sc-efield" data-testid={testId}>
      <span className="sc-efield__label">{label}</span>
      <div className="sc-row sc-wrap" style={{ gap: 6 }}>
        {items.map((it) => (
          <span key={it.key} className={cx('sc-echip', gray && 'sc-echip--gray')} data-testid={`${testId}-chip`} data-new={it.isNew || undefined}>
            {it.label}
            <button type="button" className="sc-chip__x" aria-label={`${it.label} 빼기`} onClick={() => onRemove(it.key)}><Icon name="x" size={9} strokeWidth={3} /></button>
            {it.isNew && <span className="sc-echip__new">새로</span>}
          </span>
        ))}
        <div className="sc-menuwrap" ref={menuRef}>
          <button type="button" className="sc-echip-add" aria-haspopup="menu" aria-expanded={open} onClick={onOpen} disabled={options.length === 0}
            title={options.length === 0 ? '더 넣을 항목이 없어요' : undefined}>{addLabel}</button>
          {open && (
            <div className="sc-menu sc-menu--left" role="menu" style={{ maxHeight: 240, overflow: 'auto', minWidth: 220 }}>
              {options.map((o) => (
                <button key={o.key} type="button" role="menuitem" onClick={() => onPick(o.key)} style={o.sub ? { height: 'auto', padding: '6px 10px', flexDirection: 'column', alignItems: 'flex-start', gap: 1 } : undefined}>
                  <span>{o.label}</span>{o.sub && <span style={{ fontSize: 11, color: 'var(--wm-text-muted)' }}>{o.sub}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CarryRow({ k, v, testId }: { k: string; v: string; testId?: string }) {
  return <div className="sc-row" style={{ gap: 8, whiteSpace: 'nowrap' }}><span style={{ width: 28, flexShrink: 0, color: 'var(--wm-text-subtle)' }}>{k}</span><span className="wm-ellipsis" data-testid={testId}>{v}</span></div>;
}
