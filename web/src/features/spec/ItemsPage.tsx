/** SP2 — 항목 · 형식(`/spec/:id/items`, 06-spec §4.7) */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { toast } from '@/ui';
import { diffItems, errText, generate, isApiError, putItems, useSheet, useSheetCache, type Sheet } from './api';
import { Agent, BigButton, Chip2, Dock, SpPage, UserBubble, useSpecShell } from './ui';

type Lang = 'ko' | 'en' | 'ko_en';
const LANGS: Array<[Lang, string]> = [['ko', '한국어'], ['en', 'English'], ['ko_en', '한/영']];

/** 1단계 화면(시작 갈래별) */
export function step1Route(s: Sheet): string {
  if (s.start === 'find') return `/spec/${s.id}/find`;
  if (s.start === 'requirements') return `/spec/${s.id}/requirements`;
  return `/spec/${s.id}/products`;
}

export default function ItemsPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const cache = useSheetCache();
  const [checked, setChecked] = useState<Record<string, boolean> | null>(null);
  const [layout, setLayout] = useState<'compare' | 'per_product'>('compare');
  const [lang, setLang] = useState<Lang>('ko');
  const [hl, setHl] = useState(true);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);
  const pending = useRef<null | (() => Promise<void>)>(null);

  // 서버 값으로 한 번 채운다(이후는 화면 값이 우선 — 디바운스 저장)
  useEffect(() => {
    if (!s || checked) return;
    setChecked(Object.fromEntries(s.items.map((i) => [i.key, i.checked])));
    setLayout(s.layout ?? 'compare');
    setLang((s.format.language ?? 'ko') as Lang);
    setHl(s.options.highlight_wins ?? true);
  }, [s, checked]);

  useSpecShell(s, 2);

  const flush = async () => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
    const p = pending.current;
    pending.current = null;
    if (p) await p();
  };
  useEffect(() => () => { void flush(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = (next: { checked?: Record<string, boolean>; layout?: typeof layout; lang?: Lang; hl?: boolean }) => {
    if (!s) return;
    const c = next.checked ?? checked ?? {};
    const body = {
      items: Object.entries(c).map(([key, v]) => ({ key, checked: v })),
      layout: next.layout ?? layout, language: next.lang ?? lang, highlight_wins: next.hl ?? hl,
    };
    pending.current = async () => {
      try { cache.put(await putItems(s.id, body)); } catch (e) { toast(errText(e)); }
    };
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void flush(); }, 400);
  };

  const toggle = (key: string) => {
    const c = { ...(checked ?? {}), [key]: !(checked ?? {})[key] };
    setChecked(c);
    save({ checked: c });
  };
  const all = () => {
    const c = Object.fromEntries((s?.items ?? []).map((i) => [i.key, true]));
    setChecked(c);
    save({ checked: c });
  };
  const onlyDiff = async () => {
    if (!s) return;
    try {
      await flush();
      const diff = new Set(await diffItems(s.id));
      if (!diff.size) { toast('모델 간 값이 다른 항목이 없어요.'); return; }
      const c = Object.fromEntries(s.items.map((i) => [i.key, diff.has(i.key)]));
      setChecked(c);
      save({ checked: c });
    } catch (e) { toast(errText(e)); }
  };

  const n = useMemo(() => Object.values(checked ?? {}).filter(Boolean).length, [checked]);
  const multi = (s?.products.length ?? 0) >= 2;

  const start = async () => {
    if (!s) return;
    setBusy(true);
    try {
      await flush();
      const r = await generate(s.id, { mode: 'full' });
      nav(`/spec/${s.id}/generating?job=${r.job_id}`);
    } catch (e) {
      const running = isApiError(e, 'RUN_IN_PROGRESS') ? ((e.details as { job_id?: string }).job_id ?? s.active_job?.id) : null;
      if (running) { nav(`/spec/${s.id}/generating?job=${running}`); return; }
      toast(errText(e));
    } finally { setBusy(false); }
  };

  if (sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;
  if (!s || !checked) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const prev = async () => { await flush(); nav(step1Route(s)); };

  return (
    <SpPage
      dock={
        <Dock title="스펙 항목" meta={`${n}개 선택 · 2 / 3`}
          right={
            <>
              <button type="button" className="sp-link" onClick={all}>전체 선택</button>
              {multi && <button type="button" className="sp-link" onClick={() => void onlyDiff()}>차이 있는 항목만</button>}
            </>
          }
          row={
            <>
              <button type="button" className="sp-btn2" onClick={() => void prev()}>이전</button>
              <span style={{ flex: 1 }} />
              <BigButton onClick={() => void start()} disabled={!n} busy={busy} title="항목을 하나 이상 골라 주세요">시트 생성</BigButton>
            </>
          }>
          <div className="sp-chiprow" role="group" aria-label="스펙 항목">
            {s.items.map((i) => (
              <Chip2 key={i.key} check={false} on={!!checked[i.key]} onClick={() => toggle(i.key)}>{i.label}</Chip2>
            ))}
          </div>
          <div className="sp-optgrid">
            {multi && (
              <div className="sp-optcol">
                <div className="sp-optcol__label" id="sp-opt-layout">형식</div>
                <div className="sp-chiprow" role="group" aria-labelledby="sp-opt-layout">
                  <Chip2 h={34} check={false} on={layout === 'compare'} onClick={() => { setLayout('compare'); save({ layout: 'compare' }); }}>비교표</Chip2>
                  <Chip2 h={34} check={false} on={layout === 'per_product'} onClick={() => { setLayout('per_product'); save({ layout: 'per_product' }); }}>제품별 개별 시트</Chip2>
                </div>
              </div>
            )}
            <div className="sp-optcol">
              <div className="sp-optcol__label" id="sp-opt-lang">
                언어 <Link className="sp-link" to={`/spec/${s.id}/format?from=items`} onClick={() => void flush()}>언어 · 단위 자세히</Link>
              </div>
              <div className="sp-chiprow" role="group" aria-labelledby="sp-opt-lang">
                {LANGS.map(([k, label]) => (
                  <Chip2 key={k} h={34} check={false} on={lang === k} onClick={() => { setLang(k); save({ lang: k }); }}>{label}</Chip2>
                ))}
              </div>
            </div>
            {multi && (
              <div className="sp-optcol">
                <div className="sp-optcol__label" id="sp-opt-hl">차이 강조</div>
                <div className="sp-chiprow" role="group" aria-labelledby="sp-opt-hl">
                  <Chip2 h={34} check={false} on={hl} onClick={() => { setHl(!hl); save({ hl: !hl }); }}>우위 항목 하이라이트</Chip2>
                </div>
              </div>
            )}
          </div>
        </Dock>
      }>
      {s.agent?.sp2_user && <UserBubble>{s.agent.sp2_user}</UserBubble>}
      <Agent text={s.agent?.sp2 ?? ''} />
    </SpPage>
  );
}
