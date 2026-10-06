/**
 * MI4 `Storyboard · Key Message에 근거로 붙이기`(§4.14 다른 기능 · 02-storyboard §8.3 웹 스냅숏 넘기기).
 * mi 는 storyboard 를 부르지 않는다 — 웹이 익명 처리를 마친 근거 스냅숏(`GET /evidence`)을 읽어
 * `POST /api/storyboard/v1/storyboards/{sb}/key-messages/{kmsg}/evidence` 로 올린다.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Modal, Skeleton, cx, toast } from '@/ui';
import { useFeatureItems } from '@/shell';
import { addKeyMessageEvidence, errText, useEvidence, useKeyMessages, type EvidenceItem } from '../api';
import { BigButton, ErrorBand, SecButton } from '../parts';

export function EvidenceSheet({ aid, onClose }: { aid: string; onClose: () => void }) {
  const qc = useQueryClient();
  const ev = useEvidence(aid);
  const sbItems = useFeatureItems('SB', 20);
  const linked = ev.data?.storyboard_id ?? null;
  const [sb, setSb] = useState<string | null>(null);
  const sbId = sb ?? linked ?? sbItems.data?.items?.[0]?.item_id ?? null;
  const kms = useKeyMessages(sbId);
  const [km, setKm] = useState<string | null>(null);
  const [on, setOn] = useState<Record<string, boolean> | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ n: number; place: string } | null>(null);

  const items = useMemo(() => ev.data?.items ?? [], [ev.data]);
  useEffect(() => { if (ev.data && on === null) setOn(Object.fromEntries(items.map((i) => [i.key, i.default_on]))); }, [ev.data, items, on]);
  useEffect(() => { setKm(null); }, [sbId]);
  const kmId = km ?? kms.data?.[0]?.id ?? null;
  const picked = items.filter((i) => on?.[i.key]);
  const sbTitle = linked ? ev.data?.storyboard_title || '연결된 Storyboard' : sbItems.data?.items?.find((x) => x.item_id === sbId)?.title;
  const noSb = !linked && sbItems.isSuccess && !(sbItems.data?.items ?? []).length;

  async function attach() {
    if (!sbId || !kmId || !ev.data || !picked.length) return;
    setBusy(true);
    const src = (ev.data.source ?? {}) as Record<string, unknown>;
    const source = { service: 'mi', ref_id: String(src.ref_id ?? aid), title: String(src.title ?? ''), route: src.route ? String(src.route) : `/mi/${aid}/result` };
    let n = 0;
    try {
      for (const it of picked) {
        await addKeyMessageEvidence(sbId, kmId, { source, text: it.text, citations: (it.citations ?? []).map((c) => ({ title: c.title, url: c.url ?? null })) });
        n += 1;
        setOn((o) => ({ ...(o ?? {}), [it.key]: false }));
      }
      void qc.invalidateQueries({ queryKey: ['mi', 'sb-key-messages', sbId] });
      setDone({ n, place: kms.data?.find((k) => k.id === kmId)?.place_label ?? '' });
    } catch (e) {
      toast(n ? `${n}건을 붙이고 멈췄어요 · ${errText(e)}` : `근거를 붙이지 못했어요 · ${errText(e)}`);
    } finally { setBusy(false); }
  }

  return (
    <Modal open onClose={onClose} title="Key Message에 근거로 붙이기" width={640} footer={
      done ? (
        <div className="mi-row" style={{ justifyContent: 'flex-end', gap: 8 }}>
          <SecButton onClick={onClose}>닫기</SecButton>
          {sbId && <Link to={`/storyboard/${sbId}/direction`} className="mi-btn mi-btn--primary">Storyboard 에서 보기</Link>}
        </div>
      ) : (
        <div className="mi-row" style={{ justifyContent: 'space-between', gap: 12 }}>
          <span className="mi-note">익명 처리를 마친 분석 문장만 붙여요. 출처는 각주로 함께 갑니다.</span>
          <div className="mi-row" style={{ gap: 8, flexShrink: 0 }}>
            <SecButton onClick={onClose}>취소</SecButton>
            <BigButton onClick={() => void attach()} busy={busy} disabled={!sbId || !kmId || !picked.length} arrow={false} testId="mi4-ev-attach"
              reason={!sbId ? '붙일 Storyboard 가 없어요' : !kmId ? 'Key Message 를 골라 주세요' : '붙일 근거를 골라 주세요'}>
              근거 {picked.length}건 붙이기
            </BigButton>
          </div>
        </div>
      )}>
      {done ? (
        <div className="mi-ev__done" role="status" data-testid="mi4-ev-done">
          <b>{done.place ? `${done.place} Key Message에` : 'Key Message에'} 근거 {done.n}건을 붙였어요.</b>
          <span className="mi-note">Storyboard 기획 방향에서 근거와 출처를 볼 수 있어요.</span>
        </div>
      ) : (
        <div className="mi-ev" data-testid="mi4-ev">
          <div className="mi-ev__row">
            <span className="mi-ev__label">Storyboard</span>
            {linked ? <span className="mi-ell"><b>{sbTitle}</b><span className="mi-sub"> · 연결됨</span></span>
              : noSb ? <span className="mi-note">붙일 Storyboard 가 없어요. Storyboard 에서 Key Message 를 만든 뒤 다시 열어 주세요.</span>
                : (
                  <select className="mi-select__btn" style={{ flex: 1, minWidth: 0 }} aria-label="Storyboard" value={sbId ?? ''} onChange={(e) => setSb(e.target.value || null)}>
                    {(sbItems.data?.items ?? []).map((x) => <option key={x.item_id} value={x.item_id}>{x.title}</option>)}
                  </select>
                )}
          </div>

          {sbId && (
            <div className="mi-ev__sec">
              <span className="mi-ev__label">Key Message</span>
              {kms.isLoading && <Skeleton h={64} r={12} />}
              {kms.isError && <ErrorBand message="Key Message 를 읽지 못했어요" onRetry={() => void kms.refetch()} />}
              {kms.isSuccess && !kms.data.length && <span className="mi-note">이 Storyboard 에 아직 Key Message 가 없어요.</span>}
              {kms.isSuccess && kms.data.length > 0 && (
                <div role="radiogroup" aria-label="Key Message" className="mi-ev__list">
                  {kms.data.map((k) => (
                    <div key={k.id} role="radio" aria-checked={kmId === k.id} tabIndex={0} className="mi-opt mi-ev__km" onClick={() => setKm(k.id)}
                      onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setKm(k.id); } }}>
                      <span className="mi-opt__radio" />
                      <div className="mi-opt__body">
                        <span className="mi-row" style={{ gap: 6 }}>
                          <span className="mi-tag mi-tag--brand">{k.place_label}</span>
                          {k.axis_label && <span className="mi-note">{k.axis_label}</span>}
                          {(k.evidence ?? []).length > 0 && <span className="mi-note">· 근거 {(k.evidence ?? []).length}</span>}
                        </span>
                        <span className="mi-opt__desc mi-ev__text">{k.text}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="mi-ev__sec">
            <span className="mi-ev__label">붙일 근거 <span className="mi-sub">· {picked.length} / {items.length}</span></span>
            {ev.isLoading && <Skeleton h={80} r={12} />}
            {ev.isError && <ErrorBand message={errText(ev.error)} onRetry={() => void ev.refetch()} />}
            {ev.isSuccess && !items.length && <span className="mi-note">붙일 만한 분석 문장이 아직 없어요.</span>}
            <div className="mi-ev__list">
              {items.map((it) => <EvidenceRow key={it.key} it={it} on={!!on?.[it.key]} set={(v) => setOn((o) => ({ ...(o ?? {}), [it.key]: v }))} />)}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}

function EvidenceRow({ it, on, set }: { it: EvidenceItem; on: boolean; set: (v: boolean) => void }) {
  return (
    <label className={cx('mi-ev__item', on && 'mi-ev__item--on')} data-kind={it.kind}>
      <input type="checkbox" checked={on} onChange={(e) => set(e.target.checked)} aria-label={`${it.kind_label} · ${it.text}`} />
      <span className="mi-ev__body">
        <span className="mi-row" style={{ gap: 6 }}>
          <span className={cx('mi-tag', it.kind === 'strength' ? 'mi-tag--solid' : 'mi-tag--brand')}>{it.kind_label}</span>
          {it.status && <span className={cx('mi-ev__st', it.status !== '원문 일치' && 'mi-ev__st--warn')}>{it.status}</span>}
          {it.citations.length > 0 && <span className="mi-note">출처 {it.citations.length}</span>}
        </span>
        <span className="mi-ev__text">{it.text}</span>
      </span>
    </label>
  );
}
