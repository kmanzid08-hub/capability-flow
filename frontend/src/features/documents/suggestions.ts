import type { DocumentType, ProfileSuggestion } from "../../types";

export function validateDocumentSelection(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  if (file.name.startsWith("~$") || lowerName.startsWith(".~lock.")) {
    return `${file.name} is an Office temporary file. Close the document in Word/LibreOffice and upload the original file instead.`;
  }
  if (file.size === 0) {
    return `${file.name} is empty (0 KB). Please upload the original document.`;
  }
  const maxBytes = 250 * 1024 * 1024;
  if (file.size > maxBytes) {
    return `${file.name} exceeds the 250 MB upload limit.`;
  }
  return null;
}

export const documentTypeOptions: { value: DocumentType; label: string; }[] = [
  { value: "cv", label: "CV / Resume" },
  { value: "certificate", label: "Professional certificate" },
  { value: "degree", label: "Degree / academic evidence" },
  { value: "good_completion_certificate", label: "Good completion certificate" },
  { value: "reference_letter", label: "Reference letter" },
  { value: "license", label: "License / accreditation" },
  { value: "project_evidence", label: "Project evidence" },
  { value: "employment_evidence", label: "Employment evidence" },
  { value: "other", label: "Other" },
];

export type SuggestionFieldKind =
  | "text"
  | "number"
  | "date"
  | "textarea"
  | "select"
  | "checkbox";

export type SuggestionField = {
  key: string;
  label: string;
  kind?: SuggestionFieldKind;
  options?: { value: string; label: string; }[];
  placeholder?: string;
};

export const suggestionFields: Record<ProfileSuggestion["category"], SuggestionField[]> = {
  profile: [
    { key: "professional_title", label: "Professional title" },
    { key: "summary", label: "Professional summary", kind: "textarea" },
    { key: "nationality", label: "Nationality" },
    { key: "country_of_residence", label: "Country of residence" },
  ],
  skill: [
    { key: "name", label: "Skill" },
    {
      key: "proficiency",
      label: "Proficiency",
      kind: "select",
      options: [
        { value: "", label: "Not specified" },
        { value: "beginner", label: "Beginner" },
        { value: "intermediate", label: "Intermediate" },
        { value: "advanced", label: "Advanced" },
        { value: "expert", label: "Expert" },
      ],
    },
    { key: "years_experience", label: "Years of experience", kind: "number" },
    { key: "last_used_year", label: "Last used year", kind: "number" },
    { key: "notes", label: "Notes", kind: "textarea" },
  ],
  education: [
    {
      key: "degree_level",
      label: "Degree level",
      kind: "select",
      options: [
        { value: "secondary", label: "Secondary" },
        { value: "certificate", label: "Certificate" },
        { value: "diploma", label: "Diploma" },
        { value: "associate", label: "Associate" },
        { value: "bachelor", label: "Bachelor" },
        { value: "master", label: "Master" },
        { value: "doctorate", label: "Doctorate" },
        { value: "professional", label: "Professional" },
        { value: "other", label: "Other" },
      ],
    },
    { key: "degree_name", label: "Degree name" },
    { key: "field_of_study", label: "Field of study" },
    { key: "institution", label: "Institution" },
    { key: "country", label: "Country" },
    { key: "start_date", label: "Start date", kind: "date" },
    { key: "graduation_date", label: "Graduation / completion date", kind: "date" },
    { key: "notes", label: "Notes", kind: "textarea" },
  ],
  certification: [
    { key: "name", label: "Certification" },
    { key: "issuer", label: "Issuer" },
    { key: "credential_id", label: "Credential ID" },
    { key: "issue_date", label: "Issue date", kind: "date" },
    { key: "expiry_date", label: "Expiry date", kind: "date" },
    { key: "verification_url", label: "Verification URL" },
    { key: "notes", label: "Notes", kind: "textarea" },
  ],
  employment: [
    { key: "employer_name", label: "Employer" },
    { key: "job_title", label: "Job title" },
    {
      key: "employment_type",
      label: "Employment type",
      kind: "select",
      options: [
        { value: "", label: "Not specified" },
        { value: "full_time", label: "Full time" },
        { value: "part_time", label: "Part time" },
        { value: "contract", label: "Contract" },
        { value: "consulting", label: "Consulting" },
        { value: "temporary", label: "Temporary" },
        { value: "internship", label: "Internship" },
        { value: "volunteer", label: "Volunteer" },
        { value: "other", label: "Other" },
      ],
    },
    { key: "industry", label: "Industry / sector" },
    { key: "location", label: "Location" },
    { key: "country", label: "Country" },
    { key: "start_date", label: "Start date", kind: "date" },
    { key: "end_date", label: "End date", kind: "date" },
    { key: "is_current", label: "Current employment", kind: "checkbox" },
    { key: "description", label: "Role description", kind: "textarea" },
    { key: "responsibilities", label: "Responsibilities", kind: "textarea" },
    { key: "achievements", label: "Achievements", kind: "textarea" },
  ],
  project: [
    { key: "project_name", label: "Project name" },
    { key: "client_name", label: "Client" },
    { key: "role", label: "Role" },
    { key: "sector", label: "Sector" },
    { key: "location", label: "Location" },
    { key: "country", label: "Country" },
    { key: "start_date", label: "Start date", kind: "date" },
    { key: "end_date", label: "End date", kind: "date" },
    { key: "is_current", label: "Ongoing project", kind: "checkbox" },
    { key: "description", label: "Project description", kind: "textarea" },
    { key: "responsibilities", label: "Responsibilities", kind: "textarea" },
    { key: "outcomes", label: "Outcomes", kind: "textarea" },
    { key: "skills_summary", label: "Skills used", kind: "textarea" },
  ],
};

export function readableSuggestionValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not recorded";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return String(value).replaceAll("_", " ");
}

export function normalizeSuggestionPayload(
  category: ProfileSuggestion["category"],
  values: Record<string, unknown>,
): Record<string, unknown> {
  const numericFields = new Set([
    "years_experience",
    "last_used_year",
  ]);
  const result: Record<string, unknown> = {};

  for (const field of suggestionFields[category]) {
    const value = values[field.key];
    if (field.kind === "checkbox") {
      result[field.key] = Boolean(value);
    } else if (numericFields.has(field.key)) {
      result[field.key] =
        value === "" || value === null || value === undefined
          ? null
          : Number(value);
    } else {
      result[field.key] = value === "" || value === undefined ? null : value;
    }
  }

  return result;
}

export function suggestionValidationHint(suggestion: ProfileSuggestion): string | null {
  const payload = suggestion.payload;

  if (suggestion.category === "employment" || suggestion.category === "project") {
    const startDate = payload.start_date;
    if (startDate === null || startDate === undefined || startDate === "") {
      return "A start date is required. Year-only, year-month, and full dates are all accepted; keep the precision stated by the source.";
    }
  }


  return null;
}

