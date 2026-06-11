# EvalFlow — Backlog

Golden rule: every new idea or requirement lands here first — never directly
into the current release scope.

## Bucket 2 — Second release (important, after MVP delivery)

- Reviewer comment system on requirements (raise / resolve threads)
- QA Lead extended powers: edit documents in review, change requirement
  notes, upload developer defense responses
- ST document integration: direct Word upload, show matched security
  features alongside each requirement during assessment
- Multi-round assessment support (round 1, round 2, …) + defense upload
  from round 2 onward; populate VTR rounds 2–4 columns from real data
- Full company history view: which system, which assessor, how many
  findings, which round
- Document versioning and valid-version control (version numbers, validity
  status, retention of previous versions, version comparison)
- Management dashboard and basic reporting (open cases, stalled cases,
  average review time, rejected items, assessor performance)
- In-system notifications and reminders (assignment, correction requests,
  uploads, approvals, deadlines); email/SMS desirable
- Archiving and retention (finalized documents read-only, retention
  periods, audit retrieval)
- Basic KPI tracking (review time, finalized count, first-pass approval
  rate, findings count, delay rate)
- Optional AI assistant (Ollama) for text rewriting only — human approval
  required, AI-suggested content flagged, usage logged
- Clause-level structure editor in the admin UI (add/remove requirements
  and clauses from the browser; currently via load_frameworks/Django admin)
- Persian (Shamsi) date picker in the UI for test_completed_date
- Change-log (تغییرات سند) editor in the workspace
- Word output: table of contents, document-version table on cover,
  per-class section numbering matching the official template even closer
- Phrase bank (pre-defined standard phrases) beyond per-status default text
- Final review checklist per document type (mandatory/optional items,
  step-by-step completion, signature before finalization)
- Electronic signature records for every action (creation, editing,
  approval, rejection, finalization, archiving)

## Bucket 3 — Standalone projects (separate scope and timeline each)

- Full ISO/IEC 17025 compliance (document control, records control,
  traceability as a formal standard)
- Organizational SSO + Jira-based login (identity provider integration,
  account deactivation propagation)
- Full Jira integration with data sync and error handling
- Complete SLA engine: per-stage time targets, monitoring, auto-alerts,
  violation reports, requester-wait vs internal-time split
- Enterprise auditability: organizational audit reporting, tamper-evident
  log storage (e.g. hash chaining), audit trail extraction
- Advanced multi-layer reporting with PDF/Excel export of all report types
- Watermarks on draft/confidential printed documents; organizational
  print templates
- Confidentiality levels per document and download restriction policies
