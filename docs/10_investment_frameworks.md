# Investment Frameworks Encoded in OvelhaInvest

> Reference: CLAUDE.md Sections 6 and 26

## 6.1 David Swensen / Yale Endowment Model
Primary allocation framework. Asset location: bonds→tax-deferred, equities→Roth/taxable.
Fee drag calculator. REITs in US equity sleeve.

## 6.2 Ray Dalio / All Weather / Risk Parity
Risk parity weights (Dalio All-Weather logic). Correlation matrix. Macro regime 4-quadrant classifier.
Rising growth+low inflation→equities; Falling growth→bonds; Rising inflation→real assets; Stagflation→gold/TIPS.

## 6.3 Howard Marks / Market Cycles
Opportunity Tier 1/2 triggers. Cycle position indicator. Second-level thinking prompt in AI advisor.
Market sentiment gauge in signals_runs.inputs_summary.

## 6.4 Graham / Buffett Valuation Framework
margin_of_safety_pct = (fair_value - price) / fair_value.
Buy zone: margin_of_safety >= 15% AND quality_score >= 0.6.
moat_rating stored on assets. DCF eligible only for stable FCF + moat != "none".

## 6.5 Bogle / Index Investing
Expense ratio tracker. Cost-optimized benchmark comparison.
Alert if individual stock sleeve > 25% of equity without justification.

## 26. Factor Research (Fama-French + Carhart)
Five factors: Market (Beta), Size (SMB), Value (HML), Profitability (RMW), Investment (CMA) + Momentum.
Factor composite weights shift by macro regime (FACTOR_COMPOSITE_WEIGHTS_BY_REGIME).
Buy signal requires all three factors above minimum threshold — no isolation.
