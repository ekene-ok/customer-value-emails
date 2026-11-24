"""README charts in the portfolio chart style: one message per chart, one highlight colour, short direct labels."""
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import brand_style as b

ROOT = Path(__file__).resolve().parents[1]
RES, OUT = ROOT / "results", ROOT / "charts"
OUT.mkdir(exist_ok=True)
HL = b.PROJECT["customer-value-emails"]
SRC = "Simulated data for Fieldnote (fictional), 8,000 accounts, 10% random holdout"

# Chart 1: open-rate reporting against the holdout
d = pd.read_csv(RES / "open_rate_vs_holdout.csv")
fig, ax = b.chart(height=3.6, label_in=2.1)
b.hbar(ax, ["Open-rate report", "Holdout test"], d.points.tolist(), {1}, lambda v: f"+{v:.1f} pts", HL,
       sublabels=["accounts that open vs rarely open", "emailed vs a random no-email group"])
b.titles(fig, "Open rates make the emails look three times as effective",
         "Increase in renewal rate credited to the emails, percentage points, measured two ways")
b.credit(fig, SRC)
b.save(fig, OUT / "01_open_rates_overstate.png")

# Chart 2: lift by usage tier, with how often each tier opens
cut = pd.read_csv(RES / "cost_of_cutting_rare_openers.csv").set_index("usage_tier").loc[
    ["Low use", "Medium use", "High use"]]
fig, ax = b.chart(height=3.9, label_in=1.25, right_in=1.3)
b.dotrange(ax, cut.index.tolist(), cut.renewal_lift_points.tolist(), cut.ci_low.tolist(), cut.ci_high.tolist(),
           {0}, lambda v: f"+{v:.1f}", HL, xlim=(-2, 13))
for y, (t, r) in zip([2, 1, 0], cut.iterrows()):
    ax.text(1.03, y, f"{r.open_rate:.0%}", transform=ax.get_yaxis_transform(), va="center", fontsize=b.VALUE,
            color=b.INK if t == "Low use" else b.MUTED)
ax.text(1.03, 2.75, "Open rate", transform=ax.get_yaxis_transform(), va="center", fontsize=9, color=b.MUTED)
b.titles(fig, "Low-use accounts gain the most from the emails, and open them least",
         "Renewal lift against the no-email group, percentage points, with 95% range, by product usage")
b.credit(fig, SRC)
b.save(fig, OUT / "02_who_the_emails_help.png")
print("charts saved")
