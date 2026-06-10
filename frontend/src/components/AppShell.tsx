import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";

const ROLE_LABELS: Record<string, string> = {
  admin: "مدیر سیستم",
  assessor: "ارزیاب",
  reviewer: "بازبین",
  qa_lead: "مسئول تضمین کیفیت",
};

function NavItem({ to, label, end }: { to: string; label: string; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `block rounded-lg px-3 py-2 text-sm transition-colors ${
          isActive
            ? "bg-accent-600/15 font-medium text-accent-400"
            : "text-ink-300 hover:bg-surface-800 hover:text-ink-100"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export function AppShell() {
  const { user, logout, hasRole } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-e border-surface-800 bg-surface-900">
        <div className="border-b border-surface-800 px-5 py-5">
          <div className="text-xl font-extrabold tracking-tight text-ink-100">
            Eval<span className="text-accent-400">Flow</span>
          </div>
          <div className="mt-1 text-xs text-ink-500">
            سامانه مدیریت ارزیابی امنیتی
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          <NavItem to="/" label="ارزیابی‌ها" end />
          <NavItem to="/companies" label="شرکت‌ها و سامانه‌ها" />
          {hasRole("admin") && <NavItem to="/admin/frameworks" label="چارچوب‌های الزامات" />}
          {hasRole("admin", "qa_lead") && <NavItem to="/admin/users" label="کاربران" />}
          {hasRole("admin", "qa_lead") && <NavItem to="/admin/audit" label="گزارش رویدادها" />}
        </nav>
        <div className="border-t border-surface-800 p-4">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-600/20 text-sm font-bold text-accent-400">
              {(user?.first_name?.[0] ?? user?.username?.[0] ?? "؟").toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-ink-100">
                {user?.first_name
                  ? `${user.first_name} ${user.last_name}`
                  : user?.username}
              </div>
              <div className="text-xs text-ink-500">
                {ROLE_LABELS[user?.role ?? ""] ?? ""}
              </div>
            </div>
          </div>
          <button
            onClick={() => void logout()}
            className="w-full rounded-lg border border-surface-600 px-3 py-1.5 text-xs text-ink-300 hover:bg-surface-800"
          >
            خروج از حساب
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 bg-surface-950">
        <Outlet />
      </main>
    </div>
  );
}
