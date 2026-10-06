/**
 * 오류 경계 화면 — 기능 하나가 깨져도 앱 전체가 빈 화면이 되지 않게(proposal-web 요청).
 *
 * - `FeatureLoadFailed`: 기능 모듈 import 가 실패(없는 파일 · 문법 오류 · 빈 모듈) — 그 기능 경로 전체.
 * - `FeatureError`: 기능 화면을 그리다 오류(라우트 errorElement) — 셸(사이드바 · 상단바)은 그대로, 본문만.
 * - `RootError`: 셸 자체 오류(최상위) · `PublicError`: 셸 밖 경로(휴대폰 업로드 · 로그인) 오류.
 */
import { useState } from 'react';
import { isRouteErrorResponse, Link, useRouteError } from 'react-router';
import { Button, Icon } from '@/ui';
import { shellFeatureByKey } from './catalog';
import { useShellPage } from './ShellContext';

function messageOf(err: unknown): string {
  if (isRouteErrorResponse(err)) return `${err.status} ${err.statusText}`;
  if (err instanceof Error) return err.message || err.name;
  if (typeof err === 'string') return err;
  try { return JSON.stringify(err); } catch { return String(err); }
}

function stackOf(err: unknown): string | null {
  return err instanceof Error && err.stack ? err.stack.split('\n').slice(0, 8).join('\n') : null;
}

export function ErrorPanel({ title, sub, error, home = true, retryLabel = '다시 시도', onRetry, compact }:
  { title: string; sub?: string; error?: unknown; home?: boolean; retryLabel?: string; onRetry?: () => void; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const msg = error !== undefined ? messageOf(error) : null;
  const stack = error !== undefined ? stackOf(error) : null;
  return (
    <div className={compact ? 'sh-error sh-error--compact' : 'sh-error'} role="alert" data-shell-error="">
      <span className="sh-error__icon" aria-hidden="true"><Icon name="warn" size={20} strokeWidth={2.2} /></span>
      <h1 className="sh-error__title">{title}</h1>
      {sub && <p className="sh-error__sub">{sub}</p>}
      <div className="sh-error__acts">
        <Button h={38} variant="primary" onClick={onRetry ?? (() => window.location.reload())}>{retryLabel}</Button>
        {home && <Link to="/" className="wm-btn wm-btn--h38">홈으로</Link>}
      </div>
      {msg && (
        <div className="sh-error__detail">
          <button type="button" className="sh-error__toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            <Icon name={open ? 'chevronDown' : 'chevronRight'} size={12} strokeWidth={2.4} />자세한 오류
          </button>
          {open && <pre className="sh-error__pre">{stack && stack.includes(msg) ? stack : [msg, stack].filter(Boolean).join('\n\n')}</pre>}
        </div>
      )}
    </div>
  );
}

/** 기능 모듈을 불러오지 못함(그 기능 경로 전체) */
export function FeatureLoadFailed({ featureKey, error }: { featureKey: string; error?: unknown }) {
  const f = shellFeatureByKey(featureKey);
  const name = f?.name ?? featureKey;
  useShellPage({ section: name, title: '불러오지 못함', hasTask: false, sidebarGroup: featureKey });
  return (
    <ErrorPanel title="이 기능을 불러오지 못했어요" error={error}
      sub={`「${name}」 화면 코드를 불러오는 중 문제가 생겼어요. 다른 기능은 그대로 쓸 수 있어요. 잠시 뒤 다시 시도해 주세요.`} />
  );
}

/** 기능 화면을 그리다 오류(기능 라우트 errorElement) */
export function FeatureError({ featureKey }: { featureKey: string }) {
  const error = useRouteError();
  const f = shellFeatureByKey(featureKey);
  const name = f?.name ?? featureKey;
  const notFound = isRouteErrorResponse(error) && error.status === 404;
  useShellPage({ section: name, title: notFound ? '찾을 수 없음' : '오류', hasTask: false, sidebarGroup: featureKey });
  if (notFound) return <ErrorPanel title="페이지를 찾을 수 없어요" sub="주소가 바뀌었거나 지워진 화면이에요." retryLabel="새로 고침" />;
  return (
    <ErrorPanel title="화면을 그리다 문제가 생겼어요" error={error}
      sub={`「${name}」 화면에서 오류가 났어요. 다른 기능과 사이드바는 그대로 쓸 수 있어요.`} />
  );
}

/** 셸(레이아웃) 자체 오류 — 사이드바 없이 전체 화면 */
export function RootError() {
  const error = useRouteError();
  return (
    <div className="sh-error-page">
      <ErrorPanel title="화면을 그리다 문제가 생겼어요" sub="새로 고치면 대부분 해결돼요. 계속되면 관리자에게 알려 주세요." error={error} retryLabel="새로 고침" />
    </div>
  );
}

/** 셸 밖 경로(휴대폰 업로드 · 로그인) 오류 — 홈 링크 없이 */
export function PublicError() {
  const error = useRouteError();
  return (
    <div className="sh-error-page">
      <ErrorPanel title="화면을 그리다 문제가 생겼어요" sub="새로 고쳐 다시 열어 주세요." error={error} retryLabel="새로 고침" home={false} />
    </div>
  );
}
