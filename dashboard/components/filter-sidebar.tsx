"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Filters } from "@/lib/types";

type FilterSidebarProps = {
  filters: Filters;
  countries: string[];
  cities: string[];
  amenities: string[];
  cuisines: string[];
  onChange: (filters: Filters) => void;
  onReset: () => void;
};

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-md border border-white/10 bg-slate-950/70 px-3 text-sm text-slate-100 outline-none transition hover:bg-slate-900/80 focus:border-blue-400"
      >
        <option value="all">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex h-10 w-full items-center justify-between rounded-md border border-white/10 bg-slate-950/62 px-3 text-sm text-slate-200 transition hover:bg-slate-900/80"
    >
      <span>{label}</span>
      <span
        className={`h-5 w-9 rounded-full p-0.5 transition ${checked ? "bg-blue-500" : "bg-slate-700"}`}
      >
        <span
          className={`block h-4 w-4 rounded-full bg-white transition ${checked ? "translate-x-4" : "translate-x-0"}`}
        />
      </span>
    </button>
  );
}

export function FilterSidebar({
  filters,
  countries,
  cities,
  amenities,
  cuisines,
  onChange,
  onReset,
}: FilterSidebarProps) {
  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Filters</CardTitle>
        <Button className="h-8 px-2 text-xs" onClick={onReset}>
          <RotateCcw className="h-3.5 w-3.5" />
          Reset
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <SelectField
          label="Country"
          value={filters.country}
          options={countries}
          onChange={(country) => onChange({ ...filters, country })}
        />
        <SelectField
          label="City"
          value={filters.city}
          options={cities}
          onChange={(city) => onChange({ ...filters, city })}
        />
        <SelectField
          label="Amenity"
          value={filters.amenity}
          options={amenities}
          onChange={(amenity) => onChange({ ...filters, amenity })}
        />
        <SelectField
          label="Cuisine"
          value={filters.cuisine}
          options={cuisines}
          onChange={(cuisine) => onChange({ ...filters, cuisine })}
        />
        <div className="space-y-2 pt-1">
          <ToggleField
            label="Has website"
            checked={filters.hasWebsite}
            onChange={(hasWebsite) => onChange({ ...filters, hasWebsite })}
          />
          <ToggleField
            label="Has menu URL"
            checked={filters.hasMenuUrl}
            onChange={(hasMenuUrl) => onChange({ ...filters, hasMenuUrl })}
          />
        </div>
      </CardContent>
    </Card>
  );
}
