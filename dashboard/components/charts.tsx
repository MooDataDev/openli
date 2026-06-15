"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type ChartDatum = {
  name: string;
  value: number;
};

type TooltipPayloadItem = {
  name?: string | number;
  value?: number | string;
  color?: string;
};

type ChartTooltipProps = {
  active?: boolean;
  label?: string | number;
  payload?: TooltipPayloadItem[];
};

const COLORS = ["#3b82f6", "#14b8a6", "#a855f7", "#f59e0b", "#ec4899", "#64748b"];

function ChartTooltip({ active, label, payload }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-md border border-slate-400/25 bg-slate-950/95 px-3 py-2 text-xs shadow-panel">
      {label ? <div className="mb-1 font-medium text-slate-200">{label}</div> : null}
      {payload.map((item) => (
        <div key={`${item.name}-${item.value}`} className="flex items-center gap-2 text-[#e2e8f0]">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: item.color ?? "#3b82f6" }}
          />
          <span>{item.name ?? "Value"}</span>
          <span className="font-semibold text-[#e2e8f0]">{Number(item.value ?? 0).toLocaleString("en-US")}</span>
        </div>
      ))}
    </div>
  );
}

function CuisineBarChart({
  data,
  emptyLabel,
}: {
  data: ChartDatum[];
  emptyLabel: string;
}) {
  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-sm text-slate-400">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 18 }}>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.13)" horizontal={false} />
          <XAxis type="number" hide />
          <YAxis
            dataKey="name"
            type="category"
            width={92}
            tick={{ fill: "#cbd5e1", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip cursor={{ fill: "rgba(59, 130, 246, 0.1)" }} content={<ChartTooltip />} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DashboardCharts({
  viewportCuisineData,
  cuisineData,
}: {
  viewportCuisineData: ChartDatum[];
  cuisineData: ChartDatum[];
}) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card className="min-h-[280px]">
        <CardHeader>
          <CardTitle>Top Cuisines Visualized</CardTitle>
        </CardHeader>
        <CardContent>
          <CuisineBarChart data={viewportCuisineData} emptyLabel="Move or zoom the map to populate this view." />
        </CardContent>
      </Card>
      <Card className="min-h-[280px]">
        <CardHeader>
          <CardTitle>Top Cuisines</CardTitle>
        </CardHeader>
        <CardContent>
          <CuisineBarChart data={cuisineData} emptyLabel="No cuisine data for the selected filters." />
        </CardContent>
      </Card>
    </div>
  );
}
