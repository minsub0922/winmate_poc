/** BE3 — 가구 추천 3/5(`/birdseye/:id/furniture`, §4.6): 추천 카드 4(상위 3 미리 선택) · 선택 칩 · 다른 추천 · 가구 없이 진행 · 직접 입력. */
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, Skeleton, toast } from '@/ui';
import { useJob } from '@/api/jobs';
import { be, errText, qk, useBe, useFurniture, type S } from '../api';
import { Agent, BePage, Dock, DockLink, Echo, Loading, MainButton, PromptBar, SubButton, useBeShell } from '../ui';

export default function FurniturePage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const fq = useFurniture(id);
  const [busy, setBusy] = useState<'next' | 'none' | 'more' | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: qk.furniture(id) });
  useJob(fq.data?.running ? fq.data.job_id : null, { onDone: () => void refresh() });
  useBeShell(bq.data, 3);
  if (bq.isLoading || fq.isLoading) return <Loading />;
  const fv = fq.data;
  if (!fv) return <Loading />;
  const selected = fv.selected ?? [];
  const cards = fv.cards ?? [];

  const put = async (items: Array<S['FurniturePick']>, opts: { none?: boolean } = {}) => {
    try { await be.putFurniture(id, { items, none: !!opts.none, replace: false }); await refresh(); } catch (e) { toast(errText(e)); }
  };
  const toggle = (c: S['FurnitureCard']) => put([c.item_id ? { id: c.item_id, selected: !c.selected } : { catalog_code: c.code, selected: !c.selected }]);
  const more = async () => {
    setBusy('more');
    try { await be.recommend(id, fv.shown_codes); await refresh(); } catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const layout = async (none: boolean) => {
    setBusy(none ? 'none' : 'next');
    try {
      await be.generate(id, none);
      void qc.invalidateQueries({ queryKey: qk.layout(id) });
      nav(`/birdseye/${id}/layout`);
    } catch (e) { toast(errText(e)); setBusy(null); }
  };

  return (
    <BePage testId="be3" dock={(
      <Dock title="선택된 가구" meta={<>{selected.length}개 · 3 / 5</>}
        right={(
          <>
            <DockLink onClick={more} disabled={busy === 'more' || fv.running || !fv.more_available} icon={<Icon name="refresh" size={13} />}
              title="더 추천할 가구가 없어요">다른 가구 추천</DockLink>
            <DockLink onClick={() => void layout(true)} disabled={!!busy}>가구 없이 진행</DockLink>
          </>
        )}
        foot={(
          <>
            <PromptBar label="가구 직접 입력" placeholder="가구를 직접 입력해 추가 (예: 화분, 안내 데스크)" testId="be3-custom"
              onSend={async (t) => { await put([{ name: t, selected: true }]); }} />
            <SubButton to={`/birdseye/${id}/products`}>이전</SubButton>
            <MainButton onClick={() => void layout(false)} busy={busy === 'next'} disabled={fv.running} testId="be3-next">배치안 보기</MainButton>
          </>
        )}>
        {selected.length > 0 && (
          <div className="be-row" data-testid="be3-selected">
            {selected.map((f) => (
              <span key={f.id} className={f.dims_estimated ? 'be-selchip be-selchip--est' : 'be-selchip'}>
                {f.chip_label}
                <button type="button" aria-label={`${f.name} 빼기`} onClick={() => void put([{ id: f.id, selected: false }])}>×</button>
              </span>
            ))}
          </div>
        )}
      </Dock>
    )}>
      <Echo text={fv.echo} />
      <Agent text={fv.w_message} busy={fv.running}>
        <div className="be-cards4" data-testid="be3-cards">
          {fv.running && !cards.length && [0, 1, 2, 3].map((i) => <Skeleton key={i} h={72} r={12} />)}
          {cards.map((c) => (
            <button key={c.code} type="button" className={c.selected ? 'be-rec be-rec--on' : 'be-rec'} aria-pressed={c.selected} onClick={() => void toggle(c)}
              data-testid={`be3-card-${c.code}`}>
              <b>{c.name}</b>
              <span>{c.reason}</span>
              <i className="be-rec__check" aria-hidden="true">{c.selected && <Icon name="check" size={11} strokeWidth={3} />}</i>
            </button>
          ))}
        </div>
      </Agent>
    </BePage>
  );
}
