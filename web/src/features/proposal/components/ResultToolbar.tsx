/**
 * 결과 툴바(보드 PR7P · PR7C · PR7V 공통, h52): 「‹ 결과」 · 파일 · 버전 칩 · 상태 글 | 확정 필요 n · 버전 · 검토 · 편집 · 내보내기.
 * 「내보내기」는 지금 화면 위에 PR7X 모달(`?export=1`).
 */
import type { ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Icon, cx } from '@/ui';
import { R } from '../lib/routes';

export type ResultTab = 'preview' | 'review' | 'versions' | 'confirm';

const ClockIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></svg>;
const ChatIcon = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 5h16v11H9l-5 4V5z" /></svg>;
const EditIcon = () => <Icon name="edit" size={14} />;

export function useExportParam() {
  const [sp, setSp] = useSearchParams();
  const open = sp.get('export') === '1';
  const openExport = (o: { lang?: string; version?: number | null } = {}) => setSp((cur) => {
    const x = new URLSearchParams(cur); x.set('export', '1');
    if (o.lang) x.set('lang', o.lang);
    if (o.version) x.set('version', String(o.version));
    return x;
  });
  const closeExport = () => setSp((cur) => { const x = new URLSearchParams(cur); x.delete('export'); x.delete('lang'); x.delete('version'); return x; });
  const lang = (sp.get('lang') as 'ko' | 'en' | 'ko_en' | null) ?? null;
  const version = sp.get('version') ? Number(sp.get('version')) : null;
  return { open, openExport, closeExport, lang, version };
}

export function ResultToolbar({ id, tab, fileName, pill, meta, openConfirm, extra, onExport, testId }:
  { id: string; tab: ResultTab; fileName?: string | null; pill?: ReactNode; meta?: ReactNode; openConfirm?: number | null; extra?: ReactNode; onExport: () => void; testId?: string }) {
  return (
    <div className="pr-restool" data-testid={testId ?? 'pr-restool'}>
      <Link to={R.result(id)} className="pr-restool__back"><Icon name="chevronLeft" size={15} strokeWidth={2.2} />결과</Link>
      <span className="pr-vdiv" style={{ height: 20 }} />
      <span className="pr-restool__icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 4h18v12H3z M8 20h8 M12 16v4" /></svg></span>
      {fileName && <span className="pr-ell" style={{ fontSize: 13.5, fontWeight: 600, maxWidth: 260 }}>{fileName}</span>}
      {pill && <span className={cx('pr-restool__pill', `pr-restool__pill--${tab}`)} data-testid="pr-restool-pill">{pill}</span>}
      {meta && <span className="pr-ell" style={{ fontSize: 12, color: 'var(--wm-text-muted)', minWidth: 0 }}>{meta}</span>}
      <span className="pr-grow" />
      {tab !== 'preview' && <Link to={R.preview(id)} className="pr-restool__btn"><EditIcon />편집</Link>}
      {tab !== 'confirm' && (
        <Link to={R.confirm(id)} className="pr-restool__btn" data-testid="pr-restool-confirm">확정 필요{(openConfirm ?? 0) > 0 && <span className="pr-restool__count">{openConfirm}</span>}</Link>
      )}
      {tab !== 'versions' && <Link to={R.versions(id)} className="pr-restool__btn"><ClockIcon />버전</Link>}
      {tab !== 'review' && <Link to={R.review(id)} className="pr-restool__btn"><ChatIcon />{tab === 'versions' ? '검토' : '검토 요청'}</Link>}
      {extra}
      <button type="button" className="pr-restool__btn pr-restool__btn--primary" onClick={onExport} data-testid="pr-restool-export"><Icon name="download" size={14} strokeWidth={2.2} />내보내기</button>
    </div>
  );
}
