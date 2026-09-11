import { expect, test } from "vitest";
import { normalizeSuggestionPayload, validateDocumentSelection } from "../features/documents/suggestions";
import { formatPartialEvidenceDate } from "../features/profile/dates";
import { externalHref } from "../lib/links";
function withSize(size: number, name = "evidence.pdf"): File {
  const file = new File(["content"], name); Object.defineProperty(file, "size", { value: size }); return file;
}
test("accepts a 75 MB document and exactly the 250 MB upper boundary", () => {
  expect(validateDocumentSelection(withSize(75 * 1024 * 1024))).toBeNull();
  expect(validateDocumentSelection(withSize(250 * 1024 * 1024))).toBeNull();
});
test("rejects an oversized upload before sending it", () => {
  expect(validateDocumentSelection(withSize(250 * 1024 * 1024 + 1))).toContain("250 MB");
});
test("still rejects empty and Office temporary files", () => {
  expect(validateDocumentSelection(withSize(0))).toContain("empty");
  expect(validateDocumentSelection(withSize(100, "~$evidence.docx"))).toContain("temporary");
});
test("review editing preserves partial evidence dates and permissive numeric values", () => {
  const education = normalizeSuggestionPayload("education", { start_date: "2020", graduation_date: "2023-07" });
  expect(education.start_date).toBe("2020"); expect(education.graduation_date).toBe("2023-07");
  expect(normalizeSuggestionPayload("skill", { name: "Guiding", years_experience: "95" }).years_experience).toBe(95);
});
test("partial date display does not invent a missing day", () => {
  expect(formatPartialEvidenceDate("2020")).toBe("2020");
  expect(formatPartialEvidenceDate("2020-13")).toBe("2020-13");
  expect(formatPartialEvidenceDate("2020-02-31")).toBe("2020-02-31");
});
test("source links never expose executable protocols", () => {
  expect(externalHref("javascript:alert(1)")).toBeUndefined();
  expect(externalHref("data:text/html,test")).toBeUndefined();
  expect(externalHref("https://example.com/credential")).toBe("https://example.com/credential");
});
