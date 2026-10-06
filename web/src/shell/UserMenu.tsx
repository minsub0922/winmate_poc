/**
 * 사용자 카드 메뉴 — 설정 버튼(`aria-label="설정"`, §6.4)을 누르면 위로 열린다 [제안: 보드에 목적지 없음 Q-NAV-4].
 * 알림(작업물 알림 최근 8 · 모두 읽음) · 로그인한 사용자(아이디 · 역할) · 사용자 관리(관리자 · AUTH_MODE=none) · 비밀번호 바꾸기 · 로그아웃.
 * 로그아웃은 AUTH_MODE=local 에서만(none 은 모두가 개발 사용자라 로그아웃이 없다).
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { api, ApiError, unwrap } from '@/api/client';
import { Avatar, Button, Icon, IconButton, Modal, Notice, SlidersIcon, relativeTime, toast, useEscape } from '@/ui';
import { logout, useAuthMe } from './auth';
import { FeatureIcon } from './icons';
import { markNotificationsRead, useMe, useNotificationCounts, useNotifications, type WsNotification } from './workspace';

/** 마감일(YYYY-MM-DD, KST) → `D-3` · `D-day` · `마감 지남` (검토 알림 data.due_date) */
export function ddayLabel(due: unknown, now = new Date()): string | null {
  if (typeof due !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(due)) return null;
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
  const d = Math.round((Date.parse(`${due}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)) / 86_400_000);
  return d > 0 ? `D-${d}` : d === 0 ? 'D-day' : '마감 지남';
}

function NotiRow({ n, onOpen }: { n: WsNotification; onOpen: (n: WsNotification) => void }) {
  const dday = ddayLabel((n.data as Record<string, unknown> | null | undefined)?.due_date);
  return (
    <button type="button" role="menuitem" className={n.read ? 'sh-noti' : 'sh-noti sh-noti--new'} onClick={() => onOpen(n)} data-noti={n.id}>
      <span className="sh-noti__icon" aria-hidden="true">
        {n.item?.feature ? <FeatureIcon code={n.item.feature} size={14} color="var(--wm-brand)" /> : <Icon name="info" size={14} color="var(--wm-brand)" />}
      </span>
      <span className="sh-noti__body">
        <span className="sh-noti__title">{n.title}</span>
        <span className="sh-noti__meta">
          {[n.by_name, relativeTime(n.created_at, new Date())].filter(Boolean).join(' · ')}
          {dday && <b className="sh-noti__due" data-dday={dday}>{dday}</b>}
        </span>
      </span>
      {!n.read && <span className="sh-noti__dot" aria-label="읽지 않음" />}
    </button>
  );
}

function PasswordDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [cur, setCur] = useState('');
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { if (open) { setCur(''); setNext(''); setAgain(''); setErr(null); } }, [open]);
  const submit = async () => {
    if (next.length < 6) { setErr('새 비밀번호는 6자 이상이에요'); return; }
    if (next !== again) { setErr('새 비밀번호가 서로 달라요'); return; }
    setBusy(true);
    setErr(null);
    try {
      unwrap(await api.workspace.POST('/v1/me/password', { body: { current_password: cur, new_password: next } }));
      toast('비밀번호를 바꿨어요');
      onClose();
    } catch (e) {
      setErr(e instanceof ApiError && e.code === 'INVALID_PASSWORD' ? '지금 비밀번호가 맞지 않습니다' : e instanceof Error ? e.message : '바꾸지 못했어요');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="비밀번호 바꾸기" width={420} variant="dialog"
      footer={<><Button h={38} onClick={onClose}>취소</Button><Button h={38} variant="primary" loading={busy} onClick={submit}>바꾸기</Button></>}>
      <form className="sh-form" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
        {err && <Notice tone="danger">{err}</Notice>}
        <label className="sh-login__field"><span>지금 비밀번호</span>
          <input className="wm-input" type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} autoFocus /></label>
        <label className="sh-login__field"><span>새 비밀번호 <small className="wm-subtle">· 6자 이상</small></span>
          <input className="wm-input" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} /></label>
        <label className="sh-login__field"><span>새 비밀번호 확인</span>
          <input className="wm-input" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} /></label>
        <button type="submit" hidden />
      </form>
    </Modal>
  );
}

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const nav = useNavigate();
  const qc = useQueryClient();
  const me = useMe();
  const auth = useAuthMe();
  const counts = useNotificationCounts();
  const list = useNotifications(8, open);
  const unread = counts.data?.unread ?? 0;
  const local = auth.data?.auth_mode === 'local';
  const canAdmin = me.data?.role === 'admin' || (!!auth.data && auth.data.auth_mode === 'none');

  useEscape(() => setOpen(false), open);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const refresh = () => void qc.invalidateQueries({ queryKey: ['ws', 'notifications'] });
  const openNoti = async (n: WsNotification) => {
    setOpen(false);
    if (!n.read) { try { await markNotificationsRead({ ids: [n.id] }); } catch { /* 무시 */ } refresh(); }
    if (n.route) nav(n.route);
  };
  const readAll = async () => {
    try { await markNotificationsRead({}); } catch { /* 무시 */ }
    refresh();
  };
  const doLogout = async () => {
    setOpen(false);
    await logout();
    // 다른 사용자 데이터가 남지 않게 새로 연다
    window.location.replace('/login');
  };
  const items = list.data?.items ?? [];

  return (
    <div className="sh-umenu-wrap" ref={wrap}>
      <IconButton label="설정" title={unread ? `설정 · 알림 ${unread}건` : '설정 · 알림 · 로그아웃'} aria-haspopup="menu" aria-expanded={open}
        onClick={() => setOpen((v) => !v)} data-unread={unread || undefined}>
        <SlidersIcon size={16} />
        {unread > 0 && <span className="sh-umenu__badge" aria-hidden="true" />}
      </IconButton>
      {open && (
        <div className="sh-umenu" role="menu" aria-label="사용자 메뉴">
          <div className="sh-umenu__head">
            <span>알림{unread > 0 && <b className="wm-num"> {unread}</b>}</span>
            {unread > 0 && <button type="button" className="sh-umenu__link" onClick={readAll}>모두 읽음</button>}
          </div>
          <div className="sh-umenu__notis">
            {list.isLoading && <div className="sh-umenu__empty">불러오는 중…</div>}
            {list.isError && <div className="sh-umenu__empty">알림을 불러오지 못했어요</div>}
            {!list.isLoading && !list.isError && items.length === 0 && <div className="sh-umenu__empty">새 알림이 없어요</div>}
            {items.map((n) => <NotiRow key={n.id} n={n} onOpen={openNoti} />)}
          </div>
          <div className="wm-menu__sep" />
          <div className="sh-umenu__who">
            <Avatar initial={me.data?.initial ?? '·'} size={28} />
            <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
              <b className="wm-ellipsis">{me.data?.name ?? auth.data?.name ?? ''}</b>
              <small className="wm-ellipsis" data-login-id="">
                {local ? `아이디 ${me.data?.username ?? auth.data?.id ?? ''}` : '로그인 없이 쓰는 중(AUTH_MODE=none)'}
                {me.data?.role === 'admin' ? ' · 관리자' : ''}
              </small>
            </span>
          </div>
          {canAdmin && (
            <button type="button" role="menuitem" className="wm-menu__item" onClick={() => { setOpen(false); nav('/admin/users'); }}>
              <Icon name="user" size={14} />사용자 관리
            </button>
          )}
          {local && me.data?.has_password && (
            <button type="button" role="menuitem" className="wm-menu__item" onClick={() => { setOpen(false); setPwOpen(true); }}>
              <Icon name="lock" size={14} />비밀번호 바꾸기
            </button>
          )}
          <button type="button" role="menuitem" className="wm-menu__item" onClick={doLogout} disabled={!local}
            title={local ? undefined : '로그인 없이 쓰는 모드(AUTH_MODE=none)라 로그아웃이 없어요'}>
            <Icon name="arrowLeft" size={14} />로그아웃
          </button>
        </div>
      )}
      <PasswordDialog open={pwOpen} onClose={() => setPwOpen(false)} />
    </div>
  );
}
