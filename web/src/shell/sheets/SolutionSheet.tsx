/**
 * 솔루션 상세 시트(00-shell §5.9, 보드 SolutionDetail · HomeSolutionDetail · HomeSolutionImages · HomeSolutionCases) — 1200×828.
 * `?detail=solution:<id>&tab=overview|images|cases&img=img_…`
 */
import { useMemo, useState, type ReactNode } from 'react';
import { Badge, Button, CaseRow, Icon, Img, InfoBox, KeyChip, MiniChip, Skeleton, displayUrl, formatDate, josa } from '@/ui';
import { imageAlt, imageSrc, ref, useSolution, useSolutionCases, useSolutionImages } from '../kb';
import type { KbImageMeta, KbSolutionDetail } from '../kbTypes';
import { useShellUrl } from '../urlState';
import { Gallery, Hero, SelectedImagePanel, SheetAddButton, SheetError, SheetFrame, SheetHeader, SheetTabs, imageLabel } from './common';

type Tab = 'overview' | 'images' | 'cases';
const TABS: Tab[] = ['overview', 'images', 'cases'];
const CASE_LIST_URL = 'https://www.samsung.com/sec/business/insights/case-study/';

type Msg = KbSolutionDetail['messages'][number] & { basis?: string | null };

/** KB 원문 메시지(프로필이 있어도 보여 준다 — 2026-10-08: 프로필 있는 MagicINFO 는 메시지 14개가 화면에 없었다). */
function MessageList({ msgs, max }: { msgs: Msg[]; max: number }) {
  const [all, setAll] = useState(false);
  const shown = all ? msgs : msgs.slice(0, max);
  const textMatch = msgs.some((m) => m.basis === 'text_match');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} data-solution-messages="">
      <div className="sh-subhead"><b>삼성 공식 메시지 {msgs.length}</b><span className="sh-note" style={{ marginLeft: 6 }}>{textMatch ? '이름이 나오는 원문 문장 · 확인 필요' : '원문 그대로'}</span></div>
      {shown.map((m, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 4 }} data-message-level={m.level}>
          <span style={{ fontSize: 13.5, lineHeight: 1.6, color: 'var(--wm-text-2)', fontWeight: 600 }}>{m.text}</span>
          {(m.children ?? []).map((c, j) => <span key={j} style={{ fontSize: 12.5, color: 'var(--wm-text-2)', paddingLeft: 12 }}>· {typeof c === 'string' ? c : (c as { text?: string }).text}</span>)}
        </div>
      ))}
      {msgs.length > max && <Button h={28} onClick={() => setAll((v) => !v)} style={{ alignSelf: 'flex-start' }}>{all ? '접기' : `메시지 ${msgs.length - max}개 더 보기`}</Button>}
    </div>
  );
}

function OverviewTab({ s }: { s: KbSolutionDetail }) {
  const p = s.profile;
  const msgs = (s.messages ?? []) as Msg[];
  if (!p) {
    if (!msgs.length) return <div className="sh-note" data-overview-empty="">아직 정리된 개요가 없어요. 견적 문의 페이지에서 확인하세요.</div>;
    return (
      <>
        <span className="sh-note">정리된 개요 대신 KB 메시지(원문 그대로)를 보여 줍니다.</span>
        <MessageList msgs={msgs} max={8} />
      </>
    );
  }
  return (
    <>
      {p.intro && <span style={{ fontSize: 13.5, lineHeight: 1.6, color: 'var(--wm-text-2)' }}>{p.intro}</span>}
      {!!p.pillars?.length && (
        <div className="sh-pillars">
          {p.pillars.map((pl) => (
            <div key={pl.name} className="sh-pillar" data-pillar={pl.name}>
              <span style={{ fontSize: 13.5, fontWeight: 700 }}>{pl.name}</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>{pl.items.map((it) => <MiniChip key={it} tone="line">{it}</MiniChip>)}</div>
            </div>
          ))}
        </div>
      )}
      {!!p.parts?.length && (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="sh-subhead"><b>구성 요소</b></div>
          {p.parts.map((pt) => <div key={pt.name} className="sh-part" data-part={pt.name}><b>{pt.name}</b><span>{pt.does}</span></div>)}
        </div>
      )}
      {!!p.deploy?.length && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
          {p.deploy.map((d) => (
            <div key={d.name} className="sh-deploy" data-deploy="">
              <span style={{ fontSize: 13, fontWeight: 700 }}>{d.name}</span>
              <span style={{ fontSize: 12, color: 'var(--wm-text-2)', lineHeight: 1.5 }}>{d.desc}</span>
              {d.evidence?.title && <span style={{ fontSize: 11, color: 'var(--wm-text-subtle)' }}>근거 · {d.evidence.title}{d.evidence.date ? ` (${formatDate(d.evidence.date)})` : ''}</span>}
            </div>
          ))}
        </div>
      )}
      {!!p.device_functions?.length && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }} data-device-functions="">
          <span style={{ fontSize: 11.5, color: 'var(--wm-text-muted)', marginRight: 2 }}>기기 관리 기능</span>
          {p.device_functions.map((x) => <MiniChip key={x}>{x}</MiniChip>)}
        </div>
      )}
      {p.source_note && <span className="sh-note">{p.source_note}</span>}
      {!!msgs.length && <MessageList msgs={msgs} max={4} />}
    </>
  );
}

function ImagesTab({ s, focusId, setFocus }: { s: KbSolutionDetail; focusId: string | null; setFocus: (id: string) => void }) {
  const imgs = useSolutionImages(s.id);
  const groups = imgs.data?.groups ?? [];
  const all = groups.flatMap((g) => g.items.map((i) => ({ ...i, _group: g.key })));
  const focus = all.find((i) => i.id === focusId) ?? all[0];
  if (imgs.isLoading) return <><Skeleton h={24} w={300} />{[0, 1].map((i) => <Skeleton key={i} h={130} r={10} />)}</>;
  if (imgs.isError) return <div className="sh-note" role="alert">이미지를 불러오지 못했어요. <Button h={26} onClick={() => imgs.refetch()}>다시 시도</Button></div>;
  const official = groups.find((g) => g.key === 'official');
  const cases = groups.find((g) => g.key === 'case');
  const isCase = (im?: KbImageMeta) => !!im && (im.rights === 'customer_case' || cases?.items.some((c) => c.id === im.id));
  const context = groups.find((g) => (g.key as string) === 'context');
  const isContext = (im?: KbImageMeta) => !!im && !!context?.items.some((c) => c.id === im.id);
  return (
    <>
      <div className="sh-h">
        <span className="sh-h__title">이미지 {all.length}</span>
        <span className="sh-h__desc">{official?.label ?? '공식 소개 이미지'} {official?.items.length ?? 0}{context ? ` · ${context.label} ${context.items.length}` : ''} · {cases?.label ?? '도입사례 사진'} {cases?.items.length ?? 0} — 모두 samsung.com 게시물</span>
      </div>
      {groups.map((g) => (
        <div key={g.key} style={{ display: 'flex', flexDirection: 'column', gap: 6 }} data-image-group={g.key}>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--wm-brand)' }}>{g.label} {g.items.length}{g.source_label ? ` · ${g.source_label}` : ''}</span>
          {g.items.length
            ? <Gallery images={g.items} focusId={focus?.id ?? null} onFocus={setFocus} cols={5} imgHeight={82} fit="cover" compact />
            : <span className="sh-note">아직 가져오지 않았어요.</span>}
        </div>
      ))}
      {focus && (
        <SelectedImagePanel im={focus} label={imageLabel(focus)} withPageNote
          badge={isCase(focus) ? <Badge tone="dark">도입사례 사진</Badge> : isContext(focus) ? <Badge tone="brand">삼성 공식 · 공간 · 업종 페이지 이미지</Badge> : <Badge tone="brand">삼성 공식 · 솔루션 소개 이미지</Badge>} />
      )}
    </>
  );
}

function CasesTab({ s }: { s: KbSolutionDetail }) {
  const cases = useSolutionCases(s.id);
  const d = cases.data;
  if (cases.isLoading) return <><Skeleton h={60} r={12} />{[0, 1, 2].map((i) => <Skeleton key={i} h={114} r={12} />)}</>;
  if (cases.isError || !d) return <div className="sh-note" role="alert">도입사례를 불러오지 못했어요. <Button h={26} onClick={() => cases.refetch()}>다시 시도</Button></div>;
  const total = d.total ?? d.title_explicit.length + d.body_mentions.length;
  const checked = formatDate(d.corpus?.checked_at) || '[확인 필요]';
  const byDate = <T extends { date?: string | null }>(a: T, b: T) => (b.date ?? '').localeCompare(a.date ?? '');
  return (
    <>
      <div className="sh-summary" style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: '10px 14px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: 1, minWidth: 0 }}>
          <span className="sh-summary__title">본문에 {s.name}{josa(s.name, '이', '가')} 나오는 도입사례 {total}건</span>
          <span className="sh-summary__body">삼성 고객 도입사례 {d.corpus?.count ?? '[확인 필요]'}건(본문 있는 사례, {checked} 확인)에서 찾았습니다 · 제목에 명시 {d.title_explicit.length}건 · 본문 언급 {d.body_mentions.length}건</span>
        </div>
        <a className="wm-btn wm-btn--h28" href={CASE_LIST_URL} target="_blank" rel="noopener noreferrer">도입사례 목록 ↗</a>
      </div>
      {[...d.title_explicit].sort(byDate).map((c) => {
        const p = c.photos?.items?.[0];
        return (
          <CaseRow key={c.id} size="solution" title={c.title} date={formatDate(c.date)} url={c.url} urlDisplay={c.url_display || displayUrl(c.url)} summary={c.summary} quote={c.quote}
            badge={<Badge tone="dark">제목에 명시</Badge>} photo={p ? { src: imageSrc(p), alt: imageAlt(p, c.title), focal: p.focal } : null} />
        );
      })}
      {d.body_mentions.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="sh-subhead" style={{ height: 24 }}><b>본문 언급 {d.body_mentions.length}</b><span>사진은 아직 가져오지 않았어요 · 원문에서 확인</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', columnGap: 24 }}>
            {[...d.body_mentions].sort(byDate).map((m) => (
              <a key={m.id} className="sh-mention" href={m.url ?? undefined} target="_blank" rel="noopener noreferrer" title={m.title} data-mention="">
                <span className="sh-ell" style={{ flex: 1 }}>{m.title}</span>
                <span style={{ fontSize: 11, color: 'var(--wm-text-subtle)', whiteSpace: 'nowrap' }}>{formatDate(m.date)}</span>
                <span style={{ color: 'var(--wm-brand)', fontSize: 11 }}>↗</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export function SolutionSheet({ id, onClose }: { id: string; onClose: () => void }) {
  const url = useShellUrl();
  const { update } = url;
  const sol = useSolution(id);
  const s = sol.data;
  const imgs = useSolutionImages(id);
  const tab: Tab = TABS.includes(url.tab as Tab) ? (url.tab as Tab) : 'overview';
  const setTab = (t: string) => update({ tab: t, img: t === 'images' ? url.img : null });
  const setFocus = (imgId: string) => update({ tab: 'images', img: imgId });
  const back = () => update({ detail: null, tab: null, img: null, pop: 'solution', node: null, q: null });
  const official = imgs.data?.groups.find((g) => g.key === 'official')?.items ?? [];
  const first = official[0];
  const name = s?.name ?? id;
  const ex = s?.supported_devices?.example;
  const purchase = s?.purchase;
  const purchaseLine = purchase?.label && purchase.site_code && purchase.label.includes(purchase.site_code) ? purchase.label
    : purchase?.site_code ? `별도 구매 · 견적 문의 (${purchase.site_code}) · 라이선스 단가 [견적 확인]` : purchase?.label;

  const left: ReactNode = useMemo(() => {
    if (!s) return null;
    return (
      <aside className="sh-sheet__left" aria-label="솔루션 요약">
        {first
          ? <Hero src={imageSrc(first, 'stored')} alt={`${s.name} 대표 이미지 — ${imageAlt(first, '공식 연출 이미지')}`} height={162} fit="cover" focal={first.focal}
            badge={`1 / ${official.length} · 공식 연출 이미지`} />
          : <div className="sh-sheet__hero" style={{ height: 162, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'var(--wm-text-subtle)' }}>
            공식 소개 이미지는 아직 수집하지 않았어요
          </div>}
        {official.length > 0 && (
          <div className="sh-thumbs" style={{ gridTemplateColumns: 'repeat(5, minmax(0, 1fr))' }}>
            {official.map((im, i) => (
              <button key={im.id} type="button" className={i === 0 ? 'sh-thumb sh-thumb--on' : 'sh-thumb'} style={{ height: 44 }} aria-label={`${imageLabel(im)} 이미지 보기`} onClick={() => setFocus(im.id)}>
                <Img src={imageSrc(im)} alt={imageLabel(im)} focal={im.focal} />
              </button>
            ))}
          </div>
        )}
        {official.length > 0 && (
          <button type="button" className="sh-srcline" onClick={() => setTab('images')}>
            <Icon name="info" size={13} color="var(--wm-brand)" />이미지 출처 · samsung.com {s.name} 소개 · {formatDate(first?.collected_at) || '[확인 필요]'} 수집
          </button>
        )}
        <hr className="wm-divider" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, minWidth: 0 }}>
            <span className="sh-idname">{s.name}</span>{s.version_label && <span className="sh-idcode">{s.version_label}</span>}
          </div>
          {s.subtitle && <span style={{ fontSize: 14.5, fontWeight: 600 }}>{s.subtitle}</span>}
          {!!s.key_chips?.length && <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>{s.key_chips.map((k) => <KeyChip key={k}>{k}</KeyChip>)}</div>}
          {purchaseLine && <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }} data-purchase="">{purchaseLine}</span>}
        </div>
        {s.supported_devices?.label && (
          <InfoBox title={`지원 기기 — ${s.supported_devices.label}`}
            sub={ex?.series_label ? `예: ${ex.series_label.replace(/ Series$/, '')} 시리즈 (제품 페이지에 지원 명시)` : undefined}
            action={ex?.model_code ? (
              <button type="button" style={{ border: 'none', background: 'transparent', color: 'var(--wm-brand)', fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap', padding: 0 }}
                onClick={() => update({ detail: `product:${ex.model_code}`, tab: 'spec', img: null })}>{ex.display_name || ex.model_code} 상세 →</button>
            ) : undefined} />
        )}
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {s.quote_url
            ? <a className="wm-btn wm-btn--primary wm-btn--h44 wm-btn--grow" href={s.quote_url} target="_blank" rel="noopener noreferrer">견적 문의 페이지 열기 ↗</a>
            : <Button h={44} grow disabled disabledReason="견적 문의 페이지가 없습니다">견적 문의 페이지 열기 ↗</Button>}
          <SheetAddButton type="solution" r={ref.solution(s.id)} />
        </div>
      </aside>
    );
  }, [s, first, official, purchaseLine, ex, update]);

  return (
    <SheetFrame ariaLabel={`${name} 솔루션 상세`} onClose={onClose} ready={!!s}>
      <SheetHeader backLabel="솔루션 탐색" onBack={back} path={s?.category_path ?? []} last={name} onClose={onClose}
        links={[{ label: '견적 문의 페이지 ↗', href: s?.quote_url }, { label: 'samsung.com 소개 페이지 ↗', href: s?.intro_url }]} />
      {sol.isError ? <SheetError message="솔루션 정보를 불러오지 못했어요." onRetry={() => sol.refetch()} onClose={onClose} />
        : !s ? (
          <div className="sh-sheet__main">
            <aside className="sh-sheet__left"><Skeleton h={162} r={12} /><Skeleton h={44} /><Skeleton h={30} w="60%" /><Skeleton h={18} /></aside>
            <section className="sh-sheet__right"><div className="sh-sheet__tabs" /><div className="sh-sheet__body">{[0, 1, 2].map((i) => <Skeleton key={i} h={22} />)}</div></section>
          </div>
        ) : (
          <div className="sh-sheet__main">
            {left}
            <section className="sh-sheet__right">
              <SheetTabs value={tab} onChange={setTab} verified={s.verified_at}
                tabs={[{ value: 'overview', label: '개요 · 구성' }, { value: 'images', label: '이미지', count: s.counts?.images ?? (imgs.data ? imgs.data.groups.reduce((a, g) => a + g.items.length, 0) : '') },
                  { value: 'cases', label: '활용 사례', count: s.counts?.cases ?? '' }]} />
              <div className="sh-sheet__body" role="tabpanel" aria-label={tab}>
                {tab === 'overview' && <OverviewTab s={s} />}
                {tab === 'images' && <ImagesTab s={s} focusId={url.img} setFocus={setFocus} />}
                {tab === 'cases' && <CasesTab s={s} />}
              </div>
            </section>
          </div>
        )}
    </SheetFrame>
  );
}
