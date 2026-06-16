"use client";

import { Suspense, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import NeighbourhoodSnapshot from "@/components/NeighbourhoodSnapshot";

const NeighbourhoodMap = dynamic(() => import("@/components/NeighbourhoodMap"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center text-slate-400">
      Loading the map, one sec...
    </div>
  ),
});

function NeighbourhoodInner() {
  const params = useSearchParams();
  const initialId = params.get("id");
  const [selected, setSelected] = useState<string | null>(initialId);

  useEffect(() => {
    if (initialId) setSelected(initialId);
  }, [initialId]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Map</h1>
        <p className="text-sm text-slate-500">
          Click any neighbourhood to see what's going on there.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-[70vh] overflow-hidden rounded-xl border border-slate-200">
          <NeighbourhoodMap onSelect={setSelected} />
        </div>
        <div className="h-[70vh] overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-5">
          <NeighbourhoodSnapshot neighbourhoodId={selected} />
        </div>
      </div>
    </div>
  );
}

export default function NeighbourhoodPage() {
  return (
    <Suspense fallback={<div className="text-slate-400">Loading...</div>}>
      <NeighbourhoodInner />
    </Suspense>
  );
}
