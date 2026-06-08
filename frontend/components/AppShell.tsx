import Link from "next/link";
import AppNav from "@/components/AppNav";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="page-shell">
      <header className="topbar">
        <Link href="/" className="brand">
          <span className="brand-mark">A</span>
          <span>ATRIS</span>
        </Link>
        <AppNav />
      </header>
      {children}
    </div>
  );
}
