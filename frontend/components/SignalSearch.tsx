"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Recommendation, formatPercent, formatSignedPercent } from "@/lib/api";

export default function SignalSearch({ recommendations }: { recommendations: Recommendation[] }) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const normalizedQuery = query.trim().toLowerCase();
  const results = useMemo(() => {
    if (!normalizedQuery) return recommendations.slice(0, 5);

    return recommendations
      .filter((recommendation) =>
        [
          recommendation.market_question,
          recommendation.side,
          recommendation.reasoning,
          recommendation.evidence_summary,
        ]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery),
      )
      .slice(0, 5);
  }, [normalizedQuery, recommendations]);
  const shouldShowPanel = isFocused || query.length > 0;

  return (
    <div className="search-wrap">
      <input
        className="searchbox"
        onBlur={() => window.setTimeout(() => setIsFocused(false), 120)}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => setIsFocused(true)}
        placeholder="Search markets, outcomes, signals..."
        value={query}
      />

      {shouldShowPanel ? (
        <div className="search-panel">
          {results.length ? (
            results.map((recommendation) => (
              <Link className="search-result" href={`/recommendation/${recommendation.id}`} key={recommendation.id}>
                <span className="search-result-title">{recommendation.market_question}</span>
                <span className="search-result-meta">
                  {recommendation.side} · edge {formatSignedPercent(recommendation.edge)} · confidence{" "}
                  {formatPercent(recommendation.confidence, 0)}
                </span>
              </Link>
            ))
          ) : (
            <div className="search-empty">
              {recommendations.length ? "No matching signals." : "No active signals to search yet."}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
