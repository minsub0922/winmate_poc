/** 휴대폰 사진 올리기(`/birdseye/m/:token`, §4.4 QR 업로드) — 카메라 · 앨범 → files 업로드 → 토큰으로 인식 잡. 셸 밖 `/m/upload/:token` 은 workspace 요청 중. */
import { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useShellPage } from '@/shell/ShellContext';
import { Icon, Spinner } from '@/ui';
import { be, errText, uploadAll } from '../api';
import { SECTION } from '../ui';

export default function MobileUploadPage() {
  const { token = '' } = useParams();
  useShellPage({ section: SECTION, title: '휴대폰으로 올리기', hasTask: false, sidebarGroup: 'birdseye' });
  const info = useQuery({ queryKey: ['be', 'token', token], queryFn: () => be.tokenInfo(token), retry: 0 });
  const [done, setDone] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const ref = useRef<HTMLInputElement>(null);
  const send = async (files: File[]) => {
    const ok = files.filter((f) => /\.(png|jpe?g|heic|heif)$/i.test(f.name) || /^image\/(png|jpeg|heic|heif)$/.test(f.type));
    if (ok.length !== files.length) setErr('JPG · PNG · HEIC만 올릴 수 있어요');
    if (!ok.length) return;
    setBusy(true);
    try {
      const up = await uploadAll(ok);
      for (const f of up) { await be.tokenPhoto(token, f.id); setDone((d) => [...d, f.name]); }
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  };
  if (info.isLoading) return <div className="be-center"><Spinner /></div>;
  const valid = info.data?.valid;
  // 셸(사이드바)은 휴대폰 폭을 모른다 — 셸 밖 경로(/m/upload/:token, workspace 요청)가 생길 때까지 화면 전체를 덮어 보인다
  return createPortal(
    <div className="be-mobile-full"><div className="be-mobile" data-testid="be-mobile">
      <h1>{info.data?.title || '조감도'} · 현장 사진 올리기</h1>
      {!valid ? (
        <div className="be-notice" role="alert">QR 유효 시간이 지났어요. PC 화면에서 새 QR을 만들어 주세요.</div>
      ) : (
        <>
          <button type="button" className="be-mobile__pick" onClick={() => ref.current?.click()} disabled={busy}>
            {busy ? <Spinner label="올리는 중" /> : <Icon name="image" size={24} />}
            사진 찍기 · 앨범에서 고르기
            <span className="be-small be-muted">JPG · PNG · HEIC</span>
          </button>
          <input ref={ref} type="file" accept="image/jpeg,image/png,image/heic,image/heif" capture="environment" multiple hidden
            onChange={(e) => { void send(Array.from(e.target.files ?? [])); e.target.value = ''; }} />
          {done.map((n, i) => <div key={i} className="be-row"><Icon name="check" size={14} />{n} · 올렸어요</div>)}
          <span className="be-note">PC 의 현장 사진 화면에 바로 나타나요</span>
        </>
      )}
      {err && <div className="be-err" role="alert">{err}</div>}
    </div></div>,
    document.body,
  );
}
