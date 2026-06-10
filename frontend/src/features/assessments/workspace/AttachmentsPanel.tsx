import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import { Button, ErrorText } from "@/components/ui";

interface Attachment {
  id: number;
  original_name: string;
  size: number;
  uploaded_at: string;
}

function formatSize(bytes: number): string {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.ceil(bytes / 1024)} KB`;
}

export function AttachmentsPanel({
  assessmentId,
  editable,
}: {
  assessmentId: string;
  editable: boolean;
}) {
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");

  const attachments = useQuery({
    queryKey: ["attachments", assessmentId],
    queryFn: () =>
      api
        .get<Attachment[]>(`/assessments/${assessmentId}/attachments/`)
        .then((r) => r.data),
  });

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post(`/assessments/${assessmentId}/attachments/`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => {
      setError("");
      void queryClient.invalidateQueries({ queryKey: ["attachments", assessmentId] });
    },
    onError: (err) => setError(apiErrorMessage(err)),
  });

  async function download(att: Attachment) {
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

  const canUpload = editable && !hasRole("reviewer");

  return (
    <div className="space-y-3 p-4">
      {canUpload && (
        <>
          <input
            ref={fileInput}
            type="file"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
              e.target.value = "";
            }}
          />
          <Button
            variant="ghost"
            className="w-full"
            disabled={upload.isPending}
            onClick={() => fileInput.current?.click()}
          >
            {upload.isPending ? "در حال بارگذاری…" : "+ بارگذاری مستندات"}
          </Button>
          <ErrorText>{error}</ErrorText>
        </>
      )}
      <ul className="space-y-1.5">
        {attachments.data?.map((att) => (
          <li key={att.id}>
            <button
              onClick={() => void download(att)}
              className="flex w-full items-center justify-between rounded-lg border border-surface-700 px-3 py-2 text-start text-xs text-ink-300 hover:border-accent-600/50"
            >
              <span className="truncate">{att.original_name}</span>
              <span className="ms-2 shrink-0 text-ink-600 fa-nums">
                {formatSize(att.size)}
              </span>
            </button>
          </li>
        ))}
        {attachments.data?.length === 0 && (
          <li className="py-2 text-center text-xs text-ink-600">
            مستندی بارگذاری نشده است.
          </li>
        )}
      </ul>
    </div>
  );
}
