"use client";
import { useWorkspaceStore } from "@/store/workspace";
import { Box, Cpu } from "lucide-react";

export function AppHeader() {
  const { sessionTitle, activeJobId, jobs } = useWorkspaceStore();
  const activeJob = activeJobId ? jobs[activeJobId] : null;

  return (
    <header className="flex items-center h-14 px-6 border-b border-surface-500 bg-surface-800 flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 mr-6">
        <div className="w-8 h-8 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
          <Box className="w-4 h-4 text-brand-400" />
        </div>
        <span className="font-semibold text-surface-100 text-sm tracking-tight">
          Claude 3D
        </span>
      </div>

      {/* Session title */}
      {sessionTitle && (
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-1 h-1 rounded-full bg-surface-500" />
          <span className="text-sm text-surface-300 truncate max-w-xs">
            {sessionTitle}
          </span>
        </div>
      )}

      <div className="ml-auto flex items-center gap-3">
        {activeJob && (
          <div className="flex items-center gap-1.5 text-xs text-surface-400">
            <Cpu className="w-3.5 h-3.5" />
            <span>
              {activeJob.status === "running"
                ? "Generating…"
                : activeJob.status === "pending"
                ? "Queued"
                : null}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
