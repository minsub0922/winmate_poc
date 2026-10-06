/**
 * SC2 · 공간 시나리오 입력(§4.5) — 예시 골격 3 · 시나리오 텍스트(≤ 3,000자) · 등장인물(멈춘 뒤 1초 추출, 지운 역할은 다시 넣지 않음)
 * · 사이드바 조감도 · Storyboard 끌어오기 → 파싱 잡 → R2(SC3 또는 SC2E).
 * `?view=text`(SC2E 「텍스트로 보기」)면 타임라인을 시각 줄 텍스트로 채우고, 고쳐서 넘기면 다시 나눈다(확인).
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { DropZone, useConfirm } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi } from '../api';
import { useDebounced, useInvalidate, useScenario, waitJob } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Btn, Card, ChipX, Echo, Loading, NextButton, Note, Screen, W } from '../parts';

const MAX = 3000;

export default function InputPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const textView = sp.get('view') === 'text';
  const [text, setText] = useState('');
  const [chars, setChars] = useState<string[]>([]);
  const [removed, setRemoved] = useState<string[]>([]);
  const [add, setAdd] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const loadedText = useRef<string>('');
  const { confirm, dialog } = useConfirm();
  const skeletons = useQuery({ queryKey: ['scenario', 'skeletons', sc.data?.vertical_code ?? ''], queryFn: () => scApi.skeletons(sc.data?.vertical_code), enabled: !!sc.data, staleTime: 300_000 });

  // 처음 한 번 채우기(텍스트로 보기면 타임라인 직렬화)
  useEffect(() => {
    if (!sc.data || ready) return;
    const init = async () => {
      let raw = sc.data.raw_text ?? '';
      if (textView) {
        try { raw = (await scApi.timelineText(id)).raw_text; } catch { /* 원문 유지 */ }
      }
      loadedText.current = raw;
      setText(raw);
      setChars(sc.data.characters ?? []);
      setRemoved(sc.data.removed_characters ?? []);
      setReady(true);
    };
    void init();
  }, [sc.data, ready, textView, id]);

  // 자동 저장(입력 · 등장인물)
  const dText = useDebounced(text, 800);
  useEffect(() => {
    if (!ready || !sc.data || textView) return;
    // 디바운스 값이 아직 따라오지 않았다 — 첫 로드 직후(dText 는 아직 '') 미리 채운 입력(Storyboard 공간 · MI 페르소나 · VP 가치)을 빈 값으로 덮어쓰지 않게(통합)
    if (dText !== text) return;
    if (dText === (sc.data.raw_text ?? '')) return;
    void scApi.patch(id, { raw_text: dText.slice(0, MAX) }).catch(() => undefined);
  }, [dText, ready]); // eslint-disable-line react-hooks/exhaustive-deps

  // 등장인물 추출: 입력이 멈추고 1초 뒤(§4.5, 제한 5초)
  const exText = useDebounced(text, 1000);
  useEffect(() => {
    if (!ready || exText.trim().length < 10) return;
    const ctl = new AbortController();
    const t = window.setTimeout(() => ctl.abort(), 5000);
    scApi.extract(id, exText, removed, ctl.signal)
      .then((r) => {
        setChars((cur) => {
          const next = [...cur];
          for (const c of r.characters) if (!next.includes(c) && !removed.includes(c)) next.push(c);
          if (next.length !== cur.length) void scApi.patch(id, { characters: next }).catch(() => undefined);
          return next;
        });
      })
      .catch(() => undefined)
      .finally(() => window.clearTimeout(t));
    return () => { ctl.abort(); window.clearTimeout(t); };
  }, [exText, ready]); // eslint-disable-line react-hooks/exhaustive-deps

  useShellPage({
    section: SECTION, title: sc.data?.title ?? '', stepper: stepper(2), sidebarGroup: 'scenario',
    accepts: ['work_item'], acceptsWork: ['BE', 'SB'],
  });

  if (sc.isLoading || !ready) return <Loading />;
  const s = sc.data!;

  const removeChar = (c: string) => {
    const next = chars.filter((x) => x !== c);
    const rem = Array.from(new Set([...removed, c]));
    setChars(next); setRemoved(rem);
    void scApi.patch(id, { characters: next, removed_characters: rem }).catch(() => undefined);
  };
  const addChar = () => {
    const c = add.trim();
    if (!c) return;
    setAdd('');
    if (chars.includes(c)) return;
    const next = [...chars, c];
    const rem = removed.filter((x) => x !== c);
    setChars(next); setRemoved(rem);
    void scApi.patch(id, { characters: next, removed_characters: rem }).catch(() => undefined);
  };
  const appendText = (more: string) => {
    if (!more.trim()) return;
    setText((cur) => {
      const base = cur.replace(/\s+$/u, '');
      return (base ? `${base}\n${more}` : more).slice(0, MAX);
    });
  };

  const submit = async () => {
    const raw = text.trim();
    if (raw.length < 10) return;
    if (textView && raw !== loadedText.current.trim()) {
      const yes = await confirm({ title: '텍스트를 고치면 타임라인을 다시 나눠요', message: '타임라인에서 옮기거나 더한 장면은 고친 텍스트 기준으로 다시 만들어져요.', confirmLabel: '다시 나누기' });
      if (!yes) return;
    } else if (textView) {
      await scApi.patch(id, { step: 3 }).catch(() => undefined);
      nav(route.solutions(id));
      return;
    }
    setBusy(true); setErr(null);
    try {
      const acc = await scApi.parse(id, raw, chars);
      const r = await waitJob(acc.job_id, { timeoutMs: 120_000 });
      if (r.status !== 'succeeded') {
        setErr(r.error?.message ? `장면으로 나누지 못했어요 · ${r.error.message}` : '장면으로 나누지 못했어요 · 잠시 뒤 다시 시도해 주세요');
        return;
      }
      const fresh = await scApi.get(id);
      await inv.sc(id);
      nav(fresh.parse?.next === 'SC2E' ? route.timeline(id) : route.solutions(id));
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(false); }
  };

  const short = text.trim().length < 10;
  const sk = skeletons.data?.items ?? [];
  const dock = (
    <Card title="공간 시나리오" meta="2 / 4" testId="sc2-card"
      right={(
        <div className="sc-row" style={{ gap: 6 }} data-testid="sc2-skeletons">
          <span className="sc-label">예시 골격</span>
          {sk.map((k) => <button key={k.title} type="button" className="sc-pill" onClick={() => appendText(k.text)}>{k.title}</button>)}
        </div>
      )}>
      <div className="sc-card__sec">
        <label htmlFor="sc2-text" className="wm-sr-only">공간 시나리오 입력</label>
        <textarea id="sc2-text" className="sc-textarea" value={text} maxLength={MAX} onChange={(e) => setText(e.target.value)} data-testid="sc2-text"
          placeholder={'07:00 점장이 매장을 오픈한다. 메뉴보드가 아침 메뉴로 켜져 있어야 한다.\n11:30 점심 피크. 주문 줄이 길어진다.'} />
        {text.length > MAX * 0.9 && <div className="sc-hint sc-hint--sm" style={{ textAlign: 'right', marginTop: 4 }}><span className="wm-num">{text.length.toLocaleString()}</span> / 3,000자</div>}
      </div>
      <div className="sc-card__sec sc-row sc-wrap" data-testid="sc2-chars">
        <span className="sc-label">등장인물</span>
        {chars.map((c) => <ChipX key={c} label={c} onRemove={() => removeChar(c)} removeLabel="등장인물 지우기" testId="sc2-char" />)}
        <label htmlFor="sc2-add" className="wm-sr-only">등장인물 추가</label>
        <input id="sc2-add" className="sc-chip-input" style={{ width: 120 }} value={add} placeholder="추가…" onChange={(e) => setAdd(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); addChar(); } }} onBlur={addChar} />
      </div>
      <div className="sc-card__sec">
        <DropZone accept={['work_item']} acceptWork={['BE', 'SB']} idleText="사이드바에서 끌어오기" chipLabels={{ work_item: '조감도 · Storyboard 작업 (사이드바)' }}
          onDrop={async (p) => {
            try {
              const r = await scApi.importItem(id, { feature: p.feature === 'SB' ? 'SB' : 'BE', ref: p.ref });
              appendText(r.append_text);
              await inv.sc(id);
              return { note: p.feature === 'SB' ? '고객 · 공간 줄을 덧붙였어요' : '공간 · 제품 줄을 덧붙였어요' };
            } catch (e) { setErr(errMessage(e)); return false; }
          }} />
      </div>
      {err && <div className="sc-card__sec"><Note tone="err" testId="sc2-err">{err}</Note></div>}
      <div className="sc-card__foot">
        <Btn to={textView ? route.timeline(id) : route.type(id)} testId="sc2-prev">이전</Btn>
        <NextButton onClick={() => void submit()} busy={busy} disabled={short} reason="시나리오를 10자 이상 적어 주세요" testId="sc2-next">솔루션 · 제품 입력</NextButton>
      </div>
    </Card>
  );

  return (
    <Screen dock={dock} testId="sc2">
      <Echo testId="sc2-echo"><b>{s.type_label}</b> · {s.type_sub}</Echo>
      <W testId="sc2-w" extra={(
        <>
          <div className="sc-w__tip"><b>Tip</b><span>Storyboard나 조감도 작업이 있다면 사이드바에서 끌어와 공간·고객 정보를 재사용할 수 있습니다.</span></div>
          {textView && <div className="sc-w__note" data-testid="sc2-textview">타임라인을 시각 줄 텍스트로 옮겼어요 · 텍스트를 고치면 타임라인을 다시 나눠요</div>}
          {busy && <div className="sc-w__note"><span className="wm-spinner" aria-hidden="true" />입력하신 시나리오를 장면으로 나누는 중이에요</div>}
        </>
      )}>
        고객 공간에서 벌어지는 시나리오를 적어주세요. 하루의 흐름(오픈 → 피크 → 마감)이나 특정 상황(신메뉴 출시일)처럼 시간 축이 있으면 장면을 나누기 좋습니다. 등장인물(점장, 손님, 본사 담당자)도 함께 적어주세요.
      </W>
      {dialog}
    </Screen>
  );
}
