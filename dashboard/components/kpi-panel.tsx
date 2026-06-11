"use client";

import { Building2, Globe2, Link2, MapPin, Sparkles, Utensils } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatPercent } from "@/lib/utils";

type KpiPanelProps = {
  totalPois: number;
  restaurants: number;
  countriesCovered: number;
  citiesCovered: number;
  websiteCoverage: number;
  menuCoverage: number;
  insights: string[];
};

const kpiIcons = [Utensils, Building2, Globe2, Link2, MapPin, Sparkles];

export function KpiPanel({
  totalPois,
  restaurants,
  countriesCovered,
  citiesCovered,
  websiteCoverage,
  menuCoverage,
  insights,
}: KpiPanelProps) {
  const values = [
    ["Total POIs", formatNumber(totalPois)],
    ["Restaurants", formatNumber(restaurants)],
    ["Website coverage", formatPercent(websiteCoverage)],
    ["Menu coverage", formatPercent(menuCoverage)],
    ["Countries", formatNumber(countriesCovered)],
    ["Cities", formatNumber(citiesCovered)],
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Overview</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3">
          {values.map(([label, value], index) => {
            const Icon = kpiIcons[index];
            return (
              <div
                key={label}
                className="rounded-lg border border-white/10 bg-white/[0.04] p-3 transition hover:bg-white/[0.07]"
              >
                <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-md bg-blue-500/16 text-blue-300">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="text-xl font-semibold tracking-tight text-white">{value}</div>
                <div className="mt-1 text-xs text-slate-400">{label}</div>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {insights.map((insight) => (
            <Badge key={insight} className="w-full justify-start rounded-md py-2">
              {insight}
            </Badge>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
