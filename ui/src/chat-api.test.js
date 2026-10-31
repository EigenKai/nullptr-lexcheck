import { afterEach, expect, it, vi } from "vitest";
import { request } from "./api.js";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function delayedResponse(delayMs) {
  return vi.fn(
    (_url, { signal }) => new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => resolve({ ok: true, json: async () => ({ answer: "Có căn cứ" }) }),
        delayMs,
      );
      signal.addEventListener("abort", () => {
        clearTimeout(timer);
        reject(signal.reason);
      }, { once: true });
    }),
  );
}

function fakeTimeouts() {
  vi.useFakeTimers();
  vi.spyOn(AbortSignal, "timeout").mockImplementation((timeoutMs) => {
    const controller = new AbortController();
    setTimeout(
      () => controller.abort(new DOMException("Timed out", "TimeoutError")),
      timeoutMs,
    );
    return controller.signal;
  });
}

it("waits for a chat response beyond the ordinary 15 second API budget", async () => {
  fakeTimeouts();
  const result = request("/chat", { method: "POST" }, delayedResponse(20000))
    .then((value) => ({ value }), (error) => ({ error }));
  await vi.advanceTimersByTimeAsync(20000);
  expect(await result).toEqual({ value: { answer: "Có căn cứ" } });
});

it("keeps ordinary requests bounded and distinguishes a timeout from disconnection", async () => {
  fakeTimeouts();
  const result = request("/history", {}, delayedResponse(20000))
    .then((value) => ({ value }), (error) => ({ error }));
  await vi.advanceTimersByTimeAsync(16000);
  expect((await result).error?.message).toContain("quá thời gian chờ");
});
