import { useEffect, useState } from "react";
import PricingLab from "./components/PricingLab";
import NewConceptModal from "./components/NewConceptModal";
import { downloadCsv } from "./utils/exportCsv";

const API_BASE = "http://127.0.0.1:8000";
const AGE_GROUPS = ["ALL", "18-24", "25-40", "41-56", "57+"];

export default function App() {
  const [products, setProducts] = useState([]);
  const [selectedIds, setSelectedIds] = useState([1, 3, 4]);
  const [ageGroup, setAgeGroup] = useState("ALL");
  const [activeTab, setActiveTab] = useState("shelf");
  const [showConceptModal, setShowConceptModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/products`)
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch(() => setError("Could not connect to FastAPI at http://127.0.0.1:8000"));
  }, []);

  const toggleProduct = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };
  const handleConceptCreated = (newProduct) => {
  setProducts((prev) => [...prev, newProduct]);
  setSelectedIds((prev) => [...prev, newProduct.id]);
};

const handleExportShelfWar = () => {
  if (!result?.persona_decisions?.length) return;

  const headers = [
    "Persona",
    "Age Group",
    "Monthly Budget (INR)",
    "Chosen Product",
    "Evaluated Product",
    "Price (INR)",
    "Base Utility (U0)",
    "Value Score",
    "Winner",
    "Reaction",
  ];

  const rows = result.persona_decisions.flatMap((pd) =>
    pd.comparisons.map((c) => [
      pd.persona_name,
      pd.age_group,
      pd.budget,
      pd.chosen_product,
      c.product_name,
      c.price,
      c.base_utility_u0,
      c.value_score,
      c.product_name === pd.chosen_product ? "Yes" : "No",
      c.reaction,
    ])
  );

  const stamp = new Date().toISOString().slice(0, 10);
  downloadCsv(`shelf_war_${stamp}.csv`, headers, rows);
};

  const runAnalysis = async () => {
    if (selectedIds.length < 2) {
      setError("Select at least 2 products to compare.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const payload = {
        product_ids: selectedIds,
        ...(ageGroup !== "ALL" ? { age_group: ageGroup } : {}),
      };
      const res = await fetch(`${API_BASE}/market-analysis/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Simulation failed");
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <header className="border-b border-slate-800 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-emerald-400 font-semibold">
              SSR + Discrete Choice Engine
            </p>
            <h1 className="text-3xl font-bold tracking-tight mt-1">
              Consumer Market Analysis Simulator
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-slate-400">Age Segment:</label>
            <select
              value={ageGroup}
              onChange={(e) => setAgeGroup(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
            >
              {AGE_GROUPS.map((g) => (
                <option key={g} value={g}>
                  {g === "ALL" ? "All Age Groups" : g}
                </option>
              ))}
            </select>
            {activeTab === "shelf" && (
              <button
                onClick={runAnalysis}
                disabled={loading}
                className="bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 disabled:text-slate-400 text-slate-950 font-semibold px-5 py-2 rounded-lg text-sm transition cursor-pointer"
              >
                {loading ? "Simulating..." : "Run Market Analysis"}
              </button>
            )}
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className="flex gap-2 border-b border-slate-800 pb-3">
          <button
            onClick={() => setActiveTab("shelf")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition cursor-pointer ${
              activeTab === "shelf"
                ? "bg-slate-800 text-emerald-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Shelf War (Discrete Choice)
          </button>
          <button
            onClick={() => setActiveTab("pricing")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition cursor-pointer ${
              activeTab === "pricing"
                ? "bg-slate-800 text-emerald-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Pricing Lab (Price Elasticity)
          </button>
        </div>

        {activeTab === "shelf" ? (
          <div className="space-y-8">
            {error && (
              <div className="bg-red-950/60 border border-red-800 text-red-200 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {/* Product Selector */}
            <section>
             
              <div className="flex items-center justify-between mb-3">
  <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
    1. Select Competing Products ({selectedIds.length} selected)
  </h2>
  <button
    onClick={() => setShowConceptModal(true)}
    className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-emerald-400 text-xs font-semibold px-3 py-1.5 rounded-lg transition cursor-pointer"
  >
    + Test New Concept
  </button>
</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {products.map((p) => {
                  const active = selectedIds.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      onClick={() => toggleProduct(p.id)}
                      className={`text-left p-4 rounded-xl border transition cursor-pointer ${
                        active
                          ? "bg-emerald-950/40 border-emerald-500/70"
                          : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex justify-between items-start gap-2">
                        <span className="font-semibold text-sm">{p.name}</span>
                        <span className="text-emerald-400 font-mono text-sm">₹{p.price}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{p.description}</p>
                    </button>
                  );
                })}
              </div>
            </section>

            {/* Loading Banner */}
            {loading && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-2">
                <div className="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm text-slate-300">
                  Eliciting persona reactions via Ollama and computing SSR utilities...
                </p>
                <p className="text-xs text-slate-500">Usually takes 15–25 seconds</p>
              </div>
            )}

            {/* Results */}
            {result && !loading && (
              <div className="space-y-8">
                {/* Market Share Bar Chart */}
                <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold">Market Share Breakdown</h2>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-400">
                        {result.total_personas_evaluated} personas evaluated
                      </span>
                      <button
                        onClick={handleExportShelfWar}
                        className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium px-3 py-1.5 rounded-lg transition cursor-pointer"
                      >
                        Export CSV
                      </button>
                    </div>
                  </div>
                  <div className="space-y-4">
                    {Object.entries(result.market_share).map(([name, stats]) => (
                      <div key={name}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium">{name}</span>
                          <span className="font-mono text-emerald-400">
                            {stats.share_pct}% ({stats.wins} {stats.wins === 1 ? "win" : "wins"})
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                          <div
                            className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
                            style={{ width: `${stats.share_pct}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Persona Decisions */}
                <section className="space-y-4">
                  <h2 className="text-lg font-semibold">Persona-by-Persona Decisions</h2>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {result.persona_decisions.map((pd) => (
                      <div
                        key={pd.persona_id}
                        className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4"
                      >
                        <div className="flex justify-between items-start border-b border-slate-800 pb-3">
                          <div>
                            <h3 className="font-bold text-base">
                              {pd.persona_name}{" "}
                              <span className="text-xs font-normal text-slate-400 ml-1">
                                ({pd.age_group})
                              </span>
                            </h3>
                            <p className="text-xs text-slate-400 mt-0.5">
                              Monthly Budget: ₹{pd.budget}
                            </p>
                          </div>
                          <span className="bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs font-semibold px-2.5 py-1 rounded-full">
                            Picked: {pd.chosen_product}
                          </span>
                        </div>

                        <div className="space-y-3">
                          {pd.comparisons.map((c) => {
                            const isWinner = c.product_name === pd.chosen_product;                            
                            
                            return (
                              <div
                                key={c.product_id}
                                className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                                  isWinner
                                    ? "bg-emerald-950/30 border-emerald-500/40"
                                    : "bg-slate-950/60 border-slate-800/80"
                                }`}
                              >
                                <div className="flex justify-between items-center font-semibold">
                                  <span>
                                    {c.product_name} (₹{c.price})
                                  </span>
                                  <span className="font-mono text-slate-300">
                                    U0: {c.base_utility_u0} | Val: {c.value_score}
                                  </span>
                                </div>
                                <p className="text-slate-400 leading-relaxed italic">
                                  "{c.reaction}"
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </div>
        ) : (
          <PricingLab products={products} ageGroup={ageGroup} />
        )}
      </div>
       <NewConceptModal
        isOpen={showConceptModal}
        onClose={() => setShowConceptModal(false)}
        onCreated={handleConceptCreated}
      />
    </div>
  );
}