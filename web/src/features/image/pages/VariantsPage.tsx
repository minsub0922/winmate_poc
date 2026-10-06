/**
 * IMG3V · 변형 · 비율 · 해상도(§4.10) — 기준 시안의 변형(A~D, 이어서 E~H) 중 하나를 골라 비율(다중) · 맞추는 방법 · 업스케일로 다시 만든다.
 * 「{k}개 비율로 만들기」 → `POST renditions` → IMG3G. 능력이 없으면 버튼을 끄고 이유를 툴팁으로.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Button, cx, ErrorState, Icon, Img } from '@/ui';
import { errMessage, img, type RunDetail, type Shot } from '../api';
import { AskInput, Echo, Loading, Pill, Screen, Seg, ShotCard, useImgShell, WSay } from '../components';
import { isActive, qk, useCaps, useImage, useInvalidate } from '../hooks';
import { ASPECTS_ALL, josa, route, sizeFor, sizeLabel, type AspectAll } from '../lib';

const USE: Record<AspectAll, string> = { '16:9': '슬라이드 · 표지', '4:3': '4:3 제안서 템플릿', '1:1': 'SNS · 썸네일', '9:16': '세로형 사이니지 · 모바일' };
const UP_KIND = { '1x': 'fhd', '2x': 'uhd', '4x': 'uhd8k' } as const;
const UP_LABEL = { '1x': '원본', '2x': '×2', '4x': '×4' } as const;
type Fit = 'recompose' | 'crop' | 'outpaint';
type Up = '1x' | '2x' | '4x';

const ratioOf = (a: string) => { const [x, y] = a.split(':').map(Number); return x / y; };
/** 새로 채울 쪽(§4.10) — 지시문에 위쪽 · 아래쪽이 있으면 그 반대쪽, 아니면 세로로 길어지면 위아래 · 가로로 넓어지면 양옆 */
function fillSide(base: string, target: string, instr?: string): string {
  if (instr && /위쪽|위에|상단/.test(instr)) return '아래쪽';
  if (instr && /아래쪽|아래에|하단/.test(instr)) return '위쪽';
  return ratioOf(target) < ratioOf(base) ? '위아래' : '양옆';
}

export default function VariantsPage() {
  const { workId = '', imageId = '' } = useParams();
  const loc = useLocation();
  const nav = useNavigate();
  const inv = useInvalidate();
  const caps = useCaps();
  const base = useImage(imageId);
  const runsQ = useQuery({ queryKey: [...qk.runs(workId), 'variants'], queryFn: () => img.runs(workId, { kind: 'variants' }), enabled: !!workId, staleTime: 1_000,
    refetchInterval: (q) => ((q.state.data?.items ?? []).some((r) => r.base_image_id === imageId && isActive(r.status)) ? 2_000 : false) });
  const vRuns: RunDetail[] = useMemo(() => (runsQ.data?.items ?? []).filter((r) => r.base_image_id === imageId).reverse(), [runsQ.data, imageId]);
  const shots: Shot[] = useMemo(() => vRuns.flatMap((r) => r.shots).filter((s) => s.state !== 'canceled'), [vRuns]);
  const running = vRuns.some((r) => isActive(r.status));
  const [selId, setSelId] = useState<string | null>(null);
  const firstDone = shots.find((s) => s.state === 'done');
  useEffect(() => { if (!selId && firstDone) setSelId(firstDone.image_id); }, [selId, firstDone]);
  const selShot = shots.find((s) => s.image_id === selId) ?? null;
  const selIsBase = !selShot;
  const targetId = selShot?.state === 'done' ? selShot.image_id : selIsBase ? imageId : null;
  const targetAspect = (selIsBase ? base.data?.aspect : selShot?.aspect) ?? '16:9';
  const [aspects, setAspects] = useState<AspectAll[] | null>(null);
  const [fit, setFit] = useState<Fit>('recompose');
  const [up, setUp] = useState<Up>('2x');
  const [instr, setInstr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  useEffect(() => { if (aspects === null && base.data) setAspects([base.data.aspect as AspectAll]); }, [aspects, base.data]);

  const f = caps.data?.features;
  const noRecompose = !!f && !f.recompose;
  const noOutpaint = !!f && !f.outpaint;
  const no4x = !!f && !f.upscale_4x;
  useEffect(() => { if (fit === 'recompose' && noRecompose) setFit('crop'); if (up === '4x' && no4x) setUp('2x'); }, [noRecompose, no4x, fit, up]);

  const label = selShot ? (selShot.letter ? `변형 ${selShot.letter}` : selShot.label) : base.data?.label ?? '기준 시안';
  const thumb = selShot?.thumb_url ?? (selIsBase ? base.data?.thumb_url : null) ?? null;
  const sel = aspects ?? [];
  const k = sel.length;
  const start = async () => {
    if (!targetId || !k) return;
    setBusy('make'); setMsg(null);
    try {
      const acc = await img.renditions(targetId, { aspects: sel, fit, upscale: up, instructions: Object.keys(instr).length ? instr : undefined });
      void inv.gallery();
      nav(route.run(workId, acc.run_id));
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const more = async (axis: 'any' | 'lighting' | 'people', instruction?: string) => {
    setBusy(axis); setMsg(null);
    try { await img.variants(imageId, { count: 4, axis, instruction }); await runsQ.refetch(); setSelId(null); } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const ask = async (text: string) => {
    setBusy('ask'); setMsg(null);
    try {
      const r = await img.interpret(targetId ?? imageId, { text, screen: 'variants' });
      if (r.action === 'aspect_instruction' && r.aspect) {
        setInstr((m) => ({ ...m, [r.aspect!]: r.instruction || text }));
        if (!sel.includes(r.aspect as AspectAll)) setAspects([...sel, r.aspect as AspectAll]);
        setMsg({ text: `${r.aspect} 구도 지시를 저장했어요 · ${r.instruction || text}`, ok: true });
      } else if (r.action === 'variants') await more('any', r.instruction || text);
      else setMsg({ text: r.question ?? '어떤 변형을 원하는지 조금 더 알려 주세요', ok: false });
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };

  useImgShell({ title: base.data?.work_title || base.data?.title || '변형', step: 3 });
  if (base.isLoading || runsQ.isLoading) return <Loading />;
  if (!base.data) return <div className="img-center"><ErrorState message="시안을 불러오지 못했어요" onRetry={() => base.refetch()} /></div>;
  const b = base.data;
  const baseLabel = b.label;
  const n = shots.length;
  const echo = (loc.state as { echo?: string } | null)?.echo ?? `${baseLabel}${josa(baseLabel, '으로', '로')} 변형 만들기`;
  const wText = !n
    ? `${baseLabel}${josa(baseLabel, '을', '를')} 기준으로 변형을 만들거나, 원하는 비율과 해상도로 다시 만들 수 있어요.`
    : running
      ? `${baseLabel}${josa(baseLabel, '을', '를')} 기준으로 변형 ${n}장을 만들고 있어요.`
      : `${baseLabel}${josa(baseLabel, '을', '를')} 기준으로 변형 ${n}장을 만들었습니다. 제품 배치는 그대로 두고 시간대 · 조명 · 시점을 조금씩 달리했어요. 고른 변형은 원하는 비율과 해상도로 다시 만들 수 있습니다.`;
  const upText = up === '1x' ? '업스케일 없음' : `${UP_LABEL[up]} 업스케일`;
  return (
    <Screen testid="img3v" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span data-testid="img3v-head">{label} 선택됨<small> · {k ? sel.join(' + ') : '비율 없음'} · {upText}</small></span>
            <span className="img-quick">
              <Pill disabled={!!busy || running} onClick={() => void more('any')}>변형 4장 더</Pill>
              <Pill disabled={!!busy || running} onClick={() => void more('lighting')}>조명만 바꾸기</Pill>
              <Pill disabled={!!busy || running} onClick={() => void more('people')}>손님 넣기</Pill>
            </span>
          </div>
          {msg && <div className={cx('img-askline', !msg.ok && 'img-err')} role="status" data-testid="img3v-msg"><Icon name={msg.ok ? 'check' : 'info'} size={13} />{msg.text}</div>}
          <div className="wm-composer__foot">
            <AskInput label="변형 요청" placeholder="요청 (예: 세로 버전은 메뉴보드를 위쪽에)" busy={busy === 'ask'} onSend={ask} testid="img3v-ask" />
            <Button h={44} onClick={() => nav(route.result(workId, imageId))}>결과로 돌아가기</Button>
            <Button h={44} variant="primary" disabled={!k || !targetId || !!busy} loading={busy === 'make'} disabledReason={!k ? '비율을 하나 이상 골라 주세요' : '완성된 변형을 골라 주세요'}
              onClick={() => void start()} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>{k}개 비율로 만들기</Button>
          </div>
        </div>
      </div>
    }>
      <Echo head="변형" text={echo} />
      <WSay text={wText}>
        <div className="img-card img-card--pad">
          <div className="img-card__head">
            <span className="img-card__title">변형 {n}장<small> · 기준 {baseLabel} · 제품 배치 유지</small></span>
            <span className="img-row" style={{ gap: 6 }}>
              {selShot?.state === 'done' && <Link to={route.edit(workId, selShot.image_id)} className="img-btn30" style={{ height: 26 }}>부분 수정</Link>}
              {targetId && <Link to={route.exportTo(workId, targetId)} className="img-btn30" style={{ height: 26, color: 'var(--wm-brand)' }}>이 변형 바로 내보내기</Link>}
            </span>
          </div>
          <div className="img-vars" data-testid="img3v-vars">
            {n === 0 && (
              <button type="button" className="img-var" aria-pressed aria-label={`${baseLabel} 기준 시안 선택됨`}>
                <Img src={b.thumb_url} alt={`${baseLabel} 기준 시안`} />
                <span className="img-var__check"><Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} /></span>
                <span className="img-var__tag">{baseLabel} · 기준</span>
              </button>
            )}
            {shots.map((s) => {
              const on = s.image_id === selId;
              const letter = s.letter ?? s.label.split(' ')[0];
              if (s.state !== 'done') return <div key={s.image_id} className="img-var"><ShotCard shot={s} fill /></div>;
              return (
                <button key={s.image_id} type="button" className="img-var" aria-pressed={on} aria-label={on ? `변형 ${letter} 선택됨` : `변형 ${letter}`} onClick={() => setSelId(s.image_id)}>
                  <Img src={s.thumb_url} alt={`변형 ${s.label}`} />
                  {on && <span className="img-var__check"><Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} /></span>}
                  {s.layout_note && <span className="img-var__note">{s.layout_note}</span>}
                  <span className="img-var__tag">{s.label}</span>
                </button>
              );
            })}
          </div>
        </div>
        <div className="img-card img-card--pad">
          <div className="img-card__head">
            <span className="img-card__title">비율 · 해상도<small> · 여러 비율을 한 번에 만들 수 있어요</small></span>
            <span className="img-hint img-hint--sm">{label} 기준 · {k}개 선택</span>
          </div>
          <div className="img-ratios" role="group" aria-label="비율" data-testid="img3v-ratios">
            {ASPECTS_ALL.map((a) => {
              const on = sel.includes(a);
              const [pw, ph] = sizeFor(a, UP_KIND[up]);
              const r = ratioOf(a);
              const bw = r >= 1 ? Math.min(142, 80 * r) : 80 * r; const bh = r >= 1 ? bw / r : 80;
              const isBase = a === targetAspect;
              const side = fillSide(targetAspect, a, instr[a]);
              const noteText = isBase ? null : fit === 'crop' ? '일부를 잘라요' : `${side}${josa(side, '은', '는')} 새로 채움`;
              return (
                <button key={a} type="button" className="img-ratio" aria-pressed={on} aria-label={`${a} ${sizeLabel(pw, ph)}`}
                  onClick={() => setAspects(on ? sel.filter((x) => x !== a) : [...sel, a])}>
                  <span className="img-ratio__pv">
                    <span className="img-ratio__img" style={{ width: bw, height: bh }}>
                      <Img src={thumb} alt={`${a} 미리보기`} />
                      {isBase && <span className="img-ratio__orig">원본 비율</span>}
                    </span>
                    {on && noteText && <span className="img-ratio__note">{noteText}</span>}
                  </span>
                  <span style={{ display: 'flex', flexDirection: 'column', gap: 2, width: '100%' }}>
                    <span className="img-row" style={{ gap: 6 }}>
                      <span className="img-ratio__box">{on && <Icon name="check" size={10} color="var(--wm-surface)" strokeWidth={3} />}</span>
                      <span className="img-ratio__name">{a}</span>
                      <span style={{ flex: 1 }} />
                      <span className="img-ratio__px">{sizeLabel(pw, ph)}</span>
                    </span>
                    <span className="img-ratio__use">{instr[a] ? `지시: ${instr[a]}` : USE[a]}</span>
                  </span>
                </button>
              );
            })}
          </div>
          <div className="img-row" style={{ gap: 20, paddingTop: 2, flexWrap: 'wrap' }}>
            <span className="img-row">
              <span className="img-label" style={{ whiteSpace: 'nowrap' }}>비율 맞추는 방법</span>
              <Seg ariaLabel="비율 맞추는 방법" value={fit} onChange={setFit} items={[
                { value: 'recompose', label: '다시 구성', disabled: noRecompose, title: noRecompose ? '지금 모델로는 다시 구성할 수 없어요' : undefined },
                { value: 'crop', label: '잘라내기' },
                { value: 'outpaint', label: '바깥 채우기', disabled: noOutpaint, title: noOutpaint ? '지금 모델로는 바깥 채우기를 할 수 없어요' : undefined },
              ]} />
            </span>
            <span className="img-row">
              <span className="img-label">업스케일</span>
              <Seg ariaLabel="업스케일" value={up} onChange={setUp} items={[
                { value: '1x', label: '원본' }, { value: '2x', label: '×2' },
                { value: '4x', label: '×4', disabled: no4x, title: no4x ? '×4는 업스케일 모델이 있어야 해요' : undefined },
              ]} />
            </span>
            <span style={{ flex: 1 }} />
            <span className="img-row img-hint img-hint--sm" style={{ gap: 5 }}><Icon name="info" size={13} />제품 외형은 고정</span>
          </div>
        </div>
      </WSay>
    </Screen>
  );
}
