import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  Assessment,
  ClauseAssessment,
  ClauseStatusValue,
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
    mutationFn: ({
      id,
      ...patch
    }: {
      id: number;
      status?: ClauseStatusValue;
      text?: string;
    }) =>
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
