import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useAuth } from "@/auth/AuthProvider";
import { apiErrorMessage } from "@/api/client";
import { Button, ErrorText, Input } from "@/components/ui";

const schema = z.object({
  username: z.string().min(1, "نام کاربری را وارد کنید."),
  password: z.string().min(1, "کلمه عبور را وارد کنید."),
});

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const parsed = schema.safeParse({ username, password });
    if (!parsed.success) {
      setError(parsed.error.issues[0].message);
      return;
    }
    setBusy(true);
    try {
      await login(username, password);
      const from = (location.state as { from?: Location })?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="text-3xl font-extrabold tracking-tight text-ink-100">
            Eval<span className="text-accent-400">Flow</span>
          </div>
          <p className="mt-2 text-sm text-ink-500">
            سامانه مدیریت اسناد ارزیابی امنیتی
          </p>
        </div>
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-surface-700 bg-surface-900 p-6 shadow-xl"
        >
          <Input
            label="نام کاربری"
            dir="ltr"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <Input
            label="کلمه عبور"
            type="password"
            dir="ltr"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "در حال ورود…" : "ورود به سامانه"}
          </Button>
        </form>
        <p className="mt-4 text-center text-xs text-ink-600">
          تمامی رویدادهای ورود در سامانه ثبت می‌شوند.
        </p>
      </div>
    </div>
  );
}
