export type Role = "admin" | "assessor" | "reviewer" | "qa_lead";

export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  assessor_code: string;
  is_active: boolean;
  must_change_password: boolean;
}

export interface Company {
  id: number;
  name: string;
  name_en: string;
  systems_count: number;
  created_at: string;
}

export interface ProductSystem {
  id: number;
  company: number;
  company_name: string;
  name: string;
  name_en: string;
  version: string;
  description: string;
  created_at: string;
}

export interface Framework {
  id: number;
  code: string;
  title: string;
  kind: "TRP" | "VTR";
  is_active: boolean;
  requirements_count: number;
  clauses_count: number;
}

export type AssessmentStatus = "under_assessment" | "under_review" | "completed";
export type ClauseStatusValue =
  | "unreviewed"
  | "compliant"
  | "finding"
  | "not_applicable";

export interface StatusCounts {
  total: number;
  compliant: number;
  finding: number;
  not_applicable: number;
  unreviewed: number;
}

export interface Assessment {
  id: number;
  system: number;
  system_name: string;
  company_name: string;
  framework: number;
  framework_title: string;
  kind: "TRP" | "VTR";
  status: AssessmentStatus;
  assessor: number;
  assessor_name: string;
  reviewer: number | null;
  reviewer_name: string | null;
  tester_code: string;
  approver_code: string;
  test_completed_date: string | null;
  architecture_overview: string;
  test_configuration: string;
  doc_version: string;
  change_log: { version: string; date: string; description: string }[];
  status_counts: StatusCounts;
  compliance_percent: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClauseAssessment {
  id: number;
  assessment: number;
  clause: number;
  clause_code: string;
  clause_title: string;
  clause_description: string;
  clause_objective: string;
  requirement_id: number;
  requirement_title: string;
  klass_title: string;
  guidance: string;
  status: ClauseStatusValue;
  text: string;
  text_edited: boolean;
  updated_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
