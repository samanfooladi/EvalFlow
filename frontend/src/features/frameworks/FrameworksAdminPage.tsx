import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "@/api/client";
import type { Framework, Paginated } from "@/api/types";
import { Badge, Button, ErrorText, Textarea } from "@/components/ui";

interface Requirement {
  id: number;
  code: string;
  title: string;
  klass_title: string;
  guidance: string;
}

interface DefaultText {
  id: number;
  framework: number;
  status: "compliant" | "finding" | "not_applicable";
  template: string;
}

const TEMPLATE_LABELS: Record<DefaultText["status"], string> = {
  compliant: "متن پیش‌فرض «قبول»",
  finding: "متن پیش‌فرض «عدم انطباق»",
  not_applicable: "متن پیش‌فرض «مصداق ندارد»",
};

function TemplateEditor({ template }: { template: DefaultText }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(template.template);
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: () =>
      api.patch(`/default-texts/${template.id}/`, { template: draft }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["default-texts"] }),
    onError: (err) => setError(apiErrorMessage(err)),
  });

  return (
    <div className="rounded-xl border border-surface-700 bg-surface-900 p-4">
      <h3 className="mb-2 text-sm font-medium text-ink-300">
        {TEMPLATE_LABELS[template.status]}
      </h3>
      <Textarea rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} />
      <p className="mt-2 text-xs text-ink-600" dir="ltr">
        {"{{clause_code}} {{clause_title}} {{requirement_title}} {{product_name}} {{company_name}}"}
      </p>
      <div className="mt-2 flex items-center gap-3">
        <Button
          variant="ghost"
          disabled={draft === template.template || save.isPending}
          onClick={() => save.mutate()}
        >
          ذخیره
        </Button>
        <ErrorText>{error}</ErrorText>
      </div>
    </div>
  );
}

function GuidanceEditor({ requirement }: { requirement: Requirement }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(requirement.guidance);
  const save = useMutation({
    mutationFn: () =>
      api.patch(`/requirements/${requirement.id}/`, { guidance: draft }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["requirements"] }),
  });

  return (
    <div className="rounded-lg border border-surface-700 p-3">
      <div className="mb-2 flex items-center gap-2 text-sm">
        <span className="font-mono text-xs text-accent-400" dir="ltr">
          {requirement.code}
        </span>
        <span className="text-ink-100">{requirement.title}</span>
        <Badge tone="neutral">{requirement.klass_title}</Badge>
      </div>
      <Textarea
        rows={2}
        placeholder="راهنمای ارزیاب برای این الزام…"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="mt-2">
        <Button
          variant="ghost"
          disabled={draft === requirement.guidance || save.isPending}
          onClick={() => save.mutate()}
        >
          ذخیره راهنما
        </Button>
      </div>
    </div>
  );
}

export function FrameworksAdminPage() {
  const [selected, setSelected] = useState<Framework | null>(null);

  const frameworks = useQuery({
    queryKey: ["frameworks"],
    queryFn: () =>
      api.get<Paginated<Framework>>("/frameworks/").then((r) => r.data.results),
  });
  const templates = useQuery({
    queryKey: ["default-texts", selected?.id],
    enabled: selected != null,
    queryFn: () =>
      api
        .get<Paginated<DefaultText>>(`/default-texts/?framework=${selected!.id}`)
        .then((r) => r.data.results),
  });
  const requirements = useQuery({
    queryKey: ["requirements", selected?.id],
    enabled: selected != null,
    queryFn: () =>
      api
        .get<Paginated<Requirement>>(`/requirements/?framework=${selected!.id}`)
        .then((r) => r.data.results),
  });

  return (
    <div className="p-8">
      <h1 className="mb-2 text-2xl font-bold text-ink-100">چارچوب‌های الزامات</h1>
      <p className="mb-6 text-sm text-ink-500">
        ویرایش متن‌های پیش‌فرض و راهنمای ارزیاب. ساختار کامل الزامات از طریق
        دستور load_frameworks یا پنل مدیریت جنگو قابل به‌روزرسانی است.
      </p>

      <div className="mb-6 flex flex-wrap gap-3">
        {frameworks.data?.map((fw) => (
          <button
            key={fw.id}
            onClick={() => setSelected(fw)}
            className={`rounded-xl border p-4 text-start transition-colors ${
              selected?.id === fw.id
                ? "border-accent-500 bg-accent-600/10"
                : "border-surface-700 bg-surface-900 hover:border-surface-600"
            }`}
          >
            <div className="flex items-center gap-2">
              <Badge tone={fw.kind === "TRP" ? "accent" : "warn"}>{fw.kind}</Badge>
              <span className="font-medium text-ink-100">{fw.title}</span>
            </div>
            <div className="mt-1 text-xs text-ink-500 fa-nums">
              {fw.requirements_count} الزام · {fw.clauses_count} بند
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <section className="space-y-3">
            <h2 className="text-sm font-medium text-ink-500">متن‌های پیش‌فرض</h2>
            {templates.data?.map((t) => (
              <TemplateEditor key={`${t.id}-${t.template.length}`} template={t} />
            ))}
          </section>
          <section>
            <h2 className="mb-3 text-sm font-medium text-ink-500">
              راهنمای ارزیاب به تفکیک الزام
            </h2>
            <div className="max-h-[60vh] space-y-2 overflow-y-auto pe-2">
              {requirements.data?.map((r) => (
                <GuidanceEditor key={r.id} requirement={r} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
