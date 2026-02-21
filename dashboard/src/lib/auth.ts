/**
 * Cognito authentication utilities.
 *
 * Wraps amazon-cognito-identity-js for sign-in, sign-up, token retrieval.
 * When VITE_COGNITO_USER_POOL_ID is empty, auth is disabled (demo mode).
 */

import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from "amazon-cognito-identity-js";

const USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID ?? "";
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID ?? "";

/** Returns true when Cognito auth is configured. */
export function isAuthEnabled(): boolean {
  return USER_POOL_ID.length > 0 && CLIENT_ID.length > 0;
}

function getUserPool(): CognitoUserPool {
  return new CognitoUserPool({
    UserPoolId: USER_POOL_ID,
    ClientId: CLIENT_ID,
  });
}

function makeCognitoUser(email: string): CognitoUser {
  return new CognitoUser({
    Username: email,
    Pool: getUserPool(),
  });
}

/** Sign in with email and password. Returns the session on success. */
export function signIn(
  email: string,
  password: string,
): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    const user = makeCognitoUser(email);
    const authDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    user.authenticateUser(authDetails, {
      onSuccess: (session) => resolve(session),
      onFailure: (err) => reject(err as Error),
    });
  });
}

/** Register a new user with email and password. */
export function signUp(email: string, password: string): Promise<void> {
  return new Promise((resolve, reject) => {
    getUserPool().signUp(email, password, [], [], (err) => {
      if (err) {
        reject(err as Error);
        return;
      }
      resolve();
    });
  });
}

/** Confirm registration with the verification code sent to email. */
export function confirmSignUp(email: string, code: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const user = makeCognitoUser(email);
    user.confirmRegistration(code, true, (err) => {
      if (err) {
        reject(err as Error);
        return;
      }
      resolve();
    });
  });
}

/** Sign out the current user (clears local session). */
export function signOut(): void {
  const user = getUserPool().getCurrentUser();
  if (user) {
    user.signOut();
  }
}

/** Get the current authenticated user's session, or null if not signed in. */
export function getCurrentSession(): Promise<CognitoUserSession | null> {
  return new Promise((resolve) => {
    const user = getUserPool().getCurrentUser();
    if (!user) {
      resolve(null);
      return;
    }
    user.getSession(
      (err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session?.isValid()) {
          resolve(null);
          return;
        }
        resolve(session);
      },
    );
  });
}

/** Get the current ID token JWT string, or null if not authenticated. */
export async function getIdToken(): Promise<string | null> {
  const session = await getCurrentSession();
  return session?.getIdToken().getJwtToken() ?? null;
}
