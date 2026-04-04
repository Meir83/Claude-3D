import { render, screen } from "@testing-library/react";
import { JobStatusBadge } from "@/components/shared/JobStatusBadge";

describe("JobStatusBadge", () => {
  it.each([
    ["pending", "Queued"],
    ["running", "Generating"],
    ["done", "Done"],
    ["error", "Failed"],
  ] as const)("renders %s status as '%s'", (status, label) => {
    render(<JobStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows execution time for done status", () => {
    render(<JobStatusBadge status="done" executionTimeMs={3200} />);
    expect(screen.getByText(/3\.2s/)).toBeInTheDocument();
  });

  it("does not show execution time for non-done status", () => {
    render(<JobStatusBadge status="running" executionTimeMs={3200} />);
    expect(screen.queryByText(/3\.2s/)).not.toBeInTheDocument();
  });
});
