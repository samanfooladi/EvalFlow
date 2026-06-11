import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "@/api/client";
import type {
  Assessment,
  AssessmentStatus,
  Framework,
  Paginated,
  ProductSystem,
  User,
} from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import {
  Badge,
  Button,
  EmptyState,
  ErrorText,
  Modal,
  Select,
} from "@/components/ui";

export const STATUS_LABELS: Record<AssessmentStatus, string> = {
  under_assessment: "در حال ارزیابی",
  under_review: "در حال بازبینی",
  completed: "تکمیل‌شده",
};

const STATUS_TONES: Record<AssessmentStatus, "warn" | "accent" | "compliant"> = {
  under_assessment: "warn",
  under_review: "accent",
  completed: "compliant",
};

function CreateAssessmentForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [system, setSystem] = useState("");
  const [framework, setFramework] = useState("");
  const [assessor, setAssessor] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [error, setError] = useState("");

  const systems = useQuery({
    queryKey: ["systems", "all"],
    queryFn: () =>
      api.get<Paginated<ProductSystem>>("/systems/").then((r) => r.data.results),
  });
  const frameworks = useQuery({
    queryKey: ["frameworks"],
    queryFn: () =>
      api.get<Paginated<Framework>>("/frameworks/").then((r) => r.data.results),
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () =>
      api.get<Paginated<User>>("/auth/users/").then((r) => r.data.results),
  });

  const create = useMutation({
    mutationFn: () =>
      api.post("/assessments/", {
        system: Number(system),
        framework: Number(framework),
        assessor: Number(assessor),
        reviewer: reviewer ? Number(reviewer) : null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessments"] });
      onDone();
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!system || !framework || !assessor) {
      setError("سامانه، چارچوب و ارزیاب الزامی هستند.");
      return;
    }
    create.mutate();
  }

  const assessors = users.data?.filter((u) => u.role === "assessor" && u.is_active);
  const reviewers = users.data?.filter((u) => u.role === "reviewer" && u.is_active);

  return (
    <form onSubmit={submit} className="space-y-4">
      <Select label="سامانه" value={system} onChange={(e) => setSystem(e.target.value)}>
        <option value="">انتخاب کنید…</option>
        {systems.data?.map((s) => (
          <option key={s.id} value={s.id}>
            {s.company_name} — {s.name} {s.version}
          </option>
        ))}
      </Select>
      <Select label="چارچوب ارزیابی" value={framework} onChange={(e) => setFramework(e.target.value)}>
        <option value="">انتخاب کنید…</option>
        {frameworks.data?.map((f) => (
          <option key={f.id} value={f.id}>
            {f.kind} — {f.title} ({f.clauses_count} بند)
          </option>
        ))}
      </Select>
      <Select label="ارزیاب" value={assessor} onChange={(e) => setAssessor(e.target.value)}>
        <option value="">انتخاب کنید…</option>
        {assessors?.map((u) => (
          <option key={u.id} value={u.id}>
            {u.first_name ? `${u.first_name} ${u.last_name}` : u.username}
          </option>
        ))}
      </Select>
      <Select label="بازبین (اختیاری)" value={reviewer} onChange={(e) => setReviewer(e.target.value)}>
        <option value="">—</option>
        {reviewers?.map((u) => (
          <option key={u.id} value={u.id}>
            {u.first_name ? `${u.first_name} ${u.last_name}` : u.username}
          </option>
        ))}
      </Select>
      <ErrorText>{error}</ErrorText>
      <Button type="submit" disabled={create.isPending} className="w-full">
        ایجاد ارزیابی
      </Button>
    </form>
  );
}

export function AssessmentsPage() {
  const { hasRole } = useAuth();
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const assessments = useQuery({
    queryKey: ["assessments", statusFilter],
    queryFn: () =>
      api
        .get<Paginated<Assessment>>(
          `/assessments/${statusFilter ? `?status=${statusFilter}` : ""}`,
        )
        .then((r) => r.data.results),
  });

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink-100">ارزیابی‌ها</h1>
        <div className="flex items-center gap-3">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">همه وضعیت‌ها</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          {hasRole("admin", "qa_lead") && (
            <Button onClick={() => setShowCreate(true)}>+ ارزیابی جدید</Button>
          )}
        </div>
      </div>

      {assessments.data?.length === 0 && (
        <EmptyState>ارزیابی‌ای یافت نشد.</EmptyState>
      )}

      <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {assessments.data?.map((a) => {
          const done = a.status_counts.total - a.status_counts.unreviewed;
          const progress =
            a.status_counts.total > 0
              ? Math.round((100 * done) / a.status_counts.total)
              : 0;
          return (
            <li key={a.id}>
              <Link
                to={`/assessments/${a.id}`}
                className="block rounded-2xl border border-surface-700 bg-surface-900 p-5 transition-colors hover:border-accent-600/60"
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div>
                    <div className="font-bold text-ink-100">{a.system_name}</div>
                    <div className="mt-0.5 text-xs text-ink-500">{a.company_name}</div>
                  </div>
                  <Badge tone={a.kind === "TRP" ? "accent" : "warn"}>{a.kind}</Badge>
                </div>
                <div className="mb-3 flex items-center gap-2">
                  <Badge tone={STATUS_TONES[a.status]}>{STATUS_LABELS[a.status]}</Badge>
                  {a.status_counts.finding > 0 && (
                    <Badge tone="finding">{a.status_counts.finding} عدم انطباق</Badge>
                  )}
                </div>
                <div className="mb-1.5 flex items-center justify-between text-xs text-ink-500">
                  <span>پیشرفت بررسی</span>
                  <span className="fa-nums">
                    {done} از {a.status_counts.total}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-700">
                  <div
                    className="h-full rounded-full bg-accent-500 transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="mt-3 text-xs text-ink-600">
                  ارزیاب: {a.assessor_name}
                  {a.compliance_percent != null && (
                    <span className="ms-3">انطباق: {a.compliance_percent}٪</span>
                  )}
                </div>
              </Link>
            </li>
          );
        })}
      </ul>

      <Modal open={showCreate} title="ایجاد ارزیابی جدید" onClose={() => setShowCreate(false)}>
        <CreateAssessmentForm onDone={() => setShowCreate(false)} />
      </Modal>
    </div>
  );
}
