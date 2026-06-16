"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Film, Home, History, Heart, ShieldCheck, LogOut, LogIn } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { href: "/", label: "Browse", icon: Home },
  { href: "/history", label: "History", icon: History },
  { href: "/favorites", label: "Favorites", icon: Heart },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout, loading } = useAuth();

  return (
    <aside className="hidden md:flex md:flex-col md:fixed md:inset-y-0 md:left-0 md:w-60 border-r border-border bg-surface px-4 py-6">
      <Link href="/" className="flex items-center gap-2 px-2 mb-8">
        <Film className="text-accent" size={26} />
        <span className="font-display font-extrabold text-xl tracking-tight">
          Streamline
        </span>
      </Link>

      <nav className="flex flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-surface-2 text-text"
                  : "text-text-muted hover:text-text hover:bg-surface-2"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}

        {!loading && user?.role === "admin" && (
          <Link
            href="/admin"
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
              pathname.startsWith("/admin")
                ? "bg-surface-2 text-text"
                : "text-text-muted hover:text-text hover:bg-surface-2"
            }`}
          >
            <ShieldCheck size={18} />
            Admin
          </Link>
        )}
      </nav>

      <div className="mt-auto pt-4 border-t border-border">
        {!loading && user ? (
          <div className="flex items-center justify-between px-2">
            <div className="min-w-0">
              <p className="text-sm truncate">{user.name || user.email}</p>
              <p className="text-xs text-text-muted capitalize">{user.role}</p>
            </div>
            <button
              onClick={logout}
              title="Log out"
              className="p-2 rounded-lg text-text-muted hover:text-accent hover:bg-surface-2"
            >
              <LogOut size={18} />
            </button>
          </div>
        ) : !loading ? (
          <Link
            href="/login"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-muted hover:text-text hover:bg-surface-2"
          >
            <LogIn size={18} />
            Log in
          </Link>
        ) : null}
      </div>
    </aside>
  );
}
