import { useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Bar,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { downloadCsv } from "../utils/exportCsv";

const API_BASE = "http://127.0.0.1:8000";

export default function PricingLab({ products, ageGroup }) {
  const [targetId, setTargetId] = useState(1);
  const [competitorIds, setCompetitorIds] = useState([3, 4]);
  const [minPct, setMinPct] = useState(-40);
  const [maxPct, setMaxPct] = useState(20);
  const [steps, setSteps] = useState(7);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [choiceModel, setChoiceModel] = useState("logit");

  const toggleCompetitor = (id) => {
    if (id === targetId) return;
    setCompetitorIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleTargetChange = (newId) => {
    const id = Number(newId);
    setTargetId(id);
    setCompetitorIds((prev) => prev.filter((c) => c !== id));
  };

  const runSweep = async () => {
    if (competitorIds.length < 1) {
      setError("Select at least 1 competitor.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const payload = {
        target_product_id: targetId,
        competitor_ids: competitorIds,
        min_pct: Number(minPct),
        max_pct: Number(maxPct),
        steps: Number(steps),
        force_refresh: forceRefresh,
        choice_model: choiceModel,
        ...(ageGroup !== "ALL" ? { age_group: ageGroup } : {}),
      };
      const res = await fetch(`${API_BASE}/pricing-lab/sweep`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Price sweep failed");
      }
      setData(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExportSweep = () => {
  if (!data?.sweep_curve?.length) return;

  const headers = Object.keys(data.sweep_curve[0]);
  const rows = data.sweep_curve.map((pt) => headers.map((h) => pt[h]));
  const stamp = new Date().toISOString().slice(0, 10);
  const slug = data.target_product.name.toLowerCase().replace(/[^a-z0-9]+/g, "_");

  downloadCsv(`pricing_sweep_${slug}_${stamp}.csv`, headers, rows);
};

const handleExportWtp = () => {
  if (!data?.wtp_breakdown?.length) return;

  const headers = [
  "Persona",
  "Age Group",
  "Budget (INR)",
  "Base Utility (U0)",
  "Best Rival",
  "Switching Price (INR)",
  `Price Headroom @ ₹${data.target_product.base_price}`,
];
const rows = data.wtp_breakdown.map((row) => [
  row.persona_name,
  row.age_group,
  row.budget,
  row.base_utility_u0,
  row.best_competitor,
  row.switching_price,
  row.price_headroom,
]);
  const stamp = new Date().toISOString().slice(0, 10);
  const slug = data.target_product.name.toLowerCase().replace(/[^a-z0-9]+/g, "_");

  downloadCsv(`wtp_breakdown_${slug}_${stamp}.csv`, headers, rows);
};
  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
              Target Product (Price to Sweep)
            </label>
            <select
              value={targetId}
              onChange={(e) => handleTargetChange(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (₹{p.price})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
              Sweep Range ({minPct > 0 ? `+${minPct}` : minPct}% to {maxPct > 0 ? `+${maxPct}` : maxPct}%)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={minPct}
                onChange={(e) => setMinPct(e.target.value)}
                className="w-1/2 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono"
              />
              <span className="text-slate-500 text-xs">to</span>
              <input
                type="number"
                value={maxPct}
                onChange={(e) => setMaxPct(e.target.value)}
                className="w-1/2 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
              Price Points (Steps)
            </label>
            <input
              type="number"
              min="3"
              max="15"
              value={steps}
              onChange={(e) => setSteps(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>

        {/* Competitors */}
        <div>
          <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
            Shelf Competitors ({competitorIds.length} selected)
          </label>
          <div className="flex flex-wrap gap-2">
            {products
              .filter((p) => p.id !== targetId)
              .map((p) => {
                const active = competitorIds.includes(p.id);
                return (
                  <button
                    key={p.id}
                    onClick={() => toggleCompetitor(p.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs border transition cursor-pointer ${
                      active
                        ? "bg-emerald-950/50 border-emerald-500/70 text-emerald-200"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    {p.name} (₹{p.price})
                  </button>
                );
              })}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
              className="accent-emerald-500"
            />
            Force refresh LLM cache (slower, re-runs Ollama)
          </label>
          <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Choice Model:</span>
          <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setChoiceModel("deterministic")}
              className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                choiceModel === "deterministic"
                  ? "bg-emerald-500/20 text-emerald-300 font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Deterministic
            </button>
            <button
              type="button"
              onClick={() => setChoiceModel("logit")}
              className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                choiceModel === "logit"
                  ? "bg-emerald-500/20 text-emerald-300 font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Logit (Probabilistic)
            </button>
          </div>
        </div>
          <button
            onClick={runSweep}
            disabled={loading}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 text-slate-950 font-semibold px-5 py-2 rounded-lg text-sm transition cursor-pointer"
          >
            {loading ? "Running Sweep..." : "Run Price Elasticity Sweep"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-800 text-red-200 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {data && !loading && (
        <div className="space-y-6">
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Optimal Price</p>
              <p className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                ₹{data.optimal_price_point.test_price}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {data.optimal_price_point.price_change_pct > 0 ? "+" : ""}
                {data.optimal_price_point.price_change_pct}% vs Base ₹{data.target_product.base_price}
              </p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Projected Revenue</p>
              <p className="text-2xl font-bold font-mono text-slate-100 mt-1">
                ₹{data.optimal_price_point.projected_revenue}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                From {data.optimal_price_point.target_wins} of {data.total_personas} personas
              </p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <p className="text-xs uppercase tracking-wider text-slate-400">Peak Market Share</p>
              <p className="text-2xl font-bold font-mono text-sky-400 mt-1">
                {data.optimal_price_point.market_share_pct}%
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Target: {data.target_product.name}
              </p>
            </div>
          </div>

          {/* Revenue & Market Share Curve */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-semibold">
              Demand &amp; Revenue Curve — {data.target_product.name}
              </h3>
              <button
                onClick={handleExportSweep}
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium px-3 py-1.5 rounded-lg transition cursor-pointer"
              >
                Export Curve CSV
              </button>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.sweep_curve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="test_price"
                    tickFormatter={(v) => `₹${v}`}
                    stroke="#94a3b8"
                    fontSize={12}
                  />
                  <YAxis
                    yAxisId="left"
                    tickFormatter={(v) => `₹${v}`}
                    stroke="#10b981"
                    fontSize={12}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    stroke="#38bdf8"
                    fontSize={12}
                  />
                  <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      labelFormatter={(v) => `Test Price: ₹${v}`}
                      formatter={(value, name, props) => {
                        if (name === "Market Share (%)") {
                          return [
                            `${value}% (${props.payload.target_wins} of ${data.total_personas} personas)`,
                            "Demand",
                          ];
                        }
                        return [`₹${value}`, name];
                      }}
                    />
                  <ReferenceLine
                    x={data.target_product.base_price}
                    yAxisId="left"
                    stroke="#f59e0b"
                    strokeDasharray="4 4"
                    label={{ value: "Base", fill: "#f59e0b", fontSize: 11, position: "top" }}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey="projected_revenue"
                    name="Projected Revenue (₹)"
                    fill="#10b981"
                    radius={[4, 4, 0, 0]}
                    barSize={32}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="market_share_pct"
                    name="Market Share (%)"
                    stroke="#38bdf8"
                    strokeWidth={2.5}
                    dot={{ r: 4 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Willingness to Pay (WTP) Table */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 overflow-x-auto">
            <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-semibold">
              Competitive Switching Price &amp; Pricing Headroom
            </h3>
            <button
              onClick={handleExportWtp}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium px-3 py-1.5 rounded-lg transition cursor-pointer"
            >
              Export Switching CSV
            </button>
          </div>
            <table className="w-full text-left text-sm">
            <thead>
  <tr className="border-b border-slate-800 text-xs uppercase text-slate-400">
    <th className="py-2 pr-4">Persona</th>
    <th className="py-2 pr-4">Age</th>
    <th className="py-2 pr-4">Budget</th>
    <th className="py-2 pr-4">Base U0</th>
    <th className="py-2 pr-4">Current Choice</th>
    <th className="py-2 pr-4">Best Rival</th>
    <th className="py-2 pr-4">Switching Price</th>
    <th className="py-2">Headroom @ ₹{data.target_product.base_price}</th>
  </tr>
</thead>
<tbody className="divide-y divide-slate-800/70 font-mono text-xs">
  {data.wtp_breakdown.map((row) => {
    const isBuyingTarget = row.switching_price > 0 && row.price_headroom >= 0;
    return (
      <tr key={row.persona_name}>
        <td className="py-2.5 pr-4 font-sans font-medium text-slate-200">
          {row.persona_name}
        </td>
        <td className="py-2.5 pr-4 text-slate-400">{row.age_group}</td>
        <td className="py-2.5 pr-4">₹{row.budget}</td>
        <td className="py-2.5 pr-4">{row.base_utility_u0}/100</td>
        <td className="py-2.5 pr-4 font-sans">
          {isBuyingTarget ? (
            <span className="bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[11px] font-medium px-2 py-0.5 rounded-full">
              {data.target_product.name}
            </span>
          ) : (
            <span className="bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[11px] font-medium px-2 py-0.5 rounded-full">
              {row.best_competitor}
            </span>
          )}
        </td>
        <td className="py-2.5 pr-4 font-sans text-slate-300">
          {row.best_competitor}
        </td>
        <td
          className={`py-2.5 pr-4 ${
            row.switching_price > 0 ? "text-emerald-400" : "text-slate-500"
          }`}
        >
          {row.switching_price > 0 ? `₹${row.switching_price}` : "Won't Switch"}
        </td>
        <td
          className={`py-2.5 ${
            row.switching_price === 0
              ? "text-slate-500"
              : row.price_headroom >= 0
              ? "text-sky-400"
              : "text-red-400"
          }`}
        >
          {row.switching_price === 0
            ? "N/A"
            : `${row.price_headroom >= 0 ? "+" : ""}₹${row.price_headroom}`}
        </td>
      </tr>
    );
  })}
</tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}