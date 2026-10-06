/**
 * 셸 ↔ 기능 모듈 계약(HTTP 아님, 00-shell §7.5). 셸 세션(workspace)이 소유한다.
 * 기능 모듈은 web/src/features/<기능>/index.tsx 에서 `export default feature({...})` 만 하면 셸이 자동으로 모은다.
 * 필드는 더하기만 한다(이름 바꾸기 · 지우기 금지).
 */
import type { ReactNode } from 'react';
import type { RouteObject } from 'react-router';

export type FeatureCode = 'RQ' | 'SB' | 'IMG' | 'BE' | 'SC' | 'MI' | 'CA' | 'VP' | 'SP' | 'PR';
/** 끌기 · 추가 유형. 키트(@/ui DragType)와 같은 값 */
export type DragType = 'product' | 'solution' | 'image' | 'case' | 'work_item';

export interface FeatureModule {
  /** workspace feature 값 */
  code: FeatureCode;
  /** 서비스 이름 = URL 첫 조각 (requirements, storyboard, …) */
  key: string;
  /** 사이드바 그룹 이름 · 상단바 section */
  name: string;
  /** 사이드바 순서(00-shell §6.2) */
  order: number;
  /**
   * 홈 카드. 셸 카탈로그(shell/catalog.ts)에 있는 기능 10개는 §5.1.1 고정 문구를 쓰고 이 값은 무시한다(새 기능에만 쓰임).
   */
  home?: { section: 'plan' | 'visual' | 'hero'; title: string; desc: string; feeds?: string; mark?: 'start' | 'new' };
  /** `/<key>` 아래 라우트(index = 작업 목록, 'new' = 새 작업, ':id/*' = 작업물) */
  routes: RouteObject[];
  /**
   * 셸 밖 최상위 경로 — 사이드바 · 상단바 없이, 로그인 확인(AUTH_MODE=local)도 없이 그린다(휴대폰 QR 업로드 등).
   * path 는 `/` 로 시작하는 절대 경로(예: `/m/upload/:token`). 401 이 와도 로그인 화면으로 보내지 않는다.
   * 화면은 셸 맥락(useShellPage)을 불러도 되지만 팝오버 · 상세 시트 · 끌어서 추가는 없다.
   */
  publicRoutes?: RouteObject[];
}

/** 화면이 셸에 넘기는 맥락(00-shell §7.5). 없으면 홈 기본값(hasTask=false). */
export interface ShellPageConfig {
  /** 상단바 브레드크럼 두 번째 조각(기능 이름) */
  section?: string;
  /** 브레드크럼 마지막 조각(작업 제목 · `새 작업` · `작업 목록`) */
  title?: string;
  /**
   * 진행 중인 작업이 있으면 팝오버의 추가가 켜진다. 명시하지 않으면 section 이 있을 때만 true(§5.2.3).
   * 작업 목록 화면은 false 로 명시한다.
   */
  hasTask?: boolean;
  /** 지금 화면에 그 유형을 받는 드롭 영역이 있다 → 팝오버 항목 · 사이드바 항목에 끌기 손잡이가 붙는다 */
  accepts?: DragType[];
  /** accepts 에 'work_item' 이 있을 때 받는 기능(없으면 모든 기능). 예: 제안서 MI 섹션 = ['MI'] */
  acceptsWork?: FeatureCode[];
  /** 이미 추가된 참조(팝오버에서 '✓ 추가됨' 표시) — `kb:model:mdl_…` 등 */
  added?: string[];
  /** `현재 작업에 추가` · 시트 `현재 작업에 추가`·`작업에 추가`. 없으면 추가 버튼은 꺼진다(Q-UI-7). */
  onAdd?: (type: DragType, refs: string[]) => Promise<{ added: string[] }> | { added: string[] };
  /** onAdd 가 처리하는 유형(없으면 4종 모두) */
  addable?: DragType[];
  /** `대화에 첨부` · `{N}장 대화에 첨부` — 출처 메타데이터(ImageMeta: source_page · original_url · usage_note …)가 함께 온다 */
  onAttach?: (images: Array<Record<string, unknown>>) => void | Promise<void>;
  stepper?: StepperConfig;
  /** 사이드바에서 펼쳐 둘 그룹(기능 key). 없으면 현재 라우트의 기능 */
  sidebarGroup?: string;
  /** 팝오버 기본값에 쓰는 작업 정보(유관 사례 업종 · 제품 필터) */
  taskContext?: TaskContext;
}

export interface TaskContext {
  /** KB 업종 id(`kr_retail_fnb` …) — 유관 사례 검색의 기본 업종 */
  verticalId?: string;
  verticalName?: string;
  /** 현재 작업의 제품 · 솔루션(유관 사례 `제품:` 메뉴) — ref 는 `kb:family:fam_…` · `kb:solution:…` */
  products?: Array<{ ref: string; label: string }>;
}

export interface StepperPlanRow { label: string; note: string }

/** 스텝바(00-shell §5.11) */
export interface StepperConfig {
  steps: string[];
  /** 1부터 */
  current: number;
  /** 전부 끝남(모든 단계 done) */
  complete?: boolean;
  /** 이 단계부터 딸깍이 자동으로 채움(0 = 없음) */
  autoFrom?: number;
  /** 자동으로 끝난 단계(1부터) — autoFrom 과 함께 쓸 수 있다 */
  auto?: number[];
  /** 있으면 단계를 누를 수 있다(보드는 클릭 불가 — Q-UI-6) */
  onStep?: (index: number) => void;
  /** 딸깍 버튼(제안서만). onRun 은 `딸깍, 완성하기` 에서 한 번 불린다 */
  oneClick?: { label?: string; onRun: (opts: { markInferred: boolean; collectReview: boolean }) => void; disabled?: boolean; running?: boolean };
  /** 딸깍 팝오버를 열린 채로 */
  oneClickOpen?: boolean;
  /** 딸깍 팝오버 `확정된 내용` 칩(기본: 현재 단계 앞 단계들) */
  planConfirmed?: string[];
  /** `딸깍이 추론해 채울 부분` 행(기본: 현재 단계부터) */
  planRows?: StepperPlanRow[];
  /** 오른쪽 요약(기본 `남은 {n}단계`) */
  planSummary?: string;
  /** 스텝바 오른쪽에 둘 요소 */
  right?: ReactNode;
}

/**
 * 셸이 기능 화면에 주는 참조 문자열 형식:
 * kb:model:<mdl_id> · kb:family:<fam_id> · kb:solution:<catalog id> · kb:image:<img_id> · kb:case:<dep_id> · ws:item:<id> · img:image:<id> · custom:<글>
 */
export type Ref = string;
