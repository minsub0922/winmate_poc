/**
 * 제품 상세 시트(00-shell §5.8, 보드 ProductDetail · HomeProductDetail · HomeProductImages · HomeProductCases) — 1200×828.
 * `?detail=product:<모델코드>&tab=spec|images|cases&img=img_…`
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Badge, Button, CaseRow, Icon, Img, InfoBox, KeyChip, MatchChip, Skeleton, displayUrl, formatDate } from '@/ui';
import { imageAlt, imageSrc, modelName, ref, seriesCode, useModel, useModelCases, useModelImages } from '../kb';
import type { KbModelCase, KbModelDetail } from '../kbTypes';
import { registerNode } from '../pop/productTree';
import { useShellRuntime } from '../runtime';
import { useShellUrl } from '../urlState';
import { Gallery, Hero, SelectedImagePanel, SheetAddButton, SheetError, SheetFrame, SheetHeader, SheetTabs, imageLabel } from './common';

type Tab = 'spec' | 'images' | 'cases';
const TABS: Tab[] = ['spec', 'images', 'cases'];

/**
 * 스펙 그룹을 두 열로 나눈다(보드: 왼쪽 디스플레이 · 전원 · 크기·무게 / 오른쪽 나머지).
 * kb 가 `column`(left · right)을 주면 그대로, 없으면 행 수가 비슷하게.
 */
function splitGroups<T extends { rows: unknown[]; column?: string | null }>(groups: T[]): [T[], T[]] {
  if (groups.some((g) => g.column === 'left' || g.column === 'right')) {
    return [groups.filter((g) => g.column !== 'right'), groups.filter((g) => g.column === 'right')];
  }
  const total = groups.reduce((a, g) => a + g.rows.length + 1, 0);
  const left: T[] = [];
  let acc = 0;
  let i = 0;
  for (; i < groups.length; i++) {
    if (acc >= total / 2 && left.length) break;
    left.push(groups[i]);
    acc += groups[i].rows.length + 1;
  }
  return [left, groups.slice(i)];
}

function SpecTab({ m }: { m: KbModelDetail }) {
  const groups = m.spec?.groups ?? [];
  const [l, r] = splitGroups(groups);
  const pdp = m.spec?.source_url || m.family.detail_url;
  const col = (gs: typeof groups) => (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      {gs.map((g) => (
        <div key={g.name} data-spec-group={g.name}>
          <div className="sh-spec__ghead">{g.name}</div>
          {g.rows.map((row) => (
            <div key={row.label} className="sh-spec__row" data-spec-row={row.label}>
              <span className="sh-spec__k">{row.label}</span>
              <span className="sh-spec__v" title={row.value}>{row.value}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
  return (
    <>
      <div className="sh-h">
        <span className="sh-h__title">핵심 스펙</span>
        <span className="sh-h__desc">공식 스펙 표에서 제안에 자주 쓰는 항목 · 값은 원문 그대로</span>
        {pdp && <a className="sh-srcpill" href={pdp} target="_blank" rel="noopener noreferrer">출처 samsung.com 스펙 ↗</a>}
      </div>
      {groups.length ? <div className="sh-spec">{col(l)}{col(r)}</div> : <div className="sh-note">이 제품의 스펙 표를 아직 가져오지 않았어요.</div>}
      {m.documents?.length ? (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="sh-subhead"><b>공식 자료 {m.documents.length}</b><span>제품 페이지 '매뉴얼' 기준</span></div>
          {m.documents.map((d) => (
            <div key={d.name + d.url} className="sh-docrow">
              <span title={d.name}>{d.name}</span><span>{d.version}</span><span>{d.lang}</span><span style={{ textAlign: 'right' }}>{d.size_label}</span><span>{d.date}</span>
              <a href={d.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600, textAlign: 'right', whiteSpace: 'nowrap' }}>{d.cta || 'PDF'} ↗</a>
            </div>
          ))}
        </div>
      ) : pdp ? (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="sh-subhead"><b>공식 자료</b><span>제품 페이지 '매뉴얼' 기준</span></div>
          <a href={pdp} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, padding: '7px 0', fontWeight: 600 }} data-docs-fallback="">
            공식 자료는 samsung.com 제품 페이지의 '매뉴얼'에서 확인하세요 ↗
          </a>
        </div>
      ) : null}
    </>
  );
}

function ImagesTab({ m, focusId, setFocus }: { m: KbModelDetail; focusId: string | null; setFocus: (id: string) => void }) {
  const rt = useShellRuntime();
  const imgs = useModelImages(m.model_code);
  const list = imgs.data?.items ?? [];
  const focus = list.find((i) => i.id === focusId) ?? list[0];
  const [attaching, setAttaching] = useState(false);
  const canAttach = !!rt.page.onAttach && rt.hasTask;
  const attachAll = async () => {
    if (!rt.page.onAttach || !list.length) return;
    setAttaching(true);
    try { await rt.page.onAttach(list.map((i) => ({ ...i, ref: ref.image(i.id), usage_note: i.usage_note || '삼성전자 저작물 · 대외 사용 범위 확인 필요' }))); } finally { setAttaching(false); }
  };
  if (imgs.isLoading) return <><Skeleton h={24} w={300} /><div className="sh-gallery" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} h={156} r={10} />)}</div></>;
  if (imgs.isError) return <div className="sh-note" role="alert">이미지를 불러오지 못했어요. <Button h={26} onClick={() => imgs.refetch()}>다시 시도</Button></div>;
  return (
    <>
      <div className="sh-h">
        <span className="sh-h__title">이미지 {list.length}</span>
        <span className="sh-h__desc">모두 삼성전자 공식 제품 이미지 · 원본은 공식 페이지에 그대로 있습니다</span>
        <span style={{ flex: 1 }} />
        <Button h={28} disabled={!canAttach || !list.length} loading={attaching} onClick={attachAll} disabledReason={rt.hasTask ? '이 화면에는 첨부할 대화가 없습니다' : '진행 중인 작업이 없습니다'}>
          {list.length}장 대화에 첨부
        </Button>
      </div>
      <Gallery images={list} focusId={focus?.id ?? null} onFocus={setFocus} cols={4} imgHeight={108} fit="contain" familyName={m.family.name} />
      {focus && (
        <SelectedImagePanel im={focus} label={imageLabel(focus, m.family.name)} withPosted pageLabel={`samsung.com · ${m.model_code}`}
          badge={<Badge tone="brand">삼성 공식 · 제품 이미지</Badge>}
          actions={<SheetAddButton type="image" r={ref.image(focus.id)} h={28} label="작업에 추가" />} />
      )}
    </>
  );
}

function CasesTab({ m }: { m: KbModelDetail }) {
  const [match, setMatch] = useState<string | undefined>(undefined);
  const cases = useModelCases(m.model_code, match);
  const d = cases.data;
  // 기본 on = kb `default_match`, 없으면 모델 → 시리즈 → 용도 중 처음으로 1건 이상인 것
  const auto = d?.default_match ?? (d?.counts ? (d.counts.model ? 'model' : d.counts.series ? 'series' : 'usage') : undefined);
  const on = match ?? auto;
  if (cases.isLoading && !d) return <><Skeleton h={96} r={12} />{[0, 1, 2].map((i) => <Skeleton key={i} h={146} r={12} />)}</>;
  if (cases.isError && !d) return <div className="sh-note" role="alert">도입사례를 불러오지 못했어요. <Button h={26} onClick={() => cases.refetch()}>다시 시도</Button></div>;
  if (!d) return null;
  const name = modelName(m);
  const code = seriesCode(m.family.series_label);
  const seriesTxt = code ? `${code} 시리즈` : m.family.name;
  const counts = d.counts ?? {};
  const corpus = d.corpus ?? m.case_corpus;
  const checked = formatDate(corpus?.checked_at) || '[확인 필요]';
  const usage = d.usage_label || '[확인 필요]';
  const noDirect = !counts.model && !counts.series;
  const items = d.items.filter((i) => !on || !i.match_type || i.match_type === on);
  const badgeOf = (c: KbModelCase): ReactNode => c.match_type === 'model' ? <Badge tone="dark">모델 일치</Badge>
    : c.match_type === 'series' ? <Badge tone="dark">시리즈 일치</Badge> : <Badge tone="dashed">용도 일치 · {usage}</Badge>;
  return (
    <>
      <div className="sh-summary">
        <span className="sh-summary__title">
          {noDirect ? `${name} · ${seriesTxt}가 본문에 나오는 도입사례는 아직 없습니다` : `본문에 ${name}이 나오는 도입사례 ${(counts.model ?? 0) + (counts.series ?? 0)}건`}
        </span>
        <span className="sh-summary__body">
          {noDirect
            ? `삼성 고객 도입사례 ${corpus?.count ?? '[확인 필요]'}건(본문 있는 사례, ${checked} 확인)을 모델 · 시리즈명으로 찾았습니다. 같은 용도(${usage})로 쓰인 사례 ${counts.usage ?? 0}건을 대신 보여 주고, 제안서에는 '유사 용도 사례'로 표기됩니다.`
            : `삼성 고객 도입사례 ${corpus?.count ?? '[확인 필요]'}건(본문 있는 사례, ${checked} 확인)을 모델 · 시리즈명으로 찾았습니다.`}
        </span>
        <div style={{ display: 'flex', gap: 6 }} role="group" aria-label="일치 유형">
          <MatchChip label="모델 일치" n={counts.model ?? 0} on={on === 'model'} onClick={() => setMatch('model')} />
          <MatchChip label="시리즈 일치" n={counts.series ?? 0} on={on === 'series'} onClick={() => setMatch('series')} />
          <MatchChip label="용도 일치" n={counts.usage ?? 0} on={on === 'usage'} onClick={() => setMatch('usage')} />
        </div>
      </div>
      {items.length === 0 && <div className="sh-note">이 일치 유형의 사례가 없어요.</div>}
      {items.map((c) => {
        const p = c.photos?.items?.[0];
        return (
          <CaseRow key={c.id} title={c.title} date={formatDate(c.date)} url={c.url} urlDisplay={c.url_display || displayUrl(c.url)} summary={c.summary} quote={c.quote}
            usedLine={c.used_products_line || (c.products ?? []).map((x) => x.label).join(' · ') || null} badge={badgeOf(c)}
            photo={p ? { src: imageSrc(p), alt: imageAlt(p, c.title), focal: p.focal } : null} />
        );
      })}
      <span className="sh-note">사례 내용 · 사진 출처: 삼성전자 고객 도입사례 (samsung.com) · {items.some((c) => c.summary) ? '요약은 원문을 줄여 쓴 것' : '따옴표 안은 원문 인용'}</span>
    </>
  );
}

export function ProductSheet({ code, onClose }: { code: string; onClose: () => void }) {
  const url = useShellUrl();
  const { update } = url;
  const model = useModel(code);
  const m = model.data;
  const imgs = useModelImages(code);
  const tab: Tab = TABS.includes(url.tab as Tab) ? (url.tab as Tab) : 'spec';
  const setTab = (t: string) => update({ tab: t, img: t === 'images' ? url.img : null });
  const setFocus = (id: string) => update({ tab: 'images', img: id });

  // 트리 경로를 미리 알려 둔다(뒤로 → 시리즈 노드)
  useEffect(() => {
    if (!m) return;
    const cp = m.category_path ?? [];
    cp.forEach((c, i) => registerNode({ id: c.id, name: c.name, parentId: i ? cp[i - 1].id : null, kind: i ? 'cat' : 'top' }));
    registerNode({ id: m.family.id, name: m.family.series_label || m.family.name, parentId: cp.length ? cp[cp.length - 1].id : null, kind: 'fam' });
  }, [m]);

  const name = m ? modelName(m) : code;
  const back = () => update({ detail: null, tab: null, img: null, pop: 'product', node: m?.family.id ?? url.node, q: null });
  const list = imgs.data?.items ?? [];
  const first = list[0];
  const firstLabel = first ? imageLabel(first, m?.family.name) : '';
  const collected = formatDate(first?.collected_at ?? m?.verified_at);
  const sol = m?.supported_solutions ?? [];

  const left = useMemo(() => {
    if (!m) return null;
    return (
      <aside className="sh-sheet__left" aria-label="제품 요약">
        <Hero src={imageSrc(first, 'stored')} alt={first ? `${name} ${firstLabel} — 삼성전자 공식 제품 이미지` : `${name} 이미지 없음`} height={229} fit="contain"
          badge={first ? `1 / ${list.length} · ${firstLabel} · 삼성 공식` : undefined} />
        {list.length > 0 && (
          <div className="sh-thumbs" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
            {list.map((im, i) => (
              <button key={im.id} type="button" className={i === 0 ? 'sh-thumb sh-thumb--on' : 'sh-thumb'} style={{ height: 54 }} aria-label={`${imageLabel(im, m.family.name)} 이미지 보기`}
                onClick={() => setFocus(im.id)}>
                <Img src={imageSrc(im)} alt={imageLabel(im, m.family.name)} fit="contain" />
              </button>
            ))}
          </div>
        )}
        {list.length > 0 && (
          <button type="button" className="sh-srcline" onClick={() => setTab('images')}>
            <Icon name="info" size={13} color="var(--wm-brand)" />이미지 출처 · samsung.com 제품 페이지 · {collected || '[확인 필요]'} 수집
          </button>
        )}
        <hr className="wm-divider" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, minWidth: 0 }}>
            <span className="sh-idname">{name}</span><span className="sh-idcode" data-model-code="">{m.model_code}</span>
          </div>
          {m.title_line && <span style={{ fontSize: 14.5, fontWeight: 600 }} data-title-line="">{m.title_line}</span>}
          {!!m.key_chips?.length && <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }} aria-label="핵심">{m.key_chips.map((k) => <KeyChip key={k}>{k}</KeyChip>)}</div>}
          {!!m.facts?.length && <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }} data-facts="">{m.facts.map((f) => `${f.label} ${f.value}`).join(' · ')}</span>}
        </div>
        {sol.length > 0 && (
          <InfoBox title={`${sol[0].kind_label || 'CMS'} — ${sol.map((s) => s.name).join(' · ')} 지원`}
            sub={(sol[0].kind_label || 'CMS') === 'CMS' ? 'CMS는 별도 구매 · 공식 페이지 기준' : undefined}
            action={<button type="button" style={{ border: 'none', background: 'transparent', color: 'var(--wm-brand)', fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap', padding: 0 }}
              onClick={() => update({ detail: `solution:${sol[0].id}`, tab: 'overview', img: null })}>{sol[0].name} 상세 →</button>} />
        )}
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <Link to={`/spec/new?models=${encodeURIComponent(m.model_code)}`} className="wm-btn wm-btn--primary wm-btn--h44 wm-btn--grow">Spec 시트 만들기</Link>
          <SheetAddButton type="product" r={ref.model(m.id)} />
        </div>
      </aside>
    );
  }, [m, list, first, firstLabel, name, collected, sol, update]);

  return (
    <SheetFrame ariaLabel={`${name} 제품 상세`} onClose={onClose} ready={!!m}>
      <SheetHeader backLabel="제품 탐색" onBack={back} path={[...(m?.category_path ?? []).map((c) => c.name), ...(m ? [m.family.series_label || m.family.name] : [])]}
        last={name} links={[{ label: 'samsung.com 제품 페이지', href: m?.family.detail_url, icon: true }]} onClose={onClose} />
      {model.isError ? <SheetError message="제품 정보를 불러오지 못했어요." onRetry={() => model.refetch()} onClose={onClose} />
        : !m ? (
          <div className="sh-sheet__main">
            <aside className="sh-sheet__left"><Skeleton h={229} r={12} /><Skeleton h={54} /><Skeleton h={30} w="60%" /><Skeleton h={18} /><Skeleton h={18} w="80%" /></aside>
            <section className="sh-sheet__right"><div className="sh-sheet__tabs" /><div className="sh-sheet__body">{[0, 1, 2, 3].map((i) => <Skeleton key={i} h={22} />)}</div></section>
          </div>
        ) : (
          <div className="sh-sheet__main">
            {left}
            <section className="sh-sheet__right">
              <SheetTabs value={tab} onChange={setTab} verified={m.verified_at}
                tabs={[{ value: 'spec', label: '스펙 · 자료' }, { value: 'images', label: '이미지', count: m.counts?.images ?? list.length }, { value: 'cases', label: '활용 사례', count: m.counts?.cases ?? '' }]} />
              <div className="sh-sheet__body" role="tabpanel" aria-label={tab}>
                {tab === 'spec' && <SpecTab m={m} />}
                {tab === 'images' && <ImagesTab m={m} focusId={url.img} setFocus={setFocus} />}
                {tab === 'cases' && <CasesTab m={m} />}
              </div>
            </section>
          </div>
        )}
    </SheetFrame>
  );
}
