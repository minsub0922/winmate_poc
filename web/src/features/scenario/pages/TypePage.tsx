/**
 * SC1 · 유형 선택(§4.2) — WITH(기본) / WITHOUT 카드, 「조감도 추가」(기본 꺼짐) + 새로 만들기 / 기존 조감도 연결.
 * `/scenario/new`(새로 · ?sb= Storyboard · ?project= · ?mi= MI 페르소나 · ?from=vp: VP 가치 — `seed.ts`) 와 `/scenario/:id/type`(고치기) 둘 다.
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { cx } from '@/ui';
import { useShellPage } from '@/shell';
import { errMessage, scApi, type Aerial } from '../api';
import { ArtWith, ArtWithout } from '../art';
import { qk, useInvalidate, useScenario } from '../hooks';
import { route, SECTION, stepper } from '../lib';
import { Card, Ico, Loading, NextButton, Note, P, Screen, useOutside, W } from '../parts';
import { loadSeed, seedSource, seedText } from '../seed';

export default function TypePage() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const sc = useScenario(id);
  const [type, setType] = useState<'with' | 'without'>('with');
  const [aerial, setAerial] = useState<Aerial>({ enabled: false, source: 'new', birdseye_id: null, title: null, created: false });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pickOpen, setPickOpen] = useState(false);
  const pickRef = useOutside<HTMLDivElement>(pickOpen, () => setPickOpen(false));
  const opts = useQuery({ queryKey: qk.beOptions(), queryFn: scApi.birdseyeOptions, staleTime: 30_000, retry: 0 });
  // MI4 · VP4 에서 넘어온 재료(새 작업만) — 읽는 동안은 다음을 잠근다
  const src = id ? null : seedSource(sp);
  const seed = useQuery({ queryKey: ['scenario', 'seed', src?.feature ?? '', src?.ref ?? ''], queryFn: () => loadSeed(src!), enabled: !!src, retry: 0, staleTime: 60_000 });

  useEffect(() => {
    if (!sc.data) return;
    setType(sc.data.type);
    setAerial({ ...sc.data.aerial });
  }, [sc.data?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useShellPage({ section: SECTION, title: sc.data?.title ?? '새 작업', stepper: stepper(1), sidebarGroup: 'scenario' });

  if (id && sc.isLoading) return <Loading />;
  const n = opts.data?.count ?? 0;
  const picked = (opts.data?.items ?? []).find((b) => b.id === aerial.birdseye_id);

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const body = { type, aerial: aerial.enabled ? aerial : { ...aerial, enabled: false } };
      let sid = id;
      const sd = !id ? seed.data : undefined;
      if (!sid) {
        const created = await scApi.create({ ...body, project_id: sp.get('project') || sd?.project_id || undefined, storyboard_id: sp.get('sb') || undefined,
          customer_name: sd?.customer_name || undefined });
        sid = created.id;
      }
      const cur = id ? sc.data?.step ?? 1 : 1;
      await scApi.patch(sid, { ...body, step: Math.max(2, cur), ...(sd && sd.lines.length ? { raw_text: seedText(sd.lines) } : {}),
        ...(sd && sd.characters.length ? { characters: sd.characters } : {}) });
      await inv.sc(sid);
      nav(route.input(sid));
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(false); }
  };
  const existingOff = n === 0;
  const existingSub = picked ? picked.label : `조감도 작업 ${n}개에서 고르기`;

  const dock = (
    <Card title="시나리오 유형" meta="하나 선택 · 1 / 4" testId="sc1-card"
      foot={<NextButton onClick={() => void submit()} busy={busy} testId="sc1-next"
        disabled={(aerial.enabled && aerial.source === 'existing' && !aerial.birdseye_id) || (!!src && seed.isLoading)}
        reason={src && seed.isLoading ? '넘어온 자료를 읽는 중이에요' : '연결할 조감도를 고르세요'}>공간 시나리오 입력</NextButton>}>
      <div className="sc-types" role="radiogroup" aria-label="시나리오 유형">
        <TypeCard checked={type === 'with'} onPick={() => setType('with')} code="WITH 솔루션" name="솔루션 + 연관 제품 활용" art={<ArtWith />} testId="sc1-with"
          desc="시나리오 속에 MagicINFO·SmartThings Pro 같은 솔루션이 동작하는 장면과, 그 솔루션에 연결된 제품 활용을 함께 넣습니다. 운영·관리 효과를 보여줄 때 적합."
          tags={['본사 원격 배포 장면', '에너지 자동 제어']} />
        <TypeCard checked={type === 'without'} onPick={() => setType('without')} code="WITHOUT 솔루션" name="제품 활용만" art={<ArtWithout />} testId="sc1-without"
          desc="고객의 공간 시나리오에 제품이 쓰이는 장면만 넣습니다. 하드웨어 중심 제안이나 솔루션 도입 전 단계에 적합." tags={['메뉴보드 시청 장면', '키오스크 주문']} />
      </div>
      <div className="sc-card__sec" style={{ paddingTop: 12 }}>
        <div className="sc-aerial" data-testid="sc1-aerial">
          <div className="sc-row" style={{ gap: 12 }}>
            <span className={cx('sc-aerial__icon', aerial.enabled && 'sc-aerial__icon--on')}><Ico d={P.cube} size={16} /></span>
            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <div className="sc-row">
                <span className="sc-aerial__name">조감도 추가</span>
                <span className={cx('sc-tag', aerial.enabled && 'sc-tag--brand')} data-testid="sc1-aerial-tag">{aerial.enabled ? '켜짐' : '선택 · 기본 꺼짐'}</span>
              </div>
              <div className="sc-hint" style={{ lineHeight: 1.5 }}>장면이 일어나는 위치를 공간 조감도 위에 번호로 표시해 시나리오와 함께 넣습니다.</div>
            </div>
            <button type="button" className="sc-switch" aria-label="조감도 추가" aria-pressed={aerial.enabled} data-testid="sc1-aerial-toggle"
              onClick={() => setAerial({ ...aerial, enabled: !aerial.enabled, source: aerial.enabled ? aerial.source : 'new' })} />
          </div>
          {aerial.enabled && (
            <div className="sc-aerial__opts" data-testid="sc1-aerial-opts">
              <button type="button" className="sc-opt" aria-pressed={aerial.source === 'new'} onClick={() => setAerial({ ...aerial, source: 'new', birdseye_id: null })} data-testid="sc1-aerial-new">
                <b>새로 만들기</b><span>시나리오 공간으로 조감도 생성</span>
              </button>
              <div className="sc-menuwrap" ref={pickRef} style={{ display: 'flex' }}>
                <button type="button" className="sc-opt" style={{ flex: 1 }} aria-pressed={aerial.source === 'existing'} disabled={existingOff}
                  title={existingOff ? (opts.data?.available === false ? '조감도 서비스에 연결할 수 없어요' : '아직 조감도 작업이 없어요') : undefined}
                  aria-haspopup="menu" aria-expanded={pickOpen} data-testid="sc1-aerial-existing"
                  onClick={() => { setAerial({ ...aerial, source: 'existing' }); setPickOpen(true); }}>
                  <b>기존 조감도 연결</b><span data-testid="sc1-aerial-existing-sub">{existingSub}</span>
                </button>
                {pickOpen && (
                  <div className="sc-menu sc-menu--left sc-menu--up" role="menu" style={{ minWidth: 260, maxHeight: 280, overflow: 'auto' }} data-testid="sc1-aerial-picker">
                    <div className="sc-menu__head">조감도 작업</div>
                    {(opts.data?.items ?? []).map((b) => (
                      <button key={b.id} type="button" role="menuitemradio" aria-checked={b.id === aerial.birdseye_id}
                        onClick={() => { setAerial({ ...aerial, source: 'existing', birdseye_id: b.id, title: b.title }); setPickOpen(false); }}>{b.label}</button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      {src && !seed.isLoading && (
        <div className="sc-card__sec">
          {seed.data ? <Note testId="sc1-seed">{seed.data.note}</Note>
            : <Note tone="warn" testId="sc1-seed">{src.feature === 'mi' ? 'Market Intelligence' : 'Value Proposition'} 자료를 읽지 못했어요 — 빈 입력으로 시작해요.</Note>}
        </div>
      )}
      {err && <div className="sc-card__sec"><Note tone="err">{err}</Note></div>}
    </Card>
  );

  return (
    <Screen dock={dock} testId="sc1">
      <W testId="sc1-w">공간 시나리오는 고객의 공간에서 하루 또는 특정 상황이 어떻게 흘러가는지를 이야기로 풀고, 그 안에 삼성 제품의 활용 장면을 넣습니다. 솔루션을 함께 엮을지 먼저 정해주세요.</W>
    </Screen>
  );
}

function TypeCard({ checked, onPick, code, name, desc, tags, art, testId }:
  { checked: boolean; onPick: () => void; code: string; name: string; desc: string; tags: string[]; art: React.ReactNode; testId: string }) {
  return (
    <button type="button" role="radio" aria-checked={checked} className="sc-type" onClick={onPick} data-testid={testId}>
      <div className="sc-type__art">{art}</div>
      <div className="sc-type__top">
        <span className="sc-type__code">{code}</span>
        <span className={cx('sc-radio', checked && 'sc-radio--on')}>{checked && <Ico d={P.check} size={11} sw={3} />}</span>
      </div>
      <div className="sc-type__name">{name}</div>
      <div className="sc-type__desc">{desc}</div>
      <div className="sc-type__tags">{tags.map((t) => <span key={t}>{t}</span>)}</div>
    </button>
  );
}
