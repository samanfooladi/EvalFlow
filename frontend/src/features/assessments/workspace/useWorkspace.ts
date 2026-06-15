import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  Assessment,
  ClauseAssessment,
  ClauseImage,
  ClauseStatusValue,
  SubClauseAssessment,
} from "@/api/types";

export function useAssessment(id: string) {
  return useQuery({
    queryKey: ["assessment", id],
    queryFn: () => api.get<Assessment>(`/assessments/${id}/`).then((r) => r.data),
  });
}

export function useClauseAssessments(id: string) {
  return useQuery({
    queryKey: ["clause-assessments", id],
    queryFn: () =>
      api
        .get<ClauseAssessment[]>(`/assessments/${id}/clause-assessments/`)
        .then((r) => r.data),
  });
}

export function useUpdateClause(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    // Only the document text is editable here; the verdict is derived from
    // the sub-clauses server-side.
    mutationFn: ({ id, ...patch }: { id: number; text?: string }) =>
      api
        .patch<ClauseAssessment>(`/clause-assessments/${id}/`, patch)
        .then((r) => r.data),
    onSuccess: (updated) => {
      queryClient.setQueryData<ClauseAssessment[]>(
        ["clause-assessments", assessmentId],
        (old) => old?.map((ca) => (ca.id === updated.id ? updated : ca)),
      );
      void queryClient.invalidateQueries({ queryKey: ["assessment", assessmentId] });
    },
  });
}

export function useResetClauseText(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api
        .post<ClauseAssessment>(`/clause-assessments/${id}/reset-text/`)
        .then((r) => r.data),
    onSuccess: (updated) => {
      queryClient.setQueryData<ClauseAssessment[]>(
        ["clause-assessments", assessmentId],
        (old) => old?.map((ca) => (ca.id === updated.id ? updated : ca)),
      );
    },
  });
}

export function useUpdateSubClause(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...patch
    }: {
      id: number;
      status?: ClauseStatusValue;
      notes?: string;
    }) =>
      api
        .patch<SubClauseAssessment>(`/sub-clause-assessments/${id}/`, patch)
        .then((r) => r.data),
    // The parent verdict and default text are recomputed server-side, so
    // refetch the whole clause list rather than patching the cache.
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["clause-assessments", assessmentId],
      });
      void queryClient.invalidateQueries({ queryKey: ["assessment", assessmentId] });
    },
  });
}

export function useUploadEvidence(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ subId, file }: { subId: number; file: File }) => {
      const form = new FormData();
      form.append("file", file);
      form.append("sub_clause_assessment", String(subId));
      return api.post(`/assessments/${assessmentId}/attachments/`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["clause-assessments", assessmentId],
      });
      void queryClient.invalidateQueries({ queryKey: ["attachments", assessmentId] });
    },
  });
}

export function useDeleteEvidence(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (attachmentId: number) =>
      api.delete(`/attachments/${attachmentId}/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["clause-assessments", assessmentId],
      });
      void queryClient.invalidateQueries({ queryKey: ["attachments", assessmentId] });
    },
  });
}

export function useClauseImages(clauseId: number) {
  return useQuery({
    queryKey: ["clause-images", clauseId],
    queryFn: () =>
      api.get<ClauseImage[]>(`/clause-assessments/${clauseId}/images/`).then((r) => r.data),
  });
}

export function useUploadClauseImage(clauseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api
        .post<ClauseImage>(`/clause-assessments/${clauseId}/images/`, form, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        .then((r) => r.data);
    },
    onSuccess: (image) => {
      queryClient.setQueryData<ClauseImage[]>(
        ["clause-images", clauseId],
        (old) => (old ? [...old, image] : [image]),
      );
    },
  });
}

/** Fetch an authenticated clause image and expose it as an object URL for
 * <img src>, since <img> tags can't carry the Bearer auth header. */
export function useClauseImageBlobUrl(url: string | undefined) {
  return useQuery({
    queryKey: ["clause-image-blob", url],
    queryFn: () =>
      api.get(url as string, { responseType: "blob" }).then((r) => URL.createObjectURL(r.data as Blob)),
    enabled: !!url,
    staleTime: Infinity,
  });
}

export function useTransition(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (status: string) =>
      api
        .post<Assessment>(`/assessments/${assessmentId}/transition/`, { status })
        .then((r) => r.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assessment", assessmentId] });
      void queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
  });
}

export async function downloadExport(
  assessmentId: string,
  type: "trp" | "vtr" | "brp",
  filename: string,
) {
  const res = await api.get(`/assessments/${assessmentId}/export/?type=${type}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
