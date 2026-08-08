"""
Stock Reallocation LP Model -- India, 55 warehouses, real-distance costs.
Same formulation as the 18-warehouse version (transportation problem +
expiry hard constraint + stockout penalty), adapted for a per-warehouse-pair
cost lookup instead of a bucketed region matrix.
"""
import pandas as pd
import pulp

TIME_HORIZON_MONTHS = 6
SURPLUS_COVER_THRESHOLD = 45
DEFICIT_COVER_THRESHOLD = 20
EXPIRY_URGENT_THRESHOLD = 45
STOCKOUT_PENALTY_PER_UNIT_INR = 130.0
WASTE_PENALTY_PER_UNIT_INR = 220.0
# ^ Rs./unit penalty for leaving near-expiry surplus unallocated, applied on
# top of normal holding cost. Reflects write-off/heavy-discount risk on
# stock that may expire before use. Deliberately a SOFT penalty (added cost),
# not a hard "X% must move" constraint: with 30 warehouses, a hard constraint
# can demand more units be shipped than the network's deficit warehouses
# actually need, which is infeasible (you can't force product where there's
# no demand for it). The soft penalty lets the LP prioritize moving
# near-expiry stock wherever real deficit demand exists, while honestly
# reporting that some near-expiry surplus may go unrecovered if network-wide
# demand can't absorb it -- a more realistic outcome than a threshold that
# silently breaks depending on the data draw.
# ^ Rs./unit proxy for the cost of leaving deficit unmet (emergency local
# procurement / expedited freight / lost service). Chosen to sit meaningfully
# above typical same-zone transfer costs (a few Rs./unit) but below the
# most expensive cross-country lanes (~Rs.75/unit), so the model faces a
# genuine trade-off rather than always/never shipping. Stated assumption,
# not sourced -- flagged in Assumptions & Method.


def load_data(warehouse_csv="warehouse_dataset_india.csv", cost_csv="warehouse_transfer_cost_matrix.csv"):
    wh = pd.read_csv(warehouse_csv, keep_default_na=False, na_values=[""])
    cost = pd.read_csv(cost_csv, keep_default_na=False, na_values=[""])
    cost_lookup = {(r["from_warehouse"], r["to_warehouse"]): r["cost_per_unit_inr"] for _, r in cost.iterrows()}
    return wh, cost_lookup


def classify(wh, demand_multiplier=1.0):
    df = wh.copy()
    df["avg_monthly_demand"] = df["avg_monthly_demand"] * demand_multiplier
    df["days_of_stock_cover"] = df["current_stock"] / (df["avg_monthly_demand"] / 30)
    df["surplus_units"] = (df["current_stock"] - SURPLUS_COVER_THRESHOLD * (df["avg_monthly_demand"] / 30)).clip(lower=0)
    df["deficit_units"] = (DEFICIT_COVER_THRESHOLD * (df["avg_monthly_demand"] / 30) - df["current_stock"]).clip(lower=0)
    df["is_urgent_expiry"] = df["expiry_days_remaining"] < EXPIRY_URGENT_THRESHOLD
    return df


def solve_lp(df, cost_lookup, time_horizon_months=TIME_HORIZON_MONTHS, verbose=False):
    warehouses = df["warehouse_id"].tolist()
    surplus = dict(zip(df["warehouse_id"], df["surplus_units"]))
    deficit = dict(zip(df["warehouse_id"], df["deficit_units"]))
    holding_cost = dict(zip(df["warehouse_id"], df["unit_holding_cost_per_month_inr"]))
    urgent = dict(zip(df["warehouse_id"], df["is_urgent_expiry"]))
    city_of = dict(zip(df["warehouse_id"], df["city"]))

    surplus_whs = [w for w in warehouses if surplus[w] > 0]
    deficit_whs = [w for w in warehouses if deficit[w] > 0]

    prob = pulp.LpProblem("StockReallocationIndia", pulp.LpMinimize)

    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
         for i in surplus_whs for j in deficit_whs}
    unalloc = {i: pulp.LpVariable(f"unalloc_{i}", lowBound=0) for i in surplus_whs}
    unmet = {j: pulp.LpVariable(f"unmet_{j}", lowBound=0) for j in deficit_whs}

    transfer_cost_term = pulp.lpSum(x[(i, j)] * cost_lookup[(i, j)] for i in surplus_whs for j in deficit_whs)
    holding_cost_term = pulp.lpSum(unalloc[i] * holding_cost[i] * time_horizon_months for i in surplus_whs)
    # Extra waste penalty on unallocated surplus from urgent-expiry warehouses,
    # on top of normal holding cost (soft prioritization, not a hard quota)
    waste_term = pulp.lpSum(unalloc[i] * WASTE_PENALTY_PER_UNIT_INR for i in surplus_whs if urgent[i])
    stockout_term = pulp.lpSum(unmet[j] * STOCKOUT_PENALTY_PER_UNIT_INR for j in deficit_whs)
    prob += transfer_cost_term + holding_cost_term + waste_term + stockout_term

    for i in surplus_whs:
        prob += pulp.lpSum(x[(i, j)] for j in deficit_whs) + unalloc[i] == surplus[i]
    for j in deficit_whs:
        prob += pulp.lpSum(x[(i, j)] for i in surplus_whs) + unmet[j] == deficit[j]

    status = prob.solve(pulp.PULP_CBC_CMD(msg=verbose))

    records = []
    for (i, j), var in x.items():
        val = var.value()
        if val and val > 0.5:
            records.append({
                "from_warehouse": i, "from_city": city_of[i],
                "to_warehouse": j, "to_city": city_of[j],
                "units_transferred": round(val),
                "cost_per_unit_inr": cost_lookup[(i, j)],
                "transfer_cost_inr": round(val * cost_lookup[(i, j)], 2),
                "from_urgent_expiry": urgent[i],
            })
    transfer_df = pd.DataFrame(records).sort_values("transfer_cost_inr", ascending=False) if records else pd.DataFrame(
        columns=["from_warehouse", "from_city", "to_warehouse", "to_city", "units_transferred",
                 "cost_per_unit_inr", "transfer_cost_inr", "from_urgent_expiry"])

    total_cost = pulp.value(prob.objective)
    unalloc_df = pd.DataFrame([{"warehouse_id": i, "unallocated_surplus": round(unalloc[i].value() or 0)}
                                for i in surplus_whs])
    unmet_df = pd.DataFrame([{"warehouse_id": j, "unmet_deficit": round(unmet[j].value() or 0)}
                              for j in deficit_whs])

    return transfer_df, unalloc_df, unmet_df, pulp.LpStatus[status], total_cost


if __name__ == "__main__":
    wh, cost_lookup = load_data()
    df = classify(wh)
    transfer_df, unalloc_df, unmet_df, status, total_cost = solve_lp(df, cost_lookup, verbose=False)

    print("LP Status:", status)
    print(f"Total network cost: Rs.{total_cost:,.2f}\n")
    print(f"Number of transfer lanes used: {len(transfer_df)}")
    print(transfer_df.head(15).to_string(index=False))
    print(f"\nTotal units reallocated: {transfer_df['units_transferred'].sum():,.0f}")
    print(f"Total transfer cost: Rs.{transfer_df['transfer_cost_inr'].sum():,.2f}")
    print(f"\nUnallocated surplus (idle): {unalloc_df['unallocated_surplus'].sum():,.0f} units")
    print(f"Unmet deficit (stockout risk remaining): {unmet_df['unmet_deficit'].sum():,.0f} units")
