import { ChatStreamEvent } from "@/types/api";

/**
 * Parse a single SSE chunk into a ChatStreamEvent.
 * SSE format: "event: <name>\ndata: <payload>\n\n"
 */
export function parseSSEChunk(chunk: string): ChatStreamEvent[] {
  const events: ChatStreamEvent[] = [];
  const messages = chunk.split("\n\n").filter(Boolean);

  for (const msg of messages) {
    const lines = msg.split("\n");
    let eventName = "message";
    let data = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventName = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        data = line.slice(6);
      }
    }

    if (eventName && data !== undefined) {
      events.push({ event: eventName as ChatStreamEvent["event"], data });
    }
  }

  return events;
}

/**
 * Async generator that reads an SSE stream and yields parsed events.
 */
export async function* readSSEStream(
  response: Response
): AsyncGenerator<ChatStreamEvent> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages (terminated by \n\n)
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const events = parseSSEChunk(part + "\n\n");
        for (const event of events) {
          yield event;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
