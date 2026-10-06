/**
 * 셸 공개 API — 기능 모듈이 쓰는 것만 모았다. 기존 경로(`@/shell/feature`, `@/shell/ShellContext`, `@/shell/types`)도 그대로 쓸 수 있다.
 * 사용법: web/src/ui/README.md 「셸 API」.
 */
export { feature } from './feature';
export { useShell, useShellPage, ShellProvider } from './ShellContext';
export type { FeatureModule, ShellPageConfig, StepperConfig, StepperPlanRow, TaskContext, DragType, FeatureCode, Ref } from './types';
export { features, featureByKey, featureByCode, failedFeatures, featureLoadFailure } from './registry';
export type { FeatureLoadFailure } from './registry';
export { useAuthMe, fetchAuthMe, logout, safeNext, loginHref } from './auth';
export type { AuthMe } from './auth';
export { ErrorPanel } from './errors';
export { CATALOG, SHELL_FEATURES, shellFeatures, featureName, shellFeatureByKey, shellFeatureByCode } from './catalog';
export type { CatalogEntry, ShellFeature, HomeCard } from './catalog';
export { FeatureIcon, FEATURE_ICON, SOLUTION_ICON, solutionIconPath, TopBarIcon } from './icons';
export { detailHref, useOpenDetail, useOpenPopover } from './DetailSheet';
export { useShellUrl, parseDetail, detailSearch } from './urlState';
export type { PopoverKind, DetailKind } from './urlState';
export {
  kb, kbGet, getJson, ref, parseRef, modelName, seriesCode, imageKindLabel, imageSrc, imageAlt, usageNotePopover, usageNoteSheet,
  useKbMeta, useCategories, useFamilies, useModels, useModel, useModelImages, useModelCases, useSolutions, useSolution, useSolutionImages,
  useSolutionCases, useImageSearch, useImageSearchPages, useImageMeta, useCaseSearch, useCaseSearchPages, useVerticals, useMyImages, useMyImageInfo,
} from './kb';
export type * from './kbTypes';
export {
  useMe, useItemCounts, useFeatureItems, useRecentItems, useAssetUsage, usageText, useNotificationCounts, useNotifications, markNotificationsRead, useUsers,
} from './workspace';
export type { WsMe, WsItem, WsFeatureCount, WsNotification, WsNotificationCounts, WsUser } from './workspace';
export { WorkListPage } from './WorkListPage';
