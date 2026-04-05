"use client";
import { useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { Job } from "@/types/api";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * Subscribes to SSE job events for the given jobId.
 * Updates the store's jobs map on every status transition.
 * Automatically sets the viewer to "preview" or "model" once the job is done.
 */
export function useJob(jobId: string | null) {
  const { upsertJob, setViewerMode, activeJobId } = useWorkspaceStore();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    // Close any existing connection
    esRef.current?.close();

    const es = new EventSource(api.jobEventsUrl(jobId));
    esRef.current = es;

    es.addEventListener("status", (e: MessageEvent) => {
      try {
        const job: Job = JSON.parse(e.data);
        upsertJob(job);

        // Auto-switch viewer when this is the active job
        if (job.id === activeJobId) {
          if (job.status === "done") {
            setViewerMode(job.has_stl ? "model" : "preview");
          }
        }

        if (job.status === "done" || job.status === "error") {
          es.close();
        }
      } catch {}
    });

    es.onerror = () => {
      // EventSource auto-reconnects; we close it once terminal status is reached above
    };

    return () => {
      es.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);
}
