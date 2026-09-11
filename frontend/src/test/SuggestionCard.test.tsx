import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { SuggestionCard } from "../features/documents/SuggestionCard";
import type { ProfileSuggestion } from "../types";
const suggestion: ProfileSuggestion = {
  id: "suggestion-a", organization_id: "org-a", person_id: "person-a", source_document_id: "doc-a",
  category: "education", title: "Example qualification", payload: { institution: "Example College", start_date: "2020", graduation_date: "2023-07" }, confidence: 0.9,
  created_by_user_id: "user-a", status: "pending", review_note: null, applied_entity_id: null, reviewed_by_user_id: null, reviewed_at: null,
  created_at: "2026-01-01", updated_at: "2026-01-01",
};
function mount(canReview = true, isEditing = false) {
  const onAccept = vi.fn(); const onReject = vi.fn(); const onEdit = vi.fn();
  render(<SuggestionCard suggestion={suggestion} expanded isEditing={isEditing} busy={false} canReview={canReview}
    previewBusy={false} editPayload={suggestion.payload} note="" onToggle={vi.fn()} onAccept={onAccept}
    onReject={onReject} onEdit={onEdit} onSave={vi.fn()} onCancel={vi.fn()} onChange={vi.fn()} onNote={vi.fn()} onPreview={vi.fn()} />);
  return { onAccept, onReject, onEdit };
}
test("Accept uses the existing review action", () => {
  const { onAccept } = mount(); fireEvent.click(screen.getByRole("button", { name: "Accept" })); expect(onAccept).toHaveBeenCalledOnce();
});
test("review keyboard shortcuts operate only on the focused card, not in a note", () => {
  const { onAccept, onReject } = mount();
  fireEvent.keyDown(screen.getByRole("article", { name: "Review Example qualification" }), { key: "a" });
  expect(onAccept).toHaveBeenCalledOnce();
  fireEvent.keyDown(screen.getByRole("textbox", { name: /Review note/ }), { key: "r" });
  expect(onReject).not.toHaveBeenCalled();
});
test("read-only users cannot see acceptance controls", () => {
  mount(false); expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
});
test("the edit form retains year-only and year-month dates", () => {
  mount(true, true);
  expect(screen.getByRole("textbox", { name: "Start date" })).toHaveValue("2020");
  expect(screen.getByRole("textbox", { name: "Graduation / completion date" })).toHaveValue("2023-07");
});
