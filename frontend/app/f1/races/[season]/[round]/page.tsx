import F1CommandCenter from "@/components/F1CommandCenter";

type F1RaceCommandPageProps = {
  params: Promise<{
    season: string;
    round: string;
  }>;
  searchParams: Promise<{
    tab?: string;
  }>;
};

export default async function F1RaceCommandPage({ params, searchParams }: F1RaceCommandPageProps) {
  const { season, round } = await params;
  const { tab } = await searchParams;
  return <F1CommandCenter season={Number(season)} round={Number(round)} mode="race" activeTab={tab} />;
}
