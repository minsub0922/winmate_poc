import type { FeatureModule } from './types';

/** 기능 모듈 정의 도우미(타입 검사용). */
export function feature(m: FeatureModule): FeatureModule {
  return m;
}
