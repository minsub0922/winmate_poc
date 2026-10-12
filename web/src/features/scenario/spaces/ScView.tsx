/**
 * SC_View — 저장한 공간 시나리오 보기(보드 webapp1 View content=sc · SC_View). 저장 뒤 · 목록 · 작업 내역에서 열면 이 화면이다.
 * 왼쪽 236px 공간 목록(「공간 · DSS-01」 · 시나리오 n · 제품 n) | 오른쪽 1fr 고른 공간(머리 · 제품 · 솔루션 칩) + 시나리오 카드 두 칸.
 * 고른 공간은 화면 안 상태(처음엔 시나리오가 있는 첫 공간). 후속 작업 없음. 값은 묶음 문서 그대로 — 없는 값은 「—」, `[확인 필요]` 는 주황.
 */
import { useState } from 'react';
import { FlowContentView, useFlow, whenText } from '@/shell';
import { cx } from '@/ui';
import type { SSDoc, SSScenario } from './api';

const CHECK = '[확인 필요]';

/** 출처 태그(보드 c.by): 직접 · AI A안 · 수락 */
function byTag(by: string | null | undefined): [string, string] {
  if (!by || by === 'manual') return ['직접', ''];
  return [`AI ${by.split('-').pop()}안 · 수락`, 'fl-vtag--ai'];
}

function ScCard({ sc, spNames }: { sc: SSScenario; spNames: string[] }) {
  const [tag, tagCls] = byTag(sc.by);
  const prods = sc.products.filter((p) => spNames.includes(p));
  const steps = sc.steps.filter((t) => t.text.trim() || t.product);
  const fields = sc.fields.filter((f) => f.k.trim() || (f.v ?? '').trim());
  return (
    <div className="scv-card" data-testid="scv-card">
      <span className="scv-card__top"><span className={cx('scv-card__title', !sc.title && 'scv-muted')}>{sc.title || '이름 없는 시나리오'}</span>
        <span className={cx('fl-vtag', tagCls)}>{tag}</span></span>
      <span className="scv-kv"><span className="scv-k">사용자</span>
        <span className={cx(!sc.user && 'scv-muted', sc.user.includes(CHECK) && 'scv-check')}>{sc.user || '—'}</span></span>
      <span className="scv-kv"><span className="scv-k">제품</span>
        <span className="scv-pills">{prods.length ? prods.map((p) => <span key={p} className="scv-pill">{p}</span>) : <span className="scv-muted">—</span>}</span></span>
      {steps.length > 0 && (
        <span className="scv-steps">
          {steps.map((t, j) => (
            <span key={j} className="scv-step"><span className="scv-n">{j + 1}</span>
              <span className={cx('scv-st', !t.text.trim() && 'scv-muted', t.text.includes(CHECK) && 'scv-check')}>{t.text.trim() || '—'}</span>
              {t.product && <span className="scv-sprod">{t.product}</span>}</span>
          ))}
        </span>
      )}
      {fields.map((f, i) => (
        <span key={i} className="scv-kv"><span className="scv-k">{f.k}</span>
          <span className={cx(!(f.v ?? '').trim() && 'scv-muted', (f.v ?? '').includes(CHECK) && 'scv-check')}>{(f.v ?? '').trim() || '—'}</span></span>
      ))}
    </div>
  );
}

export function ScView({ doc }: { doc: SSDoc }) {
  const spaces = doc.spaces;
  const [pick, setPick] = useState<string | null>(null);
  const sp = spaces.find((s) => s.id === pick) ?? spaces.find((s) => s.scenarios.length) ?? spaces[0];
  const nSc = spaces.reduce((a, s) => a + s.scenarios.length, 0);
  const noSc = spaces.filter((s) => !s.scenarios.length).length;
  // 저장 시각 — 허브 기록(같은 참조 · 판)의 시각, 없으면 저장 직후 상태의 문서 시각
  const flow = useFlow(doc.sb_id ?? null).data;
  const hist = flow?.history?.slice().reverse().find((h) => h.key === 'sc' && h.ref === doc.code);
  const savedAt = hist?.at ?? (doc.status === 'done' ? doc.updated_at : null);
  const spNames = sp ? sp.products.map((p) => p.name) : [];
  return (
    <FlowContentView stageKey="sc" sbIds={doc.sb_id ? [doc.sb_id] : []} title={doc.title || '공간 시나리오'} refVer={`${doc.code ?? doc.id} v${doc.ver}`}
      meta={[savedAt && `${whenText(savedAt)} 저장`, `공간 ${spaces.length}`, `시나리오 ${nSc}`, `시나리오 없는 공간 ${noSc}`]}>
      <div className="scv-grid">
        <div className="fl-vcard scv-spaces" role="group" aria-label="공간">
          <span className="scv-spaces__h">공간 · {doc.dss_ref ?? 'DSS'}</span>
          {spaces.map((s) => {
            const n = s.scenarios.length;
            const on = s.id === sp?.id;
            return (
              <button key={s.id} type="button" aria-pressed={on} className={cx('scv-sp', on && 'scv-sp--on')} onClick={() => setPick(s.id)}>
                <span className="scv-sp__name">{s.name}</span>
                <span className={cx('scv-sp__sub', !n && 'scv-sp__sub--empty')}>{n ? `시나리오 ${n} · 제품 ${s.products.length}` : `시나리오 없음 · 제품 ${s.products.length}`}</span>
              </button>
            );
          })}
        </div>
        <div className="fl-vcard scv-main">
          {sp && (
            <>
              <div className="scv-head">
                <span className="scv-head__name">{sp.name}</span>
                <span className="scv-head__n">시나리오 {sp.scenarios.length}</span>
                <span className="scv-grow" />
                {sp.products.map((p) => (
                  <span key={p.name} className="scv-chip"><span className={cx('scv-chip__kind', p.kind === 'solution' && 'scv-chip__kind--sol')}>{p.kind === 'solution' ? '솔루션' : '제품'}</span>
                    <span className="scv-chip__name">{p.name}</span></span>
                ))}
              </div>
              <div className="scv-body">
                {!sp.scenarios.length ? (
                  <div className="scv-empty"><b>이 공간은 시나리오가 없어요</b><span>편집에서 시나리오를 더할 수 있어요.</span></div>
                ) : (
                  <div className="scv-cards">{sp.scenarios.map((sc) => <ScCard key={sc.id} sc={sc} spNames={spNames} />)}</div>
                )}
              </div>
            </>
          )}
          {!sp && <div className="scv-body"><span className="fl-muted">공간이 없어요</span></div>}
        </div>
      </div>
    </FlowContentView>
  );
}
