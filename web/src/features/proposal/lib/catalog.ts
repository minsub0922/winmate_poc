/**
 * 제안서 고정 표 — 보드 SectionStep · PR3 스크립트 원문(10-proposal 부록 A–E).
 * 서버가 값을 주면 서버 값이 먼저다. 여기 값은 문구 원문 · 서버가 아직 주지 않는 화면 계산의 기본값으로 쓴다.
 */
export type ProposalType = 'standard' | 'quickwin' | 'solution';
export type SectionKey = 'mi' | 'bigMi' | 'vp' | 'birdseye' | 'spaceProducts' | 'solution' | 'cases' | 'why' | 'spec' | 'spaceScenario';
export type ItemKind = 'product' | 'solution' | 'image' | 'case';

export const STEPS = ['고객 · 프로젝트', '제안서 유형', '시트 구성', '섹션 작성', '디자인 템플릿', 'PPTX 생성'];

/** 템플릿: [코드, 이름, 언제 쓰나, 썸네일 kind] */
type Tpl = [string, string, string, string];
export interface RoleDef { name: string; msg: string; tpls?: Tpl[]; product?: boolean; role?: 'I' | 'D' | 'S'; generic?: string[] }

/** 시트 역할(SectionStep `ST`) */
export const ROLES: Record<string, RoleDef> = {
  MS: { name: '시장 규모 · 성장', msg: '이 시장은 크고, 커지고 있다', tpls: [
    ['MS-A', '핵심 수치 4', '지표는 여럿인데 연도별 추이는 없을 때', 'kpi4'],
    ['MS-B', '성장 추이', '연도별 시장 규모 데이터가 있을 때', 'barline'],
    ['MS-C', 'TAM · SAM · SOM', '전체 중 노릴 수 있는 몫을 말할 때', 'circles'],
    ['MS-D', '세그먼트 규모 × 성장률', '어디가 크고 빠른지, 고객 위치를 찍을 때', 'bubble'],
    ['MS-E', '성장 동인 → 전망', '수치는 적어도 왜 커지는지 설득할 때', 'panel']] },
  TR: { name: '산업 트렌드', msg: '업계가 이렇게 바뀐다', tpls: [
    ['TR-A', '흐름 타임라인', '과거에서 다음으로 가는 방향을 보여줄 때', 'timeline'],
    ['TR-B', '트렌드 → 고객 시사점', "트렌드마다 '그래서 A 커피는'을 붙일 때", 'cards2tier'],
    ['TR-C', '영향도 × 시급성', '트렌드가 많아 우선순위가 필요할 때', 'quad']] },
  CB: { name: '고객사 비즈니스', msg: '고객을 제대로 이해했다', tpls: [
    ['CB-A', '한 줄 요약 + 3단', '공개 자료로 현황을 요약할 때', 'summary3'],
    ['CB-B', '전략 목표 → 과제', '고객 전략과 이번 제안을 연결할 때', 'tree'],
    ['CB-C', '운영 흐름 속 문제', '업무 단계마다 문제가 있을 때', 'process'],
    ['CB-D', 'SWOT', '내부 · 외부 상황을 균형 있게 볼 때', 'swot']] },
  US: { name: '사용자 분석', msg: '고객의 손님과 직원을 안다', tpls: [
    ['US-A', '페르소나 3', '사용자 유형이 뚜렷이 나뉠 때', 'persona'],
    ['US-B', '고객 여정 맵', '경험 흐름 속 개입 지점을 보여줄 때', 'journey'],
    ['US-C', '사용자 구성 + 니즈', '방문객 구성 비율 데이터가 있을 때', 'donut']] },
  CP: { name: '경쟁 환경', msg: '시장 판도는 이렇다', tpls: [
    ['CP-A', '비교표', '공급사를 항목별로 따져볼 때', 'table'],
    ['CP-B', '포지셔닝 맵', '구도와 빈자리를 한눈에 보여줄 때', 'scatter'],
    ['CP-C', '점유율 + 추이', '점유율 데이터가 있을 때', 'stack']] },
  IM: { name: 'MI 시사점', msg: '그래서 이번 제안은', tpls: [
    ['IM-A', '발견 → 시사점 → 방향', 'MI를 제안 방향 하나로 좁힐 때', 'funnel'],
    ['IM-B', '4분면 요약 + 결론', '경영진용 한 장 요약', 'quadCircle']] },
  CH: { name: '고객 과제', msg: '지금 이런 문제가 있다', tpls: [
    ['CH-A', '과제 3 + 영향', '문제와 그 비용을 함께 보여줄 때', 'pillars'],
    ['CH-B', '지금 → 바라는 모습', '고객이 원하는 상태가 분명할 때', 'asis'],
    ['CH-C', '문제 → 근본 원인', '원인을 짚어 제안의 필요성을 만들 때', 'tree']] },
  VP: { name: '가치 제안', msg: '우리는 이런 가치를 준다', tpls: [
    ['VP-A', '과제 ↔ 해결 1:1', '과제마다 해법을 짝지을 때', 'rows'],
    ['VP-B', '가치 기둥 2 · 3 · 4', 'Key Message 수만큼 기둥으로 세울 때', 'pillars'],
    ['VP-C', '한 문장 + 근거 3', '메시지 하나를 강하게 말할 때', 'statement'],
    ['VP-D', '이해관계자별 가치', '의사결정자가 여럿일 때', 'persona']] },
  EF: { name: '기대 효과', msg: '도입하면 이만큼 좋아진다', tpls: [
    ['EF-A', 'KPI 전 → 후', '개선 수치(전/후)가 있을 때', 'hbars'],
    ['EF-B', '투자 회수', '재무 관점으로 설득해야 할 때', 'roi'],
    ['EF-C', '정량 + 정성 효과', '수치와 체감 효과를 함께 말할 때', 'split']] },
  BV: { name: '공간 전경', msg: '완성된 공간을 미리 본다', tpls: [
    ['BV-A', '풀폭 전경', '조감도 한 장으로 충분할 때', 'image'],
    ['BV-B', '두 시점 비교', '주간/야간, 도입 전/후를 비교할 때', 'image2'],
    ['BV-C', '전경 + 한 장 요약', '경영진에게 제안 전체를 요약할 때', 'imagePanel']] },
  ZP: { name: '존별 포인트', msg: '공간마다 무엇이 달라지나', tpls: [
    ['ZP-A', '번호 콜아웃', '조감도 한 장 위에 포인트를 찍을 때', 'callouts'],
    ['ZP-B', '존 확대 컷', '존마다 디테일 이미지가 있을 때', 'zoom'],
    ['ZP-C', '고객 동선 따라가기', '손님 동선 순서로 설명할 때', 'path']] },
  SM: { name: '공간 맵', msg: '어디에 무엇을', tpls: [
    ['SM-A', '존 맵 + 목록', '공간이 3곳 안팎일 때', 'zones'],
    ['SM-B', '공간 × 제품 수량표', '공간 · 제품이 많아 교차표가 필요할 때', 'qtyMatrix']] },
  PI: { name: '공간 제품 소개', msg: '이 공간에는 이 제품', product: true },
  BM: { name: '구성 · 수량', msg: '무엇을 몇 대', tpls: [
    ['BM-A', '전체 구성표', '견적 전에 전체 물량을 확정할 때', 'table'],
    ['BM-B', '매장 유형별 구성', '매장 규모가 여러 가지일 때', 'cards3img']] },
  SA: { name: '솔루션 구성도', msg: '어떻게 연결되나', tpls: [
    ['SA-A', '계층형', '본사 → 클라우드 → 매장 구조일 때', 'tiers'],
    ['SA-B', '허브형', '솔루션 하나가 여러 기기를 묶을 때', 'hub'],
    ['SA-C', '레이어 스택', '제공 범위(누가 무엇을)를 보여줄 때', 'layers']] },
  OP: { name: '운영 시나리오', msg: '어떻게 쓰이나', tpls: [
    ['OP-A', '단계 타임라인', '하루 · 이벤트 흐름을 따라갈 때', 'timeline'],
    ['OP-B', '역할별 스윔레인', '여러 역할이 한 흐름에 관여할 때', 'swimlane'],
    ['OP-C', '도입 전 → 후 업무', '업무가 얼마나 줄어드는지 보여줄 때', 'stepsCompare']] },
  SF: { name: '솔루션 상세', msg: '이 솔루션은 무엇을 하나', tpls: [
    ['SF-A', '솔루션 + 함께 쓰는 제품', '솔루션 하나를 소개할 때', 'panelLeft'],
    ['SF-B', '기능 → 고객 효과', '기능을 고객의 언어로 옮길 때', 'featureMap']] },
  SXI: { name: '솔루션 소개', msg: '이 솔루션은 무엇이고, 언제 쓰나', role: 'I', generic: ['SF-A', 'SF-B'] },
  SXD: { name: '솔루션 구성도', msg: '어떻게 연결되고 움직이나', role: 'D', generic: ['SA-A', 'SA-B', 'SA-C'] },
  SXS: { name: '솔루션 공간 시나리오', msg: '고객의 공간에서 언제 · 어디서 일하나', role: 'S', generic: ['OP-A', 'OP-B', 'SS-A'] },
  VM: { name: '공간 × 솔루션 전체 맵', msg: '공간마다 어떤 솔루션이', tpls: [
    ['VM-A', '공간 × 솔루션 매트릭스', '공간과 솔루션이 격자로 맞을 때', 'matrix'],
    ['VM-B', '공간 3개 한 장', '공간이 3곳이라 나란히 볼 때', 'cards3img'],
    ['VM-C', '조감도 위 솔루션 핀', '조감도가 있어 위치로 보여줄 때', 'pins'],
    ['VM-D', '하루 타임라인 × 공간', '시간에 따라 공간을 넘나들 때', 'swimlane']] },
  SS: { name: '공간 시나리오', msg: '이 공간에서 이렇게 가치가 생긴다', tpls: [
    ['SS-A', '한 공간의 장면 3', '시간대별 장면이 있을 때', 'scenes'],
    ['SS-B', '솔루션 → 제품 → 가치', '인과(무엇이 · 무엇으로 · 어떤 가치)를 보일 때', 'chain'],
    ['SS-C', '이 공간 전 → 후', '변화가 눈에 보이는 공간일 때', 'image2']] },
  CD: { name: '사례 상세', msg: '비슷한 고객이 이렇게 성공했다', tpls: [
    ['CD-A', '과제 · 해결 · 성과', '사례를 이야기로 풀 때', 'cases'],
    ['CD-B', '도입 전 → 후 사진', '전후 사진이 있을 때', 'image2kpi'],
    ['CD-C', '성과 수치 + 코멘트', '공개된 성과 수치가 강할 때', 'bignum']] },
  CL: { name: '사례 모음', msg: '이미 여러 곳에서 검증됐다', tpls: [
    ['CL-A', '2건 비교', '비슷한 사례 두 건을 나란히', 'cards2'],
    ['CL-B', '3건 요약', '업종이 다른 사례 세 건', 'list3'],
    ['CL-C', '레퍼런스 월', '사례 수 자체가 메시지일 때', 'logos']] },
  CM: { name: '경쟁 비교', msg: '경쟁사보다 낫다', tpls: [
    ['CM-A', '비교표 (삼성 강조)', '항목별로 우위를 보일 때', 'tableHl'],
    ['CM-B', '요구사항별 충족도', '고객 요구사항을 기준으로 비교할 때', 'hbars'],
    ['CM-C', '레이더 종합 비교', '여러 기준을 한 번에 종합할 때', 'radar']] },
  ST: { name: '삼성 강점', msg: '삼성이어야 하는 이유', tpls: [
    ['ST-A', '강점 3', '강점이 3개로 정리될 때', 'pillars'],
    ['ST-B', '요구 ↔ 강점 2×2', '요구사항 4개에 하나씩 답할 때', 'grid4'],
    ['ST-C', '강점 + 증거 수치', '검증된 수치가 있을 때', 'panel']] },
  SV: { name: '지원 체계', msg: '도입 후에도 책임진다', tpls: [
    ['SV-A', '도입 로드맵', '일정 · 단계 · 책임을 제시할 때', 'gantt'],
    ['SV-B', '서비스 커버리지 + SLA', '매장이 전국에 흩어져 있을 때', 'mapTable']] },
  SC: { name: '스펙 비교', msg: '제품별 사양 차이', tpls: [
    ['SC-A', '사양 비교표 2~5개', '제품 간 사양 차이를 볼 때', 'specTable'],
    ['SC-B', '요구사항 대응표', '요구사항 충족을 증명해야 할 때', 'checkTable']] },
  SD: { name: '제품 상세', msg: '한 제품의 모든 것', tpls: [
    ['SD-A', '그룹별 상세 사양', '사양 전체를 정리할 때', 'specGroups'],
    ['SD-B', '치수 · 설치 정보', '설치 검토가 필요할 때', 'drawing']] },
};

/** 시트 구성 화면 이름(PR3 `STN`): [이름, 말하는 것, 템플릿 수] */
export const STN: Record<string, [string, string, number]> = {
  MS: ['시장 규모 · 성장', '이 시장은 크고, 커지고 있다', 5], TR: ['산업 트렌드', '업계가 이렇게 바뀐다', 3],
  CB: ['고객사 비즈니스', '고객을 제대로 이해했다', 4], US: ['사용자 분석', '고객의 손님과 직원을 안다', 3],
  CP: ['경쟁 환경', '시장 판도는 이렇다', 3], IM: ['MI 시사점', '그래서 이번 제안은', 2],
  CH: ['고객 과제', '지금 이런 문제가 있다', 3], VP: ['가치 제안', '우리는 이런 가치를 준다', 4], EF: ['기대 효과', '도입하면 이만큼 좋아진다', 3],
  BV: ['공간 전경', '완성된 공간을 미리 본다', 3], ZP: ['존별 포인트', '공간마다 무엇이 달라지나', 3],
  SM: ['공간 맵', '어디에 무엇을', 2], PI: ['공간 제품 소개', '이 공간에는 이 제품', 20], BM: ['구성 · 수량', '무엇을 몇 대', 2],
  SA: ['통합 구성도', '여러 솔루션이 어떻게 이어지나', 3], OP: ['통합 운영 시나리오', '솔루션들이 함께 어떻게 쓰이나', 3], SF: ['솔루션 상세', '이 솔루션은 무엇을 하나', 2],
  VM: ['공간 × 솔루션 맵', '공간마다 어떤 솔루션이', 4], SS: ['공간 시나리오', '이 공간에서 이렇게 가치가 생긴다', 3],
  CD: ['사례 상세', '비슷한 고객이 이렇게 성공했다', 3], CL: ['사례 모음', '이미 여러 곳에서 검증됐다', 3],
  CM: ['경쟁 비교', '경쟁사보다 낫다', 3], ST: ['삼성 강점', '삼성이어야 하는 이유', 3], SV: ['지원 체계', '도입 후에도 책임진다', 2],
  SC: ['스펙 비교', '제품별 사양 차이', 2], SD: ['제품 상세', '한 제품의 모든 것', 2],
  MGI: ['MagicINFO', '설치형 사이니지 CMS', 0], VXT: ['Samsung VXT', '클라우드 사이니지 CMS', 0],
  STP: ['SmartThings Pro', '여러 사업장 IoT · 에너지', 0], KNX: ['Knox Suite', '업무용 갤럭시 관리 · 보안', 0],
  CCH: ['삼성 콜드체인', '냉장 · 냉동 + 에어컨 통합 관리', 0], HVC: ['삼성 통합공조', '개별 + 중앙공조 + b.IoT', 0],
  SAC: ['SAC 제어 시스템', '시스템에어컨 제어 · 전력량 분배', 0],
  BIT: ['b.IoT', '공조 중심 빌딩 관리 · b.IoT / Lite 비교', 0], LYN: ['LYNK Cloud', '투숙객 · 호텔 양쪽의 가치', 0],
  KCP: ['Knox Capture', '전용 스캐너 + 단말 → 갤럭시 1대', 0], DEX: ['Samsung DeX', '휴대폰 하나로 PC 업무까지', 0],
};

/** 솔루션 11개 · 전용 템플릿 설명(SectionStep `SOLS`) */
export const SOLS: Record<string, [string, { I: string; D: string; S: string }]> = {
  MGI: ['MagicINFO', { I: '서버 · 보안 요건과 데이터 연동을 앞세울 때', D: '사내 서버 · 방화벽 안에서 도는 구조', S: '가격이 바뀌면 매장까지 몇 분 — 데이터 연동 흐름' }],
  VXT: ['Samsung VXT', { I: '설치 없이 바로 쓰는 구독형임을 강조할 때', D: '매장엔 화면만, 나머지는 클라우드', S: '점장이 휴대폰으로 3분 만에 교체' }],
  STP: ['SmartThings Pro', { I: '여러 매장의 기기 · 에너지를 한 화면에', D: '기기는 매장에, 판단은 클라우드에', S: '매장의 하루 — 에너지 자동화' }],
  BIT: ['b.IoT', { I: '공조 중심 빌딩 관리 · b.IoT / Lite 비교', D: '층별 설비 → 게이트웨이 → 관리 화면', S: '층 × 시간 — 쓰는 층만 쾌적하게' }],
  LYN: ['LYNK Cloud', { I: '투숙객 · 호텔 양쪽의 가치', D: 'PMS ↔ LYNK Cloud ↔ 객실 TV', S: '체크인부터 체크아웃까지 객실 TV' }],
  KNX: ['Knox Suite', { I: '받는 날부터 회수까지 — 기기 수명주기', D: '콘솔 하나 · 기기 속 업무 영역', S: '새 태블릿이 매장에서 바로 일하기까지' }],
  KCP: ['Knox Capture', { I: '전용 스캐너 + 단말 → 갤럭시 1대', D: '스캔 값이 기존 앱까지 가는 길', S: '입고부터 계산대까지 한 대로' }],
  DEX: ['Samsung DeX', { I: '휴대폰 하나로 PC 업무까지', D: '연결 방식 · 업무 자원 · 보안', S: '영업 사원의 하루, 기기는 하나' }],
  CCH: ['삼성 콜드체인', { I: '성능 · 설치 · 관리 · 서비스 4 UP', D: '실외기 → 쇼케이스 · 저장고 → b.IoT Cloud', S: '한여름 오후 · 새벽에도 보관 온도 유지' }],
  HVC: ['삼성 통합공조', { I: '개별 + 중앙공조 = b.IoT 하나로', D: '열원 → 냉수 → AHU · FCU, 개별 DVM', S: '건물마다 다른 운전 시간을 한 화면에' }],
  SAC: ['SAC 제어 시스템', { I: '리모컨부터 BMS 연동까지 제어 단계', D: 'DMS · R1/R2 · F1/F2 통신 구조', S: '임대 호실별 제어 · 전력량 분배' }],
};
export const SOL_CODES = Object.keys(SOLS);
const SOL_ROLE: Record<'I' | 'D' | 'S', [string, string]> = { I: ['전용 소개', 'solIntro'], D: ['전용 구성도', 'solDiagram'], S: ['전용 공간 시나리오', 'solScene'] };
/** 솔루션 업종 코드(`IND`) */
export const SOL_IND: Record<string, string> = { OF: '오피스', HT: '비즈니스 호텔', RT: '매장', GF: '스크린골프장', AC: '학원', LG: '물류센터', FD: '제조 현장', WH: '저온 저장시설' };
export const SOL_VARS: Record<string, string[]> = { MGI: ['RT', 'HT'], VXT: ['RT', 'GF'], STP: ['OF', 'HT', 'GF'], BIT: ['HT', 'RT'], LYN: ['HT'], KNX: ['AC', 'FD'], KCP: ['LG'], DEX: ['OF', 'FD'], CCH: ['RT', 'WH'], HVC: ['OF', 'HT'], SAC: ['AC', 'GF'] };

/** 16업종(`INDS`, 부록 C) */
export const INDUSTRIES: Record<string, string> = {
  FB: '외식 · 카페', RT: '리테일 · 플래그십', SV: '생활 편의 · 무인 매장', HT: '호텔 · 리조트', TP: '테마파크 · 전시', VN: '공연장 · 경기장', AD: '옥외 광고', OF: '오피스',
  RS: '주거 분양', ID: '인테리어 · 빌트인', ED: '교육 · 캠퍼스', PB: '공공 · 교통', MD: '의료 · 요양', MF: '제조 · 물류 · 현장', FN: '금융', OE: '파트너 전용 단말',
};
/** PR1 업종 칩(넓은 묶음 → 16코드 후보, ⚠Q9) */
export const INDUSTRY_CHIPS: Array<{ label: string; codes: string[] }> = [
  { label: '리테일 · F&B', codes: ['FB', 'RT', 'SV'] },
  { label: '호스피탈리티', codes: ['HT', 'TP', 'VN'] },
  { label: '교육', codes: ['ED'] },
  { label: '헬스케어', codes: ['MD'] },
];
/** 업종 레이아웃 변형(`IROLE`): 계열 → 변형 → [이름, 썸네일, 설명] */
export const IROLE: Record<'MI' | 'VP' | 'SS', Record<'A' | 'B' | 'C', [string, string, string]>> = {
  MI: { A: ['시장 · 트렌드', 'barline', '업종 시장 규모 · 동인 → 그래서 고객에게'], B: ['고객 비즈니스 · 운영 과제', 'process', '업종 사업 구조 · KPI · 운영 과제'], C: ['사용자 여정', 'journey', '사용자 · 이해관계자 여정과 개입 지점'] },
  VP: { A: ['과제 → 해법 → 효과', 'indVP', '업종 핵심 과제마다 삼성 해법과 효과'], B: ['이해관계자별 가치', 'persona', '업종의 결정권자 · 이용자별 가치'], C: ['기대 효과', 'hbars', '업종 KPI 전 → 후 · 투자 효과'] },
  SS: { A: ['공간 맵', 'indMap', '업종 공간 전체 × 제품 · 솔루션 · 가치'], B: ['대표 공간 장면', 'scenes', '업종의 핵심 공간 한 곳의 장면'], C: ['하루 · 동선', 'indDay', '하루 · 동선 · 역할별 스윔레인'] },
};
/** 역할 → 업종 레이아웃(`IND_FOR`) */
export const IND_FOR: Record<string, ['MI' | 'VP' | 'SS', 'A' | 'B' | 'C']> = {
  MS: ['MI', 'A'], TR: ['MI', 'A'], CB: ['MI', 'B'], CP: ['MI', 'B'], IM: ['MI', 'B'], US: ['MI', 'C'], CH: ['VP', 'A'], VP: ['VP', 'A'], EF: ['VP', 'C'],
  VM: ['SS', 'A'], SM: ['SS', 'A'], SS: ['SS', 'B'], OP: ['SS', 'C'],
};
const PV: Record<'A' | 'B' | 'C' | 'D', [string, string, string]> = {
  A: ['제품 이미지 중심', '제품 사진이 좋을 때 (기본)', 'pA'], B: ['공간 · 설치 중심', '설치 모습 · 조감도가 연결됐을 때', 'pB'],
  C: ['스펙 · 비교 중심', '수치 비교 · 라인업이 핵심일 때', 'pC'], D: ['강조형', '주력 제품을 지정했을 때', 'pD'],
};

export interface TplInfo { code: string; name: string; when: string; kind: string; n: number }
/** 템플릿 코드 → 이름 · 언제 쓰나 · 썸네일(보드 `tplOf`) */
export function tplOf(code: string): TplInfo {
  const m = /^P(\d)-([A-D])$/.exec(code || '');
  if (m) {
    const c = Number(m[1]);
    const v = m[2] as 'A' | 'B' | 'C' | 'D';
    const one = v === 'D' && c === 1;
    return { code, name: one ? '메시지 강조' : PV[v][0], when: one ? '제품 하나의 메시지를 강하게 말할 때' : PV[v][1], kind: one ? 'pD1' : PV[v][2], n: c };
  }
  const im = /^(MI|VP|SS)-([A-Z]{2})-([ABC])$/.exec(code || '');
  if (im && INDUSTRIES[im[2]]) {
    const r = IROLE[im[1] as 'MI'][im[3] as 'A'];
    return { code, name: `${INDUSTRIES[im[2]]} · ${r[0]}`, when: `${INDUSTRIES[im[2]]} 고객용 — ${r[2]}`, kind: r[1], n: 3 };
  }
  const sm = /^([A-Z]{3})-([IDS])(?:-([A-Z]{2}))?$/.exec(code || '');
  if (sm && SOLS[sm[1]] && sm[3] && SOL_IND[sm[3]]) {
    return { code, name: `${SOL_IND[sm[3]]} 업종 버전`, when: `고객 업종이 ${SOL_IND[sm[3]]}일 때 — 그 업종의 공간 사진과 순서로`, kind: 'solSceneInd', n: 3 };
  }
  if (sm && SOLS[sm[1]]) {
    const r = sm[2] as 'I' | 'D' | 'S';
    return { code, name: `${SOLS[sm[1]][0]} ${SOL_ROLE[r][0]}`, when: SOLS[sm[1]][1][r], kind: SOL_ROLE[r][1], n: 3 };
  }
  const st = ROLES[(code || '').split('-')[0]];
  const t = st?.tpls?.find((x) => x[0] === code);
  return t ? { code, name: t[1], when: t[2], kind: t[3], n: 3 } : { code, name: code, when: '', kind: 'table', n: 3 };
}

/** 템플릿 고르기 후보(§4.16 · 보드 로직) — 서버가 후보를 주지 않을 때 */
export function templateCandidates(role: string, opts: { solution?: string | null; industry?: string | null; productCount?: number }): string[] {
  const def = ROLES[role];
  if (!def) return [];
  if (def.product) {
    const n = Math.min(Math.max(opts.productCount ?? 3, 1), 5);
    return ['A', 'B', 'C', 'D'].map((v) => `P${n}-${v}`);
  }
  if (def.generic && def.role) {
    const sol = opts.solution ?? '';
    const own = sol ? [`${sol}-${def.role}`] : [];
    const vars = def.role === 'S' && sol ? (SOL_VARS[sol] ?? []).map((x) => `${sol}-S-${x}`) : [];
    return own.concat(vars, def.generic).slice(0, 5);
  }
  const ind = opts.industry && IND_FOR[role] ? [`${IND_FOR[role][0]}-${opts.industry}-${IND_FOR[role][1]}`] : [];
  return ind.concat((def.tpls ?? []).map((x) => x[0])).slice(0, 5);
}

export interface TypeDef { name: string; short: string; secs: SectionKey[]; opt: SectionKey[]; desc: string; prefix: 'PRS' | 'PRQ' | 'PRX'; open: number }
/** 제안서 유형(§3.3 · 부록 D) */
export const TYPES: Record<ProposalType, TypeDef> = {
  standard: { name: '표준 제안서', short: '표준', secs: ['mi', 'vp', 'birdseye', 'spaceProducts', 'solution', 'cases', 'why', 'spec'], opt: ['mi', 'solution'], prefix: 'PRS', open: 0,
    desc: '시장 분석부터 공간·제품·솔루션·스펙까지 전 과정을 담는 기본형' },
  quickwin: { name: '퀵윈(제품) 제안서', short: '퀵윈', secs: ['vp', 'spaceProducts', 'solution', 'cases', 'spec'], opt: ['solution'], prefix: 'PRQ', open: 1,
    desc: '제품 중심으로 빠르게 결정을 끌어내는 간결형' },
  solution: { name: 'Solution형 제안서', short: 'Solution형', secs: ['bigMi', 'vp', 'spaceScenario', 'cases', 'why'], opt: ['vp'], prefix: 'PRX', open: 2,
    desc: '대규모 MI와 공간별 가치 제공 시나리오로 설득하는 솔루션 중심형' },
};
export const TYPE_ROW_LABEL: Record<ProposalType, string> = { standard: '표준', quickwin: '퀵윈(제품)', solution: 'Solution형' };

export interface SectionDef {
  name: string; short: string; intro: string; side: string[]; sideFeatures: string[]; accepts: ItemKind[]; quick: string[]; infer: string;
  /** 보드 예시 시트(제목 · 역할 · 자동 템플릿 · 이유 · 솔루션) */
  sheets: Array<[string, string, string, string, string?]>;
}
/** 섹션 정의(SectionStep `SEC` · `INFER`, 부록 D) — sideFeatures = 사이드바에서 받는 기능 코드 */
export const SECTIONS: Record<SectionKey, SectionDef> = {
  mi: { name: 'Market Intelligence', short: 'MI',
    intro: 'Market Intelligence 섹션입니다. 사이드바의 MI 작업을 끌어 놓으면 필요한 내용만 뽑아 시트에 넣고, 시트마다 데이터 모양에 맞는 템플릿을 골라 둡니다.',
    side: ['MI 작업'], sideFeatures: ['MI'], accepts: ['case'], quick: ['수치 근거 보강', '더 간결하게'], infer: '연결된 MI 작업 + 요구사항 기반 조사',
    sheets: [['시장 규모 · 성장', 'MS', 'MS-B', '연결된 MI에 연도별 시장 규모(2020~2028)가 있어요'], ['고객사 비즈니스', 'CB', 'CB-C', '요구사항이 매장 운영 문제(메뉴 교체 · 가격 표기)예요'], ['경쟁 환경', 'CP', 'CP-A', '경쟁사 3곳을 요구사항 5개로 비교해요']] },
  bigMi: { name: '대규모 MI', short: '대규모 MI',
    intro: 'Solution형 제안서의 출발점인 대규모 Market Intelligence입니다. 산업·고객사·사용자·경쟁 구도를 넓게 다루며, 사이드바의 MI 작업 여러 개를 끌어 놓아 합칠 수 있습니다.',
    side: ['MI 작업'], sideFeatures: ['MI'], accepts: ['case'], quick: ['조사 범위 넓히기', '출처 보기'], infer: '연결된 MI 2건 + 산업·경쟁 추가 조사',
    sheets: [['시장 규모 · 성장', 'MS', 'MS-C', '전 매장 확장 계획이 있어 노릴 수 있는 몫이 핵심이에요'], ['산업 트렌드', 'TR', 'TR-B', '트렌드 3개가 모두 A 커피 과제와 이어져요'], ['고객사 비즈니스', 'CB', 'CB-B', "고객 전략 문서에 '운영 효율' 목표가 있어요"], ['사용자 분석', 'US', 'US-B', '매장 방문 흐름 인터뷰가 있어요'], ['경쟁 환경', 'CP', 'CP-B', '공급사 6곳을 두 축으로 나눌 수 있어요']] },
  vp: { name: 'Value Props', short: 'Value Props',
    intro: '고객에게 줄 핵심 가치를 정리합니다. Storyboard의 Key Message와 제안 전략을 가져와 고객 과제 → 가치 제안 흐름의 시트로 만들었습니다.',
    side: ['Storyboard 작업'], sideFeatures: ['SB'], accepts: ['image'], quick: ['가치 하나 추가', '경영진 톤으로'], infer: 'Storyboard Key Message · 전략으로 작성',
    sheets: [['고객 과제', 'CH', 'CH-B', '요구사항에 바라는 운영 모습이 적혀 있어요'], ['가치 제안', 'VP', 'VP-B', 'Storyboard Key Message가 3개예요']] },
  birdseye: { name: '조감도', short: '조감도',
    intro: '공간 특징이 드러나는 조감도 시트입니다. 공간 조감도 작업의 결과를 연결했고, 다른 조감도 작업이나 이미지를 끌어 놓아 바꿀 수 있습니다.',
    side: ['조감도 작업'], sideFeatures: ['BE'], accepts: ['image'], quick: ['시점 추가', '조감도 새로 만들기'], infer: '연결된 조감도 작업으로 완성',
    sheets: [['공간 전경', 'BV', 'BV-A', '조감도 1장에 공간 전체가 들어와요'], ['존별 포인트', 'ZP', 'ZP-A', '조감도 위에 포인트 4곳이 표시돼 있어요']] },
  spaceProducts: { name: '공간별 제품', short: '공간별 제품',
    intro: '공간마다 어떤 제품이 어디에 놓이는지 보여줍니다. 조감도 배치안에서 공간 3곳과 제품을 가져왔고, 제품 탐색에서 끌어 놓아 더할 수 있습니다.',
    side: ['조감도 · Spec 시트 작업'], sideFeatures: ['BE', 'SP'], accepts: ['product', 'image'], quick: ['공간 추가', '수량 조정'], infer: '조감도 배치안 · 요구사항에서 제품 추론',
    sheets: [['공간 맵', 'SM', 'SM-A', '공간이 3곳이라 존 맵으로 충분해요'], ['카운터 · 메뉴보드', 'PI', 'P3-B', ''], ['쇼윈도 · 외부', 'PI', 'P2-A', ''], ['주문 · 대기 공간', 'PI', 'P1-B', '']] },
  solution: { name: '솔루션 제안', short: '솔루션 제안',
    intro: '제품과 함께 쓸 솔루션을 제안합니다. 솔루션마다 전용 템플릿(소개 · 구성도 · 공간 시나리오)으로 그 솔루션의 특징대로 보여주고, 두 개 이상이면 통합 구성도를 더합니다.',
    side: ['공간 시나리오 작업'], sideFeatures: ['SC'], accepts: ['solution', 'product'], quick: ['통합 운영 시나리오 추가', '운영 비용 추가'], infer: '연결된 솔루션 2개 · 시나리오로 작성',
    sheets: [['MagicINFO · 소개', 'SXI', 'MGI-I', '연결된 솔루션 — MagicINFO 전용 템플릿이 있어요', 'MGI'], ['MagicINFO · 구성도', 'SXD', 'MGI-D', '요구사항에 사내 서버 · 보안 조건이 있어요', 'MGI'],
      ['MagicINFO · 공간 시나리오', 'SXS', 'MGI-S', 'POS 가격 연동이 핵심 장면이에요', 'MGI'], ['SmartThings Pro · 소개', 'SXI', 'STP-I', '연결된 솔루션 — SmartThings Pro 전용 템플릿이 있어요', 'STP'],
      ['SmartThings Pro · 구성도', 'SXD', 'STP-D', '매장 기기가 여러 종류이고 매장이 많아요', 'STP'], ['SmartThings Pro · 공간 시나리오', 'SXS', 'STP-S', '영업시간 기반 에너지 절감이 요구사항에 있어요', 'STP'],
      ['통합 구성도', 'SA', 'SA-A', '두 솔루션이 본사 → 매장으로 함께 배포돼요', '']] },
  cases: { name: '유관 사례', short: '유관 사례',
    intro: '비슷한 고객의 도입 사례로 설득력을 더합니다. 유사도가 높은 사례 2건을 골라 두었고, 유관 사례 검색에서 끌어 놓아 바꾸거나 더할 수 있습니다.',
    side: [], sideFeatures: [], accepts: ['case', 'image'], quick: ['성과 수치 강조', '사례 한 장으로 모으기'], infer: '유사도 상위 사례 자동 선택',
    sheets: [['사례 · 커피 프랜차이즈', 'CD', 'CD-A', '과제 · 해결 · 성과가 모두 있는 사례예요'], ['사례 · 편의점 체인', 'CD', 'CD-B', '도입 전후 사진이 있어요']] },
  why: { name: 'Why Samsung', short: 'Why Samsung',
    intro: '경쟁사 대비 삼성의 강점을 정리합니다. MI의 경쟁사 분석에서 비교 항목과 강점 3개를 가져왔습니다. 수치는 검증 전이라 [확정 필요]로 표시해 두었습니다.',
    side: ['MI 작업'], sideFeatures: ['MI', 'CA'], accepts: ['case'], quick: ['비교 항목 추가', '레퍼런스 강조'], infer: 'MI 경쟁사 분석으로 비교 작성',
    sheets: [['경쟁 비교', 'CM', 'CM-A', '경쟁사 2곳을 항목 6개로 비교해요'], ['삼성 강점', 'ST', 'ST-A', '강점이 3개이고 수치는 아직 검증 전이에요']] },
  spec: { name: '제품 스펙', short: '제품 스펙',
    intro: '제안한 제품의 스펙을 정리합니다. 공간별 제품에 들어간 모델로 비교표를 만들었고, Spec 시트 작업이나 제품 탐색에서 끌어 놓아 더할 수 있습니다.',
    side: ['Spec 시트 작업'], sideFeatures: ['SP'], accepts: ['product'], quick: ['제품별로 나누기', '영문 스펙'], infer: '공간별 제품 모델로 비교표 생성',
    sheets: [['스펙 비교', 'SC', 'SC-A', '제품 3종의 사양 차이를 보여줘요'], ['제품 상세 · QM55C', 'SD', 'SD-A', '주력 제품 1종의 전체 사양이에요']] },
  spaceScenario: { name: '공간별 가치 제공 시나리오', short: '공간별 가치 시나리오',
    intro: '어떤 솔루션이 어느 공간에서, 어떤 제품과 함께, 어떻게 쓰이는지를 시나리오로 보여줍니다. 공간 시나리오 작업을 가져와 공간 3곳 × 솔루션 2개로 구성했습니다.',
    side: ['공간 시나리오 · 조감도 작업'], sideFeatures: ['SC', 'BE'], accepts: ['solution', 'product', 'image'], quick: ['공간 추가', '솔루션 추가'], infer: '시나리오 작업 + 공간별 솔루션 매핑 추론',
    sheets: [['공간 × 솔루션 맵', 'VM', 'VM-A', '공간 3곳 × 솔루션 2개가 격자로 맞아요'], ['본사 운영실', 'SS', 'SS-B', '솔루션 → 제품 → 가치가 한 공간에서 이어져요'], ['매장 카운터', 'SS', 'SS-A', '시간대별 장면 3개가 있어요'], ['매장 외부', 'SS', 'SS-C', '도입 전후 차이가 눈에 보이는 공간이에요']] },
};
export const isSectionKey = (k: string | undefined): k is SectionKey => !!k && k in SECTIONS;

/** 시트 구성 기본값(PR3 `SECS`, 부록 E): [코드, 상태 1 넣음 · 2 추천 · 0 안 넣음, 반복, 자료] */
export const COMPOSITION: Record<SectionKey, Array<[string, 0 | 1 | 2, number, string]>> = {
  mi: [['MS', 1, 1, 'MI 작업에서'], ['CB', 1, 1, 'MI 작업에서'], ['CP', 1, 1, 'MI 작업에서'], ['TR', 0, 1, '새로 조사'], ['US', 0, 1, '새로 조사'], ['IM', 2, 1, 'MI 내용을 요약']],
  bigMi: [['MS', 1, 1, 'MI 작업 2건'], ['TR', 1, 1, 'MI 작업 2건'], ['CB', 1, 1, 'MI 작업에서'], ['US', 1, 1, '인터뷰 자료'], ['CP', 1, 1, 'MI 작업에서'], ['IM', 2, 1, 'MI 내용을 요약']],
  vp: [['CH', 1, 1, 'Storyboard에서'], ['VP', 1, 1, 'Storyboard에서'], ['EF', 2, 1, '유사 사례로 추정']],
  birdseye: [['BV', 1, 1, '조감도 작업에서'], ['ZP', 1, 1, '조감도 작업에서']],
  spaceProducts: [['SM', 1, 1, '조감도 배치안'], ['PI', 1, 3, '공간마다 1장 · 배치안 3곳'], ['BM', 0, 1, '제품 목록으로 계산']],
  solution: [['MGI', 1, 3, '연결된 솔루션'], ['STP', 1, 3, '연결된 솔루션'], ['SA', 1, 1, '솔루션이 2개 이상일 때'], ['KNX', 2, 3, '요구사항에 매장 태블릿'], ['VXT', 0, 3, '솔루션 탐색에서 추가'], ['OP', 0, 1, '시나리오 작업에서']],
  cases: [['CD', 1, 2, '사례마다 1장 · 추천 2건'], ['CL', 0, 1, '사례 검색']],
  why: [['CM', 1, 1, 'MI 경쟁사 분석'], ['ST', 1, 1, 'MI 경쟁사 분석'], ['SV', 2, 1, '서비스 표준 자료']],
  spec: [['SC', 1, 1, 'Spec 시트 작업'], ['SD', 1, 1, '주력 제품마다 1장']],
  spaceScenario: [['VM', 1, 1, '시나리오 · 조감도'], ['SS', 1, 3, '공간마다 1장 · 3곳']],
};

/** 드래그 · 칩 아이콘(SectionStep `ICON`) — 기능 키 · 항목 종류 → 24×24 path */
export const SRC_ICON: Record<string, string> = {
  mi: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2',
  market: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2',
  storyboard: 'M4 5h16v14H4z M4 11h16 M10 11v8',
  birdseye: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 12l8-4.5 M12 12v9 M12 12L4 7.5',
  scenario: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  spec: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7',
  image: 'M4 5h16v14H4z M20 15l-5-5-8 8',
  product: 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z',
  solution: 'M12 3l9 5-9 5-9-5 9-5z M3 13l9 5 9-5',
  case: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z M9 14h6',
  requirements: 'M9 4h6v3H9z M7 5H5v16h14V5h-2 M8 11h8 M8 15h6',
  competitor: 'M4 19V9 M10 19V5 M16 19v-6 M20 19H3',
  vp: 'M12 3l2.5 6H21l-5 4 2 7-6-4-6 4 2-7-5-4h6.5z',
  file: 'M6 3h8l5 5v13H6V3z M14 3v5h5',
};
export const ITEM_LABEL: Record<ItemKind, string> = { product: '제품', solution: '솔루션', image: '이미지', case: '유관 사례' };

/** 기능 코드 ↔ 서비스 키(workspace feature ↔ 반입 source.feature) */
export const FEATURE_KEY: Record<string, string> = {
  RQ: 'requirements', SB: 'storyboard', MI: 'mi', CA: 'competitor', VP: 'vp', SP: 'spec', IMG: 'image', BE: 'birdseye', SC: 'scenario', PR: 'proposal',
};
export const FEATURE_LABEL: Record<string, string> = {
  requirements: '고객 요구사항', storyboard: 'Storyboard', mi: 'Market Intelligence', competitor: '경쟁사 분석', vp: 'Value Proposition', spec: 'Spec 시트',
  image: '이미지 생성', birdseye: '공간 조감도', scenario: '공간 시나리오',
};
