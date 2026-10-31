import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";

function fixtureCopy() {
  const path = new URL("../data/fixtures/demo.json", import.meta.url);
  const legalPath = new URL("../rules/nq21-preloaded.json", import.meta.url);
  function legalPreview() {
    return fs.existsSync(legalPath)
      ? JSON.parse(fs.readFileSync(legalPath, "utf8"))
      : null;
  }
  function publicDemo() {
    const bundle = JSON.parse(fs.readFileSync(path, "utf8"));
    const access = JSON.parse(
      fs.readFileSync(
        new URL("../data/fixtures/access.json", import.meta.url),
        "utf8",
      ),
    );
    const ids = new Set(access.shared_request.records.map((r) => r.id));
    const snapshot = bundle.request;
    snapshot.records = snapshot.records.filter((r) => ids.has(r.id));
    snapshot.versions = snapshot.versions.filter((v) => ids.has(v.record_id));
    const versions = new Set(snapshot.versions.map((v) => v.id));
    snapshot.target_version_ids = snapshot.target_version_ids.filter((id) =>
      versions.has(id),
    );
    snapshot.context_version_ids = snapshot.context_version_ids.filter((id) =>
      versions.has(id),
    );
    bundle.preview.snapshot = structuredClone(snapshot);
    bundle.preview.findings = bundle.preview.findings.filter((f) =>
      versions.has(f.record_version_id),
    );
    return JSON.stringify(bundle);
  }
  function publicPreview() {
    const preview = JSON.parse(
      fs.readFileSync(
        new URL("../data/fixtures/finding-preview.json", import.meta.url),
        "utf8",
      ),
    );
    const shared = new Set(
      JSON.parse(publicDemo()).request.records.map((r) => r.id),
    );
    preview.snapshot.records = preview.snapshot.records.filter((r) =>
      shared.has(r.id),
    );
    preview.snapshot.versions = preview.snapshot.versions.filter((v) =>
      shared.has(v.record_id),
    );
    const ids = new Set(preview.snapshot.versions.map((v) => v.id));
    preview.snapshot.target_version_ids =
      preview.snapshot.target_version_ids.filter((id) => ids.has(id));
    preview.snapshot.context_version_ids =
      preview.snapshot.context_version_ids.filter((id) => ids.has(id));
    preview.findings = preview.findings.filter(
      (f) =>
        ids.has(f.record_version_id) &&
        f.evidence.every((e) => ids.has(e.record_version_id)),
    );
    return JSON.stringify(preview);
  }
  return {
    name: "current-demo-fixture",
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "finding-preview.json",
        source: publicPreview(),
      });
      this.emitFile({
        type: "asset",
        fileName: "demo.json",
        source: publicDemo(),
      });
      const layers = JSON.parse(
        fs.readFileSync(
          new URL("../data/fixtures/layers.json", import.meta.url),
          "utf8",
        ),
      );
      this.emitFile({
        type: "asset",
        fileName: "legal-event.json",
        source: JSON.stringify(
          legalPreview()?.state.event || layers.LegalChangeEvent,
        ),
      });
      if (legalPreview())
        this.emitFile({
          type: "asset",
          fileName: "legal-preview.json",
          source: JSON.stringify(legalPreview()),
        });
    },
    configureServer(server) {
      server.middlewares.use("/finding-preview.json", (_req, res) => {
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(publicPreview());
      });
      server.middlewares.use("/demo.json", (_req, res) => {
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(publicDemo());
      });
      server.middlewares.use("/legal-event.json", (_req, res) => {
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        const layers = JSON.parse(
          fs.readFileSync(
            new URL("../data/fixtures/layers.json", import.meta.url),
            "utf8",
          ),
        );
        res.end(
          JSON.stringify(
            legalPreview()?.state.event || layers.LegalChangeEvent,
          ),
        );
      });
      server.middlewares.use("/legal-preview.json", (_req, res) => {
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        const preview = legalPreview();
        if (!preview) res.statusCode = 404;
        res.end(
          JSON.stringify(
            preview || { message: "Preloaded law source unavailable." },
          ),
        );
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), fixtureCopy()],
  server: {
    proxy: {
      "/workspace-research": "http://127.0.0.1:8000",
      "/api": process.env.LEXCHECK_API_URL || "http://127.0.0.1:8000",
      "/health": process.env.LEXCHECK_API_URL || "http://127.0.0.1:8000",
    },
  },
  test: { include: ["src/**/*.test.{js,jsx}"] },
});
