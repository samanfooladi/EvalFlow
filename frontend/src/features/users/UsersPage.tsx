import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "@/api/client";
import type { Paginated, Role, User } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { Badge, Button, ErrorText, Input, Modal, Select } from "@/components/ui";

const ROLE_LABELS: Record<Role, string> = {
  admin: "مدیر سیستم",
  assessor: "ارزیاب",
  reviewer: "بازبین",
  qa_lead: "مسئول تضمین کیفیت",
};

function CreateUserForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    username: "",
    password: "",
    first_name: "",
    last_name: "",
    role: "assessor",
    assessor_code: "",
  });
  const [error, setError] = useState("");

  const create = useMutation({
    mutationFn: () => api.post("/auth/users/", form),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["users"] });
      onDone();
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!form.username || !form.password) {
      setError("نام کاربری و کلمه عبور الزامی هستند.");
      return;
    }
    create.mutate();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Input label="نام" value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
        <Input label="نام خانوادگی" value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
      </div>
      <Input label="نام کاربری" dir="ltr" autoComplete="off" value={form.username} onChange={(e) => set("username", e.target.value)} />
      <Input
        label="کلمه عبور اولیه (کاربر ملزم به تغییر آن است)"
        type="password"
        dir="ltr"
        autoComplete="new-password"
        value={form.password}
        onChange={(e) => set("password", e.target.value)}
      />
      <div className="grid grid-cols-2 gap-3">
        <Select label="نقش" value={form.role} onChange={(e) => set("role", e.target.value)}>
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Input label="کد آزمونگر" dir="ltr" value={form.assessor_code} onChange={(e) => set("assessor_code", e.target.value)} />
      </div>
      <ErrorText>{error}</ErrorText>
      <Button type="submit" disabled={create.isPending} className="w-full">
        ایجاد کاربر
      </Button>
    </form>
  );
}

export function UsersPage() {
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const isAdmin = hasRole("admin");

  const users = useQuery({
    queryKey: ["users"],
    queryFn: () =>
      api.get<Paginated<User>>("/auth/users/").then((r) => r.data.results),
  });

  const deactivate = useMutation({
    mutationFn: (id: number) => api.delete(`/auth/users/${id}/`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
  const activate = useMutation({
    mutationFn: (id: number) =>
      api.patch(`/auth/users/${id}/`, { is_active: true }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink-100">کاربران</h1>
        {isAdmin && <Button onClick={() => setShowCreate(true)}>+ کاربر جدید</Button>}
      </div>

      <div className="overflow-hidden rounded-xl border border-surface-700">
        <table className="w-full text-sm">
          <thead className="bg-surface-800 text-xs text-ink-500">
            <tr>
              <th className="px-4 py-3 text-start font-medium">کاربر</th>
              <th className="px-4 py-3 text-start font-medium">نام کاربری</th>
              <th className="px-4 py-3 text-start font-medium">نقش</th>
              <th className="px-4 py-3 text-start font-medium">کد</th>
              <th className="px-4 py-3 text-start font-medium">وضعیت</th>
              {isAdmin && <th className="px-4 py-3" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800 bg-surface-900">
            {users.data?.map((u) => (
              <tr key={u.id} className="transition-colors hover:bg-surface-800/40">
                <td className="px-4 py-3 text-[15px] font-medium text-ink-100">
                  {u.first_name ? `${u.first_name} ${u.last_name}` : "—"}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-ink-300" dir="ltr">
                  {u.username}
                </td>
                <td className="px-4 py-3 text-ink-300">{ROLE_LABELS[u.role]}</td>
                <td className="px-4 py-3 font-mono text-xs text-ink-500" dir="ltr">
                  {u.assessor_code || "—"}
                </td>
                <td className="px-4 py-3">
                  {u.is_active ? (
                    <Badge tone="compliant">فعال</Badge>
                  ) : (
                    <Badge tone="finding">غیرفعال</Badge>
                  )}
                </td>
                {isAdmin && (
                  <td className="px-4 py-3 text-end">
                    {u.is_active ? (
                      <button
                        onClick={() => deactivate.mutate(u.id)}
                        className="text-xs text-finding-400 hover:underline"
                      >
                        غیرفعال‌سازی
                      </button>
                    ) : (
                      <button
                        onClick={() => activate.mutate(u.id)}
                        className="text-xs text-compliant-400 hover:underline"
                      >
                        فعال‌سازی
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={showCreate} title="ایجاد کاربر جدید" onClose={() => setShowCreate(false)}>
        <CreateUserForm onDone={() => setShowCreate(false)} />
      </Modal>
    </div>
  );
}
