"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { Search, X, MapPin } from "lucide-react";
import NeighbourhoodSnapshot from "@/components/NeighbourhoodSnapshot";
import { client } from "@/lib/api";
import type { Neighbourhood } from "@/types";

const NeighbourhoodMap = dynamic(() => import("@/components/NeighbourhoodMap"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center text-slate-400">
      Loading the map, one sec...
    </div>
  ),
});

function HighlightMatch({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-blue-100 text-blue-800 rounded-sm px-0.5">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function NeighbourhoodInner() {
  const params = useSearchParams();
  const initialId = params.get("id");
  const [selected, setSelected] = useState<string | null>(initialId);
  const [flyToId, setFlyToId] = useState<string | null>(null);

  // Search state
  const [query, setQuery] = useState("");
  const [allNeighbourhoods, setAllNeighbourhoods] = useState<Neighbourhood[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initialId) setSelected(initialId);
  }, [initialId]);

  useEffect(() => {
    client.neighbourhoods().then(setAllNeighbourhoods).catch(() => {});
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleOutsideClick(e: MouseEvent) {
      if (
        inputRef.current?.contains(e.target as Node) ||
        dropdownRef.current?.contains(e.target as Node)
      )
        return;
      setShowDropdown(false);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const filtered =
    query.trim().length > 0
      ? allNeighbourhoods
          .filter((n) =>
            (n.neighbourhood_name ?? n.neighbourhood_id)
              .toLowerCase()
              .includes(query.toLowerCase()),
          )
          .slice(0, 8)
      : [];

  function selectNeighbourhood(n: Neighbourhood) {
    setSelected(n.neighbourhood_id);
    setFlyToId(n.neighbourhood_id);
    setQuery(n.neighbourhood_name ?? n.neighbourhood_id);
    setShowDropdown(false);
    setFocusedIndex(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setShowDropdown(true);
      setFocusedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && focusedIndex >= 0 && filtered[focusedIndex]) {
      e.preventDefault();
      selectNeighbourhood(filtered[focusedIndex]);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Map</h1>
        <p className="text-sm text-slate-500">
          Search for a neighbourhood or click anywhere on the map.
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <div
          className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm
                     transition-shadow focus-within:border-blue-400 focus-within:shadow-md focus-within:ring-2
                     focus-within:ring-blue-100"
        >
          <Search className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowDropdown(true);
              setFocusedIndex(-1);
            }}
            onFocus={() => {
              if (query.trim()) setShowDropdown(true);
            }}
            onKeyDown={handleKeyDown}
            placeholder={`Search ${allNeighbourhoods.length > 0 ? allNeighbourhoods.length + " " : ""}neighbourhoods...`}
            className="flex-1 bg-transparent text-sm text-slate-900 placeholder-slate-400 outline-none"
          />
          {query && (
            <button
              onClick={() => {
                setQuery("");
                setShowDropdown(false);
                inputRef.current?.focus();
              }}
              className="shrink-0 rounded-full p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Dropdown */}
        {showDropdown && query.trim().length > 0 && (
          <div
            ref={dropdownRef}
            className="absolute left-0 right-0 top-full z-50 mt-1.5 max-h-64 overflow-y-auto
                       rounded-xl border border-slate-200 bg-white shadow-lg"
          >
            {filtered.length > 0 ? (
              filtered.map((n, i) => (
                <button
                  key={n.neighbourhood_id}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    selectNeighbourhood(n);
                  }}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors
                    ${i === focusedIndex ? "bg-blue-50" : "hover:bg-slate-50"}`}
                >
                  <MapPin
                    className={`h-3.5 w-3.5 shrink-0 ${i === focusedIndex ? "text-blue-500" : "text-slate-300"}`}
                  />
                  <span className={`flex-1 font-medium ${i === focusedIndex ? "text-blue-700" : "text-slate-800"}`}>
                    <HighlightMatch
                      text={n.neighbourhood_name ?? n.neighbourhood_id}
                      query={query}
                    />
                  </span>
                  <span className="text-xs text-slate-400">#{n.neighbourhood_id}</span>
                </button>
              ))
            ) : (
              <div className="px-4 py-3 text-sm text-slate-400">
                No neighbourhoods match &ldquo;{query}&rdquo;
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="h-[70vh] overflow-hidden rounded-xl border border-slate-200">
          <NeighbourhoodMap
            onSelect={(id) => {
              setSelected(id);
              // When clicking the map directly, clear the search so it doesn't
              // show a stale name from a previous search selection.
              setQuery("");
            }}
            flyToId={flyToId}
            onFlown={() => setFlyToId(null)}
          />
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
