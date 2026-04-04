"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { UIMessage } from "@/types/api";
import { useWorkspaceStore } from "@/store/workspace";
import { CodeBlock } from "./CodeBlock";
import { JobStatusBadge } from "@/components/shared/JobStatusBadge";
import { clsx } from "clsx";

interface Props {
  message: UIMessage;
}

export function MessageBubble({ message }: Props) {
  const { jobs, setActiveJobId, setViewerMode } = useWorkspaceStore();
  const job = message.jobId ? jobs[message.jobId] : null;

  const isUser = message.role === "user";

  return (
    <div
      className={clsx(
        "flex gap-3 animate-fade-in",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold",
          isUser
            ? "bg-brand-500 text-white"
            : "bg-surface-600 text-surface-200 border border-surface-500"
        )}
      >
        {isUser ? "Y" : "AI"}
      </div>

      {/* Content */}
      <div className={clsx("flex-1 max-w-[85%]", isUser ? "items-end" : "items-start")}>
        <div
          className={clsx(
            "rounded-2xl px-4 py-3",
            isUser
              ? "bg-brand-600/80 text-white rounded-tr-sm"
              : "bg-surface-700 border border-surface-500 rounded-tl-sm"
          )}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className={clsx("chat-prose", message.isStreaming && "streaming-cursor")}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const isBlock = !!(node?.position?.start.line !== node?.position?.end.line);
                    if (match && isBlock) {
                      return <CodeBlock code={String(children).replace(/\n$/, "")} language={match[1]} />;
                    }
                    return <code className={className} {...props}>{children}</code>;
                  },
                }}
              >
                {message.content || (message.isStreaming ? " " : "")}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Job status chip */}
        {job && (
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={() => {
                setActiveJobId(job.id);
                if (job.status === "done") {
                  setViewerMode(job.has_stl ? "model" : "preview");
                }
              }}
              className="hover:opacity-80 transition-opacity"
            >
              <JobStatusBadge
                status={job.status}
                executionTimeMs={job.execution_time_ms}
              />
            </button>
            {job.status === "error" && job.error_message && (
              <span className="text-xs text-red-400 truncate max-w-[200px]" title={job.error_message}>
                {job.error_message.slice(0, 60)}…
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
