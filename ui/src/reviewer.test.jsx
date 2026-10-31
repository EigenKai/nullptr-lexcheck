import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import fs from "node:fs";
import Review from "./components/Review.jsx";
import Evidence from "./components/Evidence.jsx";
const bundle = JSON.parse(
  fs.readFileSync(
    new URL("../../data/fixtures/demo.json", import.meta.url),
    "utf8",
  ),
);
const preview = JSON.parse(
  fs.readFileSync(
    new URL("../../data/fixtures/finding-preview.json", import.meta.url),
    "utf8",
  ),
);

describe("reviewer presentation", () => {
  it("rendersEvidenceAndVersion", () => {
    const current = preview.findings[0];
    const clause = bundle.clauses.find(
      (c) => c.id === current.clause_version_id,
    );
    const markup = renderToStaticMarkup(
      <Evidence
        bundle={bundle}
        versions={bundle.request.versions}
        current={current}
        check={preview}
        clause={clause}
        selected={{ type: "finding" }}
        history={{ checks: [] }}
        note=""
        owner="marketing"
        features={{}}
        closureCheckId=""
      />,
    );
    expect(markup).toContain(current.rule_id);
    expect(markup).toContain(current.clause_version_id);
    expect(markup).toContain("Applicability");
    expect(markup).toContain("Đóng việc sau kiểm tra lại");
  });
  it("shows a review page with no chat or invented result", () => {
    const markup = renderToStaticMarkup(
      <Review
        bundle={bundle}
        draft={bundle.request}
        features={{}}
        history={null}
        result={null}
        session={null}
      />,
    );
    expect(markup).toContain("Rà soát hồ sơ");
    expect(markup).toContain("Chưa chạy kiểm tra");
    expect(markup).not.toContain("Trợ lý Lex");
  });
});
