/**
 * React context for Cognito authentication state.
 *
 * AuthProvider wraps the app and restores the session on mount.
 * useAuth() provides sign-in, sign-up, sign-out, and token access.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import * as auth from "./auth";

interface AuthState {
  /** Whether the initial session check is still in progress. */
  loading: boolean;
  /** The current Cognito session, or null if not authenticated. */
  session: CognitoUserSession | null;
  /** Sign in with email and password. */
  signIn: (email: string, password: string) => Promise<void>;
  /** Register a new account. */
  signUp: (email: string, password: string) => Promise<void>;
  /** Confirm registration with verification code. */
  confirmSignUp: (email: string, code: string) => Promise<void>;
  /** Sign out and clear session. */
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<CognitoUserSession | null>(null);

  // Restore session on mount
  useEffect(() => {
    auth
      .getCurrentSession()
      .then(setSession)
      .finally(() => setLoading(false));
  }, []);

  const handleSignIn = useCallback(async (email: string, password: string) => {
    const s = await auth.signIn(email, password);
    setSession(s);
  }, []);

  const handleSignUp = useCallback(async (email: string, password: string) => {
    await auth.signUp(email, password);
  }, []);

  const handleConfirmSignUp = useCallback(
    async (email: string, code: string) => {
      await auth.confirmSignUp(email, code);
    },
    [],
  );

  const handleSignOut = useCallback(() => {
    auth.signOut();
    setSession(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        loading,
        session,
        signIn: handleSignIn,
        signUp: handleSignUp,
        confirmSignUp: handleConfirmSignUp,
        signOut: handleSignOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
