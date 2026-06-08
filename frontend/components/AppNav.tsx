"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Command" },
  { href: "/f1/races", label: "Races" },
  { href: "/f1/drivers", label: "Drivers" },
  { href: "/f1/constructors", label: "Teams" },
  { href: "/f1/models", label: "Models" },
  { href: "/f1/data", label: "Data" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/" || pathname === "/f1";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="nav" aria-label="Primary navigation">
      {NAV_ITEMS.map((item) => (
        <Link key={item.href} href={item.href} className={isActive(pathname, item.href) ? "active" : ""}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
