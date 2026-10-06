/**
 * 서비스별 타입 클라이언트(openapi-fetch). 타입은 contracts/*.json 에서 생성(`npm run gen:api`).
 *
 *   import { api, unwrap } from '@/api/client';
 *   const data = unwrap(await api.kb.GET('/v1/info'));
 *
 * 브라우저는 게이트웨이(/api/<서비스>)로만 부른다.
 */
import createClient, { type Middleware } from 'openapi-fetch';
import type { paths as AiTools } from './gen/ai-tools';
import type { paths as Birdseye } from './gen/birdseye';
import type { paths as Competitor } from './gen/competitor';
import type { paths as Export } from './gen/export';
import type { paths as Files } from './gen/files';
import type { paths as Gateway } from './gen/gateway';
import type { paths as Image } from './gen/image';
import type { paths as Jobs } from './gen/jobs';
import type { paths as Kb } from './gen/kb';
import type { paths as Mi } from './gen/mi';
import type { paths as Proposal } from './gen/proposal';
import type { paths as Requirements } from './gen/requirements';
import type { paths as Scenario } from './gen/scenario';
import type { paths as Spec } from './gen/spec';
import type { paths as Storyboard } from './gen/storyboard';
import type { paths as Vp } from './gen/vp';
import type { paths as Workspace } from './gen/workspace';

// ── 로그인 필요(401) 처리 ───────────────────────────────
// AUTH_MODE=local 에서 세션이 없거나 끝나면 게이트웨이가 401 `UNAUTHENTICATED` 를 준다. 여기서 받아 셸(AuthGate)에 알리면
// 셸이 `/login?next=<지금 화면>` 으로 보낸다. 로그인 API(`/api/_auth/…`)의 401 은 알리지 않는다(로그인 화면 · 확인용).
// 셸 밖 경로(휴대폰 업로드)는 셸이 처리기를 등록하지 않으므로 로그인 화면으로 가지 않는다.

export interface UnauthorizedInfo {
  url: string;
  status: number;
}
type UnauthorizedHandler = (info: UnauthorizedInfo) => void;
const unauthorizedHandlers = new Set<UnauthorizedHandler>();
const reported = new WeakSet<object>();

/** 401(로그인 필요)을 받았을 때 부를 함수를 등록한다. 돌려준 함수로 해제한다. */
export function onUnauthorized(fn: UnauthorizedHandler): () => void {
  unauthorizedHandlers.add(fn);
  return () => { unauthorizedHandlers.delete(fn); };
}

function pathOf(url: string): string {
  try { return new URL(url, typeof window !== 'undefined' ? window.location.href : 'http://x').pathname; } catch { return url; }
}

/** 로그인 API 자체(`/api/_auth/login|logout|me`) — 401 이어도 알리지 않는다 */
export const isAuthApi = (url: string) => pathOf(url).startsWith('/api/_auth/');

/** 응답이 401 이고 우리 API(`/api/…`, 로그인 API 제외)면 셸에 알린다. 같은 응답은 한 번만. */
export function reportUnauthorized(res: { status: number } | null | undefined, url: string): void {
  if (!res || res.status !== 401) return;
  if (typeof res === 'object') {
    if (reported.has(res)) return;
    reported.add(res);
  }
  const p = pathOf(url);
  if (!p.startsWith('/api/') || isAuthApi(url)) return;
  for (const fn of [...unauthorizedHandlers]) {
    try { fn({ url: p, status: 401 }); } catch { /* 처리기 오류는 무시 */ }
  }
}

let lastProbe = 0;
/** 지금 로그인 상태를 묻고(게이트웨이 `/api/_auth/me`) 401 이면 셸에 알린다 — SSE(EventSource)처럼 상태 코드를 못 보는 연결이 끊겼을 때. 2초에 한 번만. */
export async function probeAuth(): Promise<boolean> {
  const now = Date.now();
  if (now - lastProbe < 2000) return true;
  lastProbe = now;
  try {
    const r = await fetch('/api/_auth/me', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    if (r.status === 401) {
      for (const fn of [...unauthorizedHandlers]) {
        try { fn({ url: '/api/_auth/me', status: 401 }); } catch { /* 무시 */ }
      }
      return false;
    }
    return true;
  } catch {
    return true; // 네트워크 오류는 로그인 문제가 아니다
  }
}

let guardInstalled = false;
/**
 * 전역 감시(한 번만 설치) — 기능 화면이 `fetch('/api/…')` · `new EventSource('/api/…')` 를 바로 써도 401 이면 셸에 알린다.
 * fetch 응답은 그대로 돌려준다(본문을 읽지 않는다). EventSource 는 연결이 아주 끊기면(CLOSED) `/api/_auth/me` 로 확인한다. main.tsx 가 처음에 설치한다.
 */
export function installAuthGuard(): void {
  if (guardInstalled || typeof window === 'undefined' || typeof window.fetch !== 'function') return;
  guardInstalled = true;
  const orig = window.fetch.bind(window);
  const guarded: typeof window.fetch = (input, init) => orig(input, init).then((res) => {
    if (res.status === 401) {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
      reportUnauthorized(res, url);
    }
    return res;
  });
  window.fetch = guarded;
  const OrigES = window.EventSource;
  if (typeof OrigES === 'function') {
    class GuardedEventSource extends OrigES {
      constructor(url: string | URL, init?: EventSourceInit) {
        super(url, init);
        const p = pathOf(String(url));
        if (!p.startsWith('/api/') || isAuthApi(p)) return;
        this.addEventListener('error', (ev) => {
          if (!(ev instanceof MessageEvent) && this.readyState === OrigES.CLOSED) void probeAuth();
        });
      }
    }
    window.EventSource = GuardedEventSource;
  }
}

/** openapi-fetch 클라이언트용 — 401 이면 셸에 알린다 */
const authMiddleware: Middleware = {
  onResponse({ request, response }) {
    if (response.status === 401) reportUnauthorized(response, request.url);
    return undefined;
  },
};

const mk = <P extends {}>(svc: string) => {
  const c = createClient<P>({ baseUrl: `/api/${svc}`, credentials: 'same-origin' });
  c.use(authMiddleware);
  return c;
};

export const api = {
  gateway: createClient<Gateway>({ baseUrl: '', credentials: 'same-origin' }),
  'ai-tools': mk<AiTools>('ai-tools'),
  kb: mk<Kb>('kb'),
  files: mk<Files>('files'),
  jobs: mk<Jobs>('jobs'),
  workspace: mk<Workspace>('workspace'),
  export: mk<Export>('export'),
  requirements: mk<Requirements>('requirements'),
  storyboard: mk<Storyboard>('storyboard'),
  mi: mk<Mi>('mi'),
  competitor: mk<Competitor>('competitor'),
  vp: mk<Vp>('vp'),
  spec: mk<Spec>('spec'),
  image: mk<Image>('image'),
  birdseye: mk<Birdseye>('birdseye'),
  scenario: mk<Scenario>('scenario'),
  proposal: mk<Proposal>('proposal'),
};

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) {
    super(message);
  }
}

/** openapi-fetch 결과에서 data 를 꺼내고, 오류면 ApiError 를 던진다. */
export function unwrap<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (res.error !== undefined || !res.response.ok) {
    const body = (res.error ?? {}) as Partial<ApiErrorBody>;
    throw new ApiError(res.response.status, body.error?.code ?? 'ERROR', body.error?.message ?? res.response.statusText, body.error?.details ?? {});
  }
  return res.data as T;
}

/** 파일 업로드(files 서비스, multipart). */
export async function uploadFile(file: File, opts: { confidential?: boolean; projectId?: string; purpose?: string } = {}) {
  const fd = new FormData();
  fd.append('file', file);
  if (opts.confidential !== undefined) fd.append('confidential', String(opts.confidential));
  if (opts.projectId) fd.append('project_id', opts.projectId);
  if (opts.purpose) fd.append('purpose', opts.purpose);
  const r = await fetch('/api/files/v1/files', { method: 'POST', body: fd, credentials: 'same-origin' });
  reportUnauthorized(r, '/api/files/v1/files');
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, body?.error?.code ?? 'ERROR', body?.error?.message ?? r.statusText, body?.error?.details);
  return body as { id: string; name: string; mime: string; size: number; [k: string]: unknown };
}

/** 파일 내용 URL(이미지 src 등). */
export const fileUrl = (fileId: string) => `/api/files/v1/files/${fileId}/content`;
export const fileThumbUrl = (fileId: string, w = 320) => `/api/files/v1/files/${fileId}/thumbnail?w=${w}`;
