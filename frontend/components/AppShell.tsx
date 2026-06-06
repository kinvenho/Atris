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
          <Link href="/f1">F1</Link>
          <Link href="/">Feed</Link>
          <Link href="/performance">Performance</Link>
          <a href="https://polymarket.com" target="_blank" rel="noreferrer">
            Polymarket
          </a>
        </nav>
      </header>
      {children}
    </div>
  );
}
