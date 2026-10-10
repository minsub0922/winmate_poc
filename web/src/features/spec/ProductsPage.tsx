/** SP1 — 제품 입력(`/spec/legacy/new` → `/spec/:id/products`, 06-spec §4.3) · SP1Product(셸 제품 탐색 팝오버, §4.4) */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useOpenPopover } from '@/shell';
import { useShellPage } from '@/shell/ShellContext';
import { ProductInput, toast, type ProductToken } from '@/ui';
import {
  addProducts, createSheet, errText, generate, isApiError, patchSheet, removeProduct, useCombos, useSheet, useSheetCache, type Sheet,
} from './api';
import { Agent, BigButton, Dock, SECTION, SpPage, stepper } from './ui';

const AGENT = '스펙 시트를 만들 제품을 입력해 주세요. 하나만 넣으면 단일 제품 시트, 둘 이상이면 비교표로 만들어 드립니다. 모델명을 입력하면 사내 카탈로그에서 정확한 스펙을 가져옵니다.';
const FROM = new Set(['home', 'mi', 'vp', 'birdseye', 'product_detail', 'proposal', 'clone']);

export function tokensOf(s: Sheet | undefined): ProductToken[] {
  return (s?.products ?? []).map((p) => ({ kind: p.custom ? 'custom' : 'model', ref: p.ref, label: p.bubble_label || p.display_name, model_code: p.model_code ?? undefined }));
}

export default function ProductsPage() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const cache = useSheetCache();
  const combos = useCombos();
  const openPop = useOpenPopover();
  const [limitMsg, setLimitMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const creating = useRef<Promise<Sheet> | null>(null);
  const addMode = sp.get('mode') === 'add' && !!s?.generated_at;

  /** 작업이 없으면 만들고(첫 제품 — history replace), 있으면 그 작업 */
  const ensure = async (refs: string[], start: 'model' | 'explorer' | 'link' = 'model', origin?: { from: string; ref?: string }) => {
    if (s) return { sheet: s, created: false };
    if (!creating.current) {
      creating.current = createSheet({ start, products: refs, ...(origin ? { origin: { from: origin.from as never, ref: origin.ref } } : {}) });
    }
    const made = await creating.current;
    cache.put(made);
    nav(`/spec/${made.id}/products${window.location.search}`, { replace: true });
    return { sheet: made, created: true };
  };

  const add = async (refs: string[], source: 'input' | 'explorer' = 'input'): Promise<string[]> => {
    setLimitMsg(null);
    try {
      const { sheet, created } = await ensure(refs, source === 'explorer' ? 'explorer' : 'model');
      if (created) return refs;
      const r = await addProducts(sheet.id, refs, source);
      cache.put(r.sheet);
      if (r.skipped?.some((x) => x.reason === 'limit')) setLimitMsg('한 시트에 8개까지 비교할 수 있어요.');
      return r.added;
    } catch (e) {
      if (isApiError(e, 'PRODUCT_LIMIT')) { setLimitMsg('한 시트에 8개까지 비교할 수 있어요.'); return []; }
      toast(errText(e));
      return [];
    }
  };

  // `/spec/legacy/new?models=…&from=vp:vp_…`(`/spec/new?models=…` 가 이리로 넘긴다) — 넘겨받은 제품으로 바로 작업 만들기
  const linkDone = useRef(false);
  useEffect(() => {
    if (id || linkDone.current) return;
    const models = (sp.get('models') ?? '').split(',').map((x) => x.trim()).filter(Boolean);
    if (!models.length) return;
    linkDone.current = true;
    const from = sp.get('from') ?? '';
    const [src, ref] = from.split(':');
    const origin = FROM.has(src) ? { from: src, ref } : undefined;
    void ensure(models, 'link', origin).catch((e) => toast(errText(e)));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const tokens = useMemo(() => tokensOf(s), [s]);
  const onChange = async (next: ProductToken[]) => {
    const have = new Set(tokens.map((t) => t.ref));
    const added = next.filter((t) => t.ref && !have.has(t.ref)).map((t) => t.ref!);
    const keep = new Set(next.map((t) => t.ref));
    const removed = (s?.products ?? []).filter((p) => !keep.has(p.ref));
    if (added.length) await add(added, 'input');
    for (const p of removed) {
      try { cache.put(await removeProduct(s!.id, p.id)); setLimitMsg(null); } catch (e) { toast(errText(e)); }
    }
  };

  const addCombo = async (refs: string[]) => {
    const have = new Set(tokens.map((t) => t.ref));
    const codes = new Set((s?.products ?? []).map((p) => p.model_code));
    const todo = refs.filter((r) => !have.has(r) && !codes.has(r.replace('kb:model:mdl_', '')));
    if (todo.length) await add(todo, 'input');
  };

  const next = async () => {
    if (!s) return;
    setBusy(true);
    try {
      if (addMode) {
        const r = await generate(s.id, { mode: 'columns' });
        nav(`/spec/${s.id}/generating?job=${r.job_id}`);
        return;
      }
      const u = await patchSheet(s.id, { step: 2 });
      cache.put(u);
      nav(`/spec/${s.id}/items`);
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };

  const n = s?.products.length ?? 0;
  const title = s?.title_confirmed ? s.title : '새 작업';
  useShellPage({
    section: SECTION, title, hasTask: true, accepts: ['product'], addable: ['product'],
    added: (s?.products ?? []).map((p) => p.ref).filter((r) => r.startsWith('kb:')),
    onAdd: async (_type, refs) => ({ added: await add(refs, 'explorer') }),
    stepper: stepper(1),
    taskContext: { products: (s?.products ?? []).filter((p) => p.family_id).map((p) => ({ ref: `kb:family:${p.family_id}`, label: p.series_code ?? p.display_name })) },
  });

  if (id && sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;

  return (
    <SpPage
      dock={
        <Dock title="제품 입력" meta={n ? `${n}개 추가됨 · 1 / 3` : '1 / 3'}
          right={<button type="button" className="sp-link" onClick={() => openPop('product')}>제품 탐색에서 고르기</button>}
          row={
            <>
              <span style={{ flex: 1 }} />
              <BigButton onClick={() => void next()} disabled={!n} busy={busy} title="제품을 하나 이상 넣어 주세요">
                {addMode ? '시트 다시 만들기' : '항목 · 형식 선택'}
              </BigButton>
            </>
          }>
          <ProductInput value={tokens} onChange={(v) => void onChange(v)} placeholder="제품명 · 모델명을 입력해 추가…" label={tokens.length ? '제품명 추가 입력' : '제품명 입력'}
            autoFocus />
          {limitMsg && <div className="sp-note" role="alert">{limitMsg}</div>}
          {(combos.data?.length ?? 0) > 0 && (
            <div className="sp-chiprow">
              <span style={{ fontSize: 12, color: 'var(--wm-text-muted)', fontWeight: 600, marginRight: 4 }}>자주 비교하는 조합</span>
              {combos.data!.map((c) => (
                <button key={c.label} type="button" className="sp-pillbtn" onClick={() => void addCombo(c.refs ?? c.model_codes)}>{c.label}</button>
              ))}
            </div>
          )}
        </Dock>
      }>
      <Agent text={AGENT}>
        {s?.agent?.from_note && <div className="sp-note" data-testid="sp-from-note">{s.agent.from_note}</div>}
        <div className="sp-tip"><b>Tip</b><span>같은 시리즈의 다른 크기(43"/50"/55")를 함께 넣으면 크기별 비교표가 됩니다.</span></div>
      </Agent>
    </SpPage>
  );
}
