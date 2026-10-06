/**
 * 2단계 `기획 방향` — SB2(추천 조합 · 축 3) · SB2E(파트별 핵심 메시지 · 표현 표시). §4.8–4.9
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';
import { Icon, Skeleton, toast } from '@/ui';
import {
  eul, errorText, roJosa, sbApi, sbKey, useAction, useJobRefresh, useSb, useSbShell,
  type DirectionOption, type Flag, type KeyMessage, type Sb,
} from './lib';
import { Back, Bottom, Choice, FailBand, Gate, GreyLink, Head, LoadingHead, Page, Primary, SbBadge, SkeletonRows } from './parts';

const COUNT_WORD: Record<number, string> = { 2: '두', 3: '세', 4: '네', 5: '다섯' };

function sortedOptions(sb: Sb): DirectionOption[] {
  const opts = sb.direction?.options ?? [];
  return [...opts.filter((o) => o.kind === 'combo'), ...opts.filter((o) => o.kind === 'axis').sort((a, b) => (a.key ?? '').localeCompare(b.key ?? ''))];
}

function optionTitle(o: DirectionOption) {
  return o.kind === 'axis' && o.key ? `${o.key} ${o.title}` : o.title;
}

/** SB2 — 2 기획 방향 — 추천 조합 */
export function DirectionScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 2);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const [sel, setSel] = useState<string | null>(null);
  const pending = useRef<Promise<unknown>>(Promise.resolve());
  useJobRefresh(sbId, sb?.active_job?.job_id);
  const options = useMemo(() => (sb ? sortedOptions(sb) : []), [sb]);
  useEffect(() => {
    if (sb?.direction?.ready && sel === null) setSel(sb.direction.selected_option_id ?? sb.direction.recommended_option_id ?? null);
  }, [sb, sel]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;

  const d = sb.direction;
  const running = sb.active_job?.kind === 'sb.direction';
  const failed = !running && !!d && !d.ready && !d.options?.length;
  const messagesRunning = sb.active_job?.kind === 'sb.messages';
  const retry = () => void act.run(async () => { await sbApi.startDirection(sb.id, false); await qc.invalidateQueries({ queryKey: sbKey(sb.id) }); });

  if (!d?.ready || running || !options.length) {
    return (
      <Page label="기획 방향">
        {failed ? (
          <>
            <Head title="기획 방향을 만들지 못했어요" sub="잠시 후 다시 시도해 주세요. 답한 기획 질의는 그대로 있어요." />
            <FailBand message="기획 방향을 만들지 못했어요." onRetry={retry} busy={act.busy} />
          </>
        ) : !d ? (
          <>
            <Head title="아직 기획 방향이 없어요" sub="정의서를 고르고 기획 질의에 답하면 기획 방향을 만들어요." />
          </>
        ) : (
          <>
            <LoadingHead title="기획 방향을 만드는 중이에요" sub="요구를 축으로 나누고 빠지지 않는 조합을 찾고 있어요." />
            <SkeletonRows n={4} h={68} />
          </>
        )}
        <Bottom
          back={<Back to={`/storyboard/${sb.id}/source`}>정의서</Back>}
          primary={!d ? <Primary to={`/storyboard/${sb.id}/source`}>정의서 고르기</Primary>
            : <Primary disabled disabledReason="기획 방향을 만드는 중이에요">이대로 목차 만들기</Primary>} />
      </Page>
    );
  }

  const rec = options.find((o) => o.id === d.recommended_option_id) ?? options[0];
  const axes = options.filter((o) => o.kind === 'axis');
  const total = d.total;
  const combo = options.find((o) => o.kind === 'combo');
  const comboCount = combo?.coverage?.count ?? 0;
  const title = rec.kind === 'combo'
    ? `기획 방향 — ${COUNT_WORD[axes.length] ?? axes.length} 축을 섞어 쓰는 걸 추천해요`
    : `기획 방향 — ${eul(optionTitle(rec))} 추천해요`;
  const sub = comboCount >= total
    ? `축 하나만 쓰면 빠지는 요구가 생겨요. 추천 조합은 요구 ${total}개를 모두 담아요.`
    : `축 하나만 쓰면 빠지는 요구가 생겨요. 추천 조합은 요구 ${total}개 중 ${comboCount}개를 담아요.`;
  const current = sel ?? rec.id;
  const choose = (id: string) => {
    if (id === current) return;
    setSel(id);
    pending.current = pending.current.then(() => sbApi.patchDirection(sb.id, { selected_option_id: id })
      .then(() => qc.invalidateQueries({ queryKey: sbKey(sb.id) }))
      .catch((e) => toast(errorText(e))));
  };
  const toMessages = () => void act.run(async () => { await pending.current; navigate(`/storyboard/${sb.id}/direction/messages`); });
  const makeOutline = () => void act.run(async () => {
    await pending.current;
    await sbApi.startOutline(sb.id, { retry: false });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/outline`);
  });
  return (
    <Page label="기획 방향">
      <Head title={title} sub={sub} />
      <div className="sb-choices" role="group" aria-label="기획 방향">
        {options.map((o) => {
          const on = o.id === current;
          const cov = o.coverage ?? { count: 0, total };
          const right = <>요구 <b className={on ? 'sb-hl' : undefined}>{cov.count}</b> / {cov.total}</>;
          if (o.kind === 'combo') {
            return (
              <Choice key={o.id} pressed={on} onClick={() => choose(o.id)} title={optionTitle(o)} hint={o.one_liner} right={right}
                badge={o.id === d.recommended_option_id ? <SbBadge tone="fill" small>추천</SbBadge> : undefined} testId="dir-combo">
                <span className="sb-maps">
                  {(o.mapping ?? []).map((m) => (
                    <span key={m.place_label} className="sb-map">
                      <span className="sb-map__place">{m.place_label}</span>
                      <Icon name="arrowLeft" size={13} />
                      <span className="sb-map__axis">{m.axis_label}</span>
                    </span>
                  ))}
                </span>
              </Choice>
            );
          }
          return (
            <Choice key={o.id} pressed={on} tall onClick={() => choose(o.id)} title={optionTitle(o)} hint={o.one_liner} right={right}
              badge={o.id === d.recommended_option_id ? <SbBadge tone="fill" small>추천</SbBadge> : undefined} testId={`dir-axis-${o.key}`} />
          );
        })}
      </div>
      <Bottom
        back={<GreyLink onClick={toMessages} icon={<Icon name="edit" size={13} />}>핵심 메시지 고치기</GreyLink>}
        primary={(
          <Primary onClick={makeOutline} busy={act.busy} disabled={messagesRunning} disabledReason="핵심 메시지를 다시 쓰는 중이에요">
            이대로 목차 만들기
          </Primary>
        )} />
    </Page>
  );
}

/** 표시할 구간: 검증 안 된 주장(열림) · 되돌린 내부 목표 */
function marked(f: Flag) {
  return (f.kind === 'unverified_claim' && f.state === 'open') || (f.kind === 'internal_goal' && f.state === 'reverted');
}

function MessageText({ m, onSave, disabled }: { m: KeyMessage; onSave: (text: string) => void; disabled?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  const spans = (m.flags ?? []).filter((f) => marked(f) && (f.span?.length ?? 0) === 2)
    .map((f) => ({ a: f.span![0], b: f.span![1], id: f.id }))
    .sort((x, y) => x.a - y.a);
  const parts: Array<{ text: string; mark?: string }> = [];
  let at = 0;
  for (const s of spans) {
    if (s.a < at || s.b > m.text.length) continue;
    if (s.a > at) parts.push({ text: m.text.slice(at, s.a) });
    parts.push({ text: m.text.slice(s.a, s.b), mark: s.id });
    at = s.b;
  }
  if (at < m.text.length) parts.push({ text: m.text.slice(at) });
  const commit = () => {
    const t = (ref.current?.innerText ?? '').replace(/\s+/g, ' ').trim();
    if (t && t !== m.text) onSave(t);
    else if (!t && ref.current) ref.current.innerText = m.text;
  };
  return (
    <span key={`${m.text}|${spans.map((s) => `${s.a}-${s.b}`).join(',')}`} ref={ref} className="sb-msg__text" role="textbox" tabIndex={0}
      aria-label={`${m.place_label} 핵심 메시지`} contentEditable={!disabled} suppressContentEditableWarning data-testid="kmsg-text"
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); ref.current?.blur(); }
        if (e.key === 'Escape' && ref.current) { ref.current.innerText = m.text; ref.current.blur(); }
      }}>
      {parts.map((p, i) => (p.mark ? <span key={i} className="sb-mark" data-flag={p.mark}>{p.text}</span> : p.text))}
    </span>
  );
}

function flagText(f: Flag): string {
  if (f.kind === 'unverified_claim' && f.suggestion && !f.note.includes('→')) return `${f.note} → '${f.suggestion}'${roJosa(f.suggestion)}`;
  return f.note;
}

/** SB2E — 2 핵심 메시지 고치기 */
export function MessagesScreen() {
  const { sbId = '' } = useParams();
  const q = useSb(sbId);
  const sb = q.data;
  useSbShell(sb, 2);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const act = useAction();
  const flagAct = useAction();
  const [extra, setExtra] = useState<string | null>(null);
  const saves = useRef<Promise<unknown>>(Promise.resolve());
  useJobRefresh(sbId, sb?.active_job?.job_id);
  useEffect(() => { if (sb?.direction && extra === null) setExtra(sb.direction.extra_direction ?? ''); }, [sb, extra]);
  if (!sb) return <Gate loading={q.isLoading} error={q.error} onRetry={() => void q.refetch()} />;

  const d = sb.direction;
  const running = sb.active_job?.kind === 'sb.messages' || sb.active_job?.kind === 'sb.direction' || !d?.ready;
  const msgs = d?.key_messages ?? [];
  const saveText = (m: KeyMessage, text: string) => {
    saves.current = saves.current.then(() => sbApi.patchMessage(sb.id, m.id, text)
      .then(() => qc.invalidateQueries({ queryKey: sbKey(sb.id) }))
      .catch((e) => toast(errorText(e))));
  };
  const flag = (m: KeyMessage, f: Flag, action: 'apply' | 'revert') => void flagAct.run(async () => {
    await saves.current;
    await sbApi.flag(sb.id, m.id, f.id, action);
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
  });
  const saveExtra = async () => {
    const v = (extra ?? '').trim();
    if (v !== (d?.extra_direction ?? '')) await sbApi.patchDirection(sb.id, { extra_direction: v });
  };
  const go = () => void act.run(async () => {
    (document.activeElement as HTMLElement | null)?.blur?.();
    await new Promise((r) => setTimeout(r, 0));
    await saves.current;
    await saveExtra();
    await sbApi.startOutline(sb.id, { extra_direction: (extra ?? '').trim() || null, retry: false });
    await qc.invalidateQueries({ queryKey: sbKey(sb.id) });
    navigate(`/storyboard/${sb.id}/outline`);
  });
  return (
    <Page label="파트별 핵심 메시지">
      <Head eyebrow="기획 방향 · 메시지" title="파트별 핵심 메시지" sub="문장을 눌러 바로 고치세요. 고객 문서에 넣기 어려운 표현은 AI가 표시해요." />
      {running ? (
        <div className="sb-card" aria-busy="true">
          {[0, 1, 2].map((i) => <div key={i} className="sb-msg"><Skeleton w="40%" h={14} r={5} /><Skeleton w="92%" h={20} r={6} /></div>)}
        </div>
      ) : (
        <div className="sb-card" data-testid="kmsg-list">
          {msgs.map((m) => {
            const visible = (m.flags ?? []).filter((f) => !(f.kind === 'unverified_claim' && f.state === 'applied'));
            return (
              <div key={m.id} className="sb-msg" data-testid="kmsg">
                <span className="sb-msg__head"><b className="sb-msg__place">{m.place_label} · {m.axis_label}</b><span className="sb-subtle">{m.audience}</span></span>
                <MessageText m={m} onSave={(t) => saveText(m, t)} />
                {visible.map((f) => (
                  <span key={f.id} className="sb-flag" data-kind={f.kind} data-state={f.state}>
                    <Icon name="info" size={14} />
                    <span className="sb-grow">{flagText(f)}</span>
                    {f.kind === 'unverified_claim' && f.state === 'open' && (
                      <button type="button" className="sb-flag__btn" disabled={flagAct.busy} onClick={() => flag(m, f, 'apply')}>바꾸기</button>
                    )}
                    {f.kind === 'internal_goal' && f.state === 'applied' && (
                      <button type="button" className="sb-flag__btn" disabled={flagAct.busy} onClick={() => flag(m, f, 'revert')}>되돌리기</button>
                    )}
                    {f.kind === 'internal_goal' && f.state === 'reverted' && (
                      <button type="button" className="sb-flag__btn" disabled={flagAct.busy} onClick={() => flag(m, f, 'apply')}>빼기</button>
                    )}
                  </span>
                ))}
              </div>
            );
          })}
        </div>
      )}
      <label className="sb-extra">
        <span className="sb-extra__k">방향 덧붙이기</span>
        <input value={extra ?? ''} onChange={(e) => setExtra(e.target.value)} onBlur={() => void saveExtra().catch((e) => toast(errorText(e)))}
          placeholder="예) Intro는 시장 변화로 열기, Part 3는 오피스 · 호텔 사례만" />
      </label>
      <Bottom
        back={<Back to={`/storyboard/${sb.id}/direction`}>기획 방향</Back>}
        primary={(
          <Primary onClick={go} busy={act.busy} disabled={running} disabledReason="핵심 메시지를 쓰는 중이에요">저장하고 목차 만들기</Primary>
        )} />
    </Page>
  );
}
