"use client";
import { Download, Image as ImageIcon, FileCode2 } from "lucide-react";
import { api } from "@/lib/api";
import { Job } from "@/types/api";

interface Props {
  job: Job;
}

export function DownloadBar({ job }: Props) {
  if (job.status !== "done") return null;

  const downloadFile = (url: string, filename: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
  };

  return (
    <div className="flex items-center gap-2 px-4 py-3 border-t border-surface-500 bg-surface-800">
      <span className="text-xs text-surface-400 mr-1">Download:</span>

      {job.has_stl && (
        <button
          onClick={() => downloadFile(api.stlUrl(job.id), `model_${job.id.slice(0, 8)}.stl`)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500/10 border border-brand-500/30
                     text-brand-400 hover:bg-brand-500/20 hover:border-brand-400/60 transition-colors text-xs font-medium"
        >
          <Download className="w-3.5 h-3.5" />
          STL
        </button>
      )}

      {job.has_step && (
        <button
          onClick={() => downloadFile(api.stepUrl(job.id), `model_${job.id.slice(0, 8)}.step`)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-700 border border-surface-500
                     text-surface-200 hover:bg-surface-600 transition-colors text-xs font-medium"
        >
          <FileCode2 className="w-3.5 h-3.5" />
          STEP
        </button>
      )}

      {job.has_preview && (
        <button
          onClick={() => downloadFile(api.previewUrl(job.id), `preview_${job.id.slice(0, 8)}.png`)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-700 border border-surface-500
                     text-surface-200 hover:bg-surface-600 transition-colors text-xs font-medium"
        >
          <ImageIcon className="w-3.5 h-3.5" />
          PNG
        </button>
      )}

      {job.execution_time_ms && (
        <span className="ml-auto text-xs text-surface-400">
          Generated in {(job.execution_time_ms / 1000).toFixed(1)}s
        </span>
      )}
    </div>
  );
}
