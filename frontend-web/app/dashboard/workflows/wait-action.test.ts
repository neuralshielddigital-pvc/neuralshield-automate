import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const source = fs.readFileSync(
  path.join(process.cwd(), "app/dashboard/workflows/page.tsx"),
  "utf8"
);

describe("WAIT action workflow builder", () => {
  it("renders a bounded wait-duration input", () => {
    expect(source).toContain('form.actionType === "WAIT"');
    expect(source).toContain("Wait duration (seconds)");
    expect(source).toContain('min="1"');
    expect(source).toContain('max="30"');
    expect(source).toContain('step="1"');
    expect(source).toContain("value={form.waitSeconds}");
  });

  it("serializes WAIT seconds as a strict integer", () => {
    expect(source).toContain("const seconds = Number(form.waitSeconds)");
    expect(source).toContain("Number.isInteger(seconds)");
    expect(source).toContain("return { seconds }");
  });

  it("hydrates existing WAIT action configuration", () => {
    expect(source).toContain('typeof config.seconds === "number"');
    expect(source).toContain("String(config.seconds)");
  });

  it("uses a safe one-second default", () => {
    expect(source).toContain('waitSeconds: "1"');
  });
});
