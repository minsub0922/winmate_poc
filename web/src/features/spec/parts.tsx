/** Spec 화면 사이 공유 부품(데이터를 읽는 것) — 출처 보기 · 파일 고르기 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Modal, Spinner } from '@/ui';
import { cellSources, errText, type Source } from './api';

const KIND_LABEL: Record<string, string> = { catalog: '사내 카탈로그', datasheet: '데이터시트', policy_doc: '보증 정책 문서', user: '직접 입력', derived: '계산' };

/** 출처 보기(§4.15.6) — `{출처 이름} · {버전/날짜} · {등급} · {쪽} · {인용}` */
export function SourcesModal({ sheetId, rowId, productId, title, onClose }:
  { sheetId: string; rowId: string | null | undefined; productId: string | null | undefined; title: ReactNode; onClose: () => void }) {
  const [list, setList] = useState<Source[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const open = !!rowId && !!productId;
  useEffect(() => {
    if (!open) return;
    let off = false;
    setList(null);
    setErr(null);
    cellSources(sheetId, rowId!, productId!).then((r) => { if (!off) setList(r); }).catch((e) => { if (!off) setErr(errText(e)); });
    return () => { off = true; };
  }, [open, sheetId, rowId, productId]);
  return (
    <Modal open={open} onClose={onClose} title={title} width={520}>
      {!list && !err && <div className="sp-note"><Spinner label="출처를 불러오는 중" /> 출처를 불러오는 중…</div>}
      {err && <div className="sp-note" role="alert">{err}</div>}
      {list && !list.length && <div className="sp-note">기록된 출처가 없어요.</div>}
      {list && list.length > 0 && (
        <ul className="sp-srcs" aria-label="출처">
          {list.map((x, i) => (
            <li key={i} className="sp-src">
              <div className="sp-src__head">
                <b>{x.label || KIND_LABEL[x.kind] || x.kind}</b>
                {[x.version_or_date, x.tier, x.page ? `p.${x.page}` : null].filter(Boolean).map((t) => <span key={String(t)}> · {t}</span>)}
              </div>
              {x.quote && <blockquote className="sp-src__quote">{x.quote}</blockquote>}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}

/** 숨긴 파일 입력 + 여는 함수 */
export function useFilePicker(accept: string, onPick: (f: File) => void | Promise<void>) {
  const ref = useRef<HTMLInputElement>(null);
  const input = (
    <input ref={ref} type="file" hidden accept={accept} aria-hidden="true" tabIndex={-1}
      onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) void onPick(f); }} />
  );
  return { input, open: () => ref.current?.click() };
}
