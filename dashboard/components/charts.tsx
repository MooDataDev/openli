"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
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

const COLORS = ["#3b82f6", "#14b8a6", "#a855f7", "#f59e0b", "#ec4899", "#64748b"];

export function DashboardCharts({
  countryData,
  cuisineData,
}: {
  countryData: ChartDatum[];
  cuisineData: ChartDatum[];
}) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card className="min-h-[280px]">
        <CardHeader>
          <CardTitle>POIs by Country</CardTitle>
        </CardHeader>
        <CardContent className="h-56">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <PieChart>
              <Pie data={countryData} innerRadius={58} outerRadius={86} paddingAngle={3} dataKey="value">
                {countryData.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "rgba(15, 23, 42, 0.96)",
                  border: "1px solid rgba(148, 163, 184, 0.25)",
                  borderRadius: 8,
                  color: "#e2e8f0",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card className="min-h-[280px]">
        <CardHeader>
          <CardTitle>Top Cuisines</CardTitle>
        </CardHeader>
        <CardContent className="h-56">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={cuisineData} layout="vertical" margin={{ left: 8, right: 18 }}>
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
              <Tooltip
                cursor={{ fill: "rgba(59, 130, 246, 0.1)" }}
                contentStyle={{
                  background: "rgba(15, 23, 42, 0.96)",
                  border: "1px solid rgba(148, 163, 184, 0.25)",
                  borderRadius: 8,
                  color: "#e2e8f0",
                }}
              />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {cuisineData.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
