/**
 * 페이지 틀(00-shell §3.1): 사이드바 260 + 메인(상단바 64 → [스텝바 56] → 본문) + 상세 시트 + 끌기 고스트 + 토스트.
 */
import { Outlet } from 'react-router';
import { DragGhostLayer, ToastHost } from '@/ui';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { Stepper } from './Stepper';
import { useShell } from './ShellContext';
import { DetailSheetHost } from './DetailSheet';
import { ShellRuntimeProvider } from './runtime';
import './shell.css';

export function Layout() {
  const { page } = useShell();
  return (
    <ShellRuntimeProvider>
      <div className="sh-root">
        <Sidebar />
        <main className="sh-main">
          <TopBar section={page.section} title={page.title} />
          {page.stepper && <Stepper config={page.stepper} />}
          <div className="sh-content" id="wm-main">
            <Outlet />
          </div>
        </main>
        <DetailSheetHost />
        <DragGhostLayer />
        <ToastHost />
      </div>
    </ShellRuntimeProvider>
  );
}
