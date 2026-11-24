"""README charts in the portfolio chart style: one message per chart, one highlight colour, direct labels."""
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import brand_style as b

ROOT = Path(__file__).resolve().parents[1]
RES, OUT = ROOT / "results", ROOT / "charts"
OUT.mkdir(exist_ok=True)
HL = b.PROJECT["customer-value-emails"]
SRC = "Simulated data for Fieldnote (fictional), 8,000 accounts, 10% random holdout; queries in sql/"

# Chart 1: open-rate reporting against the holdout -----------------------------------------------
d = pd.read_csv(RES / "open_rate_vs_holdout.csv")
labels = ["What an open-rate report says\n(accounts that open vs rarely open)",
          "What the emails caused\n(emailed vs random holdout)"]
fig, ax = b.figure(8, 4.6)
for y, (lab, r, c) in enumerate(zip(labels[::-1], d.iloc[::-1].itertuples(), [HL, b.CONTEXT])):
    ax.barh(y, r.points, color=c, height=0.5)
    ax.plot([r.ci_low, r.ci_high], [y, y], color=b.INK, linewidth=1.2)
    ax.text(r.ci_high + 0.3, y, f"+{r.points:.1f} points", va="center", fontsize=11.5, color=b.INK)
ax.set_yticks([0, 1])
ax.set_yticklabels(labels[::-1], fontsize=10, color=b.INK)
ax.set_xlim(0, 16.5)
ax.set_xticks([])
b.clean(ax, keep="y")
b.headline(fig, "Open rates make the emails look three times as effective as they are",
           "Difference in renewal rate, percentage points, with 95% interval")
b.source(fig, SRC)
b.finish(fig, OUT / "01_open_rates_overstate.png", top=0.78, bottom=0.12, left=0.36)

# Chart 2: lift by usage tier, against how often each tier opens --------------------------------
cut = pd.read_csv(RES / "cost_of_cutting_rare_openers.csv").set_index("usage_tier")
tiers = ["Low use", "Medium use", "High use"]
fig, ax = b.figure(8, 4.2)
for y, t in enumerate(tiers[::-1]):
    r = cut.loc[t]
    c = HL if t == "Low use" else b.CONTEXT
    ax.plot([r.ci_low, r.ci_high], [y, y], color=c, linewidth=2.2, solid_capstyle="round")
    ax.scatter([r.renewal_lift_points], [y], s=90, color=c, zorder=3)
    ax.text(r.renewal_lift_points, y + 0.22, f"+{r.renewal_lift_points:.1f}", ha="center", fontsize=11,
            color=b.INK)
    ax.text(15.2, y, f"opens {r.open_rate:.0%} of emails", va="center", fontsize=10,
            color=HL if t == "Low use" else b.MUTED)
ax.axvline(0, color=b.HAIRLINE, linewidth=1)
ax.set_yticks(range(3))
ax.set_yticklabels([f"{t} accounts" for t in tiers[::-1]], fontsize=10.5, color=b.INK)
ax.set_xlim(-3, 21)
ax.set_ylim(-0.5, 2.6)
ax.set_xticks([])
b.clean(ax, keep="y")
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.text(0, -0.45, "no effect", ha="center", va="top", fontsize=9, color=b.MUTED)
b.headline(fig, "The emails help low-use accounts most, and they rarely open them",
           "Renewal lift against the holdout, percentage points, with 95% interval, by usage at the start of the year")
b.source(fig, SRC)
b.finish(fig, OUT / "02_who_the_emails_help.png", top=0.8, bottom=0.12, left=0.2)
print("charts saved")
