import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import Chat from "./components/Chat.jsx";

it("showsCitations", () => {
  const markup = renderToStaticMarkup(
    <Chat
      features={{ layer1: true }}
      versions={[]}
      check={{ id: "CHK-TEST" }}
      prompt=""
      messages={[
        {
          question: "Cần chứng cứ gì?",
          answer: "Cần người duyệt đối chiếu.",
          model_status: "cached",
          status: "answered",
          citations: [
            {
              clause_version_id: "CV-02-v1",
              quote: "Synthetic citation for the UI test.",
            },
          ],
        },
      ]}
    />,
  );
  expect(markup).toContain("CV-02-v1");
  expect(markup).toContain("Synthetic citation for the UI test.");
  expect(markup).toContain("cached");
  expect(markup).not.toContain("Trả lời theo kịch bản");
});

it("keeps the chat shell visible but disables questions when layer 1 is off", () => {
  const markup = renderToStaticMarkup(
    <Chat
      features={{ layer1: false }}
      bundle={{ request: { records: [] } }}
      versions={[]}
      check={{ id: "CHK-PREVIEW" }}
      prompt="Cần bằng chứng gì?"
      messages={[]}
    />,
  );
  expect(markup).toContain("Chưa kết nối chatbot");
  expect(markup).toMatch(/<textarea[^>]*disabled=""/);
  expect(markup).toMatch(
    /<button[^>]*aria-label="Gửi câu hỏi"[^>]*disabled=""/,
  );
  expect(markup).toMatch(
    /<button[^>]*disabled=""[^>]*>[\s\S]*?Hỏi từ kho tri thức/,
  );
  expect(markup).not.toContain('class="message assistant"');
});
