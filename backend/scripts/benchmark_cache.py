import time
import httpx

API_URL = "http://127.0.0.1:8000/pricing-lab/sweep"

PAYLOAD = {
    "target_product_id": 1,
    "competitor_ids": [3, 4],
    "min_pct": -40,
    "max_pct": 20,
    "steps": 7,
}


def run_benchmark():
    with httpx.Client(timeout=120.0) as client:
        # 1. Cold run (forces Ollama + SSR re-evaluation)
        t0 = time.perf_counter()
        r_cold = client.post(API_URL, json={**PAYLOAD, "force_refresh": True})
        r_cold.raise_for_status()
        cold_s = time.perf_counter() - t0

        # 2. Warm run (reads U0 from PostgreSQL evaluation_cache)
        t1 = time.perf_counter()
        r_warm = client.post(API_URL, json={**PAYLOAD, "force_refresh": False})
        r_warm.raise_for_status()
        warm_s = time.perf_counter() - t1

    speedup = cold_s / warm_s if warm_s > 0 else float("inf")
    reduction_pct = ((cold_s - warm_s) / cold_s) * 100.0 if cold_s > 0 else 0.0

    print("\n--- Pricing Lab Cache Benchmark ---")
    print(f"Cold Run (LLM + SSR): {cold_s:.2f}s")
    print(f"Warm Run (PG Cache) : {warm_s:.4f}s")
    print(f"Speedup             : {speedup:.1f}x ({reduction_pct:.2f}% latency reduction)")


if __name__ == "__main__":
    run_benchmark()