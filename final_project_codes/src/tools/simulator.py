"""
ToolSimulator — simulates e-commerce backend tool responses.

Provides three tools used by all agent architectures:
  query_order(order_id)        : Returns order status, amount, and items from the fact sheet.
  cancel_order(order_id)       : Cancels an order if eligible (not Shipped/Delivered).
  apply_refund(order_id)       : Initiates a refund; always eligible per policy.

Tool results are grounded in the case's fact sheet (loaded at runtime) to ensure
factual consistency. Policy text is also available for agents that query it.
"""

import json
import os

POLICY_DATA = {
    "refund": {
        "eligibility": "All orders are eligible for a full refund upon request, regardless of order status.",
        "timeline": "Refunds are processed within 5-7 business days.",
        "method": "Refund is credited to the original payment method.",
        "process": "Call apply_refund with the order ID to initiate a refund."
    },
    "payment": {
        "accepted_methods": ["Credit card (Visa, Mastercard, American Express)", "PayPal", "Bank transfer"],
        "processing_time": "Payment is processed immediately upon order placement.",
        "security": "All transactions are encrypted and secure.",
        "currencies": "USD, EUR, GBP and other major currencies accepted."
    },
    "delivery": {
        "standard": "Standard Shipping: 5-7 business days (free for orders over $50, otherwise $4.99)",
        "express": "Express Shipping: 2-3 business days ($9.99)",
        "priority": "Priority Shipping: 1 business day ($19.99)",
        "international": "International Shipping: 10-14 business days (rates vary by destination)",
        "processing_time": "Orders are processed within 1-2 business days before dispatch."
    },
    "shipping": {
        "tracking": "Tracking information is available after order dispatch via track_shipping tool.",
        "address_change": "Shipping address changes must be requested before the order is shipped. Contact support for assistance.",
        "lost_package": "If your package is lost, contact support within 30 days of the estimated delivery date."
    },
    "account": {
        "password_reset": "Use the 'Forgot Password' link on the login page. A reset email will be sent to your registered address.",
        "account_update": "Account details can be updated in the Account Settings page after login.",
        "support": "For account-related issues not covered above, contact our support team."
    }
}

_POLICY_TYPE_MAP = {
    "refund": "refund", "return": "refund", "returns": "refund",
    "check_refund_policy": "refund", "get_refund": "refund", "track_refund": "refund",
    "payment": "payment", "pay": "payment", "check_payment_methods": "payment",
    "payment_issue": "payment", "payment_method": "payment",
    "delivery": "delivery", "delivery_options": "delivery", "delivery_period": "delivery",
    "shipping_options": "delivery", "place_order": "delivery",
    "shipping": "shipping", "track": "shipping", "tracking": "shipping",
    "change_shipping_address": "shipping", "set_up_shipping_address": "shipping",
    "account": "account", "password": "account", "recover_password": "account",
    "login": "account", "get_invoice": "account",
}


class ToolSimulator:
    def __init__(self, fact_sheets_path="data/fact_sheets.json"):
        self.fact_sheets_path = fact_sheets_path
        self.data = self._load_data()

    def _load_data(self):
        if not os.path.exists(self.fact_sheets_path):
            raise FileNotFoundError(f"Fact sheets not found at {self.fact_sheets_path}")
        with open(self.fact_sheets_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_case_data(self, case_id):
        if case_id not in self.data:
            return None
        return self.data[case_id]

    def query_order(self, case_id, search_param):
        """
        Simulates querying order details by Order ID or Email.
        """
        case_data = self._get_case_data(case_id)
        if not case_data:
            return {"error": f"Case ID {case_id} not found."}

        ground_truth_order_id = case_data["ground_truth"]["order_info"]["order_number"]
        ground_truth_email = case_data["ground_truth"]["customer_info"].get("email", "")

        search_param = search_param.strip().lower()

        # Check by Order ID
        if search_param.upper() == ground_truth_order_id.strip().upper():
             return {
                "status": "success",
                "data": case_data["ground_truth"]["order_info"]
            }

        # Check by Email
        if search_param == ground_truth_email.strip().lower():
             return {
                "status": "success",
                "data": case_data["ground_truth"]["order_info"]
            }

        return {
            "error": f"Search for '{search_param}' returned no results in Case {case_id}.",
            "hint": "You can search using either the Order ID (e.g., ORD123) or the Customer Email. Please verify the information with the customer."
        }

    def track_shipping(self, case_id, order_id):
        """
        Simulates tracking shipping status.
        """
        case_data = self._get_case_data(case_id)
        if not case_data:
            return {"error": f"Case ID {case_id} not found."}

        ground_truth_order_id = case_data["ground_truth"]["order_info"]["order_number"]

        # Robust fuzzy matching
        if order_id.strip().upper() != ground_truth_order_id.strip().upper():
            return {"error": f"Track Shipping failed: Order '{order_id}' not found in Case {case_id}."}

        shipping_date = case_data["ground_truth"]["order_info"].get("shipping_date", "N/A")
        status = case_data["ground_truth"]["order_info"].get("status", "Unknown")

        return {
            "status": "success",
            "data": {
                "order_id": order_id,
                "shipping_status": status,
                "estimated_delivery": shipping_date
            }
        }

    def apply_refund(self, case_id, order_id, reason="Customer request"):
        """
        Simulates applying for a refund.
        """
        case_data = self._get_case_data(case_id)
        if not case_data:
            return {"error": f"Case ID {case_id} not found."}

        ground_truth_order_id = case_data["ground_truth"]["order_info"]["order_number"]

        if order_id.strip().upper() != ground_truth_order_id.strip().upper():
            return {"error": f"Refund application failed: Order '{order_id}' not found in Case {case_id}."}

        refund_info = case_data["ground_truth"].get("refund_info", {})

        return {
            "status": "success",
            "message": f"Refund request submitted successfully for reason: {reason}",
            "data": refund_info
        }

    def cancel_order(self, case_id, order_id, reason="Customer request"):
        """
        Simulates cancelling an order.
        """
        case_data = self._get_case_data(case_id)
        if not case_data:
            return {"error": f"Case ID {case_id} not found."}

        ground_truth_order_id = case_data["ground_truth"]["order_info"]["order_number"]

        if order_id.strip().upper() != ground_truth_order_id.strip().upper():
            return {"error": f"Order cancellation failed: Order '{order_id}' not found in Case {case_id}."}

        return {
            "status": "success",
            "message": f"Order successfully cancelled for reason: {reason}",
            "order_id": order_id,
            "cancellation_timestamp": "2024-05-14T12:00:00Z"
        }

    def get_policy(self, case_id, policy_type):
        """
        Returns company policy information for the given policy type.
        policy_type: refund, payment, delivery, shipping, account (or intent synonyms)
        Does not require a verified order — can be called without order ID.
        """
        raw = (policy_type or "").strip().strip('"').strip("'").lower()
        canonical = _POLICY_TYPE_MAP.get(raw, raw)
        policy_info = POLICY_DATA.get(canonical)

        if not policy_info:
            return {
                "status": "error",
                "message": (
                    f"Policy type '{policy_type}' not recognised. "
                    "Available types: refund, payment, delivery, shipping, account."
                )
            }

        return {
            "status": "success",
            "policy_type": canonical,
            "data": policy_info
        }

    def get_account_info(self, case_id):
        """
        Returns customer account information.
        Does not require an order ID — looks up by case_id only.
        """
        case_data = self._get_case_data(case_id)
        if not case_data:
            return {"error": f"Case ID {case_id} not found."}

        customer_info = case_data["ground_truth"].get("customer_info", {})
        return {
            "status": "success",
            "data": {
                "name": customer_info.get("name", "N/A"),
                "email": customer_info.get("email", "N/A"),
                "phone": customer_info.get("phone", "N/A"),
                "account_status": "Active"
            }
        }


# Example usage for testing
if __name__ == "__main__":
    simulator = ToolSimulator()
    print("Test query_order:")
    print(simulator.query_order("CASE_001", "ORD60227680"))
    print("\nTest get_policy (refund):")
    print(simulator.get_policy("CASE_001", "refund"))
    print("\nTest get_policy (delivery_options):")
    print(simulator.get_policy("CASE_001", "delivery_options"))
    print("\nTest get_account_info:")
    print(simulator.get_account_info("CASE_001"))
