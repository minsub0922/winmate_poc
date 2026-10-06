/**
 * /image/new/references · /image/new/composite — 새 작업을 만들고 IMG2R · IMG2P 로 바로 간다(§2).
 * `?refs=kb:image:…,img:image:…` 가 있으면 그 이미지를 참조로 넣어 시작한다(상단 이미지 검색 「대화에 첨부」).
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { ErrorState } from '@/ui';
import { errMessage, img } from '../api';
import { Loading, useImgShell } from '../components';
import { route } from '../lib';

export default function StartPage({ start }: { start: 'references' | 'composite' }) {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [err, setErr] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const once = useRef(false);
  useImgShell({ title: '새 작업', step: 2 });
  useEffect(() => {
    if (once.current) return;
    once.current = true;
    const refs = (sp.get('refs') || '').split(',').filter(Boolean).slice(0, 3);
    img.createWork({
      start, kind: start === 'composite' ? 'composite' : undefined,
      reference_items: refs.length ? refs.map((r) => ({ source_kind: 'topbar' as const, source_ref: r, via: 'topbar' as const })) : undefined,
    })
      .then((w) => nav(start === 'composite' ? route.composite(w.id) : route.references(w.id), { replace: true }))
      .catch((e) => setErr(errMessage(e)));
  }, [start, sp, nav, attempt]);
  if (err) return <div className="img-center"><ErrorState message={`작업을 만들지 못했어요 · ${err}`} onRetry={() => { once.current = false; setErr(null); setAttempt((a) => a + 1); }} /></div>;
  return <Loading label="새 작업을 만드는 중" />;
}
