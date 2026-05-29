"""
Generate fact_sheets for 50 OOS test cases.

Reads  : data/oos_test_cases_50.json
Writes : data/oos_fact_sheets.json

All customer / order data is synthetic but internally consistent.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

random.seed(2024)

OOS_CASES_PATH = Path("data/oos_test_cases_50.json")
OUT_PATH       = Path("data/oos_fact_sheets.json")

# ---------------------------------------------------------------------------
# Name pool
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Jordan","Alex","Taylor","Morgan","Casey","Riley","Jamie","Avery","Quinn","Blake",
    "Peyton","Hayden","Kendall","Cameron","Finley","Reese","Skyler","Dakota","Emery","Drew",
    "Parker","Rowan","Sage","River","Devon","Shawn","Eden","Remy","Alexis","Logan",
    "Bailey","Harley","Jessie","Ryan","Corey","Dylan","Sam","Charlie","Chris","Pat",
    "Angel","Robin","Frankie","Kerry","Lane","Lee","Lynn","Brook","Tatum","Reagan",
]
LAST_NAMES = [
    "Wang","Chen","Lin","Liu","Kim","Park","Lee","Zhang","Li","Yang",
    "Huang","Wu","Chen","Zheng","Guo","Sun","Zhou","Tang","Lu","Xu",
    "Smith","Brown","Johnson","Williams","Jones","Garcia","Miller","Davis","Taylor","Moore",
    "Martin","Jackson","Thompson","White","Harris","Lewis","Clark","Walker","Hall","Allen",
    "Nguyen","Patel","Singh","Kumar","Ahmed","Ali","Khan","Rahman","Hassan","Malik",
]

def rand_name(i: int) -> str:
    random.seed(i * 31 + 7)
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def rand_email(i: int) -> str:
    return f"oos{i:03d}@example.com"

def rand_phone(i: int) -> str:
    return f"0912-{345 + i // 100:03d}-{i % 1000:03d}"

def rand_order_num(i: int) -> str:
    random.seed(i * 97 + 13)
    return f"ORD{random.randint(10000000, 99999999)}"

# ---------------------------------------------------------------------------
# Amount range by product category
# ---------------------------------------------------------------------------
AMOUNT_RANGES: dict[str, tuple[float, float]] = {
    "Electronics":                 (150.0, 850.0),
    "Mobile":                      (300.0, 950.0),
    "Home Appliences":             (100.0, 600.0),
    "Home":                        (40.0,  300.0),
    "LifeStyle":                   (25.0,  180.0),
    "Books & General merchandise": (10.0,  80.0),
    "Furniture":                   (150.0, 1200.0),
    "Affiliates":                  (30.0,  200.0),
    "GiftCard":                    (20.0,  200.0),
    "nan":                         (30.0,  250.0),
    None:                          (30.0,  250.0),
}

def rand_amount(product: str | None, i: int) -> float:
    key = product if product in AMOUNT_RANGES else None
    lo, hi = AMOUNT_RANGES[key]
    random.seed(i * 53 + 19)
    return round(random.uniform(lo, hi), 2)

def rand_item(product: str | None, i: int) -> str:
    prefix_map = {
        "Electronics":                 "Electronics",
        "Mobile":                      "Mobile",
        "Home Appliences":             "Appliance",
        "Home":                        "Home",
        "LifeStyle":                   "Lifestyle",
        "Books & General merchandise": "Book",
        "Furniture":                   "Furniture",
        "Affiliates":                  "Partner",
    }
    prefix = prefix_map.get(product, "Product")
    random.seed(i * 11 + 3)
    return f"{prefix}_{random.randint(1, 99)}"

# ---------------------------------------------------------------------------
# Sub-category → intent + expected_tools + order_status + refund_status
# ---------------------------------------------------------------------------
SUBCAT_MAP: dict[str, dict] = {
    # Returns
    "Reverse Pickup Enquiry": {
        "intent":         "track_return",
        "expected_tools": ["query_order", "track_shipping"],
        "order_status":   "Delivered",
        "refund_status":  "Pending",
    },
    "Return request": {
        "intent":         "return_request",
        "expected_tools": ["query_order", "apply_refund"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Missing": {
        "intent":         "missing_item",
        "expected_tools": ["query_order"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Exchange / Replacement": {
        "intent":         "exchange_request",
        "expected_tools": ["query_order"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Product related Issues": {
        "intent":         "return_request",
        "expected_tools": ["query_order", "apply_refund"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Fraudulent User": {
        "intent":         "fraud_dispute",
        "expected_tools": ["query_order", "get_policy"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Return cancellation": {
        "intent":         "cancel_return",
        "expected_tools": ["query_order"],
        "order_status":   "Delivered",
        "refund_status":  "Pending",
    },
    # Order Related
    "Delayed": {
        "intent":         "track_order",
        "expected_tools": ["query_order", "track_shipping"],
        "order_status":   "Shipped",
        "refund_status":  "N/A",
    },
    "Order status enquiry": {
        "intent":         "track_order",
        "expected_tools": ["query_order", "track_shipping"],
        "order_status":   "Processing",
        "refund_status":  "N/A",
    },
    "Installation/demo": {
        "intent":         "installation_request",
        "expected_tools": ["query_order"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Customer Requested Modifications": {
        "intent":         "change_order",
        "expected_tools": ["query_order"],
        "order_status":   "Processing",
        "refund_status":  "N/A",
    },
    # Refund Related
    "Refund Enquiry": {
        "intent":         "get_refund",
        "expected_tools": ["query_order", "apply_refund"],
        "order_status":   "Delivered",
        "refund_status":  "Pending",
    },
    "Refund Related Issues": {
        "intent":         "get_refund",
        "expected_tools": ["query_order", "apply_refund"],
        "order_status":   "Delivered",
        "refund_status":  "Processing",
    },
    "COD Refund Details": {
        "intent":         "get_refund",
        "expected_tools": ["query_order", "apply_refund"],
        "order_status":   "Delivered",
        "refund_status":  "Pending",
    },
    # Payments
    "Payment related Queries": {
        "intent":         "check_payment_methods",
        "expected_tools": ["get_policy"],
        "order_status":   "Processing",
        "refund_status":  "N/A",
    },
    "Online Payment Issues": {
        "intent":         "payment_issue",
        "expected_tools": ["get_policy"],
        "order_status":   "Processing",
        "refund_status":  "N/A",
    },
    # Cancellation
    "Not Needed": {
        "intent":         "cancel_order",
        "expected_tools": ["query_order", "cancel_order"],
        "order_status":   "Processing",
        "refund_status":  "N/A",
    },
    # Product Queries
    "Warranty related": {
        "intent":         "check_warranty",
        "expected_tools": ["get_policy"],
        "order_status":   "Delivered",
        "refund_status":  "N/A",
    },
    "Product Specific Information": {
        "intent":         "product_inquiry",
        "expected_tools": ["get_policy"],
        "order_status":   "N/A",   # not yet ordered
        "refund_status":  "N/A",
    },
}

FALLBACK = {
    "intent":         "general_inquiry",
    "expected_tools": ["query_order"],
    "order_status":   "Processing",
    "refund_status":  "N/A",
}

# ---------------------------------------------------------------------------
# Category → canonical label
# ---------------------------------------------------------------------------
CAT_LABEL: dict[str, str] = {
    "Returns":          "RETURNS",
    "Order Related":    "ORDER",
    "Refund Related":   "REFUND",
    "Payments related": "PAYMENT",
    "Cancellation":     "ORDER",
    "Product Queries":  "PRODUCT",
}

DIFF_NUM: dict[str, int] = {"easy": 1, "medium": 2, "hard": 3}

# ---------------------------------------------------------------------------
# Hard cases: order may already be shipped (harder to cancel/return)
# ---------------------------------------------------------------------------
def resolve_order_status(base_status: str, difficulty: str, intent: str) -> str:
    if difficulty == "hard" and intent == "cancel_order":
        return "Shipped"
    return base_status

def resolve_refund_amount(refund_status: str, amount: float, difficulty: str) -> float:
    if refund_status in ("Pending", "Processing"):
        return round(amount * (0.9 if difficulty == "hard" else 1.0), 2)
    return 0.0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    with open(OOS_CASES_PATH, encoding="utf-8") as f:
        oos_cases = json.load(f)

    fact_sheets: dict = {}

    for case in oos_cases:
        idx  = int(case["case_id"].split("_")[1])  # 1-based
        sub  = case["sub_category"]
        cat  = case["category"]
        prod = case.get("product")   # may be None
        diff = case["difficulty"]
        instruction = case["instruction"]

        # Lookup sub-category mapping
        mapping = SUBCAT_MAP.get(sub, FALLBACK)
        intent        = mapping["intent"]
        expected_tools = mapping["expected_tools"]
        base_status   = mapping["order_status"]
        base_refund   = mapping["refund_status"]

        order_status  = resolve_order_status(base_status, diff, intent)
        amount        = rand_amount(prod, idx)
        refund_amount = resolve_refund_amount(base_refund, amount, diff)

        # No order number for "not yet ordered" product-query cases
        order_number = rand_order_num(idx) if order_status != "N/A" else "N/A"
        shipping_date = "2024-05-01" if order_status not in ("N/A", "Processing") else None

        fact_sheet = {
            "metadata": {
                "original_index": idx - 1,
                "category":       CAT_LABEL.get(cat, cat.upper()),
                "intent":         intent,
                "difficulty":     DIFF_NUM[diff],
                "difficulty_label": diff,
                "v_i":            1,
                "expected_tools": expected_tools,
            },
            "ground_truth": {
                "customer_info": {
                    "name":  rand_name(idx),
                    "email": rand_email(idx),
                    "phone": rand_phone(idx),
                },
                "order_info": {
                    "order_number":  order_number,
                    "status":        order_status,
                    "amount":        amount,
                    "currency":      "USD",
                    "items":         [rand_item(prod, idx)],
                    "shipping_date": shipping_date,
                },
                "refund_info": {
                    "refund_status": base_refund,
                    "refund_amount": refund_amount,
                },
            },
            "agent_input": instruction,
        }

        fact_sheets[case["case_id"]] = fact_sheet

    OUT_PATH.write_text(
        json.dumps(fact_sheets, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved {len(fact_sheets)} fact_sheets → {OUT_PATH}")

    # Quick sanity check
    print("\n=== Sample (OOS_001, OOS_016, OOS_036) ===")
    for k in ["OOS_001", "OOS_016", "OOS_036"]:
        print(f"\n{k}:")
        print(json.dumps(fact_sheets[k], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
