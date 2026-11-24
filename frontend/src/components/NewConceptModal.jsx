import { useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function NewConceptModal({ isOpen, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [price, setPrice] = useState("");
  const [category, setCategory] = useState("oral_care");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    const parsedPrice = Number(price);
    if (!name.trim() || !description.trim() || !parsedPrice || parsedPrice <= 0) {
      setError("Enter a valid product name, positive price, and short pitch.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
        name: name.trim(),
        brand: brand.trim(),
        price: parsedPrice,
        category: category.trim() || "oral_care",
        description: description.trim(),
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create product");
      }
      const created = await res.json();
      onCreated(created);
      setName("");
      setBrand("");
      setPrice("");
      setDescription("");
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-5">
        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-lg font-bold text-slate-100">Test New Product Concept</h2>
            <p className="text-xs text-slate-400">
              Add a hypothetical SKU and pit it against existing competitors.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-xl leading-none cursor-pointer"
          >
            &times;
          </button>
        </div>

        {error && (
          <div className="bg-red-950/60 border border-red-800 text-red-200 px-3 py-2 rounded-lg text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">
              Product Name
            </label>
            <input
              type="text"
              placeholder="e.g., Charcoal Pro Whitening Gel"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">
                Brand
            </label>
            <input
                type="text"
                placeholder="e.g., Colgate"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            />
            </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">
                Price (₹)
              </label>
              <input
                type="number"
                min="1"
                step="1"
                placeholder="220"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">
                Category
              </label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">
              Product Pitch / Positioning
            </label>
            <textarea
              rows={3}
              placeholder="Activated bamboo charcoal + clove oil for gentle stain removal and fresh breath."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 text-slate-950 font-semibold px-4 py-2 rounded-lg text-xs transition cursor-pointer"
            >
              {submitting ? "Saving..." : "Add to Shelf"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}