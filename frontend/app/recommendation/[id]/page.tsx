import Link from "next/link";
import AppShell from "@/components/AppShell";
import RecommendationDetail from "@/components/RecommendationDetail";
import { getRecommendation } from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function RecommendationDetailPage({ params }: PageProps) {
  const { id } = await params;
  const recommendation = await getRecommendation(id);

  return (
    <AppShell>
      <main className="container">
        <Link href="/" className="mono muted">
          {"<-"} Back to feed
        </Link>
        <div className="mt-8">
          {recommendation ? (
            <RecommendationDetail recommendation={recommendation} />
          ) : (
            <div className="empty-state">Recommendation not found or no longer available.</div>
          )}
        </div>
      </main>
    </AppShell>
  );
}
