import AppShell from "@/components/AppShell";
import PerformanceStats from "@/components/PerformanceStats";
import { getAgentRuns, getPerformance } from "@/lib/api";

export default async function PerformancePage() {
  const [performance, runs] = await Promise.all([getPerformance(), getAgentRuns()]);

  return (
    <AppShell>
      <main className="container">
        <section className="hero">
          <div>
            <div className="eyebrow">
              <span className="status-dot" />
              Scoreboard
            </div>
            <h1 className="hero-title">
              Performance <span>ledger</span>
            </h1>
            <p className="hero-copy">
              Daily snapshots and run history for the Atris research agent. Accuracy is based only
              on resolved recommendations.
            </p>
          </div>
        </section>
        <PerformanceStats performance={performance} runs={runs} />
      </main>
    </AppShell>
  );
}
