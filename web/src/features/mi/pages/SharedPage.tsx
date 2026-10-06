/** 링크 공유 화면 `/mi/:id/shared` (§4.14 `링크 공유` — 결과 읽기 전용, 경쟁사는 익명 표기) */
import { useState } from 'react';
import { useShellPage } from '@/shell';
import { AREAS, useSharedView, type Area } from '../api';
import { TabBody } from '../blocks';
import { Agent, ErrorBand, LoadingCard, MiPage, ResultTabs, SECTION, useAid } from '../parts';

export function SharedPage() {
  const aid = useAid();
  const v = useSharedView(aid);
  useShellPage({ section: SECTION, title: '공유된 분석', hasTask: false, sidebarGroup: 'mi' });
  const r = v.data;
  const first = (r?.tabs.find((t) => t.status === 'done')?.area as Area | undefined) ?? 'market';
  const [tab, setTab] = useState<Area | null>(null);
  const cur = tab && AREAS.includes(tab) ? tab : first;
  const footer = r?.footers?.[cur];
  return (
    <MiPage>
      <Agent text="공유된 분석 결과예요. 읽기 전용이고, 경쟁사는 익명 표기로 보여요.">
        {v.isError && <ErrorBand onRetry={() => void v.refetch()} />}
        {!r && !v.isError && <LoadingCard lines={8} />}
        {r && (
          <div className="mi-card" data-testid="mi-shared">
            <ResultTabs tabs={r.tabs} value={cur} onChange={setTab} />
            <div className="mi-tabbody">
              <TabBody r={r} area={cur} />
              {footer && <div className="mi-footer"><span>{footer.text}</span></div>}
            </div>
          </div>
        )}
      </Agent>
    </MiPage>
  );
}
