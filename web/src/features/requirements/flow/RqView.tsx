/**
 * 고객 요구사항 최종본 본문(보드 webapp1 v62 View content=rq · RQ_View · RQ_Draft) — 칸은 보드 인라인 px 그대로(rqview.css).
 *   왼쪽 340 사실 칸(프로젝트명 · 고객사 · 최종 제안대상 · 제작자 의견 · 읽은 자료) | 오른쪽 키맨별 요구사항(머리 48 · 키맨 카드 170 | 1fr · 번호 요구 · 확인 필요).
 *   저장 전(새로 · 작성 중)은 ① 요구사항 입력 자리표시(StepSlot) — 요구사항은 입력 한 단계라 저장해야 칸이 채워진다.
 *   본문 data 속성은 입력 팝업(Editor: data-keyman · data-req)과 겹치지 않게 data-vkeyman · data-vreq.
 */
import { StepSlot, type DetailStatus } from '@/shell';
import { cx } from '@/ui';
import type { RFDoc } from './api';
import './rqview.css';

/** 저장(:finish)한 적이 있는가 — status done 또는 ver ≥ 1 */
export const rfSaved = (d: RFDoc | null | undefined): boolean => !!d && (d.status === 'done' || (d.ver ?? 0) > 0);

/** 마친 단계 수(한 단계) — 저장했으면 1 */
export const rfDone = (d: RFDoc | null | undefined): number => (rfSaved(d) ? 1 : 0);

/** 보드 View 이름(h1) — 프로젝트명 · 없으면 고객사 · 둘 다 없으면 「새 요구사항」 */
export const rfName = (d: RFDoc | null | undefined): string => d?.title?.trim() || d?.customer?.trim() || '새 요구사항';

/** 내용이 있는 키맨만(서버 counts 와 같은 규칙: 직함이나 요구가 있어야) */
const keymenOf = (d: RFDoc) => (d.keymen ?? []).filter((k) => (k.role ?? '').trim() || (k.reqs ?? []).length);

function Fact({ k, hint, v, tone }: { k: string; hint?: string; v: string; tone?: 'strong' | 'text' | 'off' | 'src' | 'warn' }) {
  return (
    <div className="rqv-fact">
      <span className="rqv-fact__k">{k}{hint && <small>· {hint}</small>}</span>
      <span className={cx('rqv-fact__v', tone && `rqv-fact__v--${tone}`)}>{v}</span>
    </div>
  );
}

export function RqViewBody({ d, status, onStep }: { d: RFDoc | null; status: DetailStatus; onStep: (k: number) => void }) {
  if (!d || status !== 'saved') {
    return (
      <StepSlot n={1} label="요구사항 입력" what="프로젝트명 · 고객사 · 최종 제안대상 · 키맨별 요구사항" next cta={status === 'draft'} onOpen={() => onStep(1)} big />
    );
  }
  const kms = keymenOf(d);
  const c = d.counts;
  const must = (v: string) => (v.trim() ? { v, tone: 'strong' as const } : { v: '[확인 필요]', tone: 'warn' as const });
  const sources = (d.sources ?? []).map((s) => s.name);
  return (
    <div className="rqv">
      <div className="rqv-facts" aria-label="요구사항 개요">
        <Fact k="프로젝트명" {...must(d.title ?? '')} />
        <Fact k="고객사" {...must(d.customer ?? '')} />
        <Fact k="최종 제안대상" {...must(d.target ?? '')} />
        <Fact k="제작자 의견" hint="고객 문서에서 빠져요" v={d.note?.trim() || '적지 않았어요'} tone={d.note?.trim() ? 'text' : 'off'} />
        <Fact k="읽은 자료" v={sources.length ? sources.join(' · ') : '직접 입력'} tone="src" />
      </div>
      <div className="rqv-kms">
        <div className="rqv-kms__h"><b>키맨별 요구사항</b><span className="rqv-kms__sum">키맨 {c.keymen} · 가중치 합 {c.weight_sum}%</span></div>
        <div className="rqv-kms__list">
          {kms.map((k, i) => {
            const who = (k.role ?? '').trim() || `키맨 ${i + 1}`;
            return (
              <div key={k.id} className="rqv-km" data-vkeyman={who}>
                <span className="rqv-km__who"><b className={cx(!(k.role ?? '').trim() && 'rqv-km__none')}>{who}</b><span className="rqv-km__w">{k.weight}%</span></span>
                <span className="rqv-km__reqs">
                  {(k.reqs ?? []).map((r, j) => (
                    <span key={r.id} className="rqv-req" data-vreq={r.id}>
                      <span className="rqv-req__n">{j + 1}</span>
                      <span className="rqv-req__t">{r.text}</span>
                      {r.status === 'check' && <span className="rqv-req__warn">확인 필요</span>}
                    </span>
                  ))}
                  {!(k.reqs ?? []).length && <span className="rqv-req rqv-req--none">요구사항 [확인 필요]</span>}
                </span>
              </div>
            );
          })}
          {!kms.length && <span className="rqv-kms__none">키맨 · 요구사항 [확인 필요] — 「요구사항 입력」에서 적어요</span>}
        </div>
      </div>
    </div>
  );
}
