import { isWorkflowEvent, type WorkflowEvent } from "../contracts/events";

interface LiveEventOptions {
  runId: string;
  lastEventId?: number;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
  onEvent: (event: WorkflowEvent) => void;
  onGap?: (gap: { expected: number; received: number }) => void;
}

export async function connectLiveEvents(options: LiveEventOptions): Promise<number> {
  const fetchImpl = options.fetchImpl ?? fetch;
  let cursor = options.lastEventId ?? 0;
  let recoveryAttempts = 0;
  while (!options.signal?.aborted) {
    const response = await fetchImpl(`/api/runs/${encodeURIComponent(options.runId)}/events`, {
      headers: { Accept: "text/event-stream", "Last-Event-ID": String(cursor) },
      signal: options.signal,
    });
    if (!response.ok || !response.body) throw new Error(`实时事件连接失败（${response.status}）`);
    const contentType = response.headers.get("Content-Type") ?? "";
    if (!contentType.startsWith("text/event-stream")) throw new Error("实时事件响应类型无效");

    let gapDetected = false;
    for await (const event of parseSse(response.body)) {
      if (event.sequence <= cursor) continue;
      if (event.sequence !== cursor + 1) {
        options.onGap?.({ expected: cursor + 1, received: event.sequence });
        gapDetected = true;
        break;
      }
      options.onEvent(event);
      cursor = event.sequence;
    }
    if (!gapDetected) return cursor;
    recoveryAttempts += 1;
    if (recoveryAttempts > 4) throw new Error("实时事件序列无法恢复");
  }
  return cursor;
}

async function* parseSse(stream: ReadableStream<Uint8Array>): AsyncGenerator<WorkflowEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const data = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (data) {
          const payload: unknown = JSON.parse(data);
          if (!isWorkflowEvent(payload)) throw new Error("实时事件不符合 PCS-Harness schema");
          yield payload;
        }
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}
