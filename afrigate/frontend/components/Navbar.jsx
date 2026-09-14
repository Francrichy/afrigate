import Link from "next/link";
import { useRouter } from "next/router";
import { useAuth } from "../lib/auth-context";

const LINKS = [
  { href: "/", label: "Models" },
  { href: "/playground", label: "Playground" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/docs", label: "Docs" },
];

export default function Navbar() {
  const router = useRouter();
  const { isAuthenticated, user, logout, setAuthModalOpen } = useAuth();

  return (
    <header className="border-b border-base-700 bg-base-950 sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-semibold text-white text-[15px] tracking-tight">
            Afri<span className="text-accent">Gate</span>
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  router.pathname === l.href ? "bg-base-800 text-white" : "text-base-200 hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <span className="hidden sm:block text-xs font-mono px-2.5 py-1 rounded-md bg-base-800 text-accent border border-base-700">
                ${(user.credit_balance / 100000).toFixed(4)}
              </span>
              <button onClick={logout} className="text-sm text-base-200 hover:text-white font-medium">
                Sign out
              </button>
            </>
          ) : (
            <button
              onClick={() => setAuthModalOpen(true)}
              className="px-4 py-1.5 rounded-md bg-accent hover:bg-accent-hover text-black text-sm font-semibold transition-colors"
            >
              Sign in
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
