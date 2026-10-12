/**
 * RQ_View — 저장한 고객 요구사항 보기(보드 webapp1 View content=rq · RQ_View). 저장 뒤 · 목록 · 작업 내역에서 열면 이 화면이다.
 * 왼쪽 340px 개요(프로젝트명 · 고객사 · 최종 제안대상 · 제작자 의견 · 읽은 자료) | 오른쪽 1fr 키맨별 요구사항. 후속 작업 = DSS.
 */
import { FlowContentView, whenText } from '@/shell';
import { cx } from '@/ui';
import type { RFDoc, RFReq } from './api';
import { euro } from './form';

/** 요구 줄 꼬리표 — 편집 화면(RQ1)과 같은 이름 */
function reqTag(r: RFReq): { t: string; cls: string } | null {
  if (r.flag === 'vague') return { t: '범위 불명확', cls: 'rqv-tag--warn' };
  if (r.flag === 'ask') return { t: '고객에게 확인', cls: 'rqv-tag--ask' };
  if (r.status === 'check') return { t: '확인 필요', cls: 'rqv-tag--warn' };
  return null;
}

export function RqView({ doc }: { doc: RFDoc }) {
  const keymen = (doc.keymen ?? []).filter((k) => k.role.trim() || k.reqs.length);
  const reqs = keymen.flatMap((k) => k.reqs);
  const flagged = reqs.filter((r) => reqTag(r)).length;
  const sum = keymen.reduce((n, k) => n + (k.weight ?? 0), 0);
  const sources = doc.sources ?? [];
  const sbIds = doc.sb_ids ?? [];
  const facts: { k: string; v: string; hint?: string; muted?: boolean; small?: boolean }[] = [
    { k: '프로젝트명', v: doc.title || '—', muted: !doc.title },
    { k: '고객사', v: doc.customer || '—', muted: !doc.customer },
    { k: '최종 제안대상', v: doc.target || '—', muted: !doc.target },
    { k: '제작자 의견', v: doc.note?.trim() || '적지 않았어요', hint: '고객 문서에서 빠져요', muted: !doc.note?.trim(), small: true },
    { k: '읽은 자료', v: sources.length ? sources.map((s) => (s.pages ? `${s.name} · ${s.pages}쪽` : s.name)).join(' · ') : '직접 입력', small: true },
  ];
  return (
    <FlowContentView stageKey="rq" sbIds={sbIds} title={doc.title || '새 요구사항'} refVer={`${doc.code} v${doc.ver}`}
      meta={[doc.saved_at && `${whenText(doc.saved_at)} 저장`, `키맨 ${keymen.length}`, `요구 ${reqs.length}`, flagged > 0 && `확인 필요 ${flagged}`]}
      follow={sbIds[0] ? [{ key: 'dss', desc: `${sbIds[0]}${euro(sbIds[0])} 공간마다 제품 · 솔루션을 골라요` }] : undefined}>
      <div className="rqv-grid">
        <div className="fl-vcard rqv-facts">
          {facts.map((f) => (
            <div key={f.k} className="rqv-fact">
              <span className="rqv-k">{f.k}{f.hint && <small>· {f.hint}</small>}</span>
              <span className={cx('rqv-v', f.small && 'rqv-v--sm', f.muted && 'rqv-v--muted')}>{f.v}</span>
            </div>
          ))}
        </div>
        <div className="fl-vcard rqv-km">
          <div className="rqv-kmhead"><b>키맨별 요구사항</b><span>키맨 {keymen.length} · 가중치 합 {sum}%</span></div>
          <div className="rqv-kmlist">
            {keymen.map((k) => (
              <div key={k.id} className="rqv-kmcard">
                <span className="rqv-who"><b>{k.role || '이름 없는 키맨'}</b><span className="rqv-w">{k.weight}%</span></span>
                <span className="rqv-reqs">
                  {k.reqs.map((r, i) => {
                    const t = reqTag(r);
                    return (
                      <span key={r.id} className="rqv-req"><span className="rqv-n">{i + 1}</span><span className="rqv-rt">{r.text}</span>
                        {t && <span className={cx('rqv-tag', t.cls)}>{t.t}</span>}</span>
                    );
                  })}
                  {!k.reqs.length && <span className="rqv-req rqv-req--empty">적은 요구사항이 없어요</span>}
                </span>
              </div>
            ))}
            {!keymen.length && <span className="fl-muted">적은 키맨이 없어요</span>}
          </div>
        </div>
      </div>
    </FlowContentView>
  );
}
