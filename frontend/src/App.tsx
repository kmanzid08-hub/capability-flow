import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { session } from "./lib/session";
import { AddPersonPage, DashboardPage, LoginPage, OrganizationPage, PeoplePage, PersonPage, RegisterPage } from "./pages";

function Protected() { return session.token() ? <AppLayout /> : <Navigate to="/login" replace />; }
export function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route element={<Protected />}>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/people" element={<PeoplePage />} />
      <Route path="/people/new" element={<AddPersonPage />} />
      <Route path="/people/:personId" element={<PersonPage />} />
      <Route path="/organization" element={<OrganizationPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}

