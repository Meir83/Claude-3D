"use client";
import { AppHeader } from "./AppHeader";
import { ResizableDivider } from "./ResizableDivider";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { ViewerPanel } from "@/components/viewer/ViewerPanel";
import { ToastNotification } from "@/components/shared/ToastNotification";
import { useResizePanel } from "@/hooks/useResizePanel";

export function WorkspaceLayout() {
  const { leftPercent, containerRef, onMouseDown } = useResizePanel({ initialPercent: 40 });

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <AppHeader />

      {/* Split pane workspace */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden">
        {/* Left: Chat */}
        <div
          style={{ width: `${leftPercent}%` }}
          className="flex flex-col overflow-hidden min-w-0"
        >
          <ChatPanel />
        </div>

        <ResizableDivider onMouseDown={onMouseDown} />

        {/* Right: Viewer */}
        <div className="flex flex-col flex-1 overflow-hidden min-w-0">
          <ViewerPanel />
        </div>
      </div>

      <ToastNotification />
    </div>
  );
}
