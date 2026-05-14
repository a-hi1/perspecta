"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: " " },
  { href: "/knowledge-base", label: "Knowledge Base", icon: " " },
  { href: "/perspectives", label: "Perspectives", icon: " " },
  { href: "/draft-studio", label: "Draft Studio", icon: " " },
  { href: "/review-queue", label: "Review Queue", icon: " " },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">PEA</h1>
        <p className="text-xs text-gray-500 mt-1">Personal Experience Amplifier</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-sm font-medium text-blue-700">U</span>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">Default User</p>
            <p className="text-xs text-gray-500">MVP Mode</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
