import Link from "next/link";
import { formatPercent, formatSignedPercent, Recommendation } from "@/lib/api";

export default function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  return (
    <Link href={`/recommendation/${recommendation.id}`} className="recommendation-card">
      <div className="card-top">
        <div className="agent-icon">{recommendation.side}</div>
        <div className={recommendation.status === "active" ? "tag lime" : "tag"}>
          {recommendation.status}
        </div>
      </div>

      <div>
        <div className="tag">Market Signal</div>
        <h2 className="card-title mt-4">{recommendation.market_question}</h2>
      </div>

      <p className="card-copy">
        {recommendation.reasoning.length > 180
          ? `${recommendation.reasoning.slice(0, 180)}...`
          : recommendation.reasoning}
      </p>

      <div className="card-stats">
        <div>
          <div className="stat-label">Market</div>
          <div className="stat-value">{formatPercent(recommendation.market_probability)}</div>
        </div>
        <div>
          <div className="stat-label">Atris</div>
          <div className="stat-value violet-text">{formatPercent(recommendation.atris_probability)}</div>
        </div>
        <div>
          <div className="stat-label">Edge</div>
          <div className="stat-value lime-text">{formatSignedPercent(recommendation.edge)}</div>
        </div>
      </div>
    </Link>
  );
}
