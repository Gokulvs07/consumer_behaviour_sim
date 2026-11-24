# Consumer Behavior & Price Elasticity Simulator (Shelf War + Pricing Lab)

An applied Generative AI and behavioral economics simulation engine that predicts consumer choice, market share, and revenue-optimal pricing across competitive product shelves.

## Why This Exists
Traditional LLM-based market simulations are slow, expensive, and non-deterministic—requiring hundreds of LLM calls to test a single pricing curve. This engine decouples **qualitative product appeal** from **quantitative price sensitivity**:
1. **LLM + Embedding Layer (Cached):** Evaluates each `(persona, product)` pair once to derive a price-independent **Base Utility ($U_0$)** on a `0–100` scale.
2. **Zero-LLM Behavioral Economics Layer:** Runs instant price-elasticity sweeps, competitive switching calculations, and probabilistic demand curves in milliseconds.

## Core Modules
- **Shelf War (Discrete Choice):** Simulates head-to-head shelf competition across personas with budget caps, price sensitivity, and reservation thresholds.
- **Pricing Lab (Price Elasticity & Switching):** Sweeps a target SKU across custom price ranges (`min_pct` to `max_pct`) against selected shelf rivals to output:
  - Optimal revenue-maximizing price point
  - Dual-axis Demand & Revenue curve with CSV export
  - Per-persona **Current Choice**, **Best Rival**, **Competitive Switching Price**, and **Pricing Headroom**

## Behavioral Economics Engine
- **Reference-Price Anchoring:** Price penalties are anchored to the average shelf price ($P_{\text{ref}}$) rather than absolute monthly budgets, keeping `monthly_budget` strictly as an affordability cap.
- **Asymmetric Loss Aversion ($\lambda = 2.0$):** Grounded in Prospect Theory—pricing above the shelf reference price incurs a $2\times$ steeper utility penalty than an equivalent discount below $P_{\text{ref}}$.
- **Dual Choice Modes:**
  - **Deterministic:** Personas select the highest net-utility option above their reservation threshold.
  - **Multinomial Logit (Probabilistic):** Softmax choice model with tunable temperature ($\tau$) that converts utility gaps into smooth, realistic S-curve demand probabilities.

## Tech Stack
- **Backend:** Python, FastAPI, Async SQLAlchemy, Pydantic, Ollama, Pytest
- **Frontend:** React, Vite, Tailwind CSS, Recharts

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/) running locally

### 1. Backend
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1 | macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload