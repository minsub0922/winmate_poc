/**
 * IMG2 · 상세 조건(2/3) — 등장 제품 · 스타일 · 비율 · 장수 · 참조 이미지(§4.3).
 * 바꾸면 바로 저장(PATCH conditions). 「이미지 {count}장 생성」 → run(initial) → IMG3G.
 */
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Button, ErrorState, Icon, Img, useDropTarget } from '@/ui';
import { ApiError, errMessage, img, type Conditions, type ProductCond, type Work } from '../api';
import { Echo, Loading, Pill, ProductChips, Screen, useImgShell, WSay } from '../components';
import { useInvalidate, useWork } from '../hooks';
import { ASPECTS_GEN, route, STYLE_LABEL } from '../lib';

const productRef = (p: ProductCond) => (p.model_code ? `kb:model:mdl_${p.model_code}` : p.family_id ? `kb:family:${p.family_id}` : '');

export default function ConditionsPage() {
  const { workId = '' } = useParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const q = useWork(workId);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const w = q.data;

  const save = async (patch: Partial<Conditions>) => {
    if (!w) return;
    const cond = { ...w.conditions, ...patch };
    inv.setWork({ ...w, conditions: cond } as Work);
    try { inv.setWork(await img.patchWork(w.id, { conditions: cond })); setErr(null); } catch (e) { setErr(errMessage(e)); void inv.work(w.id); }
  };
  const addProducts = async (refs: string[]) => {
    try { const r = await img.addProducts(workId, refs); inv.setWork(r.work); setErr(null); return r.added; } catch (e) { setErr(errMessage(e)); return []; }
  };
  const addImages = async (refs: string[]) => {
    const added: string[] = [];
    for (const r of refs) {
      try { await img.addReference(workId, { source_kind: 'topbar', source_ref: r, via: 'topbar' }); added.push(r); } catch (e) { setErr(errMessage(e)); }
    }
    await inv.work(workId);
    return added;
  };
  const removeRef = async (refId: string) => {
    try { await img.deleteReference(workId, refId); } catch (e) { setErr(errMessage(e)); }
    await inv.work(workId);
  };
  const generate = async () => {
    if (!w || busy) return;
    setBusy(true); setErr(null);
    try {
      const acc = await img.startRun(w.id, { kind: 'initial', count: w.conditions.count });
      void inv.work(w.id); void inv.gallery();
      nav(route.run(w.id, acc.run_id));
    } catch (e) {
      if (e instanceof ApiError && e.code === 'RUN_IN_PROGRESS' && typeof e.details.run_id === 'string') nav(route.run(w.id, e.details.run_id));
      else setErr(errMessage(e));
    } finally { setBusy(false); }
  };

  const refs = w?.references ?? [];
  const products = w?.conditions.products ?? [];
  useImgShell({
    title: w?.title ?? '새 작업', step: 2, accepts: ['product', 'image'], addable: ['product', 'image'],
    added: [...products.map(productRef), ...refs.map((r) => r.source_ref ?? '')].filter(Boolean),
    onAdd: async (type, list) => ({ added: type === 'product' ? await addProducts(list) : type === 'image' ? await addImages(list) : [] }),
    taskContext: { products: products.filter((p) => p.family_id).map((p) => ({ ref: `kb:family:${p.family_id}`, label: p.short })) },
  });
  const prodDrop = useDropTarget({ accept: ['product'], onDrop: async (p) => (await addProducts([p.ref])).length > 0 });
  const refDrop = useDropTarget({ accept: ['image'], disabled: refs.length >= 3, onDrop: async (p) => (await addImages([p.ref])).length > 0 });

  if (q.isLoading) return <Loading />;
  if (!w) return <div className="img-center"><ErrorState message="작업을 불러오지 못했어요" onRetry={() => q.refetch()} /></div>;
  const c = w.conditions;
  const bg = w.kind === 'background';
  const collapsed = bg && c.no_products && products.length === 0;
  const count = c.count;
  return (
    <Screen testid="img2" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head"><span>상세 조건<small> · 2 / 3</small></span></div>
          <div style={{ padding: '10px 18px 0 18px', display: 'flex', flexDirection: 'column', gap: 6 }} {...prodDrop.props}>
            <div className="img-label">등장 제품</div>
            {collapsed ? (
              <div className="img-row">
                <Pill on h={32}>제품 없이</Pill>
                <Pill h={32} onClick={() => void save({ no_products: false })}>제품 넣기</Pill>
              </div>
            ) : (
              <ProductChips value={products} dropActive={prodDrop.dragging}
                message={!products.length ? (w.prefill?.message ?? null) : null}
                onChange={(next) => void save({ products: next, no_products: bg && next.length === 0 })} />
            )}
          </div>
          <div style={{ padding: '10px 18px 0 18px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div className="img-label" id="img-style-l">스타일</div>
              <div className="img-row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-labelledby="img-style-l">
                {(['photo', 'minimal_3d', 'illustration'] as const).map((s) => (
                  <Pill key={s} h={32} on={c.style === s} onClick={() => void save({ style: s })}>{STYLE_LABEL[s]}</Pill>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div className="img-label" id="img-aspect-l">비율 · 장수</div>
              <div className="img-row" style={{ gap: 6, flexWrap: 'wrap' }} role="group" aria-labelledby="img-aspect-l">
                {ASPECTS_GEN.map((a) => <Pill key={a} h={32} on={c.aspect === a} onClick={() => void save({ aspect: a })}><span className="wm-num">{a}</span></Pill>)}
                <span className="img-vsep" />
                {([2, 4] as const).map((n) => <Pill key={n} h={32} on={count === n} onClick={() => void save({ count: n })}>{n}장</Pill>)}
              </div>
            </div>
          </div>
          <div style={{ padding: '10px 18px 0 18px' }} className="img-row" {...refDrop.props}>
            <div className="img-label" style={{ flexShrink: 0 }}>참조 이미지</div>
            <div className="img-refthumbs" data-testid="img2-refs">
              {refs.map((r) => (
                <span key={r.id} className="img-refthumb" title={`${r.label} · ${r.role_label}`}>
                  <Img src={r.thumb_url} alt={r.label} />
                  <button type="button" className="img-refthumb__x" aria-label="참조 이미지 제거" onClick={() => void removeRef(r.id)}><Icon name="x" size={9} strokeWidth={3} /></button>
                </span>
              ))}
              {refs.length >= 3
                ? <button type="button" className="img-refadd" disabled title="참조는 3장까지 고를 수 있어요" aria-label="참조 이미지 추가">+</button>
                : <Link to={route.references(w.id)} className={`img-refadd${refDrop.dragging ? ' img-refadd--drop' : ''}`} aria-label="참조 이미지 추가">+</Link>}
            </div>
            {w.ref_notice && <span className="img-hint img-hint--sm" data-testid="img2-refnotice">{w.ref_notice}</span>}
            {!w.ref_notice && refDrop.dragging && <span className="img-hint img-hint--sm">여기에 놓으면 참조 이미지로 들어가요</span>}
          </div>
          <div className="wm-composer__foot">
            {err && <span className="img-err" role="alert" style={{ flex: 1, minWidth: 0 }}>{err}</span>}
            <Button h={44} onClick={() => nav(route.newWork(w.id))}>이전</Button>
            <Button h={44} variant="primary" loading={busy} onClick={() => void generate()} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}
              disabled={w.description.trim().length < 2 && refs.length === 0} disabledReason="장면 설명을 2자 이상 적어 주세요">
              이미지 {count}장 생성
            </Button>
          </div>
        </div>
      </div>
    }>
      <Echo head={w.kind_label} text={w.description || null} />
      <WSay text="좋습니다. 장면에 등장할 삼성 제품과 표현 스타일을 정해 주세요. 제품을 지정하면 실제 제품 외형과 비율을 반영해 생성합니다." />
    </Screen>
  );
}
