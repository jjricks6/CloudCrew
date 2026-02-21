import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/AuthContext";

type Mode = "sign-in" | "sign-up" | "confirm";

export function LoginPage() {
  const { signIn, signUp, confirmSignUp } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const handleSignIn = async () => {
    setPending(true);
    setError("");
    try {
      await signIn(email, password);
      navigate("/project/demo");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setPending(false);
    }
  };

  const handleSignUp = async () => {
    setPending(true);
    setError("");
    try {
      await signUp(email, password);
      setMode("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setPending(false);
    }
  };

  const handleConfirm = async () => {
    setPending(true);
    setError("");
    try {
      await confirmSignUp(email, code);
      await signIn(email, password);
      navigate("/project/demo");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirmation failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">CloudCrew</CardTitle>
          <p className="text-sm text-muted-foreground">
            {mode === "sign-in" && "Sign in to your account"}
            {mode === "sign-up" && "Create a new account"}
            {mode === "confirm" && "Verify your email"}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {mode !== "confirm" && (
            <>
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={pending}
              />
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={pending}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (mode === "sign-in") void handleSignIn();
                    else void handleSignUp();
                  }
                }}
              />
            </>
          )}

          {mode === "confirm" && (
            <Input
              type="text"
              placeholder="Verification code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={pending}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleConfirm();
              }}
            />
          )}

          {mode === "sign-in" && (
            <>
              <Button
                className="w-full"
                onClick={handleSignIn}
                disabled={pending || !email || !password}
              >
                {pending ? "Signing in..." : "Sign In"}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                No account?{" "}
                <button
                  type="button"
                  className="underline hover:text-foreground"
                  onClick={() => {
                    setMode("sign-up");
                    setError("");
                  }}
                >
                  Sign up
                </button>
              </p>
            </>
          )}

          {mode === "sign-up" && (
            <>
              <Button
                className="w-full"
                onClick={handleSignUp}
                disabled={pending || !email || !password}
              >
                {pending ? "Creating account..." : "Sign Up"}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <button
                  type="button"
                  className="underline hover:text-foreground"
                  onClick={() => {
                    setMode("sign-in");
                    setError("");
                  }}
                >
                  Sign in
                </button>
              </p>
            </>
          )}

          {mode === "confirm" && (
            <Button
              className="w-full"
              onClick={handleConfirm}
              disabled={pending || !code}
            >
              {pending ? "Verifying..." : "Verify Email"}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
