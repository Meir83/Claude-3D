/**
 * Tests for the useChat hook's streaming state management.
 * We test the store mutations directly rather than rendering components.
 */
import { useWorkspaceStore } from "@/store/workspace";

describe("workspace store", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      messages: [],
      isStreaming: false,
      jobs: {},
      activeJobId: null,
      viewerMode: "empty",
      toastError: null,
    });
  });

  it("adds a user message", () => {
    const { addMessage } = useWorkspaceStore.getState();
    addMessage({ id: "1", role: "user", content: "hello" });
    expect(useWorkspaceStore.getState().messages).toHaveLength(1);
    expect(useWorkspaceStore.getState().messages[0].role).toBe("user");
  });

  it("appends to last assistant message while streaming", () => {
    const { addMessage, appendToLastAssistantMessage } = useWorkspaceStore.getState();
    addMessage({ id: "2", role: "assistant", content: "Hello", isStreaming: true });
    appendToLastAssistantMessage(" world");
    expect(useWorkspaceStore.getState().messages[0].content).toBe("Hello world");
  });

  it("finalises assistant message", () => {
    const { addMessage, finaliseAssistantMessage } = useWorkspaceStore.getState();
    addMessage({ id: "3", role: "assistant", content: "Done", isStreaming: true });
    finaliseAssistantMessage();
    expect(useWorkspaceStore.getState().messages[0].isStreaming).toBe(false);
  });

  it("upserts a job", () => {
    const { upsertJob } = useWorkspaceStore.getState();
    const job = {
      id: "job-1", session_id: "s-1", status: "pending" as const,
      phase: null, error_message: null, execution_time_ms: null,
      has_stl: false, has_preview: false, has_step: false,
      created_at: "", started_at: null, finished_at: null,
    };
    upsertJob(job);
    expect(useWorkspaceStore.getState().jobs["job-1"]).toEqual(job);
  });

  it("sets toast error and clears it", () => {
    const { setToastError } = useWorkspaceStore.getState();
    setToastError("Something went wrong");
    expect(useWorkspaceStore.getState().toastError).toBe("Something went wrong");
    setToastError(null);
    expect(useWorkspaceStore.getState().toastError).toBeNull();
  });
});
