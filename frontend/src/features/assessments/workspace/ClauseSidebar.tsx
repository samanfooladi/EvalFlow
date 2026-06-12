import { useMemo } from "react";
import type { ClauseAssessment, ClauseStatusValue } from "@/api/types";

export const CLAUSE_STATUS_LABELS: Record<ClauseStatusValue, string> = {
  unreviewed: "بررسی‌نشده",
  compliant: "قبول",
  finding: "عدم انطباق",
  not_applicable: "مصداق ندارد",
};

const CHIP_ACTIVE: Record<ClauseStatusValue | "all", string> = {
  all: "bg-accent-600/20 text-accent-400 ring-accent-600/40",
  unreviewed: "bg-surface-600/40 text-ink-300 ring-surface-600",
  compliant: "bg-compliant-500/15 text-compliant-400 ring-compliant-500/40",
  finding: "bg-finding-500/15 text-finding-400 ring-finding-500/40",
  not_applicable: "bg-na-400/15 text-na-400 ring-na-400/40",
};

// Progress fraction color: keyed by the derived clause verdict once every
// sub-clause is reviewed, warn-tinted while partially done.
const PROGRESS_DONE: Record<ClauseStatusValue, string> = {
  unreviewed: "text-ink-600",
  compliant: "bg-compliant-500/15 text-compliant-400",
  finding: "bg-finding-500/15 text-finding-400",
  not_applicable: "bg-na-400/15 text-na-400",
};

export type StatusFilter = ClauseStatusValue | "all";

export function ClauseSidebar({
  clauses,
  selectedId,
  onSelect,
  filter,
  onFilter,
}: {
  clauses: ClauseAssessment[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  filter: StatusFilter;
  onFilter: (f: StatusFilter) => void;
}) {
  // Filter chips count at sub-clause level — the real unit of review.
  const counts = useMemo(() => {
    const base: Record<StatusFilter, number> = {
      all: 0,
      unreviewed: 0,
      compliant: 0,
      finding: 0,
      not_applicable: 0,
    };
    for (const ca of clauses)
      for (const sub of ca.sub_assessments) {
        base.all += 1;
        base[sub.status] += 1;
      }
    return base;
  }, [clauses]);

  // A clause matches a status filter when any of its sub-clauses does.
  const filtered = useMemo(
    () =>
      filter === "all"
        ? clauses
        : clauses.filter((c) =>
            c.sub_assessments.some((s) => s.status === filter),
          ),
    [clauses, filter],
  );

  const groups = useMemo(() => {
    const map = new Map<string, ClauseAssessment[]>();
    for (const ca of filtered) {
      const list = map.get(ca.klass_title) ?? [];
      list.push(ca);
      map.set(ca.klass_title, list);
    }
    return [...map.entries()];
  }, [filtered]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap gap-1.5 border-b border-surface-800 p-3">
        {(
          ["all", "unreviewed", "compliant", "finding", "not_applicable"] as const
        ).map((key) => (
          <button
            key={key}
            onClick={() => onFilter(key)}
            className={`rounded-full px-2.5 py-1 text-xs ring-1 transition-colors ${
              filter === key
                ? CHIP_ACTIVE[key]
                : "text-ink-500 ring-surface-700 hover:text-ink-300"
            }`}
          >
            {key === "all" ? "همه" : CLAUSE_STATUS_LABELS[key]}{" "}
            <span className="fa-nums">({counts[key]})</span>
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {groups.length === 0 && (
          <p className="p-4 text-center text-xs text-ink-600">موردی یافت نشد.</p>
        )}
        {groups.map(([klass, items]) => (
          <div key={klass} className="mb-4">
            <div className="sticky top-0 z-10 bg-surface-900/95 px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-500 backdrop-blur">
              {klass}
            </div>
            <ul className="mt-0.5 space-y-px">
              {items.map((ca) => {
                const total = ca.sub_assessments.length;
                const reviewed = ca.sub_assessments.filter(
                  (s) => s.status !== "unreviewed",
                ).length;
                const progressClass =
                  reviewed === 0
                    ? "text-ink-600"
                    : reviewed < total
                      ? "bg-warn-400/15 text-warn-400"
                      : PROGRESS_DONE[ca.status];
                return (
                  <li key={ca.id}>
                    <button
                      onClick={() => onSelect(ca.id)}
                      className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-start transition-colors ${
                        selectedId === ca.id
                          ? "bg-accent-600/15 text-accent-400"
                          : "text-ink-300 hover:bg-surface-800"
                      }`}
                    >
                      <span className="min-w-0 flex-1">
                        <span
                          className="block truncate font-mono text-[11px] leading-4 text-ink-500"
                          dir="ltr"
                        >
                          {ca.clause_code}
                        </span>
                        <span className="block truncate text-xs leading-5">
                          {ca.clause_title}
                        </span>
                      </span>
                      <span
                        className={`shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-medium fa-nums ${progressClass}`}
                        title={`${reviewed} از ${total} بند بررسی شده`}
                      >
                        {reviewed}/{total}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
