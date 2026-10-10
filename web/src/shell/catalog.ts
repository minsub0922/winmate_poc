/**
 * 기능 11개 카탈로그(00-shell §6.2 · §5.1.1) — 사이드바 순서 · 이름 · 아이콘 · 홈 카드 문구의 단일 원천.
 * 기능 모듈(registry)은 라우트를 주고, 이름·문구는 여기 값을 쓴다(보드 원문 고정). 카탈로그에 없는 기능은 모듈 값을 쓴다.
 */
import { features, registryVersion } from './registry';
import type { FeatureCode, FeatureModule } from './types';

export interface HomeCard {
  section: 'plan' | 'visual' | 'hero';
  title: string;
  desc: string;
  /** 결과가 들어가는 곳(카드 아래 화살표 줄) */
  feeds?: string;
  mark?: 'start' | 'new';
}

export interface CatalogEntry {
  code: FeatureCode;
  /** 서비스 이름 = URL 첫 조각 */
  key: string;
  /** 보드 사이드바 key(market · value 등) */
  boardKey: string;
  /** 사이드바 그룹 · 상단바 section 이름 */
  name: string;
  order: number;
  home: HomeCard;
}

export const CATALOG: CatalogEntry[] = [
  { code: 'RQ', key: 'requirements', boardKey: 'requirements', name: '고객 요구사항', order: 1,
    home: { section: 'plan', title: '고객 요구사항', desc: '요청서 · 회의록 · 메모를 넣으면 요구사항 정의서로 정리해 드려요.', feeds: '모든 콘텐츠가 함께 써요', mark: 'start' } },
  { code: 'SB', key: 'storyboard', boardKey: 'storyboard', name: '전략 수립 Storyboard', order: 2,
    home: { section: 'plan', title: '전략 수립 Storyboard', desc: '요구사항을 기획 방향 · 목차 · 요구 추적표로 바꿔요.', feeds: '제안서 목차 · 뼈대' } },
  { code: 'DS', key: 'dss', boardKey: 'dss', name: '공간별 제품 매칭 DSS', order: 3,
    home: { section: 'plan', title: '공간별 제품 매칭 DSS', desc: '업종 · 공간을 정하고 공간마다 제품 · 솔루션을 골라요.', feeds: '공간 시나리오 · Spec 시트' } },
  { code: 'IMG', key: 'image', boardKey: 'image', name: '이미지 생성', order: 9,
    home: { section: 'visual', title: '이미지 생성', desc: '제안에 쓸 공간 · 배경 · 시나리오 이미지를 만들어요.', feeds: '표지 · 시트 이미지' } },
  { code: 'BE', key: 'birdseye', boardKey: 'birdseye', name: '공간 조감도 생성', order: 10,
    home: { section: 'visual', title: '공간 조감도 생성', desc: '공간 → 제품 → 배치 순서로 3D 조감도를 만들어요.', feeds: '조감도 섹션' } },
  { code: 'SC', key: 'scenario', boardKey: 'scenario', name: '공간 시나리오 생성', order: 8,
    home: { section: 'visual', title: '공간 시나리오 생성', desc: '고객 공간에서 제품과 솔루션이 쓰이는 장면을 그려요.', feeds: '공간 시나리오 섹션' } },
  { code: 'MI', key: 'mi', boardKey: 'market', name: 'Market Intelligence', order: 4,
    home: { section: 'plan', title: 'Market Intelligence', desc: '시장 · 고객사 · 사용자를 분석해 삼성의 강점을 찾아요.', feeds: '제안서 MI 섹션' } },
  { code: 'CA', key: 'competitor', boardKey: 'competitor', name: '경쟁사 분석', order: 5,
    home: { section: 'plan', title: '경쟁사 분석', desc: '고객 요구사항이나 한 문단 메모로 경쟁사를 찾고 삼성과 비교해요.', feeds: 'MI · Why Samsung 시트', mark: 'new' } },
  { code: 'VP', key: 'vp', boardKey: 'value', name: 'Value Proposition', order: 6,
    home: { section: 'plan', title: 'Value Proposition', desc: '고객 과제 → 가치 → 기대 효과로 핵심 메시지를 세워요.', feeds: '제안서 Value Props 섹션' } },
  { code: 'SP', key: 'spec', boardKey: 'spec', name: 'Spec 시트 생성', order: 7,
    home: { section: 'plan', title: 'Spec 시트 생성', desc: '제품을 골라 비교 가능한 스펙 시트를 만들어요.', feeds: '제안서 제품 스펙 섹션' } },
  { code: 'PR', key: 'proposal', boardKey: 'proposal', name: 'B2B 제안서 생성', order: 11,
    home: { section: 'hero', title: 'B2B 제안서 만들기', desc: '유형을 고르고 섹션별로 채우면 PPTX까지 완성돼요. 요구사항 정의서가 있으면 고객 정보는 자동으로 들어가요.' } },
];

/** 기획·분석 카드 순서(§5.1.1 표 — 사이드바 순서와 다르다) */
export const PLAN_ORDER: FeatureCode[] = ['RQ', 'SB', 'DS', 'MI', 'CA', 'VP', 'SP'];
export const VISUAL_ORDER: FeatureCode[] = ['IMG', 'BE', 'SC'];

export interface ShellFeature extends CatalogEntry {
  module?: FeatureModule;
  listRoute: string;
  newRoute: string;
}

const toShell = (c: CatalogEntry, m?: FeatureModule): ShellFeature => ({ ...c, module: m, listRoute: `/${c.key}`, newRoute: `/${c.key}/new` });

let shellCache: ShellFeature[] | null = null;
let shellCacheVersion = -1;

/**
 * 사이드바 · 홈이 쓰는 기능 목록: 카탈로그 10개(순서 고정) + 카탈로그에 없는 등록 모듈.
 * 처음 쓸 때 계산하고, 기능 모듈을 (다시) 불러오면(registryVersion) 새로 계산한다. 불러오지 못한 기능도 카탈로그 항목은 그대로 보인다.
 */
export function shellFeatures(): ShellFeature[] {
  if (!shellCache || shellCacheVersion !== registryVersion()) {
    shellCacheVersion = registryVersion();
    shellCache = [
      ...[...CATALOG].sort((a, b) => a.order - b.order).map((c) => toShell(c, features.find((m) => m.key === c.key))),
      ...features.filter((m) => !CATALOG.some((c) => c.key === m.key)).map((m) => toShell({
        code: m.code, key: m.key, boardKey: m.key, name: m.name, order: m.order,
        home: m.home ?? { section: 'plan', title: m.name, desc: '' },
      }, m)),
    ];
  }
  return shellCache;
}

/** `shellFeatures()` 와 같은 목록(예전 이름 — 처음 쓸 때 계산하는 배열 대리 객체). 새 코드는 `shellFeatures()`. */
export const SHELL_FEATURES: ShellFeature[] = new Proxy([] as ShellFeature[], {
  get(_t, p) {
    const a = shellFeatures();
    const v = Reflect.get(a, p, a);
    return typeof v === 'function' ? v.bind(a) : v;
  },
  has: (_t, p) => Reflect.has(shellFeatures(), p),
  ownKeys: () => Reflect.ownKeys(shellFeatures()),
  getOwnPropertyDescriptor: (_t, p) => Reflect.getOwnPropertyDescriptor(shellFeatures(), p),
});

export const shellFeatureByKey = (key?: string | null) => shellFeatures().find((f) => f.key === key);
export const shellFeatureByCode = (code?: string | null) => shellFeatures().find((f) => f.code === code);
/** 기능 이름(사이드바 · 최근 작업 `{기능명}`) */
export const featureName = (code?: string | null) => shellFeatureByCode(code)?.name ?? code ?? '';
