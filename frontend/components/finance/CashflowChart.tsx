"use client";
/**
 * CashflowChart — area chart showing projected balance over time.
 * Danger zone highlighted when balance < threshold.
 */
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

interface CashflowChartProps {
  data: { date: string; balance: number; is_today?: boolean }[];
  dangerThreshold?: number;
  height?: number;
}

function fmtUSD(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const val = payload[0]?.value ?? 0;
  return (
    <div className="glass-card p-3 text-xs">
      <p className="text-white/50 mb-1">{label}</p>
      <p className="font-mono font-semibold" style={{ color: val < 500 ? "#ef4444" : "#10b981" }}>
        {fmtUSD(val)}
      </p>
    </div>
  );
}

export function CashflowChart({
  data,
  dangerThreshold = 500,
  height = 200,
}: CashflowChartProps) {
  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    balance: Math.round(d.balance),
    is_today: d.is_today,
  }));

  const todayPoint = chartData.find((d) => d.is_today);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="cashflowGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval={Math.floor(chartData.length / 5)}
        />
        <YAxis
          tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          width={40}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={dangerThreshold}
          stroke="rgba(239,68,68,0.4)"
          strokeDasharray="4 4"
          label={{ value: `Danger $${dangerThreshold}`, fill: "rgba(239,68,68,0.5)", fontSize: 9 }}
        />
        {todayPoint && (
          <ReferenceLine
            x={todayPoint.date}
            stroke="rgba(255,255,255,0.2)"
            strokeDasharray="3 3"
            label={{ value: "Today", fill: "rgba(255,255,255,0.3)", fontSize: 9 }}
          />
        )}
        <Area
          type="monotone"
          dataKey="balance"
          stroke="#10b981"
          strokeWidth={2}
          fill="url(#cashflowGrad)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
