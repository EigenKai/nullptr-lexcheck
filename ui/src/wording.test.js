import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";
const forbidden = /\b(compliant|approved)\b|hợp lệ|đúng luật|>\s*Publish\s*</iu;

it("avoidsProhibitedVerdicts", () => {
  function check(dir) {
    for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
      const name = path.join(dir, item.name);
      if (item.isDirectory()) check(name);
      else if (/\.(js|jsx)$/.test(name) && !name.includes(".test.")) {
        expect(
          fs.readFileSync(name, "utf8").normalize("NFC"),
          name,
        ).not.toMatch(forbidden);
      }
    }
  }
  check(fileURLToPath(new URL(".", import.meta.url)));
});
