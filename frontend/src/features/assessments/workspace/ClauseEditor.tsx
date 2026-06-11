import { useEffect, useState } from "react";
import { apiErrorMessage } from "@/api/client";
import type { ClauseAssessment, ClauseStatusValue } from "@/api/types";
import { Badge, Button, ErrorText, Textarea } from "@/components/ui";
import { CLAUSE_STATUS_LABELS } from "./ClauseSidebar";
import { useResetClauseText, useUpdateClause } from "./useWorkspace";

const STATUS_OPTIONS: {
  value: ClauseStatusValue;
  ring: string;
  active: string;
}[] = [
  {
    value: "compliant",
    ring: "ring-compliant-500/40",
    active: "bg-compliant-500/15 text-compliant-400",
  },
  {
    value: "finding",
    ring: "ring-finding-500/40",
    active: "bg-finding-500/15 text-finding-400",
  },
  {
    value: "not_applicable",
    ring: "ring-na-400/40",
    active: "bg-na-400/15 text-na-400",
  },
  {
    value: "unreviewed",
    ring: "ring-surface-600",
    active: "bg-surface-600/40 text-ink-300",
  },
];

export function ClauseEditor({
  clause,
  assessmentId,
  editable,
}: {
  clause: ClauseAssessment;
  assessmentId: string;
  editable: boolean;
}) {
  const update = useUpdateClause(assessmentId);
  const resetText = useResetClauseText(assessmentId);
  const [draft, setDraft] = useState(clause.text);
  const [error, setError] = useState("");
  const [showGuidance, setShowGuidance] = useState(false);

  // Re-sync local draft when switching clause or after server updates.
  useEffect(() => {
    setDraft(clause.text);
    setError("");
  }, [clause.id, clause.text]);

  const dirty = draft !== clause.text;

  function setStatus(status: ClauseStatusValue) {
    setError("");
    update.mutate(
      // include text only if the user has unsaved edits, so the backend
      // renders the default text for the new status otherwise
      dirty ? { id: clause.id, status, text: draft } : { id: clause.id, status },
      { onError: (err) => setError(apiErrorMessage(err)) },
    );
  }

  function saveText() {
    setError("");
    update.mutate(
      { id: clause.id, text: draft },
      { onError: (err) => setError(apiErrorMessage(err)) },
    );
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="border-b border-surface-800 p-6">
        <div className="mb-1 flex items-center gap-3">
          <span className="font-mono text-sm text-accent-400" dir="ltr">
            {clause.clause_code}
          </span>
          <Badge tone="neutral">{clause.klass_title}</Badge>
          {clause.text_edited && <Badge tone="warn">متن ویرایش‌شده</Badge>}
        </div>
        <h2 className="text-lg font-bold text-ink-100">{clause.clause_title}</h2>
        {clause.clause_description && (
          <p className="mt-2 text-sm leading-7 text-ink-300">
            {clause.clause_description}
          </p>
        )}
      </div>

      {clause.clause_objective && (
        <div className="border-b border-surface-800 p-6">
          <h3 className="mb-2 text-sm font-medium text-ink-500">هدف الزام</h3>
          <div className="whitespace-pre-wrap text-sm leading-7 text-ink-300">
            {clause.clause_objective}
          </div>
        </div>
      )}

      {clause.guidance && (
        <div className="border-b border-surface-800 px-6 py-4">
          <button
            onClick={() => setShowGuidance((v) => !v)}
            className="flex w-full items-center justify-between text-sm font-medium text-ink-500 hover:text-ink-300"
          >
            <span>راهنمای ارزیاب</span>
            <span>{showGuidance ? "▴" : "▾"}</span>
          </button>
          {showGuidance && (
            <div className="mt-3 whitespace-pre-wrap rounded-lg bg-surface-800/60 p-4 text-sm leading-7 text-ink-300">
              {clause.guidance}
            </div>
          )}
        </div>
      )}

      <div className="flex-1 p-6">
        <h3 className="mb-3 text-sm font-medium text-ink-500">نتیجه آزمون</h3>
        <div className="mb-6 flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              disabled={!editable || update.isPending}
              onClick={() => setStatus(opt.value)}
              className={`rounded-lg px-4 py-2 text-sm ring-1 transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                clause.status === opt.value
                  ? `${opt.active} ${opt.ring} font-medium`
                  : "text-ink-500 ring-surface-700 hover:text-ink-300"
              }`}
            >
              {CLAUSE_STATUS_LABELS[opt.value]}
            </button>
          ))}
        </div>

        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-medium text-ink-500">
            تشریح آزمون انجام شده
          </h3>
          <button
            disabled={!editable || resetText.isPending}
            onClick={() => resetText.mutate(clause.id)}
            className="text-xs text-ink-500 underline-offset-4 hover:text-accent-400 hover:underline disabled:opacity-50"
          >
            بازنشانی به متن پیش‌فرض
          </button>
        </div>
        <Textarea
          rows={8}
          value={draft}
          readOnly={!editable}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="با انتخاب نتیجه آزمون، متن پیش‌فرض ایجاد می‌شود…"
        />
        <div className="mt-3 flex items-center gap-3">
          <Button
            onClick={saveText}
            disabled={!editable || !dirty || update.isPending}
          >
            {update.isPending ? "در حال ذخیره…" : "ذخیره متن"}
          </Button>
          {dirty && (
            <span className="text-xs text-warn-400">تغییرات ذخیره نشده دارید</span>
          )}
        </div>
        <div className="mt-3">
          <ErrorText>{error}</ErrorText>
        </div>
      </div>
    </div>
  );
}
