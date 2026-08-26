import { describe, expect, it, vi } from "vitest";

import { connectLiveEvents } from "./liveEvents";

function sse(sequence: number) {
  const event = {
    schema_version: "pcs_harness_workflow_event.v1",
    run_id: "run_001",
    source: "harness",
    event_type: "stage.completed",
    sequence,
    occurred_at: "2026-08-26T00:00:00Z",
    elapsed_ms: sequence,
    payload: {},
    candidate_id: "cand_0001",
    stage: "L1",
    artifact_refs: [],
  };
  return `id: ${sequence}\nevent: stage.completed\ndata: ${JSON.stringify(event)}\n\n`;
}

function response(body: string): Response {
  const bytes = new TextEncoder().encode(body);
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(bytes.slice(0, Math.floor(bytes.length / 2)));
        controller.enqueue(bytes.slice(Math.floor(bytes.length / 2)));
        controller.close();
      },
    }),
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  );
}

describe("connectLiveEvents", () => {
  it("sends Last-Event-ID and backfills a detected gap without duplicating events", async () => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response(sse(2) + sse(4)))
      .mockResolvedValueOnce(response(sse(3) + sse(4)));
    const received: number[] = [];
    const gaps: Array<{ expected: number; received: number }> = [];

    const last = await connectLiveEvents({
      runId: "run_001",
      lastEventId: 1,
      fetchImpl,
      onEvent: (event) => received.push(event.sequence),
      onGap: (gap) => gaps.push(gap),
    });

    expect(received).toEqual([2, 3, 4]);
    expect(gaps).toEqual([{ expected: 3, received: 4 }]);
    expect(fetchImpl).toHaveBeenNthCalledWith(
      1,
      "/api/runs/run_001/events",
      expect.objectContaining({ headers: { Accept: "text/event-stream", "Last-Event-ID": "1" } }),
    );
    expect(fetchImpl).toHaveBeenNthCalledWith(
      2,
      "/api/runs/run_001/events",
      expect.objectContaining({ headers: { Accept: "text/event-stream", "Last-Event-ID": "2" } }),
    );
    expect(last).toBe(4);
  });

  it("exposes no replay, scrubber, playback-rate, or demo-data controls", async () => {
    const module = await import("./liveEvents");
    expect(Object.keys(module)).toEqual(["connectLiveEvents"]);
    expect(JSON.stringify(module)).not.toMatch(/replay|scrubber|playback|demo.?data/i);
  });
});
