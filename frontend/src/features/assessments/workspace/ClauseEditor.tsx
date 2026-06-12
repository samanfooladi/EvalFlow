import { useEffect, useRef, useState } from "react";
import { api, apiErrorMessage } from "@/api/client";
import type {
  AttachmentInfo,
  ClauseAssessment,
  ClauseStatusValue,
  SubClauseAssessment,
} from "@/api/types";
import { Badge, Button, ErrorText, Textarea } from "@/components/ui";
import { CLAUSE_STATUS_LABELS } from "./ClauseSidebar";
import {
  useDeleteEvidence,
  useResetClauseText,
  useUpdateClause,
  useUpdateSubClause,
  useUploadEvidence,
} from "./useWorkspace";

const STATUS_BADGE_TONE: Record<ClauseStatusValue, "neutral" | "compliant" | "finding" | "warn"> = {
  unreviewed: "neutral",
  compliant: "compliant",
  finding: "finding",
  not_applicable: "warn",
};

const STATUS_OPTIONS: {
  value: ClauseStatusValue;
  active: string;
}[] = [
  {
    value: "compliant",
    active:
      "bg-compliant-500/20 text-compliant-400 shadow-[inset_0_0_0_1px] shadow-compliant-500/50",
  },
  {
    value: "finding",
    active:
      "bg-finding-500/20 text-finding-400 shadow-[inset_0_0_0_1px] shadow-finding-500/50",
  },
  {
    value: "not_applicable",
    active: "bg-na-400/20 text-na-400 shadow-[inset_0_0_0_1px] shadow-na-400/50",
  },
  {
    value: "unreviewed",
    active:
      "bg-surface-600/60 text-ink-200 shadow-[inset_0_0_0_1px] shadow-surface-500",
  },
];

/** Segmented status control — one joined group, strong selected state. */
function StatusButtons({
  value,
  disabled,
  onChange,
}: {
  value: ClauseStatusValue;
  disabled: boolean;
  onChange: (s: ClauseStatusValue) => void;
}) {
  return (
    <div
      role="radiogroup"
      className="inline-flex overflow-hidden rounded-lg ring-1 ring-surface-700"
    >
      {STATUS_OPTIONS.map((opt, i) => {
        const selected = value === opt.value;
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={`relative px-3.5 py-1.5 text-xs font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
              i > 0 ? "border-s border-surface-700" : ""
            } ${
              selected
                ? opt.active
                : "text-ink-500 hover:bg-surface-700/60 hover:text-ink-200 active:bg-surface-700"
            }`}
          >
            {selected && <span className="me-1.5">✓</span>}
            {CLAUSE_STATUS_LABELS[opt.value]}
          </button>
        );
      })}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.ceil(bytes / 1024)} KB`;
}

async function downloadAttachment(att: AttachmentInfo) {
  const res = await api.get(`/attachments/${att.id}/download/`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = att.original_name;
  link.click();
  URL.revokeObjectURL(url);
}

/** One sub-clause row: its own verdict, notes and evidence. */
function SubClauseRow({
  sub,
  index,
  assessmentId,
  editable,
}: {
  sub: SubClauseAssessment;
  index: number;
  assessmentId: string;
  editable: boolean;
}) {
  const update = useUpdateSubClause(assessmentId);
  const uploadEvidence = useUploadEvidence(assessmentId);
  const deleteEvidence = useDeleteEvidence(assessmentId);
  const fileInput = useRef<HTMLInputElement>(null);
  const [notesDraft, setNotesDraft] = useState(sub.notes);
  const [error, setError] = useState("");

  useEffect(() => {
    setNotesDraft(sub.notes);
    setError("");
  }, [sub.id, sub.notes]);

  const notesDirty = notesDraft !== sub.notes;

  function setStatus(status: ClauseStatusValue) {
    setError("");
    update.mutate(
      notesDirty ? { id: sub.id, status, notes: notesDraft } : { id: sub.id, status },
      { onError: (err) => setError(apiErrorMessage(err)) },
    );
  }

  function saveNotes() {
    setError("");
    update.mutate(
      { id: sub.id, notes: notesDraft },
      { onError: (err) => setError(apiErrorMessage(err)) },
    );
  }

  return (
    <div className="rounded-xl border border-surface-700/70 bg-surface-800/40 transition-colors hover:border-surface-600">
      <div className="flex items-start gap-3 px-4 pt-4">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-700/80 text-xs font-semibold text-ink-400 fa-nums">
          {index + 1}
        </span>
        <p className="min-w-0 flex-1 whitespace-pre-wrap text-sm leading-7 text-ink-200">
          {sub.sub_clause_text}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 px-4 pb-1 pt-3 ps-[3.25rem]">
        <StatusButtons
          value={sub.status}
          disabled={!editable || update.isPending}
          onChange={setStatus}
        />
      </div>

      <div className="px-4 pb-4 ps-[3.25rem] pt-2">
        <Textarea
          rows={2}
          value={notesDraft}
          readOnly={!editable}
          onChange={(e) => setNotesDraft(e.target.value)}
          placeholder="یادداشت ارزیاب برای این بند…"
          className="!bg-surface-900/60 text-xs"
        />
        {notesDirty && (
          <div className="mt-2 flex items-center gap-3">
            <Button
              className="!px-3 !py-1 !text-xs"
              disabled={!editable || update.isPending}
              onClick={saveNotes}
            >
              {update.isPending ? "در حال ذخیره…" : "ذخیره یادداشت"}
            </Button>
            <span className="text-xs text-warn-400">ذخیره نشده</span>
          </div>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {sub.attachments.map((att) => (
            <span
              key={att.id}
              className="group inline-flex items-center gap-1.5 rounded-md border border-surface-700 bg-surface-900/50 ps-2.5 text-xs text-ink-300"
            >
              <button
                onClick={() => void downloadAttachment(att)}
                className="py-1 hover:text-accent-400"
                title={`${att.original_name} — ${formatSize(att.size)}`}
              >
                {att.original_name}
              </button>
              {editable && (
                <button
                  onClick={() => deleteEvidence.mutate(att.id)}
                  disabled={deleteEvidence.isPending}
                  className="px-1.5 py-1 text-ink-600 hover:text-finding-400"
                  aria-label="حذف مدرک"
                >
                  ✕
                </button>
              )}
            </span>
          ))}
          {editable && (
            <>
              <input
                ref={fileInput}
                type="file"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file)
                    uploadEvidence.mutate(
                      { subId: sub.id, file },
                      { onError: (err) => setError(apiErrorMessage(err)) },
                    );
                  e.target.value = "";
                }}
              />
              <button
                disabled={uploadEvidence.isPending}
                onClick={() => fileInput.current?.click()}
                className="rounded-md border border-dashed border-surface-600 px-2.5 py-1 text-xs text-ink-500 transition-colors hover:border-accent-600/60 hover:text-accent-400 disabled:opacity-50"
              >
                {uploadEvidence.isPending ? "در حال بارگذاری…" : "+ مدرک"}
              </button>
            </>
          )}
        </div>
        {error && <div className="mt-2"><ErrorText>{error}</ErrorText></div>}
      </div>
    </div>
  );
}

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

  function saveText() {
    setError("");
    update.mutate(
      { id: clause.id, text: draft },
      { onError: (err) => setError(apiErrorMessage(err)) },
    );
  }

  const subs = clause.sub_assessments;
  const reviewed = subs.filter((s) => s.status !== "unreviewed").length;

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="border-b border-surface-800 px-8 py-6">
        <div className="mb-2 flex flex-wrap items-center gap-2.5">
          <span
            className="rounded-md bg-accent-600/10 px-2 py-0.5 font-mono text-sm font-semibold tracking-wide text-accent-400"
            dir="ltr"
          >
            {clause.clause_code}
          </span>
          <Badge tone="neutral">{clause.klass_title}</Badge>
          <Badge tone={STATUS_BADGE_TONE[clause.status]}>
            {CLAUSE_STATUS_LABELS[clause.status]}
          </Badge>
          {clause.text_edited && <Badge tone="warn">متن ویرایش‌شده</Badge>}
        </div>
        <h2 className="text-xl font-bold leading-9 text-ink-100">
          {clause.clause_title}
        </h2>
        {clause.clause_description && (
          <p className="mt-2 max-w-3xl text-sm leading-7 text-ink-400">
            {clause.clause_description}
          </p>
        )}
      </div>

      {clause.clause_objective && (
        <div className="border-b border-surface-800 px-8 py-5">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-500">
            هدف الزام
          </h3>
          <div className="max-w-3xl whitespace-pre-wrap text-sm leading-7 text-ink-300">
            {clause.clause_objective}
          </div>
        </div>
      )}

      {clause.guidance && (
        <div className="border-b border-surface-800 px-8 py-4">
          <button
            onClick={() => setShowGuidance((v) => !v)}
            className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wider text-ink-500 transition-colors hover:text-ink-300"
          >
            <span>راهنمای ارزیاب</span>
            <span>{showGuidance ? "▴" : "▾"}</span>
          </button>
          {showGuidance && (
            <div className="mt-3 max-w-3xl whitespace-pre-wrap rounded-xl border border-surface-700/60 bg-surface-800/60 p-4 text-sm leading-7 text-ink-300">
              {clause.guidance}
            </div>
          )}
        </div>
      )}

      <div className="border-b border-surface-800 px-8 py-6">
        <div className="mb-4 flex items-baseline justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-500">
            بندهای الزام
          </h3>
          <span className="text-xs text-ink-500 fa-nums">
            {reviewed} از {subs.length} بند بررسی شده
          </span>
        </div>
        <div className="space-y-3">
          {subs.map((sub, i) => (
            <SubClauseRow
              key={sub.id}
              sub={sub}
              index={i}
              assessmentId={assessmentId}
              editable={editable}
            />
          ))}
          {subs.length === 0 && (
            <p className="text-sm text-ink-600">بندی تعریف نشده است.</p>
          )}
        </div>
      </div>

      <div className="flex-1 px-8 py-6">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-500">
            تشریح آزمون انجام شده (متن سند)
          </h3>
          <button
            disabled={!editable || resetText.isPending}
            onClick={() => resetText.mutate(clause.id)}
            className="text-xs text-ink-500 underline-offset-4 transition-colors hover:text-accent-400 hover:underline disabled:opacity-50"
          >
            بازنشانی به متن پیش‌فرض
          </button>
        </div>
        <Textarea
          rows={8}
          value={draft}
          readOnly={!editable}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="با تعیین نتیجه بندها، متن پیش‌فرض سند ایجاد می‌شود…"
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
