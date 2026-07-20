# Unified pricing pipeline for automatic services

This document defines the common price structure used by all automatic services:

- `printing`
- `cnc-milling`
- `composite`
- `electroplating_auto`

The goal is to keep the same calculation structure in backend, database and Bitrix24 product fields.

## Canonical order of operations

For every automatic service the unit price is calculated in the same order:

1. Service-specific logic calculates:
   - `mat_price` — material cost for one detail;
   - `work_price` — work cost for one detail before the quantity deflator;
   - `price_special_equipment_to_quantity` — technological tooling price distributed to one detail.
2. Backend calls `calculate_cost(mat_price, work_price, location, breakdown=True)`.
3. The result of `calculate_cost` is stored in `total_price_breakdown` using the common fields:
   - `mat_price`
   - `price_of_hour`
   - `work_price`
   - `dop_salary`
   - `insurance_price`
   - `overhead_expenses`
   - `administrative_expenses`
   - `net_cost`
   - `profit`
   - `cost`
4. Distributed tooling cost is added to one detail.
5. `k_quantity` is applied to the whole unit price.
6. `total_price = detail_price * quantity`.

In formula form:

```text
base_cost = calculate_cost(mat_price, work_price, location)

detail_price_one = base_cost + price_special_equipment_to_quantity

detail_price = detail_price_one * k_quantity

total_price = detail_price * quantity
```

`detail_price_one` is the reference unit price before the quantity deflator. `detail_price` is the actual unit product price for the current order.

## `calculate_cost` formula

`calculate_cost` uses the location-specific cost structure:

```text
dop_salary = dop_salary_coef * work_price

insurance_price = insurance_coef * (work_price + dop_salary)

overhead_expenses = overhead_expenses_coef * work_price

administrative_expenses = administrative_expenses_coef * work_price

net_cost =
    mat_price
    + work_price
    + dop_salary
    + insurance_price
    + overhead_expenses
    + administrative_expenses

labor_net_cost = net_cost - mat_price

profit =
    mat_price * profit_material
    + labor_net_cost * other_profit

cost = net_cost + profit
```

## Special tooling

Tooling is a batch/order-level cost. If a service has no special tooling, it passes `0`.

```text
price_special_equipment_to_quantity = price_special_equipment / quantity
```

Current service behavior:

| service_id | Special tooling |
|---|---|
| `printing` | `0` |
| `electroplating_auto` | `0` |
| `cnc-milling` | classifier-driven special-equipment cost |
| `composite` | request-driven tooling flag `is_need_special_equipment` |

The quantity deflator is applied after tooling is added:

```text
detail_price = (cost + price_special_equipment_to_quantity) * k_quantity
```

## Frontend mini-calculation

`detail_price_calculation` is the compact user-facing calculation. It is derived from the same backend price structure and contains six canonical fields:

```text
material_price
salary_fund_with_taxes
price_special_equipment
price_without_vat
taxes
total
```

Meaning:

```text
material_price = mat_price * (1 + profit_material) * k_quantity

salary_fund_with_taxes =
    (work_price + dop_salary + insurance_price + overhead_expenses + administrative_expenses)
    * (1 + other_profit)
    * k_quantity

price_special_equipment = price_special_equipment_to_quantity * k_quantity

price_without_vat = detail_price

taxes = detail_price * VAT_RATE

total = detail_price + taxes
```

These three components should sum to the unit price without VAT:

```text
material_price + salary_fund_with_taxes + price_special_equipment = price_without_vat
```

The field name `salary_fund_with_taxes` is kept for compatibility, but its actual meaning is broader: it is the whole non-material production price bucket, including work, salary add-ons, insurance, overhead, administrative expenses and labor profit.

## Bitrix24 product fields

For product rows in Bitrix24:

```text
PRICE = detail_price
QUANTITY = quantity
```

Then the product row amount is:

```text
PRICE * QUANTITY = total_price
```

Do not use `detail_price_one` as the product price unless a reference price before quantity deflator is explicitly needed.
