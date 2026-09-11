import { lazy, Suspense, useSyncExternalStore } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { RouteFocus } from "./components/layout/RouteFocus";
import { PageSkeleton } from "./components/ui/Skeleton";
import { session } from "./lib/session";

const Login = lazy(() => import("./pages/auth").then((m) => ({ default: m.LoginPage })));
const Register = lazy(() => import("./pages/auth").then((m) => ({ default: m.RegisterPage })));
const Dashboard = lazy(() => import("./pages/dashboard").then((m) => ({ default: m.ManagementDashboardPage })));
const People = lazy(() => import("./pages/people").then((m) => ({ default: m.PeoplePage })));
const AddPerson = lazy(() => import("./pages/add-person").then((m) => ({ default: m.AddPersonPage })));
const Profile = lazy(() => import("./pages/profile").then((m) => ({ default: m.PersonPage })));
const Opportunities = lazy(() => import("./pages/opportunities").then((m) => ({ default: m.OpportunitiesPage })));
const Opportunity = lazy(() => import("./pages/opportunity").then((m) => ({ default: m.OpportunityPage })));
const Pipeline = lazy(() => import("./pages/pipeline").then((m) => ({ default: m.PipelinePage })));
const Settings = lazy(() => import("./pages/settings").then((m) => ({ default: m.OrganizationPage })));
function Protected() {
  useSyncExternalStore(session.subscribe, session.snapshot, () => "");
  return session.token() ? <AppLayout /> : <Navigate to="/login" replace />;
}
export function App() {
  return <ErrorBoundary><RouteFocus /><Suspense fallback={<PageSkeleton />}><Routes>
    <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} />
    <Route element={<Protected />}><Route path="/" element={<Dashboard />} /><Route path="/people" element={<People />} /><Route path="/people/new" element={<AddPerson />} /><Route path="/people/:personId" element={<Profile />} /><Route path="/opportunities" element={<Opportunities />} /><Route path="/opportunities/:opportunityId" element={<Opportunity />} /><Route path="/pipeline" element={<Pipeline />} /><Route path="/organization" element={<Settings />} /><Route path="*" element={<div className="cf-page"><h1 className="text-3xl font-semibold">Page not found</h1><Link to="/" className="cf-link mt-5">Return to overview</Link></div>} /></Route>
  </Routes></Suspense></ErrorBoundary>;
}
