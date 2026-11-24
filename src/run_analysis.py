"""Do customer value emails change renewal, and who should get which version?

Loads the simulated data into DuckDB, builds the views in sql/, then adds bootstrap confidence intervals,
the size of the prize and test sizes in Python. Writes CSVs to results/.
"""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, SQL, RES = ROOT / "data", ROOT / "sql", ROOT / "results"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(7)
B = 4000
TIERS = ["Low use", "Medium use", "High use"]


def boot_diff(x, y):
    """Difference in means (x minus y) with a 95% bootstrap interval, in percentage points."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = [rng.choice(x, x.size).mean() - rng.choice(y, y.size).mean() for _ in range(B)]
    lo, hi = np.percentile(d, [2.5, 97.5])
    return round((x.mean() - y.mean()) * 100, 2), round(lo * 100, 2), round(hi * 100, 2)


def per_arm_for(p, diff, z=2.8):
    """Accounts needed per group to detect a difference with 80% power at 5% significance (z = 1.96 + 0.84)."""
    return int(np.ceil(2 * p * (1 - p) * (z / diff) ** 2))


def main():
    con = duckdb.connect()
    con.execute(f"CREATE TABLE accounts AS SELECT * FROM read_csv_auto('{DATA / 'accounts.csv'}')")
    con.execute(f"CREATE TABLE email_sends AS SELECT * FROM read_csv_auto('{DATA / 'email_sends.csv'}')")
    for f in sorted(SQL.glob("*.sql")):
        con.execute(f.read_text())
    for view in ["open_rate_report", "holdout_comparison", "open_rate_by_tier"]:
        con.table(view).df().to_csv(RES / f"{view}.csv", index=False)
    a = con.table("account_outcomes").df()

    # 1. Lift against the random holdout, every assigned account counted whether it opened or not
    rows = []
    groups = {"Either email": ["recap", "recap_plus_action"], "Recap": ["recap"],
              "Recap plus next step": ["recap_plus_action"]}
    for tier in ["All accounts"] + TIERS:
        t = a if tier == "All accounts" else a[a.usage_tier == tier]
        hold = t[t.arm == "holdout"]
        for name, arms in groups.items():
            em = t[t.arm.isin(arms)]
            for metric, col in [("Renewal", "renewed_flag"), ("Reminders adoption", "adopted_flag")]:
                est, lo, hi = boot_diff(em[col], hold[col])
                rows.append({"usage_tier": tier, "email": name, "metric": metric, "emailed_accounts": len(em),
                             "holdout_accounts": len(hold), "emailed_rate": round(em[col].mean(), 4),
                             "holdout_rate": round(hold[col].mean(), 4), "lift_points": est,
                             "ci_low": lo, "ci_high": hi, "clear": lo > 0 or hi < 0})
    lift = pd.DataFrame(rows)
    lift.to_csv(RES / "lift_vs_holdout.csv", index=False)

    # 2. The next-step version against the recap alone
    rows = []
    for tier in ["All accounts"] + TIERS:
        t = a if tier == "All accounts" else a[a.usage_tier == tier]
        for metric, col in [("Renewal", "renewed_flag"), ("Reminders adoption", "adopted_flag")]:
            est, lo, hi = boot_diff(t[t.arm == "recap_plus_action"][col], t[t.arm == "recap"][col])
            rows.append({"usage_tier": tier, "metric": metric, "difference_points": est, "ci_low": lo,
                         "ci_high": hi, "clear": lo > 0 or hi < 0})
    versions = pd.DataFrame(rows)
    versions.to_csv(RES / "next_step_vs_recap.csv", index=False)

    # 3. What open-rate reporting says against what the holdout says
    emailed = a[a.emailed == "Emailed"]
    opens = emailed[emailed.open_group == "Opens most emails"].renewed_flag
    rare = emailed[emailed.open_group == "Opens few or none"].renewed_flag
    naive = boot_diff(opens, rare)
    true = lift[(lift.usage_tier == "All accounts") & (lift.email == "Either email") & (lift.metric == "Renewal")].iloc[0]
    pd.DataFrame([
        {"view": "Open-rate report: accounts that open most emails vs those that rarely open",
         "points": naive[0], "ci_low": naive[1], "ci_high": naive[2]},
        {"view": "Holdout test: emailed accounts vs accounts that got no email",
         "points": true.lift_points, "ci_low": true.ci_low, "ci_high": true.ci_high},
    ]).to_csv(RES / "open_rate_vs_holdout.csv", index=False)

    # 4. Size of the prize: renewal lift applied to the ARR that comes up for renewal each year
    total_arr = a.arr.sum()
    emailed_share = 0.9  # keep a 10% holdout running
    prize = {k: round(total_arr * emailed_share * v / 100) for k, v in
             {"estimate": true.lift_points, "low": true.ci_low, "high": true.ci_high}.items()}

    # 5. Cost of a common hygiene rule: stop emailing accounts that rarely open
    # Uses each usage tier's lift for the accounts in that tier who rarely open. Rare openers are less healthy
    # than openers within a tier, so this is a rough guide, not a measured effect.
    cut = []
    for tier in TIERS:
        t = emailed[emailed.usage_tier == tier]
        tl = lift[(lift.usage_tier == tier) & (lift.email == "Either email") & (lift.metric == "Renewal")].iloc[0]
        rare_arr = t[t.open_group == "Opens few or none"].arr.sum()
        cut.append({"usage_tier": tier, "share_rarely_opening": round((t.open_group == "Opens few or none").mean(), 3),
                    "open_rate": round(t.open_rate.mean(), 3), "renewal_lift_points": tl.lift_points,
                    "ci_low": tl.ci_low, "ci_high": tl.ci_high,
                    # scaled from this year's emailed accounts to next year's, when 90% of the whole base is emailed
                    "arr_rarely_opening_full_base": round(rare_arr * emailed_share / (len(emailed) / len(a))),
                    })
    cut = pd.DataFrame(cut)
    cut["retained_arr_lost_if_cut"] = (cut.arr_rarely_opening_full_base * cut.renewal_lift_points / 100).round()
    cut.to_csv(RES / "cost_of_cutting_rare_openers.csv", index=False)

    # 6. Test sizes for next year
    low = a[a.usage_tier == "Low use"]
    p_low = low[low.arm == "recap"].renewed_flag.mean()
    pa = a[a.arm == "recap"].adopted_flag.mean()
    sizes = pd.DataFrame([
        {"question": "Does the next-step email beat the recap on renewal (all accounts, 1-point difference)?",
         "per_group": per_arm_for(a.renewed_flag.mean(), 0.01)},
        {"question": "Does the next-step email beat the recap on renewal for low-use accounts (3-point difference)?",
         "per_group": per_arm_for(p_low, 0.03)},
        {"question": "Do value emails lift renewal at all (4-point difference, 10% holdout)?",
         "per_group": per_arm_for(a.renewed_flag.mean(), 0.04)},
        {"question": "Does the next-step email lift reminders adoption (4-point difference)?",
         "per_group": per_arm_for(pa, 0.04)},
    ])
    sizes.to_csv(RES / "test_sizes.csv", index=False)

    summary = pd.DataFrame([{"total_arr": total_arr, "accounts": len(a), "holdout_accounts": (a.arm == "holdout").sum(),
                             "open_rate": round(emailed.open_rate.mean(), 3),
                             "retained_arr_per_year": prize["estimate"], "retained_arr_low": prize["low"],
                             "retained_arr_high": prize["high"],
                             "retained_arr_lost_by_cutting_rare_openers": cut.retained_arr_lost_if_cut.sum()}])
    summary.to_csv(RES / "summary.csv", index=False)

    print(lift[lift.email == "Either email"].to_string(index=False))
    print(versions.to_string(index=False))
    print(pd.read_csv(RES / "open_rate_vs_holdout.csv").to_string(index=False))
    print(cut.to_string(index=False))
    print(sizes.to_string(index=False))
    print(summary.T.to_string())


if __name__ == "__main__":
    main()
