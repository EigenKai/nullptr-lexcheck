import React from "react";
import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { WorkspaceChat, WorkspaceConversations } from "./WorkspaceChat.jsx";

describe("workspace chat shell", () => {
  it("restores greeting, composer, document links and evidence column without a canned answer", () => {
    const html = renderToStaticMarkup(
      React.createElement(WorkspaceChat, {
        workspace: {
          id: "WS-one",
          name: "Independent company",
          documents: [
            { collection: "business", context_enabled: true },
            { collection: "legal" },
          ],
        },
        conversationId: null,
        newConversationNonce: 0,
        onConversationSelected() {},
        onTurnSaved() {},
        onBusyChange() {},
        onNavigate() {},
      }),
    );
    expect(html).toContain("Chào bạn");
    expect(html).toContain('aria-label="Câu hỏi cho Lex"');
    expect(html).toContain('aria-label="Nguồn trích dẫn và công cụ"');
    expect(html).toContain("Tài liệu doanh nghiệp");
    expect(html).toContain("Tài liệu luật");
    expect(html).toContain("Independent company");
    expect(html).not.toContain("workspace-chat-answer-head");
    expect(html).toContain("Chat bằng model đang tắt");
  });
  it("starts recent conversations empty rather than showing synthetic threads", () => {
    const html = renderToStaticMarkup(
      React.createElement(WorkspaceConversations, {
        workspaceId: "WS-one",
        selectedId: null,
        refresh: 0,
        disabled: false,
        onSelect() {},
      }),
    );
    expect(html).toContain("TRÒ CHUYỆN GẦN ĐÂY");
    expect(html).toContain("Chưa có hội thoại đã lưu");
  });
  it("shows an existing unselected workbook with a direct review and context action", () => {
    const html = renderToStaticMarkup(React.createElement(WorkspaceChat, {
      workspace: {id: "WS-one", name: "Company", documents: [
        {id: "FILE-example", name: "billing.xlsx", collection: "business", context_enabled: false},
      ]}, onBusyChange() {}, onNavigate() {},
    }));
    expect(html).toContain("billing.xlsx");
    expect(html).toContain("FILE-example");
    expect(html).toContain("Xem và chọn nội dung file");
    expect(html).toContain("Model đọc toàn bộ nội dung file được chọn");
    expect(html).not.toContain("Che thông tin cá nhân");
    expect(html).not.toContain("Mỗi câu trả lời cần căn cứ");
    expect(html).toContain("Đã có trong workspace");
  });
});
