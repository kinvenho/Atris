import { formatDate, formatPercent, formatSignedPercent, Recommendation } from "@/lib/api";

export default function RecommendationDetail({ recommendation }: { recommendation: Recommendation }) {
  return (
    <div className="detail-grid">
      <section className="panel">
        <div className="eyebrow">
          <span className="status-dot" />
          {recommendation.status} signal
        </div>
        <h1 className="detail-title">{recommendation.market_question}</h1>
        <div className="mt-8 flex flex-wrap gap-3">
          <span className="tag lime">Recommend {recommendation.side}</span>
          <span className="tag">Result {recommendation.result}</span>
        </div>

        <div className="mt-10 grid gap-6">
          <div>
            <h2 className="section-title">Reasoning</h2>
            <p className="card-copy mt-4">{recommendation.reasoning}</p>
          </div>
          <div>
            <h2 className="section-title">Evidence Summary</h2>
            <p className="card-copy mt-4 whitespace-pre-line">{recommendation.evidence_summary}</p>
          </div>
        </div>
      </section>

      <aside className="grid gap-6">
        <section className="panel">
          <h2 className="section-title">Signal</h2>
          <div className="detail-list">
            <div className="detail-row">
              <span className="metric-label">Market Odds</span>
              <strong className="mono">{formatPercent(recommendation.market_probability)}</strong>
            </div>
            <div className="detail-row">
              <span className="metric-label">Atris Estimate</span>
              <strong className="mono violet-text">{formatPercent(recommendation.atris_probability)}</strong>
            </div>
            <div className="detail-row">
              <span className="metric-label">Edge</span>
              <strong className="mono lime-text">{formatSignedPercent(recommendation.edge)}</strong>
            </div>
            <div className="detail-row">
              <span className="metric-label">Confidence</span>
              <strong className="mono">{formatPercent(recommendation.confidence)}</strong>
            </div>
            <div className="detail-row">
              <span className="metric-label">Created</span>
              <strong className="mono">{formatDate(recommendation.created_at)}</strong>
            </div>
          </div>
        </section>

        <section className="panel">
          <h2 className="section-title">Evidence</h2>
          {recommendation.evidence?.length ? (
            <div className="detail-list">
              {recommendation.evidence.map((item) => (
                <a
                  href={item.source_url}
                  key={item.id}
                  target="_blank"
                  rel="noreferrer"
                  className="detail-row"
                >
                  <span className="metric-label">Source</span>
                  <strong className="mono violet-text">Open</strong>
                </a>
              ))}
            </div>
          ) : (
            <p className="card-copy mt-4">No evidence links are attached to this recommendation yet.</p>
          )}
        </section>
      </aside>
    </div>
  );
}
