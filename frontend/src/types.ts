export type Membership = {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  role: string;
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  memberships: Membership[];
};

export type Person = {
  id: string;
  organization_id: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  display_name: string;
  professional_title?: string;
  primary_email?: string;
  primary_phone?: string;
  nationality?: string;
  country_of_residence?: string;
  summary?: string;
  availability_status: string;
  profile_status: string;
  created_at: string;
  updated_at: string;
};

export type PeoplePage = {
  items: Person[];
  total: number;
  limit: number;
  offset: number;
};

export type SkillProficiency =
  | "beginner"
  | "intermediate"
  | "advanced"
  | "expert";

export type PersonSkill = {
  id: string;
  organization_id: string;
  person_id: string;
  name: string;
  proficiency: SkillProficiency | null;
  years_experience: number | null;
  last_used_year: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type DegreeLevel =
  | "secondary"
  | "certificate"
  | "diploma"
  | "associate"
  | "bachelor"
  | "master"
  | "doctorate"
  | "professional"
  | "other";

export type PersonEducation = {
  id: string;
  organization_id: string;
  person_id: string;
  degree_level: DegreeLevel;
  degree_name: string | null;
  field_of_study: string | null;
  institution: string;
  country: string | null;
  start_year: number | null;
  graduation_year: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PersonCertification = {
  id: string;
  organization_id: string;
  person_id: string;
  name: string;
  issuer: string | null;
  credential_id: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  verification_url: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentType =
  | "cv"
  | "certificate"
  | "degree"
  | "good_completion_certificate"
  | "reference_letter"
  | "license"
  | "project_evidence"
  | "employment_evidence"
  | "report"
  | "contract"
  | "spreadsheet"
  | "presentation"
  | "image"
  | "other";

export type PersonDocument = {
  id: string;
  organization_id: string;
  person_id: string;
  document_type: DocumentType;
  title: string;
  description: string | null;
  original_filename: string;
  mime_type: string;
  file_extension: string;
  file_size: number;
  uploaded_by_user_id: string;
  certification_id: string | null;
  education_id: string | null;
  created_at: string;
  updated_at: string;
};

export type EmploymentType =
  | "full_time"
  | "part_time"
  | "contract"
  | "consulting"
  | "temporary"
  | "internship"
  | "volunteer"
  | "other";

export type EmploymentExperience = {
  id: string;
  organization_id: string;
  person_id: string;
  employer_name: string;
  job_title: string;
  employment_type: EmploymentType | null;
  industry: string | null;
  location: string | null;
  country: string | null;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  responsibilities: string | null;
  achievements: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectExperience = {
  id: string;
  organization_id: string;
  person_id: string;
  project_name: string;
  client_name: string | null;
  role: string;
  sector: string | null;
  location: string | null;
  country: string | null;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  responsibilities: string | null;
  outcomes: string | null;
  skills_summary: string | null;
  created_at: string;
  updated_at: string;
};

export type OpportunityStatus =
  | "new"
  | "analyzing"
  | "needs_review"
  | "ready"
  | "pursuing"
  | "not_pursuing"
  | "submitted"
  | "won"
  | "lost"
  | "archived";

export type AnalysisStatus =
  | "queued"
  | "fetching"
  | "extracting"
  | "analyzing"
  | "matching"
  | "building_team"
  | "complete"
  | "failed"
  | "needs_review";

export type RequirementType =
  | "skill"
  | "education"
  | "certification"
  | "experience"
  | "project_experience"
  | "sector"
  | "geography"
  | "language"
  | "availability"
  | "client_experience"
  | "document"
  | "custom";

export type RequirementImportance =
  | "mandatory"
  | "preferred"
  | "informational";

export type MatchStatus =
  | "matched"
  | "partial"
  | "missing"
  | "unverified"
  | "not_applicable";

export type TeamStatus =
  | "recommended"
  | "selected"
  | "rejected";

export type Opportunity = {
  id: string;
  organization_id: string;
  title: string;
  client_name: string | null;
  reference_number: string | null;
  description: string | null;
  source_url: string | null;
  deadline_at: string | null;
  status: OpportunityStatus;
  external_source: string | null;
  external_id: string | null;
  selected_team_id: string | null;
  selected_team_at: string | null;
  selected_team_by_user_id: string | null;
  decision_at: string | null;
  decision_by_user_id: string | null;
  submitted_at: string | null;
  submitted_by_user_id: string | null;
  outcome_at: string | null;
  outcome_by_user_id: string | null;
  internal_notes: string | null;
  outcome_notes: string | null;
  created_by_user_id: string;
  updated_by_user_id: string;
  created_at: string;
  updated_at: string;
};

export type OpportunityAnalysis = {
  id: string;
  opportunity_id: string;
  version: number;
  status: AnalysisStatus;
  model_name: string | null;
  started_at: string | null;
  completed_at: string | null;
  extracted_summary: string | null;
  error_message: string | null;
  readiness_score: number | null;
  created_at: string;
  updated_at: string;
};

export type OpportunityRequirement = {
  id: string;
  role_id: string;
  requirement_type: RequirementType;
  importance: RequirementImportance;
  label: string;
  normalized_value: string | null;
  values_json: string[] | null;
  minimum_years: number | null;
  minimum_count: number | null;
  minimum_degree_level: string | null;
  operator: string;
  weight: number;
  evidence_required: boolean;
  notes: string | null;
  source_excerpt: string | null;
  created_at: string;
  updated_at: string;
};

export type OpportunityRole = {
  id: string;
  opportunity_id: string;
  analysis_id: string;
  title: string;
  description: string | null;
  quantity: number;
  is_mandatory: boolean;
  sort_order: number;
  requirements: OpportunityRequirement[];
  created_at: string;
  updated_at: string;
};

export type RequirementEvidence = {
  source?: string;
  label?: string;
  detail?: string | null;
  [key: string]: unknown;
};

export type RequirementMatch = {
  id: string;
  requirement_id: string;
  status: MatchStatus;
  score: number;
  evidence_json: RequirementEvidence[] | null;
  explanation: string | null;
  created_at: string;
  updated_at: string;
};

export type CandidateMatch = {
  id: string;
  role_id: string;
  person_id: string;
  score: number;
  mandatory_pass_rate: number;
  preferred_pass_rate: number;
  mandatory_failed: boolean;
  rank: number | null;
  explanation: string | null;
  person_name: string | null;
  professional_title: string | null;
  requirement_matches: RequirementMatch[];
  created_at: string;
  updated_at: string;
};

export type RecommendedTeamMember = {
  id: string;
  role_id: string;
  person_id: string;
  candidate_match_id: string;
  assignment_score: number;
  person_name: string | null;
  role_title: string | null;
  created_at: string;
  updated_at: string;
};

export type RecommendedTeam = {
  id: string;
  analysis_id: string;
  name: string;
  status: TeamStatus;
  score: number;
  mandatory_constraints_satisfied: boolean;
  explanation: string | null;
  members: RecommendedTeamMember[];
  created_at: string;
  updated_at: string;
};

export type CapabilityGap = {
  id: string;
  analysis_id: string;
  role_id: string | null;
  requirement_id: string | null;
  severity: string;
  label: string;
  best_candidate_person_id: string | null;
  best_candidate_score: number | null;
  recommendation: string | null;
  created_at: string;
  updated_at: string;
};