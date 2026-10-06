/**
 * proposal 호출 결과 → 값 또는 ApiError. 호출은 `api.proposal`(openapi-fetch, 계약 타입) — proposal.ts.
 * 오류 봉투(ARCHITECTURE §3) `{error: {code, message, details}}`. 아직 구현 전인 경로는 `501 NOT_IMPLEMENTED`(또는 FastAPI 기본 404) → `isMissing`.
 */
import { ApiError } from '@/api/client';

export const ROUTE_MISSING = 'ROUTE_MISSING';

export async function call<T>(p: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  let res: { data?: T; error?: unknown; response: Response };
  try { res = await p; } catch { throw new ApiError(0, 'NETWORK', '서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요'); }
  const { response } = res;
  if (!response.ok) {
    const body = (res.error ?? {}) as { error?: { code?: string; message?: string; details?: Record<string, unknown> }; detail?: unknown };
    if (body.error?.code) throw new ApiError(response.status, body.error.code, body.error.message ?? response.statusText, body.error.details ?? {});
    if (response.status === 404 || response.status === 405) throw new ApiError(response.status, ROUTE_MISSING, '아직 준비 중인 기능이에요');
    if (response.status === 422) throw new ApiError(422, 'VALIDATION', '입력 값을 확인해 주세요', { detail: body.detail });
    throw new ApiError(response.status, 'ERROR', response.statusText || '오류');
  }
  return (res.data ?? null) as T;
}

export const isApiError = (e: unknown, code?: string): e is ApiError => e instanceof ApiError && (!code || e.code === code);
/** 서버가 아직 그 기능을 준비하지 못함(구현 전 · 경로 없음 · 서비스 꺼짐) */
export const isMissing = (e: unknown) =>
  isApiError(e) && (e.code === ROUTE_MISSING || e.code === 'NOT_IMPLEMENTED' || e.status === 501 || e.status === 503 || e.code === 'UPSTREAM_UNAVAILABLE');

/** §6.15 오류 코드 → 화면 문구(서버 한국어 메시지가 있으면 그대로) */
const FALLBACK: Record<string, string> = {
  PROPOSAL_NOT_FOUND: '제안서를 찾을 수 없어요',
  SHEET_NOT_FOUND: '제안서를 찾을 수 없어요',
  VERSION_NOT_FOUND: '제안서를 찾을 수 없어요',
  REV_CONFLICT: '다른 화면에서 바뀐 내용이 있어 새로 불러왔어요',
  JOB_ALREADY_RUNNING: '이미 진행 중이에요',
  MUST_CONFIRM_PENDING: '필수 확인을 마치면 활성화',
  UNDO_CONFLICT: '그 뒤에 바뀐 내용이 있어 되돌릴 수 없어요. 버전 · 변경 이력에서 되돌려 주세요',
  FILE_TOO_LARGE: '파일당 50MB까지 올릴 수 있어요',
  UNSUPPORTED_FILE_TYPE: 'PPTX · PDF만 올릴 수 있어요',
  BORROW_MODE_CONTENT_HIDDEN: '흐름 차용 모드에선 원본 내용을 보여주지 않아요',
  POLICY_CONFIDENTIAL: '기밀 자료라 지금 설정된 모델로는 분석할 수 없어요',
  INVALID_HEX: '#RRGGBB 형식으로 넣어 주세요',
  INVALID_SHEET_RANGE: '시트 범위를 확인해 주세요 (예: 01–07, 21)',
  DROP_NOT_ACCEPTED: '이 섹션에는 놓을 수 없는 자료예요',
  UPSTREAM_UNAVAILABLE: '연결된 서비스가 응답하지 않아요. 잠시 후 다시 시도해 주세요',
  NOT_IMPLEMENTED: '아직 준비 중인 기능이에요',
  ROUTE_MISSING: '아직 준비 중인 기능이에요',
  NETWORK: '서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요',
};
export function errText(e: unknown, fallback = '잠시 후 다시 시도해 주세요'): string {
  if (e instanceof ApiError) {
    if (e.code === 'POLICY_CONFIDENTIAL') return FALLBACK.POLICY_CONFIDENTIAL;
    if (e.message && !['ERROR', ROUTE_MISSING, 'NETWORK', 'VALIDATION'].includes(e.code) && /[가-힣]/.test(e.message)) return e.message;
    return FALLBACK[e.code] ?? fallback;
  }
  return fallback;
}
/** 잡 오류(이벤트 data · 잡 스냅숏 error) → 문구 */
export function jobErrText(err: { code?: string; message?: string } | null | undefined, fallback = '작업을 마치지 못했어요. 다시 시도해 주세요'): string {
  if (!err) return fallback;
  if (err.code === 'POLICY_CONFIDENTIAL') return FALLBACK.POLICY_CONFIDENTIAL;
  if (err.message && /[가-힣]/.test(err.message)) return err.message;
  return (err.code && FALLBACK[err.code]) || fallback;
}
export { ApiError };
