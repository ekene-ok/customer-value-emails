"""Simulate a year of customer value emails at Fieldnote, a fictional scheduling platform for small trades businesses.

Every account was randomly assigned at the start of the year:
- holdout (10%): no value emails
- recap (45%): a monthly email recapping the account's own usage
- recap_plus_action (45%): the same recap plus one recommended next step (turn on automated job reminders)

How the simulated world works (the analysis does not see these settings):
- Each account has an underlying health score. Healthier accounts open more emails AND renew more,
  which is what makes open-rate reporting misleading
- The recap email alone barely changes behaviour
- The next-step email raises adoption of job reminders, mostly for accounts that were not using the product much
- Adopting job reminders raises the chance of renewing

All data is invented. No real customer or employer data is used.
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 2026
N_ACCOUNTS = 8000
MONTHS = 12
PRICE_PER_SEAT_MONTH = 45
OUT = Path(__file__).resolve().parents[1] / "data"


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(exist_ok=True)
    n = N_ACCOUNTS
    health = rng.normal(0, 1, n)
    seats = np.clip(np.round(rng.lognormal(1.6, 0.6, n)), 1, 60).astype(int)
    arr = seats * PRICE_PER_SEAT_MONTH * 12
    # weekly active share of seats in the month before the program started: the adoption tier the team can see
    active_share = np.clip(sigmoid(0.2 + 1.1 * health + rng.normal(0, 0.45, n)), 0.02, 1)
    tier = np.where(active_share < 0.45, "Low use", np.where(active_share < 0.75, "Medium use", "High use"))
    arm = rng.choice(["holdout", "recap", "recap_plus_action"], size=n, p=[0.10, 0.45, 0.45])
    renewal_month = rng.integers(1, MONTHS + 1, n)
    industry = rng.choice(["HVAC", "Plumbing", "Electrical", "Landscaping", "Cleaning"], size=n)

    accounts = pd.DataFrame({
        "account_id": [f"A{i:05d}" for i in range(n)], "industry": industry, "seats": seats, "arr": arr,
        "active_share_start": active_share.round(3), "usage_tier": tier, "arm": arm,
        "renewal_month": renewal_month,
    })

    # Monthly sends and engagement for emailed accounts (sent until the renewal month)
    sends = []
    open_p = sigmoid(-0.55 + 0.85 * health)
    for m in range(1, MONTHS + 1):
        live = (arm != "holdout") & (renewal_month >= m)
        idx = np.flatnonzero(live)
        opened = rng.random(idx.size) < open_p[idx]
        has_action = arm[idx] == "recap_plus_action"
        clicked = opened & has_action & (rng.random(idx.size) < sigmoid(-1.1 - 0.5 * health[idx]))
        sends.append(pd.DataFrame({"account_id": accounts.account_id.values[idx], "month": m,
                                   "version": arm[idx], "opened": opened, "clicked_next_step": clicked}))
    sends = pd.concat(sends, ignore_index=True)
    months_emailed = np.where(arm == "holdout", 0, renewal_month)
    exposure = months_emailed / MONTHS

    # Adoption of job reminders by the renewal date
    already = rng.random(n) < sigmoid(-0.4 + 1.0 * health)
    lift = np.where(arm == "recap_plus_action",
                    np.select([tier == "Low use", tier == "Medium use"], [1.15, 0.55], 0.1), 0.0)
    lift = lift + np.where(arm == "recap", 0.08, 0.0)
    adopt_p = sigmoid(-1.6 + 0.6 * health + lift * (0.4 + 0.6 * exposure))
    adopted = already | (rng.random(n) < adopt_p)

    # Renewal
    renew_p = sigmoid(1.55 + 0.85 * health + 0.75 * adopted + np.where(arm == "holdout", 0, 0.04))
    renewed = rng.random(n) < renew_p

    accounts["used_reminders_at_start"] = already
    accounts["used_reminders_at_renewal"] = adopted
    accounts["renewed"] = renewed
    accounts.to_csv(OUT / "accounts.csv", index=False)
    sends.to_csv(OUT / "email_sends.csv", index=False)
    print(f"{len(accounts):,} accounts, {len(sends):,} sends written to {OUT}")


if __name__ == "__main__":
    main()
