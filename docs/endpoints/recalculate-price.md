# `POST /recalculate-price`

## Purpose

Recalculates the parents of one manually edited value in an existing order
product calculation. The route does not run CAD extraction or an ML model; it
uses the submitted calculation snapshot and the same commercial coefficients,
quantity curve, VAT rate and price formulas as `/calculate-price`.

The edited field is required as a query parameter because a complete snapshot
contains duplicate values such as top-level `mat_price` and
`total_price_breakdown.mat_price`. Without the path, the backend cannot tell
which copy the user changed.

```http
POST /recalculate-price?changed_field=total_price_breakdown.work_price
Content-Type: application/json
```

## Request

The body accepts order metadata, manufacturing inputs and both existing price
breakdowns. `quantity`, `total_price_breakdown` and
`detail_price_calculation` are required. Other fields are optional.

```json
{
  "order_id": "order-701",
  "order_name": "Pump bracket",
  "order_code": "PB-701-B",
  "service_id": "cnc-milling",
  "material_id": "non_ferrous_Д16",
  "finish_id": "1",
  "tolerance_id": "1",
  "cover_id": ["1"],
  "k_otk": 1.0,
  "manufacturing_cycle": 8,
  "coating_thickness_microns": null,
  "electroplating_family": null,
  "electroplating_process_id": null,
  "is_need_special_equipment": true,
  "k_quantity": 0.91,
  "mat_price": 120.0,
  "material_form": "sheet",
  "processing_depth_microns": null,
  "special_instructions": "Keep datum face uncoated",
  "work_price": 300.0,
  "file_id": "file-701",
  "document_ids": ["drawing-701", "spec-701"],
  "length": 120.0,
  "width": 55.0,
  "height": 18.0,
  "mat_volume": 0.00013068,
  "mat_weight": 0.366,
  "total_time": 0.65,
  "detail_price_one": 1.0,
  "quantity": 40,
  "total_price_breakdown": {
    "mat_price": 120.0,
    "dop_mat_price": 0.0,
    "price_of_hour_with_others": 3000.0,
    "price_special_equipment_to_quantity": 20.0,
    "administrative_expenses": 1.0,
    "cost": 1.0,
    "detail_price": 1.0,
    "dop_salary": 1.0,
    "insurance_price": 1.0,
    "is_need_special_equipment": true,
    "material_price_special_equipment": 250.0,
    "net_cost": 1.0,
    "overhead_expenses": 1.0,
    "price_of_hour": 732.91818,
    "price_special_equipment": 800.0,
    "profit": 1.0,
    "total_time": 0.65,
    "work_price": 475.0
  },
  "detail_price_calculation": {
    "material_price": 1.0,
    "price_special_equipment": 1.0,
    "price_without_vat": 1.0,
    "salary_fund_with_taxes": 1.0,
    "taxes": 1.0,
    "total": 2.0
  }
}
```

In this example, `475.0` is authoritative because `changed_field` points to
`total_price_breakdown.work_price`. The stale top-level `work_price` and stale
parent totals are replaced.

## Response

The response uses the standard API envelope. `data` contains the submitted
product with its recalculated fields and adds `detail_price` and `total_price`.

```json
{
  "success": true,
  "message": "Price recalculated from total_price_breakdown.work_price",
  "data": {
    "order_id": "order-701",
    "order_code": "PB-701-B",
    "quantity": 40,
    "k_quantity": 0.91,
    "mat_price": 120.0,
    "work_price": 475.0,
    "detail_price_one": 2010.74,
    "detail_price": 1829.77,
    "total_price": 73190.8,
    "total_price_breakdown": {
      "mat_price": 120.0,
      "work_price": 475.0,
      "dop_salary": 47.5,
      "insurance_price": 157.795,
      "overhead_expenses": 407.2175,
      "administrative_expenses": 408.12,
      "net_cost": 1615.6325,
      "profit": 375.108125,
      "cost": 1990.74,
      "price_special_equipment": 800.0,
      "price_special_equipment_to_quantity": 20.0,
      "detail_price": 1829.77
    },
    "detail_price_calculation": {
      "material_price": 110.29,
      "salary_fund_with_taxes": 1701.28,
      "price_special_equipment": 18.2,
      "price_without_vat": 1829.77,
      "taxes": 402.55,
      "total": 2232.32
    }
  },
  "timestamp": "2026-08-25T11:24:00",
  "version": "3.0.0"
}
```

Numeric values above illustrate the shape; the deployed commercial constants
determine the exact result.

## Recalculation mechanism

The dependency chain is:

```text
dimensions
  -> mat_volume -> mat_weight -> mat_price

total_time / price_of_hour / manufacturing coefficients
  -> work_price
  -> dop_salary
  -> insurance_price

mat_price + work_price + dop_salary + insurance_price
  + overhead_expenses + administrative_expenses
  -> net_cost -> profit -> cost

price_special_equipment / quantity
  -> price_special_equipment_to_quantity

cost + price_special_equipment_to_quantity
  -> detail_price_one
  -> detail_price = detail_price_one * k_quantity
  -> total_price = detail_price * quantity

detail_price
  -> detail_price_calculation.price_without_vat
  -> taxes -> total
```

Propagation starts at the edited node and only moves toward dependants:

- editing `work_price` recalculates all labor additions, `net_cost`, `profit`,
  `cost`, unit prices, order price and the compact calculation;
- editing `net_cost` keeps its children unchanged and recalculates `profit` and
  every value above it;
- editing `profit` recalculates `cost` and prices but not `net_cost`;
- editing `detail_price_calculation.taxes` recalculates only the compact
  `total`;
- editing one compact component recalculates `price_without_vat`, VAT, compact
  total, unit price and order price;
- editing `quantity` recalculates `k_quantity`, redistributes the total tooling
  price, and then recalculates unit and order prices;
- order identifiers, document references and instructions have no price
  dependants and are returned unchanged.

The route chooses `location_3` commercial coefficients for `printing` and
`location_1` for the other current automatic services, matching the active
calculators.

## Integration

1. Keep the last calculation response with the order product.
2. Apply the user's edit to that snapshot.
3. Send the complete updated snapshot to this route.
4. Put the exact edited JSON path in `changed_field`.
5. Replace the stored product calculation with response `data`.

Send one edit per request. If several independent fields are edited, call the
route in edit order, using each returned `data` object as the next snapshot.
This avoids ambiguous precedence between two changed branches.
