import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "@/api/client";
import type { Company, Paginated, ProductSystem } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import {
  Badge,
  Button,
  EmptyState,
  ErrorText,
  Input,
  Modal,
  Textarea,
} from "@/components/ui";

function CompanyForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [error, setError] = useState("");
  const create = useMutation({
    mutationFn: () =>
      api.post("/companies/", { name, name_en: nameEn }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      onDone();
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("نام شرکت الزامی است.");
      return;
    }
    create.mutate();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Input label="نام شرکت" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      <Input label="نام انگلیسی (اختیاری)" dir="ltr" value={nameEn} onChange={(e) => setNameEn(e.target.value)} />
      <ErrorText>{error}</ErrorText>
      <Button type="submit" disabled={create.isPending} className="w-full">
        ثبت شرکت
      </Button>
    </form>
  );
}

function SystemForm({ companyId, onDone }: { companyId: number; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const create = useMutation({
    mutationFn: () =>
      api.post("/systems/", { company: companyId, name, version, description }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["systems"] });
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      onDone();
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("نام سامانه الزامی است.");
      return;
    }
    create.mutate();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Input label="نام سامانه" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      <Input label="نسخه" dir="ltr" value={version} onChange={(e) => setVersion(e.target.value)} />
      <Textarea
        label="مشخصات فنی (در سند چاپ می‌شود)"
        rows={3}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <ErrorText>{error}</ErrorText>
      <Button type="submit" disabled={create.isPending} className="w-full">
        ثبت سامانه
      </Button>
    </form>
  );
}

export function CompaniesPage() {
  const { hasRole } = useAuth();
  const canWrite = hasRole("admin", "qa_lead");
  const [selected, setSelected] = useState<Company | null>(null);
  const [showCompanyForm, setShowCompanyForm] = useState(false);
  const [showSystemForm, setShowSystemForm] = useState(false);

  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: () =>
      api.get<Paginated<Company>>("/companies/").then((r) => r.data.results),
  });
  const systems = useQuery({
    queryKey: ["systems", selected?.id],
    enabled: selected != null,
    queryFn: () =>
      api
        .get<Paginated<ProductSystem>>(`/systems/?company=${selected!.id}`)
        .then((r) => r.data.results),
  });

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink-100">شرکت‌ها و سامانه‌ها</h1>
        {canWrite && (
          <Button onClick={() => setShowCompanyForm(true)}>+ شرکت جدید</Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-medium text-ink-500">شرکت‌ها</h2>
          {companies.data?.length === 0 && (
            <EmptyState>هنوز شرکتی ثبت نشده است.</EmptyState>
          )}
          <ul className="space-y-2">
            {companies.data?.map((company) => (
              <li key={company.id}>
                <button
                  onClick={() => setSelected(company)}
                  className={`w-full rounded-xl border p-4 text-start transition-colors ${
                    selected?.id === company.id
                      ? "border-accent-500 bg-accent-600/10"
                      : "border-surface-700 bg-surface-900 hover:border-surface-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-ink-100">{company.name}</span>
                    <Badge tone="neutral">{company.systems_count} سامانه</Badge>
                  </div>
                  {company.name_en && (
                    <div className="mt-1 text-xs text-ink-500" dir="ltr">
                      {company.name_en}
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-ink-500">
              {selected ? `سامانه‌های ${selected.name}` : "سامانه‌ها"}
            </h2>
            {canWrite && selected && (
              <Button variant="ghost" onClick={() => setShowSystemForm(true)}>
                + سامانه جدید
              </Button>
            )}
          </div>
          {!selected && <EmptyState>برای مشاهده سامانه‌ها یک شرکت انتخاب کنید.</EmptyState>}
          {selected && systems.data?.length === 0 && (
            <EmptyState>برای این شرکت سامانه‌ای ثبت نشده است.</EmptyState>
          )}
          <ul className="space-y-2">
            {systems.data?.map((system) => (
              <li
                key={system.id}
                className="rounded-xl border border-surface-700 bg-surface-900 p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink-100">{system.name}</span>
                  {system.version && (
                    <Badge tone="accent">نسخه {system.version}</Badge>
                  )}
                </div>
                {system.description && (
                  <p className="mt-2 line-clamp-2 text-xs leading-6 text-ink-500">
                    {system.description}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <Modal open={showCompanyForm} title="ثبت شرکت جدید" onClose={() => setShowCompanyForm(false)}>
        <CompanyForm onDone={() => setShowCompanyForm(false)} />
      </Modal>
      <Modal
        open={showSystemForm && selected != null}
        title={`سامانه جدید برای ${selected?.name ?? ""}`}
        onClose={() => setShowSystemForm(false)}
      >
        {selected && (
          <SystemForm companyId={selected.id} onDone={() => setShowSystemForm(false)} />
        )}
      </Modal>
    </div>
  );
}
