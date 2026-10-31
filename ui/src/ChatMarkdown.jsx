import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ChatMarkdown({ children }) {
  return (
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
        }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}
