import { JobStatus } from "@/types/api";
import { clsx } from "clsx";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

interface Props {
  status: JobStatus;
  size?: "sm" | "md";
  executionTimeMs?: number | null;
}

const STATUS_CONFIG: Record<JobStatus, { label: string; classes: string; icon: React.ReactNode }> = {
  pending: {
    label: "Queued",
    classes: "bg-surface-700 text-surface-300 border-surface-500",
    icon: <Clock className="w-3 h-3" />,
  },
  running: {
    label: "Generating",
    classes: "bg-brand-900/50 text-brand-300 border-brand-700",
    icon: <Loader2 className="w-3 h-3 animate-spin" />,
  },
  done: {
    label: "Done",
    classes: "bg-emerald-900/30 text-emerald-400 border-emerald-800",
    icon: <CheckCircle2 className="w-3 h-3" />,
  },
  error: {
    label: "Failed",
    classes: "bg-red-900/30 text-red-400 border-red-800",
    icon: <XCircle className="w-3 h-3" />,
  },
};

export function JobStatusBadge({ status, size = "sm", executionTimeMs }: Props) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 border rounded-full font-medium",
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1",
        config.classes
      )}
    >
      {config.icon}
      {config.label}
      {status === "done" && executionTimeMs && (
        <span className="opacity-60 ml-0.5">{(executionTimeMs / 1000).toFixed(1)}s</span>
      )}
    </span>
  );
}
