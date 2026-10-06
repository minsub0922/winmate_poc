/**
 * UI 키트 견본(개발용): `/_dev/kit` — 제품 입력창 · 템플릿 썸네일 · 버튼 · 칩 · 배지 · 드롭 영역 · 목록 뼈대
 * + 기능 요청으로 더한 부품(분할 버튼 · 큰 스위치 · 선택 카드 · Q 상자 · 키맨 가중치 · 판단 모드 · 출처 카드 · 근거 패널 · 메아리 · 수량 칩 · 오른쪽 시트 · 작업 고르기).
 */
import { useState } from 'react';
import {
  Badge, Banner, Button, CaseCard, ChatLine, ChoiceCard, ChoiceCustomInput, ChoiceList, Chip, Composer, CountPill, DataTable, EchoBubble, EvidencePanel,
  FilterTabs, ItemAddButton, KeyChip, KeymanAvatar, KeymanDot, ListToolbar, MatchChip, ModeChip, Notice, PageHeader, ProductInput, QBadge, SearchField, Section,
  Segmented, SideSheet, SourceBadge, SourceCard, StatusBadge, Tag, Thumb, THUMB_KINDS, Toggle, TrayChip, WeightBar, WeightStepper, WorkPickerDialog, stepWeights,
  toast, useConfirm, type ProductToken,
} from '@/ui';
import { useShellPage } from '../ShellContext';

const KEYMEN = [{ id: 'k1', name: '김 상무', colorIndex: 0 }, { id: 'k2', name: '이 팀장', colorIndex: 1 }, { id: 'k3', name: '박 책임', colorIndex: 2 }];
const ORDER_OPTS = [{ id: 'concept', title: '컨셉 방향 합의', aside: 'Overview 목적' }, { id: 'scope', title: '설계 반영 범위', aside: 'Outro 다음 단계' }, { id: 'collab', title: '협업 범위', aside: '' }];

/** 기능 요청으로 더한 부품 견본(kit-more.spec.ts 가 본다) */
function MoreKit() {
  const [seg, setSeg] = useState<'concept' | 'pitch'>('concept');
  const [view, setView] = useState<'edit' | 'compare'>('compare');
  const [lv, setLv] = useState<'1' | '2' | '3'>('2');
  const [big, setBig] = useState(false);
  const [radio, setRadio] = useState('pptx');
  const [order, setOrder] = useState<string[]>(['concept']);
  const [etc, setEtc] = useState('');
  const [etcs, setEtcs] = useState<string[]>([]);
  const [w, setW] = useState([50, 30, 20]);
  const [filter, setFilter] = useState('all');
  const [panel, setPanel] = useState(true);
  const [qtyTokens, setQtyTokens] = useState<ProductToken[]>([]);
  const [side, setSide] = useState(false);
  const [pick, setPick] = useState(false);
  const [picked, setPicked] = useState('');
  const toggleOrder = (id: string) => setOrder((o) => (o.includes(id) ? o.filter((x) => x !== id) : [...o, id]));
  const items = KEYMEN.map((k, i) => ({ ...k, weight: w[i] }));
  return (
    <div data-testid="kit-more" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Section title="분할 버튼 · 큰 스위치 (SB1S · IMG3E · IMG2R · CA2)">
        <div className="wm-row" style={{ flexWrap: 'wrap', gap: 14 }} data-testid="kit-seg">
          <Segmented tone="brand" h={32} ariaLabel="제안 방향" value={seg} onChange={setSeg} items={[{ value: 'concept', label: '컨셉 제안' }, { value: 'pitch', label: '공통 Pitch deck' }]} />
          <Segmented tone="brand" h={28} ariaLabel="보기" value={view} onChange={setView} items={[{ value: 'edit', label: '편집' }, { value: 'compare', label: '전/후 비교' }]} />
          <Segmented variant="line" h={26} ariaLabel="강도" value={lv} onChange={setLv} items={(['1', '2', '3'] as const).map((x) => ({ value: x, label: x }))} />
          <Segmented tone="brand" h={32} trackStrong ariaLabel="범위" value={seg} onChange={setSeg} items={[{ value: 'concept', label: '전체' }, { value: 'pitch', label: '선택한 섹션', disabled: true, title: '섹션을 먼저 고르세요' }]} />
          <Toggle size="lg" checked={big} onChange={setBig} label="경쟁사 A 포함" />
          <Toggle size="lg" checked disabled onChange={() => undefined} label="고정 기준" title="고정된 기준이에요" />
        </div>
      </Section>
      <Section title="선택 카드 · Q 상자 (SB1Q · SB4E)">
        <div className="wm-row" style={{ gap: 10 }} data-testid="kit-q">
          <QBadge size="xs" /><QBadge size="sm" /><QBadge /><QBadge size="lg" />
          <Button h={40} variant="primary"><QBadge size="onPrimary" />질의 시작</Button>
        </div>
        <ChoiceList label="결정할 것">
          {ORDER_OPTS.map((o) => (
            <ChoiceCard key={o.id} kind="ordered" pressed={order.includes(o.id)} order={order.indexOf(o.id) + 1} title={o.title} aside={o.aside || undefined}
              onClick={() => toggleOrder(o.id)} data-testid={`choice-${o.id}`} />
          ))}
          <ChoiceCustomInput value={etc} onChange={setEtc} onCommit={() => { if (etc.trim()) { setEtcs((x) => [...x, etc.trim()]); setEtc(''); } }} />
        </ChoiceList>
        <span className="wm-small" data-testid="choice-etc">{etcs.join(',')}</span>
        <ChoiceList label="내보내기 형식">
          <ChoiceCard kind="radio" pressed={radio === 'pptx'} icon="PPT" title="PPTX · 스토리보드 양식" hint="섹션 표 그대로 · 편집할 수 있어요" minHeight={84} onClick={() => setRadio('pptx')} data-testid="choice-pptx" />
          <ChoiceCard kind="radio" pressed={radio === 'pdf'} icon="PDF" title="PDF" hint="공유 · 인쇄용" minHeight={84} onClick={() => setRadio('pdf')} right={<>시트 <b>12</b></>} data-testid="choice-pdf" />
        </ChoiceList>
      </Section>
      <Section title="키맨 가중치 (RQ · SB · MI)">
        <div className="wm-row" style={{ gap: 8 }}>
          {items.map((k) => <KeymanAvatar key={k.id} name={k.name} colorIndex={k.colorIndex} />)}
          {[0, 1, 2, 3, 4].map((i) => <KeymanDot key={i} colorIndex={i} />)}
        </div>
        <div style={{ width: 600 }} data-testid="kit-wbar"><WeightBar items={items} onCommit={setW} /></div>
        <div className="wm-row" style={{ gap: 8 }}>
          {items.map((k, i) => <WeightStepper key={k.id} label={k.name} value={k.weight} onStep={(d) => setW(stepWeights(w, i, d))} data-testid={`wstep-${k.id}`} />)}
        </div>
      </Section>
      <Section title="판단 모드 · 출처 카드 · 근거 패널 (MI2A · MIR · MI3S)">
        <div className="wm-row" style={{ gap: 8 }} data-testid="kit-modes">
          <ModeChip mode="auto" /><ModeChip mode="check" /><ModeChip mode="ask" /><ModeChip mode="pin" /><ModeChip mode="ask">묻기</ModeChip><ModeChip mode="auto" dim />
        </div>
        <div style={{ height: 520, display: 'flex', justifyContent: 'flex-end', background: 'var(--wm-bg)', borderRadius: 12, overflow: 'hidden' }}>
          {panel ? (
            <EvidencePanel sub="시장조사 탭 · 선택한 주장의 출처 2건" onClose={() => setPanel(false)}
              filters={{ items: [{ key: 'all', label: '전체', count: 2 }, { key: 'public', label: '공개 자료', count: 2 }, { key: 'needs', label: '확인 필요', count: 1 }], value: filter, onChange: setFilter }}
              selected={{ text: '국내 F&B 매장의 디지털 메뉴보드 도입이 최근 [0]년간 [00]% 늘었습니다', meta: '출처 2건 · 원문 일치 1 · 확인 필요 1' }}
              footer={<Button h={38} variant="primary">한 번에 확정하기</Button>}>
              <SourceCard n={1} kind="공개 자료 · 시장 보고서" status="ok" title="[조사 기관] 국내 디지털 사이니지 시장 보고서" meta="[0000]년 [0]월 발행 · p.[00] · 오늘 확인"
                quote={{ before: '디지털 메뉴보드를 쓰는 매장이 [0]년간 ', highlight: '[00]% 증가' }}
                actions={[{ label: '원문 열기', icon: 'external', onClick: () => toast('원문 열기') }, { label: '각주로 복사', onClick: () => toast('각주로 복사') }]} data-testid="scard-1" />
              <SourceCard n={2} kind="공개 자료 · 기사" status="warn" title="[매체] 프랜차이즈 매장 디지털 전환 기사" meta="[0000]년 [0]월 게재 · 오늘 확인"
                quote="커피 프랜차이즈의 메뉴보드 디지털 전환 흐름" reason="수치 없이 흐름만 말해 [00]%를 뒷받침하지 못해요."
                actions={[{ label: '다른 출처 찾기', icon: 'refresh' }, { label: '값 직접 확정' }, { label: '이 출처 빼기', tone: 'ghost' }]} data-testid="scard-2" />
            </EvidencePanel>
          ) : <Button h={32} onClick={() => setPanel(true)}>근거 패널 열기</Button>}
        </div>
      </Section>
      <Section title="메아리 · W 말풍선 · 수량 칩 (IMG)">
        <EchoBubble head="공간" data-testid="kit-echo">카페 · 매장 메뉴보드 3면, 아침 시간대</EchoBubble>
        <ChatLine body={<div className="wm-row" data-testid="kit-chat-body"><Button h={32}>시안 4장 보기</Button></div>}>공간과 제품을 넣어 시안 4장을 만들었어요.</ChatLine>
        <div style={{ height: 300 }} />
        <div data-testid="product-input-qty">
          <ProductInput value={qtyTokens} onChange={setQtyTokens} qty headText={(q) => `"${q}" 검색 결과 · Enter로 추가`} placeholder="제품명을 입력해 추가…"
            label={qtyTokens.length ? '수량 칩 견본 제품 추가 입력' : '수량 칩 견본 제품 입력'} />
        </div>
        <pre data-testid="product-input-qty-value">{JSON.stringify(qtyTokens)}</pre>
      </Section>
      <Section title="오른쪽 시트 · 작업 고르기 (VPR · VP0)">
        <div className="wm-row">
          <Button onClick={() => setSide(true)}>규칙 시트 열기</Button>
          <Button onClick={() => setPick(true)}>Storyboard 고르기</Button>
          <span className="wm-small" data-testid="picked">{picked}</span>
        </div>
        <SideSheet open={side} onClose={() => setSide(false)} title="에이전트 라우팅 규칙" width={640}>
          <div className="wm-row" style={{ gap: 12, flexWrap: 'wrap' }}>
            <span className="wm-small wm-muted"><ModeChip mode="auto" /> 진행</span>
            <span className="wm-small wm-muted"><ModeChip mode="check" /> 진행 + 결과에 표시</span>
          </div>
          <p className="wm-small">읽기 전용 오른쪽 시트 견본 — Esc · 딤 클릭 · 닫기 버튼으로 닫혀요.</p>
        </SideSheet>
        {pick && (
          <WorkPickerDialog feature="SB" title="Storyboard 고르기" confirmLabel="이 자료로 시작" onClose={() => setPick(false)}
            onConfirm={(it) => { setPicked(`${it.item_id}:${it.title}`); setPick(false); }} />
        )}
      </Section>
    </div>
  );
}

export default function DevKit() {
  useShellPage({ section: '셸 개발', title: 'UI 키트', hasTask: false });
  const [tokens, setTokens] = useState<ProductToken[]>([]);
  const [q, setQ] = useState('');
  const [on, setOn] = useState(true);
  const [f, setF] = useState<'all' | 'run' | 'done'>('all');
  const { confirm, dialog } = useConfirm();
  const [answer, setAnswer] = useState<string>('');
  return (
    <div className="sh-dev">
      <PageHeader title="UI 키트 견본" desc="00-shell §2.8 컴포넌트 인벤토리" />
      <Section title="제품 입력창 (§5.10)">
        <div style={{ height: 300 }} />
        <div data-testid="product-input">
          <ProductInput value={tokens} onChange={setTokens} placeholder="제품명을 입력해 추가…" legend />
        </div>
        <pre data-testid="product-input-value">{JSON.stringify(tokens)}</pre>
      </Section>
      <Section title="버튼">
        <div className="wm-row" style={{ flexWrap: 'wrap' }}>
          <Button h={26}>상세</Button><Button h={28}>원문 열기 ↗</Button><Button h={32} variant="primary">현재 작업에 추가</Button>
          <Button h={34}>제품 탐색</Button><Button h={38}>취소</Button><Button h={40} variant="primary">바로 시작</Button><Button h={44} variant="primary">Spec 시트 만들기</Button>
          <Button h={38} variant="dark">딸깍, 완성하기</Button><Button h={40} variant="outline">새 작업</Button>
          <Button h={32} disabled disabledReason="진행 중인 작업이 없습니다">현재 작업에 추가</Button>
          <ItemAddButton state="add" name="QM55C" /><ItemAddButton state="sel" name="QM55C" /><ItemAddButton state="added" name="QM55C" /><ItemAddButton state="off" name="QM55C" />
        </div>
      </Section>
      <Section title="칩 · 배지 · 태그">
        <div className="wm-row" style={{ flexWrap: 'wrap' }}>
          <Chip on onClick={() => undefined}>리테일</Chip><Chip onClick={() => undefined}>호스피탈리티</Chip><TrayChip label="QM55C" onRemove={() => undefined} />
          <KeyChip>4K UHD</KeyChip><MatchChip label="용도 일치" n={3} on /><MatchChip label="모델 일치" n={0} /><CountPill n={3} />
          <Tag>유통/요식 · DT</Tag><Tag tone="neutral">MagicINFO Player</Tag>
          <Badge tone="photo">도입사례 사진 · 3장</Badge><Badge tone="product">제품</Badge><Badge tone="brand">삼성 공식 · 제품 이미지</Badge>
          <Badge tone="dashed">용도 일치 · 매장 메뉴보드</Badge><Badge tone="dark">제목에 명시</Badge><Badge tone="new">NEW</Badge><Badge tone="start">여기서 시작</Badge><Badge tone="core">핵심 기능</Badge>
          <Badge tone="brandline">1 / 8 · 정면 · 삼성 공식</Badge>
          <SourceBadge kind="kb">KB</SourceBadge><SourceBadge kind="ai">AI 추론</SourceBadge><SourceBadge kind="user">사용자 입력</SourceBadge><SourceBadge kind="warn">확인 필요</SourceBadge>
          <StatusBadge icon="check">완료</StatusBadge><StatusBadge tone="brand" icon="spin">확인 중</StatusBadge><StatusBadge tone="warn" icon="refresh">업데이트 필요</StatusBadge>
          <Toggle checked={on} onChange={setOn}>출처 확인된 이미지만</Toggle>
        </div>
        <Notice>진행 중인 작업이 없어 탐색만 할 수 있어요.</Notice>
        <Banner title="「QM65C」" sub="추가됨 · 카운터 · 메뉴보드 시트에 배치됨" onUndo={() => undefined} />
      </Section>
      <Section title="템플릿 썸네일 (§5.12)">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 120px)', gap: 10 }} data-testid="thumbs">
          {THUMB_KINDS.map((k, i) => <div key={k} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}><Thumb kind={k} n={(i % 5) + 1} dim={k === 'pD1'} /><span className="wm-small wm-muted">{k}</span></div>)}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}><Thumb kind="unknown-kind" n={3} /><span className="wm-small wm-muted">(모름 → table)</span></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }} data-testid="thumb-code">
            <Thumb code="MGI-S-RT" kind="cover" n={1} title="MGI-S-RT 표지" /><span className="wm-small wm-muted">code → export PNG, 없으면 그림</span>
          </div>
        </div>
      </Section>
      <Section title="작업 목록 뼈대">
        <ListToolbar left={<FilterTabs value={f} onChange={setF} items={[{ value: 'all', label: '전체', count: 3 }, { value: 'run', label: '진행 중', count: 2 }, { value: 'done', label: '저장됨', count: 1 }]} />}
          search={{ value: q, onChange: setQ, placeholder: '찾기', label: '요구사항 검색' }} />
        <DataTable rowKey={(r) => r.id} rows={[{ id: '1', t: 'E 자산운용 용산 AI Ready 오피스', s: '저장됨 · v1' }]}
          columns={[{ key: 't', label: '고객 · 사업', width: 'minmax(0, 1fr)', render: (r) => r.t }, { key: 's', label: '상태', width: '190px', render: (r) => <StatusBadge size="lg">{r.s}</StatusBadge> }]} />
      </Section>
      <Section title="사례 카드">
        <CaseCard title="맥도날드 고양삼송DT점 – 삼성 스마트 사이니지" date="2020-11-12" url="https://www.samsung.com/sec/business/insights/case-study/reference-MCDONALDSsamsong/"
          urlDisplay="samsung.com/sec/business/insights/case-study/reference-MCDONALDSsamsong" tag="유통/요식 · DT" summary="(견본) 요약 두 줄" products={['MagicINFO Player']}
          matchTerms={['메뉴보드']} photos={[]} photoCount={0} />
      </Section>
      <Section title="확인창 · 검색">
        <div className="wm-row">
          <SearchField value={q} onChange={setQ} label="견본 검색" placeholder="제품명 · 모델명 검색" />
          <Button onClick={async () => setAnswer(String(await confirm({ title: '이 작업을 지울까요?', message: '지운 작업은 되돌릴 수 없어요.', tone: 'danger', confirmLabel: '지우기' })))}>확인창 열기</Button>
          <span className="wm-small" data-testid="confirm-answer">{answer}</span>
          <Button onClick={() => toast('작업을 저장했어요', { action: { label: '열기', onClick: () => setAnswer('toast-action') } })}>토스트</Button>
        </div>
      </Section>
      <MoreKit />
      <Composer title="제품 입력" meta="2개 추가됨 · 1 / 3" actions={<Button h={44} variant="primary">항목 · 형식 선택</Button>}>
        <span className="wm-small wm-muted">(하단 입력 카드 견본)</span>
      </Composer>
      {dialog}
    </div>
  );
}
