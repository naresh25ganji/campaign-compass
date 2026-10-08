"""Generate a reproducible, original fictional retailer with observed order events.

Scenario rules live here, never in the app's diagnosis logic. Synthetic outcomes
illustrate functionality; they do not establish real platform performance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261007
AS_OF = pd.Timestamp("2026-09-30")
START = pd.Timestamp("2026-04-04")

# name, channel, goal, audience, daily spend, cpm, ctr, session cvr,
# average order value, product cost fraction, refund probability
SPECS = [
    ("Summit essentials", "Facebook", "Sales", "New customers", 210, 15, .017, .032, 165, .37, .045),
    ("Last chance packs", "Facebook", "Sales", "Returning customers", 185, 13, .027, .045, 170, .81, .19),
    ("Trail stories", "Facebook", "Awareness", "Outdoor explorers", 95, 9, .012, .014, 130, .40, .04),
    ("Alpine launch", "Instagram", "Sales", "New customers", 230, 16, .021, .033, 175, .39, .055),
    ("Weekend kit", "Instagram", "Sales", "Returning customers", 160, 12, .025, .038, 140, .45, .07),
    ("Camp in color", "Instagram", "Awareness", "Outdoor explorers", 110, 10, .022, .015, 135, .42, .05),
    ("Evergreen trail", "Pinterest", "Sales", "New customers", 155, 10, .018, .030, 185, .34, .035),
    ("Cabin collection", "Pinterest", "Sales", "Returning customers", 145, 11, .019, .028, 155, .41, .055),
    ("Adventure moodboard", "Pinterest", "Awareness", "Outdoor explorers", 90, 8, .015, .011, 140, .42, .04),
    ("Field gear", "Twitter/X", "Sales", "New customers", 150, 13, .015, .026, 160, .40, .06),
    ("Trail club", "Twitter/X", "Sales", "Returning customers", 120, 11, .019, .030, 145, .43, .06),
    ("Outside daily", "Twitter/X", "Awareness", "Outdoor explorers", 80, 7, .012, .010, 130, .41, .04),
]


def generate(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    campaigns, performance, orders = [], [], []
    serial = 0
    for i, spec in enumerate(SPECS):
        name, channel, goal, audience, budget, cpm, ctr, cvr, aov, cost, refund_p = spec
        campaign_id = f"NC-{i + 1:02d}"
        campaigns.append(dict(campaign_id=campaign_id, campaign_name=name,
                              channel=channel, goal=goal, audience=audience,
                              daily_budget=budget, target_cpa=38 if goal == "Sales" else 75))
        for day_no, day in enumerate(pd.date_range(START, AS_OF)):
            seasonal = 1 + .13 * np.sin(day_no / 11) + (.07 if day.dayofweek >= 5 else 0)
            for creative in range(2):
                creative_id = f"{campaign_id}-{'A' if creative == 0 else 'B'}"
                spend = round(budget * .5 * rng.uniform(.85, 1.15) * seasonal, 2)
                effective_cpm = cpm * rng.uniform(.85, 1.15)
                current_ctr = ctr * (1.08 if creative == 0 else .92)
                current_cvr = cvr * rng.uniform(.85, 1.15)
                # Creative A loses engagement late in the season; B stays steady.
                if i == 3 and creative == 0 and day_no > 130:
                    current_ctr *= max(.35, 1 - (day_no - 130) * .014)
                # A landing-page change depresses conversion, with stable click costs.
                if i == 9 and day_no >= 146:
                    current_cvr *= .48
                impressions = max(1, int(spend / effective_cpm * 1000))
                clicks = int(rng.binomial(impressions, min(current_ctr, 1)))
                sessions = int(rng.binomial(clicks, .88))
                eventual_purchases = int(rng.binomial(sessions, min(current_cvr, 1)))
                performance.append(dict(date=day.date().isoformat(), campaign_id=campaign_id,
                                        creative_id=creative_id, spend=spend,
                                        impressions=impressions, clicks=clicks, sessions=sessions))
                for _ in range(eventual_purchases):
                    delay = int(min(21, rng.geometric(.20 if channel == "Pinterest" else .44) - 1))
                    order_day = day + pd.Timedelta(days=delay)
                    if order_day > AS_OF:
                        continue  # Future outcomes are not observed or counted.
                    serial += 1
                    gross = round(aov * rng.uniform(.75, 1.30), 2)
                    discount = round(gross * (.14 if i == 1 else rng.uniform(0, .06)), 2)
                    paid = round(gross - discount, 2)
                    product = round(gross * cost, 2)
                    refund_day = order_day + pd.Timedelta(days=int(rng.integers(7, 36)))
                    returned = rng.random() < refund_p and refund_day <= AS_OF
                    refund = paid if returned else 0.0
                    recovery = round(product * .72, 2) if returned else 0.0
                    fulfillment = round(6.5 + paid * .029 + (8 if returned else 0), 2)
                    orders.append(dict(order_id=f"ORD-{serial:06d}", campaign_id=campaign_id,
                                       creative_id=creative_id, acquisition_date=day.date().isoformat(),
                                       order_date=order_day.date().isoformat(),
                                       refund_date=refund_day.date().isoformat() if returned else "",
                                       gross_revenue=gross, discount=discount, refund=refund,
                                       product_cost=product, recovered_cost=recovery,
                                       fulfillment_cost=fulfillment,
                                       is_new_customer=bool(rng.random() < (.90 if audience == "New customers" else .12))))
    manifest = dict(schema_version=1, brand="Northstar Outdoor", synthetic=True, seed=seed,
                    currency="USD", as_of=AS_OF.date().isoformat(),
                    attribution="Single campaign and creative credit per order; acquisition-date cohorts.",
                    scenario_notes=["High revenue with low margins and returns", "Creative engagement decline",
                                    "Landing-page conversion decline", "Delayed Pinterest purchases"])
    return pd.DataFrame(campaigns), pd.DataFrame(performance), pd.DataFrame(orders), manifest


def write_dataset(output: Path, seed: int = SEED) -> None:
    output.mkdir(parents=True, exist_ok=True)
    campaigns, performance, orders, manifest = generate(seed)
    for name, frame in [("campaigns", campaigns), ("performance", performance), ("orders", orders)]:
        frame.to_csv(output / f"{name}.csv", index=False)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(campaigns)} campaigns, {len(performance):,} daily creative rows, {len(orders):,} orders.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    write_dataset(args.output, args.seed)
