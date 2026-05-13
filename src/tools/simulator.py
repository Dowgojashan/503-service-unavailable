import json
import os

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

    def apply_refund(self, case_id, order_id):
        """
        Simulates applying for a refund.
        """
        case_data = self._get_case_data(case_id)
        if not case_data:
            return {"error": f"Case ID {case_id} not found."}

        ground_truth_order_id = case_data["ground_truth"]["order_info"]["order_number"]
        
        # Robust fuzzy matching
        if order_id.strip().upper() != ground_truth_order_id.strip().upper():
            return {"error": f"Refund application failed: Order '{order_id}' not found in Case {case_id}."}

        refund_info = case_data["ground_truth"].get("refund_info", {})
        
        return {
            "status": "success",
            "message": "Refund request submitted successfully.",
            "data": refund_info
        }

# Example usage for testing
if __name__ == "__main__":
    simulator = ToolSimulator()
    print("Test CASE_001 query_order:")
    print(simulator.query_order("CASE_001", "ORD60227680"))
    print("\nTest CASE_001 with WRONG order_id:")
    print(simulator.query_order("CASE_001", "WRONG123"))
