# Financial model contract

## Implemented: baseline assessment

All monetary inputs use USD; income and expenses are monthly. Income means take-home income after tax. Debt balance and emergency savings are current stocks, not monthly expenses. All inputs must be finite and nonnegative. A baseline payment cannot exceed outstanding debt, and a debt-free profile must have zero debt payments.

Let I = income, E = essential expenses, D = discretionary expenses, P = required monthly debt payment, S = emergency savings, C = planned savings contribution, and T = selected target months.

- Cash flow before savings transfers = I - E - D - P.
- Unallocated cash after planned savings transfers = cash flow - C. A negative result identifies an unfunded plan; it does not create negative savings automatically.
- Required monthly obligations = E + P. This conservative coverage convention includes debt service and excludes discretionary spending.
- Emergency coverage = S / (E + P). With zero obligations this is undefined, not zero or infinity.
- Emergency target = T * (E + P). T is a user choice; three months is a demonstration default, not a universal standard.
- Shortfall = max(0, target - S).
- Debt-payment-to-take-home-income ratio = P / I. With zero income it is undefined. This is not a lender's gross-income debt-to-income measure and omits debts not entered.

Manual example: I=4,000; E=2,000; D=500; P=150; S=4,500; C=400; T=3. Cash flow is 1,350; unallocated cash is 950; coverage is 4,500/2,150 = approximately 2.093 months; target is 6,450; shortfall is 1,950; payment ratio is 3.75%.

## Implemented: monthly simulation

APR is entered as a percentage; monthly interest = opening debt * (APR / 100) / 12. This is a simplified monthly approximation, excluding daily accrual, fees, penalty rates, taxes, and inflation. New borrowing accrues interest starting the following month. Negative rates are not supported for credit card debt. Opening debt is treated as principal for reporting. Actual payments are attributed to unpaid accrued interest first, then principal; this attribution does not reduce debt a second time. Accrued interest and interest paid are reported separately.

For each month:

1. Apply the selected income reduction and expense shock for their defined durations. Month 1 is the first simulated month.
2. Accrue interest on opening debt.
3. Compute the required payment as the smaller of the configured fixed payment and debt plus interest. A configured zero payment with positive debt is an explicit hypothetical assumption, not an assertion about card issuer terms.
4. Use income to cover essential expenses, discretionary expenses, the shock, and that payment exactly once.
5. Cover a deficit from emergency savings, then add any residual deficit to debt. Savings never go below zero. Borrowing is assumed available without a credit limit and is reported explicitly.
6. Allocate positive surplus to savings and extra debt repayment according to policy. Contributions cannot exceed available surplus. Cap debt payments at outstanding debt and savings allocations at the fixed baseline target. Baseline policy saves up to the planned contribution, then pays up to the planned additional debt payment, leaving unused cash unallocated. Recovery policies use the same user-selected monthly allocation cap, limited by actual surplus, and redirect unused allocation to the other goal. No savings beyond the selected target are added, and existing savings above target are preserved unless needed for a deficit.
7. Record closing savings, debt, interest, new borrowing, and unallocated cash. No investment returns apply in the MVP.

All strategies use the same initial income, expenses, shock, target, and allocation cap. They operate from month 1, including during the shock, rather than starting from different post-shock positions. Savings-first funds the target before extra debt repayment; debt-first first replenishes a user-defined reserve (zero by default), then pays extra debt before funding the rest of the savings target; balanced initially divides the cap equally and redirects unused allocations. A reserve must not exceed the target and is not protected from essential deficit withdrawals. Minimum payments apply to all strategies. Required payments fall to zero when debt is paid off, which can increase subsequent monthly cash flow. Planned baseline contributions are replaced by, not added to, the recovery allocation cap.

Report first target attainment separately from full recovery (savings at target and debt no higher than pre-shock debt after all transactions of the final shock month). Results are elapsed months from simulation start. First attainment does not guarantee balances remain adequate later. If not reached within the horizon, display “not reached within horizon,” not a fabricated recovery date. A zero target is mathematically satisfied but is not evidence of preparedness. Recovery does not imply debt freedom. Savings depletion is the first month savings reach zero, including month 0 if initially empty.

Supported shocks begin in month 1: a one-time medical or vehicle bill; total income loss; a percentage income reduction; or an additional monthly dollar amount of essential expenses. Income and expense changes last for the selected duration. Essential expenses revert afterward. Only one scenario is active at a time. The UI horizon is 24–120 months so 12/24-month recovery snapshots are always available; the engine supports 1–120 months for testing. A duration longer than the UI horizon displays a local error. Month 0 contains opening stocks only, with zero cash transactions. Money is calculated at full floating-point precision and rounded to cents only for display; balances may differ from bank statements using daily accrual and transaction-level rounding.

### Ledger identities

For every nonzero month:

```text
income + savings withdrawn + new borrowing
  = essential expenses + discretionary expenses + shock bill
    + required payment + extra payment + savings contribution + unallocated cash

closing savings = opening savings - savings withdrawn + savings contribution
closing debt = opening debt + interest - required payment - extra payment + new borrowing
```

Unallocated cash is reported as a monthly amount. It is not automatically accumulated into savings or invested. No negative savings or debt balances are permitted. Invalid inputs or numeric overflow are rejected.

Manual shock example: income 1,000; essentials 600; discretionary 100; savings 500; debt 1,000; minimum payment 100; APR 24%; unexpected expense 1,000. Month-1 interest is 20. Cash flow is -800. Savings cover 500 and new borrowing covers 300. Closing savings are zero and closing debt is 1,220. The next month's interest is 24.40.

## Implemented: long-term projection

The projection is independent of emergency simulation assets: its initial amount is not automatically withdrawn from emergency savings. It uses nominal USD and an effective annual rate, entered as a percentage. The monthly rate is `(1 + annual_rate / 100) ** (1/12) - 1`. Monthly order: apply return to the opening balance, then add the end-of-month contribution. Opening month 0 contains initial principal. A contribution pause skips the first selected monthly contributions, with no later catch-up; the opening amount remains invested. The pause is user-defined and is not inferred from emergency recovery.

For n months, monthly rate r, initial amount P and monthly contribution C (without a pause):

```text
FV = P * (1+r)^n + C * ((1+r)^n - 1) / r   if r != 0
FV = P + C*n                              if r == 0
```

The implementation iterates monthly to also support contribution pauses and first goal attainment. It shows a contributions-only 0% path, the selected constant return, and the selected return with a pause. Contributed principal and hypothetical gains/losses are separate. A zero-return path assumes contributions actually occur; it is not a guaranteed funding commitment. Negative annual assumptions above -100% are allowed; the educational model limits annual rates to at most 100% and horizons to 1–50 years. Returns are not forecasts. Fees, taxes, inflation, volatility, and investment selection are excluded. No authoritative health score or personalized recommendation is used.

For the affordability warning, compare the proposed future contribution against positive baseline cash remaining after planned savings and a feasible extra debt payment. The feasible extra payment comes from month 1 of the existing baseline simulation without an emergency: it is capped by available cash and debt remaining after interest and the required payment. This prevents subtracting an impossible extra payment when debt is zero or almost paid off. The assessment's planned savings definition remains unchanged; recovery-strategy allocations do not replace it. The warning describes a constraint and does not block educational exploration. A separate comparison shows the impact of pausing contributions and the emergency scenario's accrued debt interest. Neither cost is automatically subtracted from the independent projection.

Manual projection examples: 1,000 initial + 100 at each month end for 12 months with 0% returns = 2,200. Pausing the first three contributions gives 1,900. With no contributions and a 12% effective annual return, 1,000 becomes 1,120 after 12 months; a -10% assumption gives 900.
