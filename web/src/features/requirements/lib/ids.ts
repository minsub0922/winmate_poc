/** 클라이언트가 만드는 id(`km_<ULID>` · `ri_<ULID>`) — 서버가 그대로 받는다(§6.3). */
const CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';

export function ulid(now = Date.now()): string {
  let time = '';
  let t = now;
  for (let i = 0; i < 10; i++) {
    time = CROCKFORD[t % 32] + time;
    t = Math.floor(t / 32);
  }
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let rnd = '';
  for (let i = 0; i < 16; i++) rnd += CROCKFORD[bytes[i] % 32];
  return time + rnd;
}

export const newId = (prefix: 'km' | 'ri') => `${prefix}_${ulid()}`;
