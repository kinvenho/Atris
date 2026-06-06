import Link from "next/link";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="page-shell">
      <header className="topbar">
        <Link href="/" className="brand">
          <span className="brand-mark">A</span>
          <span>ATRIS</span>
        </Link>
        <nav className="nav" aria-label="Primary navigation">
          <Link href="/">Command</Link>
          <Link href="/f1/races">Races</Link>
        </nav>
      </header>
      {children}
    </div>
  );
}
