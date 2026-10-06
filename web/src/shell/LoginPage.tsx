/**
 * 로그인 화면 `/login?next=` (AUTH_MODE=local) — 셸 밖(사이드바 없음). 보드에 없는 화면이라 셸 모양(로고 · 토큰 · 버튼)을 그대로 쓴다 [제안].
 * 로그인하면 쿼리 캐시를 비우고(다른 사용자 데이터가 남지 않게) `next` 로 돌아간다. 이미 로그인돼 있거나 AUTH_MODE=none 이면 바로 `next`.
 */
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { Button, Icon, Notice } from '@/ui';
import { AUTH_ME_KEY, login, safeNext, useAuthMe } from './auth';
import './shell.css';

export function LoginPage() {
  const [params] = useSearchParams();
  const next = safeNext(params.get('next'));
  const me = useAuthMe();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [caps, setCaps] = useState(false);
  const userRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const prev = document.title;
    document.title = '로그인 · Winmate';
    return () => { document.title = prev; };
  }, []);

  if (me.isPending) return <div className="sh-authwait" aria-busy="true" aria-label="로그인 확인 중" />;
  if (me.data) return <Navigate to={next} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const u = username.trim();
    if (!u) { setError('아이디를 입력해 주세요'); userRef.current?.focus(); return; }
    if (!password) { setError('비밀번호를 입력해 주세요'); passRef.current?.focus(); return; }
    setBusy(true);
    setError(null);
    try {
      const who = await login(u, password);
      qc.clear();
      qc.setQueryData(AUTH_ME_KEY, who);
      nav(next, { replace: true });
    } catch (err) {
      setBusy(false);
      setPassword('');
      if (err instanceof ApiError && err.status === 401) setError('아이디 또는 비밀번호가 맞지 않습니다');
      else if (err instanceof ApiError && err.status === 429) setError('로그인 시도가 너무 많아요. 잠시 뒤 다시 해 주세요.');
      else if (err instanceof ApiError) setError(err.message || '로그인하지 못했어요. 잠시 뒤 다시 해 주세요.');
      else setError('서버에 연결하지 못했어요. 잠시 뒤 다시 해 주세요.');
      passRef.current?.focus();
    }
  };
  const onPassKey = (e: KeyboardEvent<HTMLInputElement>) => setCaps(!!e.getModifierState?.('CapsLock'));

  return (
    <main className="sh-login" aria-labelledby="sh-login-title">
      <form className="sh-login__card" onSubmit={submit} noValidate>
        <div className="sh-login__logo" aria-hidden="true">
          <span className="sh-logo__w">W</span>
          <span className="sh-logo__name">winmate</span>
        </div>
        <div className="sh-login__head">
          <h1 id="sh-login-title" className="sh-login__title">로그인</h1>
          <p className="sh-login__sub">사내 계정으로 로그인해 주세요.</p>
        </div>
        {next !== '/' && !error && <Notice>로그인하면 보던 화면으로 돌아가요.</Notice>}
        {error && <Notice tone="danger">{error}</Notice>}
        <label className="sh-login__field">
          <span>아이디</span>
          <input ref={userRef} className="wm-input" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} autoFocus
            value={username} onChange={(e) => setUsername(e.target.value)} disabled={busy} aria-invalid={!!error && !username.trim()} />
        </label>
        <label className="sh-login__field">
          <span>비밀번호</span>
          <input ref={passRef} className="wm-input" name="password" type="password" autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)} onKeyUp={onPassKey} onKeyDown={onPassKey} disabled={busy}
            aria-describedby={caps ? 'sh-login-caps' : undefined} />
          {caps && <small id="sh-login-caps" className="sh-login__caps"><Icon name="warn" size={12} strokeWidth={2.4} />Caps Lock 이 켜져 있어요</small>}
        </label>
        <Button type="submit" h={44} variant="primary" block disabled={busy} aria-busy={busy || undefined}>
          {busy ? '로그인 중…' : '로그인'}
        </Button>
        <p className="sh-login__foot">계정이 없거나 비밀번호를 잊었으면 관리자에게 요청해 주세요.</p>
      </form>
    </main>
  );
}

export default LoginPage;
