# Global Stock Reallocation Optimization

Linear programming model to optimize stock transfers across a 30-warehouse
network in India, minimizing holding, transfer, waste, and stockout costs.

## Problem
A specialty-chemicals distribution network has uneven inventory across
warehouses — some carry surplus (tying up capital, risking expiry) while
others face stockouts. No systematic process existed to rebalance it.

## Method
Built a transportation-problem LP (Python, PuLP) minimizing total network
cost across transfer, holding, expiry-waste, and stockout terms. Warehouse
locations, inter-city distances, and freight/holding cost benchmarks are
real (sourced from published Indian logistics industry data); inventory
levels are synthetic, since no company publishes that data publicly.
Benchmarked against a do-nothing baseline and a naive heuristic, and
stress-tested against ±15% demand forecast error.

## Key Results
- 1,936 units reallocated, fully resolving stockout risk at all 8 at-risk warehouses
- ₹7,13,538 net savings over a 6-month horizon vs. a do-nothing baseline
- Outperformed a naive allocation heuristic by ₹41,497 (6.2% more savings captured)
- Plan stayed net-positive (₹5.11L–₹8.39L) across a ±15% demand stress test

## Files
- `03_lp_model.py` — core optimization model
- `warehouse_dataset_india.csv` — input data
- `Stock_Reallocation_Results_India.xlsx` — full results workbook
- `Stock_Reallocation_Decision_Memo_India.pdf` — one-page write-up

## Notes on data
Locations, distances, and cost benchmarks are real. Current stock, demand,
and expiry figures are synthetic proof-of-concept data — full assumptions
log is in the results workbook and decision memo.
