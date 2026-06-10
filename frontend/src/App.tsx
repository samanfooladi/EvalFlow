import { Route, Routes } from "react-router-dom";
import { RequireAuth, RequireRole } from "./auth/RequireAuth";
import { AppShell } from "./components/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { AssessmentsPage } from "./features/assessments/AssessmentsPage";
import { CompaniesPage } from "./features/companies/CompaniesPage";
import { WorkspacePage } from "./features/assessments/workspace/WorkspacePage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<AssessmentsPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/assessments/:id" element={<WorkspacePage />} />
          <Route element={<RequireRole roles={["admin", "qa_lead"]} />}>
            {/* Admin pages land in M7 */}
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}
