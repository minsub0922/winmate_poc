/**
 * 사용자 관리 `/admin/users` [제안 — 보드 없음] — 로그인 계정 만들기 · 이름 · 소속 · 역할 · 비밀번호 재설정 · 사용 중지.
 * workspace `GET/POST /v1/users` · `PATCH /v1/users/{id}`(AUTH_MODE=local 이면 관리자만). 사용자 메뉴 `사용자 관리` 로 연다.
 */
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, ApiError, unwrap } from '@/api/client';
import {
  Button, DataTable, Empty, ErrorState, Field, Input, ListPage, Modal, Notice, Segmented, StatusBadge, TitleCell, Toggle, relativeTime, toast,
  type DataColumn,
} from '@/ui';
import { useAuthMe } from '../auth';
import { useShellPage } from '../ShellContext';
import { useMe, useUsers, type WsUser } from '../workspace';

type Role = 'member' | 'admin';
const ROLE_LABEL: Record<Role, string> = { member: '구성원', admin: '관리자' };

function errText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'CONFLICT') return '이미 있는 아이디입니다';
    if (e.code === 'LAST_ADMIN') return '마지막 관리자는 역할을 바꾸거나 사용 중지할 수 없습니다';
    if (e.code === 'VALIDATION_ERROR') return '입력 형식을 확인해 주세요(아이디는 영문 · 숫자 · . _ -, 비밀번호 6자 이상)';
    return e.message;
  }
  return e instanceof Error ? e.message : '저장하지 못했어요';
}

function UserDialog({ user, onClose }: { user: WsUser | 'new'; onClose: () => void }) {
  const qc = useQueryClient();
  const isNew = user === 'new';
  const [username, setUsername] = useState('');
  const [name, setName] = useState(isNew ? '' : user.name);
  const [org, setOrg] = useState(isNew ? '' : user.org);
  const [role, setRole] = useState<Role>(isNew ? 'member' : (user.role as Role) ?? 'member');
  const [password, setPassword] = useState('');
  const [disabled, setDisabled] = useState(isNew ? false : user.disabled);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setErr(null);
    if (isNew && !/^[A-Za-z0-9._-]{2,40}$/.test(username.trim())) { setErr('아이디는 영문 · 숫자 · . _ - 로 2~40자예요'); return; }
    if (!name.trim()) { setErr('이름을 입력해 주세요'); return; }
    if ((isNew || password) && password.length < 6) { setErr('비밀번호는 6자 이상이에요'); return; }
    setBusy(true);
    try {
      if (isNew) {
        unwrap(await api.workspace.POST('/v1/users', { body: { username: username.trim(), name: name.trim(), org: org.trim(), password, role } }));
        toast(`「${name.trim()}」 계정을 만들었어요`);
      } else {
        unwrap(await api.workspace.PATCH('/v1/users/{user_id}', {
          params: { path: { user_id: user.id } },
          body: { name: name.trim(), org: org.trim(), role, disabled, ...(password ? { password } : {}) },
        }));
        toast(password ? '저장했어요 · 비밀번호를 새로 정했어요' : '저장했어요');
      }
      await qc.invalidateQueries({ queryKey: ['ws', 'users'] });
      onClose();
    } catch (e) {
      setErr(errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open onClose={onClose} title={isNew ? '새 사용자' : `사용자 고치기 · ${user.username}`} width={480} variant="dialog"
      footer={<><Button h={38} onClick={onClose}>취소</Button><Button h={38} variant="primary" loading={busy} onClick={save}>{isNew ? '만들기' : '저장'}</Button></>}>
      <form className="sh-form" onSubmit={(e) => { e.preventDefault(); void save(); }} data-testid="user-dialog">
        {err && <Notice tone="danger">{err}</Notice>}
        {isNew && (
          <Field label="아이디" hint="로그인할 때 쓰는 이름 · 영문 · 숫자 · . _ -">
            <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" autoFocus name="username" />
          </Field>
        )}
        <Field label="이름"><Input value={name} onChange={(e) => setName(e.target.value)} name="name" autoFocus={!isNew} /></Field>
        <Field label="소속"><Input value={org} onChange={(e) => setOrg(e.target.value)} name="org" placeholder="예: B2B영업 · Samsung Research" /></Field>
        <div className="wm-field">
          <span className="wm-label">역할</span>
          <Segmented<Role> value={role} onChange={setRole} ariaLabel="역할" tone="brand"
            items={[{ value: 'member', label: ROLE_LABEL.member }, { value: 'admin', label: ROLE_LABEL.admin }]} />
        </div>
        <Field label={isNew ? '비밀번호' : '비밀번호 재설정'} hint={isNew ? '6자 이상 · 처음 로그인한 뒤 사용자 메뉴에서 바꿀 수 있어요' : '비워 두면 그대로예요'}>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" name="password" />
        </Field>
        {!isNew && (
          <Toggle checked={disabled} onChange={setDisabled} size="lg" label="사용 중지">사용 중지 · 로그인할 수 없어요</Toggle>
        )}
        <button type="submit" hidden />
      </form>
    </Modal>
  );
}

export default function UsersPage() {
  useShellPage({ section: '설정', title: '사용자 관리', hasTask: false });
  const me = useMe();
  const auth = useAuthMe();
  const none = auth.data?.auth_mode === 'none';
  const allowed = none || me.data?.role === 'admin';
  const users = useUsers(allowed);
  const [edit, setEdit] = useState<WsUser | 'new' | null>(null);

  if (me.isLoading || auth.isLoading) return null;
  if (!allowed) {
    return <Empty title="관리자만 볼 수 있어요">사용자 관리는 관리자 계정으로 로그인해야 열려요.</Empty>;
  }
  const cols: Array<DataColumn<WsUser>> = [
    { key: 'name', label: '이름 · 아이디', width: 'minmax(0, 1.4fr)', render: (u) => <TitleCell title={u.name} sub={u.username} /> },
    { key: 'org', label: '소속', width: 'minmax(0, 1fr)', render: (u) => <span className="wm-ellipsis wm-small">{u.org || '—'}</span> },
    { key: 'role', label: '역할', width: '90px', render: (u) => <StatusBadge tone={u.role === 'admin' ? 'brand' : 'neutral'}>{ROLE_LABEL[(u.role as Role) ?? 'member'] ?? u.role}</StatusBadge> },
    {
      key: 'state', label: '상태', width: '120px',
      render: (u) => (u.disabled ? <StatusBadge tone="warn">사용 중지</StatusBadge>
        : !u.has_password ? <StatusBadge title="AUTH_MODE=none 에서 자동으로 생긴 프로필 — 비밀번호를 정하면 로그인할 수 있어요">비밀번호 없음</StatusBadge>
          : <StatusBadge tone="ok" icon="check">사용 중</StatusBadge>),
    },
    { key: 'login', label: '마지막 로그인', width: '120px', render: (u) => <span className="wm-small wm-muted">{u.last_login_at ? relativeTime(u.last_login_at, new Date()) : '—'}</span> },
    { key: 'act', label: '', width: '72px', align: 'end', render: (u) => <Button h={32} onClick={() => setEdit(u)} aria-label={`${u.name} 고치기`}>고치기</Button> },
  ];
  return (
    <ListPage title="사용자 관리" desc="로그인 계정을 만들고 이름 · 소속 · 역할 · 비밀번호 · 사용 여부를 바꿔요."
      action={<Button h={44} variant="primary" onClick={() => setEdit('new')}>+ 새 사용자</Button>}
      banner={none ? <Notice tone="warn">지금은 로그인 없이 쓰는 모드(AUTH_MODE=none)라 누구나 사용자를 관리할 수 있어요. 사내망에서는 `.env` 의 AUTH_MODE=local 로 바꿔 주세요.</Notice> : undefined}
      table={users.isError
        ? <ErrorState message="사용자를 불러오지 못했어요" onRetry={() => void users.refetch()} />
        : <DataTable rowKey={(u) => u.id} rows={users.data?.items ?? []} columns={cols} loading={users.isLoading} empty="아직 사용자가 없어요." />}>
      {edit && <UserDialog user={edit} onClose={() => setEdit(null)} />}
    </ListPage>
  );
}
