/* Auth state for the app: who's signed in, plus login/logout.
   On mount, if a token is present we hydrate the current user from /auth/me so a
   refresh keeps the session. Guarded routes read `user` to decide access. */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokens, type UserOut } from "./api";

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  /** False for the read-only "viewer" role; gates create/edit/delete UI. */
  canWrite: boolean;
  login: (username: string, password: string, totp?: string) => Promise<UserOut>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      if (!tokens.access) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.me();
        if (active) setUser(me);
      } catch {
        tokens.clear();
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string, totp?: string) => {
    await api.login(username, password, totp);
    const me = await api.me();
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  const canWrite = user != null && user.role !== "viewer";

  return (
    <AuthContext.Provider value={{ user, loading, canWrite, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
