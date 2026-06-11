import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Paginated } from "@/api/types";
import { Badge, Input, Select } from "@/components/ui";

interface AuditEntry {
  id: number;
  actor_username: string | null;
  action: string;
  model: string;
  object_repr: string;
  ip: string | null;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  login_ok: "ورود موفق",
  login_fail: "ورود ناموفق",
  create: "ایجاد",
  update: "ویرایش",
  delete: "حذف",
  status_change: "تغییر وضعیت",
  export_docx: "خروجی سند",
  upload: "بارگذاری فایل",
};

const ACTION_TONES: Record<string, "finding" | "compliant" | "accent" | "neutral" | "warn"> = {
  login_fail: "finding",
  login_ok: "compliant",
  delete: "finding",
  export_docx: "accent",
  status_change: "warn",
};

export function AuditPage() {
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");

  const logs = useQuery({
    queryKey: ["audit", action, actor],
    queryFn: () => {
      const params = new URLSearchParams();
      if (action) params.set("action", action);
      if (actor) params.set("actor", actor);
      return api
        .get<Paginated<AuditEntry>>(`/audit-logs/?${params}`)
        .then((r) => r.data.results);
    },
  });

  return (
    <div className="p-8">
      <h1 className="mb-6 text-2xl font-bold text-ink-100">گزارش رویدادها</h1>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Select label="نوع رویداد" value={action} onChange={(e) => setAction(e.target.value)} className="w-44">
          <option value="">همه</option>
          {Object.entries(ACTION_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Input
          label="نام کاربری"
          dir="ltr"
          className="w-44"
          value={actor}
          onChange={(e) => setActor(e.target.value)}
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-surface-700">
        <table className="w-full text-sm">
          <thead className="bg-surface-800 text-xs text-ink-500">
            <tr>
              <th className="px-4 py-3 text-start font-medium">زمان</th>
              <th className="px-4 py-3 text-start font-medium">کاربر</th>
              <th className="px-4 py-3 text-start font-medium">رویداد</th>
              <th className="px-4 py-3 text-start font-medium">موضوع</th>
              <th className="px-4 py-3 text-start font-medium">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800 bg-surface-900">
            {logs.data?.map((entry) => (
              <tr key={entry.id}>
                <td className="whitespace-nowrap px-4 py-2.5 text-xs text-ink-500 fa-nums" dir="ltr">
                  {new Date(entry.created_at).toLocaleString("fa-IR")}
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-ink-300" dir="ltr">
                  {entry.actor_username ?? "—"}
                </td>
                <td className="px-4 py-2.5">
                  <Badge tone={ACTION_TONES[entry.action] ?? "neutral"}>
                    {ACTION_LABELS[entry.action] ?? entry.action}
                  </Badge>
                </td>
                <td className="max-w-md truncate px-4 py-2.5 text-xs text-ink-300">
                  {entry.object_repr || entry.model}
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-ink-500" dir="ltr">
                  {entry.ip ?? "—"}
                </td>
              </tr>
            ))}
            {logs.data?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-xs text-ink-600">
                  رویدادی یافت نشد.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
