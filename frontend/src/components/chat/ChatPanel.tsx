"use client";
import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@/store/workspace";
import { useChat } from "@/hooks/useChat";
import { useJob } from "@/hooks/useJob";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { Cpu } from "lucide-react";

export function ChatPanel() {
  const { messages, isStreaming, activeJobId } = useWorkspaceStore();
  const { sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Subscribe to job events for the active job
  useJob(activeJobId);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-surface-800">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-16 px-6 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-6">
        <Cpu className="w-8 h-8 text-brand-400" />
      </div>
      <h2 className="text-xl font-semibold text-surface-100 mb-3">
        Design your first 3D model
      </h2>
      <p className="text-surface-300 text-sm leading-relaxed max-w-xs mb-6">
        Describe a physical object and Claude will generate a parametric CadQuery script, export an STL, and render a preview.
      </p>
      <div className="space-y-2 w-full max-w-xs">
        {EXAMPLES.map((ex) => (
          <ExampleChip key={ex} label={ex} />
        ))}
      </div>
    </div>
  );
}

const EXAMPLES = [
  "A phone stand with cable slot for iPhone 15",
  "Raspberry Pi 4 enclosure with ventilation",
  "Wall-mount bracket for a 20mm rod",
];

function ExampleChip({ label }: { label: string }) {
  const { sendMessage } = useChat();
  return (
    <button
      onClick={() => sendMessage(label)}
      className="w-full text-left px-4 py-2.5 rounded-xl bg-surface-700 border border-surface-500
                 hover:border-brand-400/50 hover:bg-surface-600 transition-all text-sm text-surface-200
                 hover:text-surface-100"
    >
      {label}
    </button>
  );
}
