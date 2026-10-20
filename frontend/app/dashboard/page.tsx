const VIZ_URL =
  "https://public.tableau.com/views/EdmontonLens-NeighbourhoodsandTransit/Dashboard1";
const PROFILE_URL =
  "https://public.tableau.com/app/profile/zawad.nafi/viz/EdmontonLens-NeighbourhoodsandTransit/Dashboard1";

export const metadata = { title: "Dashboard | EdmontonLens" };

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900">Tableau dashboard</h1>

      <div className="card overflow-hidden p-0">
        <iframe
          title="EdmontonLens Tableau dashboard"
          src={`${VIZ_URL}?:showVizHome=no&:embed=true&:tabs=yes&:toolbar=yes`}
          className="h-[85vh] min-h-[640px] w-full border-0"
          loading="lazy"
          allowFullScreen
        />
      </div>

      <p className="text-xs text-slate-400">
        Not loading?{" "}
        <a href={PROFILE_URL} target="_blank" rel="noreferrer" className="underline">
          Open it on Tableau Public
        </a>
        . The data is a snapshot exported by <code>scripts/export_tableau.py</code>.
      </p>
    </div>
  );
}
