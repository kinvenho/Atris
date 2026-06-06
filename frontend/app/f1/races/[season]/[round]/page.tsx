import F1CommandCenter from "@/components/F1CommandCenter";

type F1RaceCommandPageProps = {
  params: Promise<{
    season: string;
    round: string;
  }>;
};

export default async function F1RaceCommandPage({ params }: F1RaceCommandPageProps) {
  const { season, round } = await params;
  return <F1CommandCenter season={Number(season)} round={Number(round)} />;
}
