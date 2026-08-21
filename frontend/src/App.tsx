import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { session } from "./lib/session";
import {
  AddPersonPage,
  LoginPage,
  OrganizationPage,
  PeoplePage,
  PersonPage,
  RegisterPage,
} from "./pages";
import { ManagementDashboardPage } from "./pages/dashboard";
import {
  OpportunityPage,
  OpportunitiesPage,
} from "./pages/opportunities";
import { PipelinePage } from "./pages/pipeline";

function Protected() {
  return session.token() ? (
    <AppLayout />
  ) : (
    <Navigate to="/login" replace />
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<Protected />}>
        <Route path="/" element={<ManagementDashboardPage />} />
        <Route path="/opportunities" element={<OpportunitiesPage />} />
        <Route
          path="/opportunities/:opportunityId"
          element={<OpportunityPage />}
        />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/people" element={<PeoplePage />} />
        <Route path="/people/new" element={<AddPersonPage />} />
        <Route path="/people/:personId" element={<PersonPage />} />
        <Route path="/organization" element={<OrganizationPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
