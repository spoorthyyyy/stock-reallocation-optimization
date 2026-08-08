# Global Stock Reallocation Optimization

A linear programming model that optimizes stock transfers across a
30-warehouse network in India, minimizing total network cost (transfer +
holding + expiry-waste + stockout risk) — built as a self-directed project
to demonstrate constrained optimization and operations-strategy thinking.

## Problem

A specialty-chemicals distribution network has demand spread unevenly
across regions. Some warehouses end up sitting on surplus stock — tying up
capital, and in some cases approaching batch expiry — while others are
understocked relative to local demand, risking stockouts. There was no
systematic process to detect these imbalances and rebalance the network
cost-effectively.

**Goal:** identify which warehouses have surplus vs. deficit, and compute
the cost-minimizing set of transfers — factoring in real transfer cost,
the cost of holding unused stock, the cost of stock going to waste before
expiry, and the cost of leaving demand unmet.

## Approach

**1. Grounded the model in real data wherever possible.** No company
publishes its actual inventory data, so a fully "real" dataset doesn't
exist — but locations, distances, and cost benchmarks don't need to be
invented:
- 30 real Indian cities, including genuine specialty-chemicals hubs
  (Vadodara, Ankleshwar, Vapi)
- Real inter-city road distances, computed from real coordinates
  (haversine formula × 1.35 road-distance factor), sanity-checked against
  known real road distances
- Real freight cost benchmark: ₹22/km, the midpoint of published 2025-26
  Indian FTL trucking rates (₹20-30/km for a medium truck)
- Real warehousing cost benchmark: ₹100-300/pallet/month, varied by
  Metro vs. Tier-2 city, from published Indian warehousing rate data

Current stock, exact demand, and expiry dates are synthetic (no public
source exists for this), generated to a deliberately realistic and messy
distribution rather than one that flatters the results. Demand is at least
scaled using each city's real Metro/Tier-2 classification, not picked
arbitrarily.

**2. Formulated it as a linear program.** Using Python + PuLP (CBC solver),
the model is a transportation problem: decide how many units to ship from
every surplus warehouse to every deficit warehouse, minimizing the sum of:
- transfer cost (real distance × real freight rate)
- holding cost on any surplus left unshipped
- a soft penalty on unshipped *near-expiry* surplus (write-off risk)
- a stockout penalty on any deficit left unmet

Both surplus and deficit constraints are modeled with slack variables
("unallocated surplus" / "unmet deficit"), so the model always has a
feasible solution and honestly reports what it couldn't fully resolve.

**3. Benchmarked the result two ways** — against a do-nothing baseline
(nobody reallocates anything) and against a naive rule-based heuristic
(sort by urgency, match greedily, ignore route cost) — so the LP's value
could be quantified against a realistic alternative, not just a strawman.

**4. Stress-tested it.** Re-ran the full pipeline with demand scaled
±15% to confirm the plan isn't fragile to forecast error.

## Key Results

| Metric | Result |
|---|---|
| Units reallocated | 1,936 |
| Warehouses de-risked | 8 of 8 (100% of stockout risk resolved) |
| Idle stock reduction | 16.5% |
| Net savings (6-month horizon) | ₹7,13,538 |
| Value over naive heuristic | +₹41,497 (6.2% more savings captured) |
| Robustness (±15% demand) | Net savings held between ₹5.11L–₹8.39L in every scenario |

Notably, the optimizer sourced **100% of the reallocation from near-expiry
surplus warehouses** — it correctly recognized that stock as the highest
financial priority to move, ahead of "safe" surplus that only costs a
small ongoing holding fee.

## A real modeling difficulty (and the fix)

An earlier version of this model used a *hard* constraint requiring 90% of
near-expiry surplus to be shipped no matter what. At this network size,
that constraint sometimes had no feasible solution — the total near-expiry
surplus exceeded what the network's deficit warehouses could actually
absorb, and you can't force stock into a warehouse that doesn't need it.

**Fix:** replaced the hard quota with a soft financial penalty for leaving
near-expiry stock unshipped. This achieves the same practical prioritization
without ever being mathematically unsolvable — and arguably it's more
realistic, since it honestly reflects that some near-expiry stock may
genuinely be unsaveable if there's insufficient demand anywhere in the
network to absorb it right now.

## Tech Stack

Python · pandas · numpy · PuLP (CBC solver) · openpyxl

## Files

- `03_lp_model.py` — the core optimization model (start here)
- `01_generate_data.py` / `02_transfer_cost_matrix.py` — data + real-distance cost generation
- `04_baseline.py` / `05_metrics.py` / `06_sensitivity.py` / `07_heuristic_comparison.py` — benchmarking pipeline
- `warehouse_dataset_india.csv` — input data
- `Stock_Reallocation_Results_India.xlsx` — full results workbook (summary, transfer plan, sensitivity, assumptions log)
- `Stock_Reallocation_Decision_Memo_India.pdf` — one-page write-up

## Scope & Limitations

Warehouse locations, distances, and cost benchmarks are real. Inventory
levels, demand, and expiry dates are a synthetic proof-of-concept dataset —
this is a self-built methodology demonstration, not a real company
engagement. Full assumptions log is in the results workbook.
