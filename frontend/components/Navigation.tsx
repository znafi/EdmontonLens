"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "@/lib/api";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/transit", label: "Transit" },
  { href: "/waste", label: "Waste" },
  { href: "/ask", label: "Ask" },
  { href: "/neighbourhood", label: "Map" },
];

export default function Navigation() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-sm font-bold text-white">
            EL
          </span>
          <span className="text-lg font-semibold text-slate-900">EdmontonLens</span>
        </Link>
        <ul className="flex items-center gap-1">
          {LINKS.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={clsx(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-brand text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                  )}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
