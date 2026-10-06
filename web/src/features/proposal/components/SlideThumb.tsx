/**
 * 슬라이드 썸네일(PR7 · OneClickDone · PR7P 레일) — export 렌더 PNG(thumb_url)가 있으면 그것, 없으면 표지/목차/템플릿 도식(Thumb).
 */
import { BoltIcon, Thumb, cx } from '@/ui';
import { tplOf } from '../lib/catalog';

export function SlideThumb({ url, label, kind, code, inferred, badge, className }: {
  url?: string | null; label?: string; kind?: string | null; code?: string | null; inferred?: boolean; badge?: string | null; className?: string;
}) {
  const isCover = !!label && /표지/.test(label) && !url;
  const isToc = !!label && /목차/.test(label) && !url;
  const t = code ? tplOf(code) : null;
  return (
    <span className={cx('pr-slidethumb', isCover && 'pr-slidethumb--cover', isToc && 'pr-slidethumb--toc', inferred && 'pr-slidethumb--inferred', className)} data-inferred={inferred || undefined}>
      {url ? <img src={url} alt="" draggable={false} />
        : isCover || isToc ? null
          : <Thumb code={code ?? undefined} kind={kind ?? t?.kind ?? 'table'} n={t?.n ?? 3} />}
      {(badge ?? (inferred ? '추론' : null)) && <span className="pr-slidethumb__badge">{!badge && <BoltIcon size={7} color="var(--wm-brand-on-dark)" />}{badge ?? '추론'}</span>}
    </span>
  );
}
