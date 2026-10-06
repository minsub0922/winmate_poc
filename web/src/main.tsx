import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router';
import '@/ui';
import { ApiError, installAuthGuard } from '@/api/client';
import { createAppRouter } from './App';
import { loadFeatures } from './shell/registry';
import { ShellProvider } from './shell/ShellContext';
import { AUTH_ME_KEY, fetchAuthMe } from './shell/auth';

// 401(로그인 필요)은 다시 시도하지 않는다 — 셸이 로그인 화면으로 보낸다(shell/auth.tsx)
const retry = (n: number, e: unknown) => n < 1 && !(e instanceof ApiError && e.status === 401);
const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 15_000, retry, refetchOnWindowFocus: false } } });

// 기능 화면이 fetch('/api/…') 를 바로 불러도 401 이면 셸이 알 수 있게(@/api/client)
installAuthGuard();
const root = createRoot(document.getElementById('root')!);

// 로그인 확인(AuthGate)을 기능 모듈과 함께 미리 시작한다(셸 밖 경로에서도 무해)
if (!/^\/m\//.test(window.location.pathname)) void qc.prefetchQuery({ queryKey: AUTH_ME_KEY, queryFn: fetchAuthMe, staleTime: 5 * 60_000 });

// 기능 모듈을 따로 불러온다(하나가 깨져도 나머지는 뜬다 — shell/registry.ts). 다 끝나면(성공 · 실패 모두) 라우터를 만든다.
void loadFeatures().then(() => {
  const router = createAppRouter();
  root.render(
    <StrictMode>
      <QueryClientProvider client={qc}>
        <ShellProvider>
          <RouterProvider router={router} />
        </ShellProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
});
