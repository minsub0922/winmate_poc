/**
 * pm2 프로세스 정의 — config/services.yaml 에서 만든다(포트·워커 여부의 단일 원천).
 *
 *   make up            # 전체(redis + 서비스 + 워커)
 *   WINMATE_ONLY=gateway,kb,ai-tools make up    # 일부만
 *
 * 환경 변수
 *   WINMATE_VENV_BIN   파이썬 가상환경 bin (기본 <루트>/.venv/bin)
 *   REDIS_MANAGED=0    Redis 를 pm2 가 띄우지 않음(시스템 서비스로 따로 운영할 때)
 *   REDIS_SERVER_BIN   redis-server(또는 valkey-server) 경로
 *   WINMATE_WEB_DEV=1  Vite 개발 서버(5001)도 함께
 */
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const ROOT = path.resolve(__dirname, '..', '..');
const reg = yaml.load(fs.readFileSync(path.join(ROOT, 'config', 'services.yaml'), 'utf8'));
const VENV_BIN = process.env.WINMATE_VENV_BIN || path.join(ROOT, '.venv', 'bin');
const LOG_DIR = path.join(ROOT, 'data', 'logs');
const REDIS_DIR = path.join(ROOT, 'data', 'redis');
fs.mkdirSync(LOG_DIR, { recursive: true });
fs.mkdirSync(REDIS_DIR, { recursive: true });

// .env 의 일부 값(APP_HOST 등)만 읽는다. 서비스 프로세스는 .env 를 스스로 읽는다.
function readDotenv() {
  const out = {};
  const p = path.join(ROOT, '.env');
  if (!fs.existsSync(p)) return out;
  for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    const q = v.match(/^(['"])(.*?)\1/);
    // 따옴표 값은 따옴표 안만, 아니면 " #" 뒤 주석을 뗀다(python-dotenv 와 같게)
    v = q ? q[2] : v.replace(/\s+#.*$/, '').trim();
    out[m[1]] = v;
  }
  return out;
}
const dotenv = readDotenv();
const only = (process.env.WINMATE_ONLY || '').split(',').map((s) => s.trim()).filter(Boolean);
const want = (name) => only.length === 0 || only.includes(name) || only.includes(name.replace(/-worker$/, ''));

const MEMORY = { 'ai-tools': '2G', kb: '1500M', files: '1G', export: '1G', image: '1G', birdseye: '1G', proposal: '1G' };
const common = (name) => ({
  cwd: ROOT,
  interpreter: 'none',
  autorestart: true,
  max_restarts: 20,
  min_uptime: '5s',
  restart_delay: 2000,
  kill_timeout: 25000,
  time: true,
  merge_logs: true,
  out_file: path.join(LOG_DIR, `${name}.log`),
  error_file: path.join(LOG_DIR, `${name}.log`),
});

const apps = [];

if (process.env.REDIS_MANAGED !== '0' && want('redis')) {
  apps.push({
    ...common('redis'),
    name: 'redis',
    script: process.env.REDIS_SERVER_BIN || 'redis-server',
    args: [path.join(ROOT, 'ops', 'redis', 'redis.conf'), '--port', String(reg.infra.redis.port), '--dir', REDIS_DIR],
  });
}

for (const [name, spec] of Object.entries(reg.services)) {
  const module = 'winmate_' + name.replace(/-/g, '_');
  const host = name === 'gateway' ? (dotenv.APP_HOST || '127.0.0.1') : '127.0.0.1';
  if (want(name)) {
    apps.push({
      ...common(name),
      name,
      script: path.join(VENV_BIN, 'uvicorn'),
      args: [`${module}.main:app`, '--host', host, '--port', String(spec.port), '--no-access-log',
        '--timeout-graceful-shutdown', '20', '--proxy-headers'],
      env: { WINMATE_SERVICE: name, PYTHONUNBUFFERED: '1' },
      max_memory_restart: MEMORY[name] || '600M',
    });
  }
  if (spec.worker && want(`${name}-worker`)) {
    apps.push({
      ...common(`${name}-worker`),
      name: `${name}-worker`,
      script: path.join(VENV_BIN, 'python'),
      args: ['-m', `${module}.worker`],
      env: { WINMATE_SERVICE: name, PYTHONUNBUFFERED: '1', JOB_CONCURRENCY: dotenv.JOB_WORKERS || '2' },
      max_memory_restart: MEMORY[name] || '800M',
    });
  }
}

if (process.env.WINMATE_WEB_DEV === '1') {
  apps.push({
    ...common('web-dev'),
    name: 'web-dev',
    cwd: path.join(ROOT, 'web'),
    script: 'npm',
    args: ['run', 'dev', '--', '--port', String(reg.infra.web_dev.port), '--strictPort'],
  });
}

module.exports = { apps };
