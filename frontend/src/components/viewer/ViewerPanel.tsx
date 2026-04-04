"use client";
import Image from "next/image";
import { useWorkspaceStore } from "@/store/workspace";
import { ModelViewer3D } from "./ModelViewer3D";
import { DownloadBar } from "./DownloadBar";
import { JobStatusBadge } from "@/components/shared/JobStatusBadge";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { api } from "@/lib/api";
import { Box, Image as ImageIcon } from "lucide-react";

export function ViewerPanel() {
  const { activeJobId, jobs, viewerMode, setViewerMode } = useWorkspaceStore();
  const job = activeJobId ? jobs[activeJobId] : null;

  return (
    <div className="flex flex-col h-full bg-surface-900">
      {/* Viewer toolbar */}
      {job && (
        <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-500 bg-surface-800">
          <JobStatusBadge status={job.status} executionTimeMs={job.execution_time_ms} size="sm" />

          {job.status === "done" && (
            <div className="flex gap-1 ml-auto">
              {job.has_stl && (
                <ViewToggleBtn
                  active={viewerMode === "model"}
                  onClick={() => setViewerMode("model")}
                  title="3D View"
                  icon={<Box className="w-3.5 h-3.5" />}
                />
              )}
              {job.has_preview && (
                <ViewToggleBtn
                  active={viewerMode === "preview"}
                  onClick={() => setViewerMode("preview")}
                  title="Preview"
                  icon={<ImageIcon className="w-3.5 h-3.5" />}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* Main viewer area */}
      <div className="flex-1 relative overflow-hidden">
        {!job && <EmptyViewer />}

        {job?.status === "pending" && (
          <div className="absolute inset-0 flex items-center justify-center">
            <LoadingSpinner label="Queued…" />
          </div>
        )}

        {job?.status === "running" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
            <LoadingSpinner size="lg" label="Generating model…" />
            <p className="text-xs text-surface-400">CadQuery is building your geometry</p>
          </div>
        )}

        {job?.status === "done" && viewerMode === "model" && job.has_stl && (
          <ModelViewer3D stlUrl={api.stlUrl(job.id)} />
        )}

        {job?.status === "done" && (viewerMode === "preview" || (viewerMode === "model" && !job.has_stl)) && job.has_preview && (
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <img
              src={api.previewUrl(job.id)}
              alt="Model preview"
              className="max-w-full max-h-full object-contain rounded-xl"
            />
          </div>
        )}

        {job?.status === "error" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8 text-center">
            <div className="w-12 h-12 rounded-2xl bg-red-900/30 border border-red-800 flex items-center justify-center">
              <span className="text-2xl">⚠</span>
            </div>
            <p className="text-sm text-surface-200 font-medium">Generation failed</p>
            {job.error_message && (
              <pre className="text-xs text-red-400 bg-red-950/50 border border-red-900 rounded-xl px-4 py-3 max-w-md overflow-auto text-left whitespace-pre-wrap">
                {job.error_message.slice(0, 500)}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* Download bar */}
      {job && <DownloadBar job={job} />}
    </div>
  );
}

function ViewToggleBtn({ active, onClick, title, icon }: {
  active: boolean;
  onClick: () => void;
  title: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors
        ${active
          ? "bg-brand-500/20 text-brand-400 border border-brand-400/40"
          : "text-surface-300 hover:text-surface-100 hover:bg-surface-700 border border-transparent"
        }`}
    >
      {icon}
      {title}
    </button>
  );
}

function EmptyViewer() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-surface-400">
      <div className="w-24 h-24 rounded-3xl border-2 border-dashed border-surface-600 flex items-center justify-center">
        <Box className="w-10 h-10 text-surface-600" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-surface-300">No model yet</p>
        <p className="text-xs mt-1 text-surface-500">
          Describe a model in the chat to get started
        </p>
      </div>
    </div>
  );
}
