import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import { AppShell } from "./components/AppShell";
import { Login } from "./pages/Login";
import { ForgotPassword } from "./pages/ForgotPassword";
import { Dashboard } from "./pages/Dashboard";
import { Recruits } from "./pages/Recruits";
import { RecruitDetail } from "./pages/RecruitDetail";
import { Cadets, CadetDetail } from "./pages/Cadets";
import { Contacts, ContactDetail } from "./pages/Contacts";
import { Events } from "./pages/Events";
import { EventDetail } from "./pages/EventDetail";
import { FollowUps } from "./pages/FollowUps";
import { Materials } from "./pages/Materials";
import { ImportRecruits } from "./pages/ImportRecruits";
import { Pipeline } from "./pages/Pipeline";
import { Territory } from "./pages/Territory";
import { Profile } from "./pages/Profile";
import { Admin } from "./pages/Admin";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 } },
});

function FullPage({ children }: { children: ReactNode }) {
  return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--muted)" }}>{children}</div>;
}

/** Gate: wait for auth hydration, then require a signed-in user. */
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullPage>Loading…</FullPage>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** If already signed in, keep users out of /login. */
function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullPage>Loading…</FullPage>;
  if (user) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
            <Route
              path="/forgot-password"
              element={<RedirectIfAuthed><ForgotPassword /></RedirectIfAuthed>}
            />
            <Route
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/recruits" element={<Recruits />} />
              <Route path="/recruits/:id" element={<RecruitDetail />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/follow-ups" element={<FollowUps />} />
              <Route path="/cadets" element={<Cadets />} />
              <Route path="/cadets/:id" element={<CadetDetail />} />
              <Route path="/contacts" element={<Contacts />} />
              <Route path="/contacts/:id" element={<ContactDetail />} />
              <Route path="/events" element={<Events />} />
              <Route path="/events/:id" element={<EventDetail />} />
              <Route path="/map" element={<Territory />} />
              <Route path="/import" element={<ImportRecruits />} />
              <Route path="/materials" element={<Materials />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
