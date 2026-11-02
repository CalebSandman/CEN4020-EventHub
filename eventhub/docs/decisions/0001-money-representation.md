# 0001 – Money representation

Status: accepted (written before the first price was computed, per Call 4)

## Decision
* All arithmetic uses `decimal.Decimal`. `float` is never used for money.
* Amounts are stored and passed between components as **integer minor units**
  (cents, yen, fils) together with the currency's **decimal places**
  (`exchange_rates.decimals`: USD/EUR/GBP/CAD/MXN = 2, JPY = 0, KWD = 3).
* Event list prices are stored in USD minor units (`events.base_price_cents`).
* Exchange rates are `Decimal` strings (units of currency per 1 USD), stored in
  the database so admins can change them without a release; `data/exchange_rates.json`
  only seeds first-time setup and never overwrites admin edits.
* `pricing.calculate_price` is the only function that multiplies, discounts,
  converts or rounds. Rounding happens **once**, on the final total, `ROUND_HALF_UP`
  to the currency's own precision. Order of operations: base x quantity -> discount -> rate -> round.
* Orders snapshot currency, rate, discount % and decimals, so history never changes
  when rates change.

## Why
Binary floats cannot represent 0.1 exactly; integer minor units make equality and
storage exact; per-currency decimals avoid showing yen with cents or truncating KWD.
