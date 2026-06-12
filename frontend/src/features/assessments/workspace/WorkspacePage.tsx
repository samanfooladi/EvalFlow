import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiErrorMessage } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import { Badge, Button } from "@/components/ui";
import { STATUS_LABELS } from "../AssessmentsPage";
import { AttachmentsPanel } from "./AttachmentsPanel";
import { ClauseEditor } from "./ClauseEditor";
import { ClauseSidebar, type StatusFilter } from "./ClauseSidebar";
import {
  downloadExport,
  useAssessment,
  useClauseAssessments,
  useTransition,
} from "./useWorkspace";

export function WorkspacePage() {
  const { id = "" } = useParams();
  const { user, hasRole } = useAuth();
  const assessment = useAssessment(id);
  const clauses = useClauseAssessments(id);
  const transitionMutation = useTransition(id);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [banner, setBanner] = useState("");
  const [showAttachments, setShowAttachments] = useState(false);

  const selected = useMemo(
    () => clauses.data?.find((c) => c.id === selectedId) ?? clauses.data?.[0] ?? null,
    [clauses.data, selectedId],
  );

  if (assessment.isLoading || clauses.isLoading) {
    return <div className="p-8 text-ink-500">در حال بارگذاری…</div>;
  }
  if (!assessment.data) {
    return (
      <div className="p-8">
        <p className="text-ink-300">ارزیابی یافت نشد یا به شما تخصیص داده نشده است.</p>
        <Link to="/" className="mt-2 inline-block text-sm text-accent-400">
          بازگشت به فهرست
        </Link>
      </div>
    );
  }

  const a = assessment.data;
  // Header progress counts sub-clauses — the unit assessors actually review.
  const counts = a.sub_status_counts;
  const done = counts.total - counts.unreviewed;
  const editable =
    a.status === "under_assessment" &&
    (hasRole("admin", "qa_lead") ||
      (user?.role === "assessor" && a.assessor === user.id));

  // Available transition per role/state (backend enforces; this is just UI).
  const transitions: { to: string; label: string; variant: "primary" | "ghost" | "danger" }[] = [];
  if (a.status === "under_assessment" && (hasRole("admin", "qa_lead") || a.assessor === user?.id)) {
    transitions.push({ to: "under_review", label: "ارسال برای بازبینی", variant: "primary" });
  }
  if (a.status === "under_review" && (hasRole("admin", "qa_lead") || (user?.role === "reviewer" && a.reviewer === user.id))) {
    transitions.push({ to: "completed", label: "تأیید نهایی", variant: "primary" });
    transitions.push({ to: "under_assessment", label: "بازگشت برای اصلاح", variant: "danger" });
  }
  if (a.status === "completed" && hasRole("admin", "qa_lead")) {
    transitions.push({ to: "under_review", label: "بازگشایی", variant: "ghost" });
  }

  async function exportDoc(type: "trp" | "vtr" | "brp") {
    setBanner("");
    try {
      await downloadExport(id, type, `${type.toUpperCase()}-${a.system_name}.docx`);
    } catch (err) {
      // Blob error responses need decoding before display
      const resp = (err as { response?: { data?: Blob } }).response;
      if (resp?.data instanceof Blob) {
        try {
          const parsed = JSON.parse(await resp.data.text());
          setBanner(
            typeof parsed.detail === "string"
              ? parsed.detail
              : Object.values(parsed).flat().join(" "),
          );
          return;
        } catch {
          /* fall through */
        }
      }
      setBanner(apiErrorMessage(err));
    }
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-surface-800 bg-surface-900 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-ink-500 hover:text-ink-100" aria-label="بازگشت">
              →
            </Link>
            <div>
              <h1 className="font-bold text-ink-100">
                {a.system_name}
                <span className="ms-2 text-sm font-normal text-ink-500">
                  {a.company_name}
                </span>
              </h1>
              <div className="mt-1 flex items-center gap-2 text-xs">
                <Badge tone={a.kind === "TRP" ? "accent" : "warn"}>{a.kind}</Badge>
                <Badge tone="neutral">{STATUS_LABELS[a.status]}</Badge>
                <span className="text-ink-500 fa-nums">
                  {done} از {counts.total} بند بررسی شده
                </span>
                {a.compliance_percent != null && (
                  <span className="text-ink-500 fa-nums">
                    انطباق: {a.compliance_percent}٪
                  </span>
                )}
                {counts.finding > 0 && (
                  <Badge tone="finding">{counts.finding} عدم انطباق</Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => setShowAttachments((v) => !v)}>
              مستندات
            </Button>
            <Button
              variant="ghost"
              onClick={() => void exportDoc(a.kind === "TRP" ? "trp" : "vtr")}
            >
              خروجی {a.kind}
            </Button>
            <Button variant="ghost" onClick={() => void exportDoc("brp")}>
              خروجی BRP
            </Button>
            {transitions.map((t) => (
              <Button
                key={t.to}
                variant={t.variant}
                disabled={transitionMutation.isPending}
                onClick={() =>
                  transitionMutation.mutate(t.to, {
                    onError: (err) => setBanner(apiErrorMessage(err)),
                  })
                }
              >
                {t.label}
              </Button>
            ))}
          </div>
        </div>
        {banner && (
          <p className="mt-3 rounded-lg bg-finding-500/10 px-3 py-2 text-sm text-finding-400">
            {banner}
          </p>
        )}
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="w-80 shrink-0 border-e border-surface-800 bg-surface-900">
          <ClauseSidebar
            clauses={clauses.data ?? []}
            selectedId={selected?.id ?? null}
            onSelect={setSelectedId}
            filter={filter}
            onFilter={setFilter}
          />
        </aside>
        <section className="min-w-0 flex-1">
          {selected ? (
            <ClauseEditor clause={selected} assessmentId={id} editable={editable} />
          ) : (
            <div className="p-8 text-ink-500">بندی برای نمایش وجود ندارد.</div>
          )}
        </section>
        {showAttachments && (
          <aside className="w-72 shrink-0 overflow-y-auto border-s border-surface-800 bg-surface-900">
            <AttachmentsPanel assessmentId={id} editable={editable} />
          </aside>
        )}
      </div>
    </div>
  );
}
