"""
Generate 50 out-of-sample test cases from Customer_support_data.csv.

Steps:
  1. Stratified sampling by category (domain) × CSAT difficulty bucket
  2. For each row, call Gemini to generate a realistic customer query instruction
  3. Save to data/oos_test_cases_50.json and data/oos_test_cases_50.csv

Difficulty mapping (CSAT Score):
  hard   = 1–2  (unresolved / complex)
  medium = 3–4
  easy   = 5    (resolved easily)
"""

from __future__ import annotations

import json
import os
import time
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_PATH  = "data/Customer_support_data.csv"
OUT_JSON   = "data/oos_test_cases_50.json"
OUT_CSV    = "data/oos_test_cases_50.csv"
GEN_MODEL  = "gemini-3.1-flash-lite"

DOMAIN_QUOTA = {
    "Returns":          15,
    "Order Related":    12,
    "Refund Related":    8,
    "Payments related":  6,
    "Cancellation":      5,
    "Product Queries":   4,
}

_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=_api_key)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a customer writing to an e-commerce customer support chatbot.
Generate ONE realistic, natural-sounding customer message that a real person would send.

Rules:
- Write in first-person as the customer
- Length: 1–3 sentences, conversational tone
- Match the difficulty level:
    easy   → polite, straightforward, single clear request
    medium → some frustration or follow-up context, moderately complex
    hard   → upset or urgent, issue has been dragging on, emotionally charged
- Include relevant context hints from the category/sub-category/product
- Do NOT mention agent names, ticket numbers, or internal system IDs
- Output ONLY the customer message, no labels or explanations
"""

def build_user_prompt(category: str, sub_category: str, product: str, difficulty: str) -> str:
    prod_line = f"Product type: {product}" if product and product != "nan" else ""
    return f"""Category: {category}
Sub-category: {sub_category}
{prod_line}
Difficulty: {difficulty}

Generate the customer message:"""


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------
def stratified_sample(df: pd.DataFrame) -> pd.DataFrame:
    def diff_bucket(score: int) -> str:
        if score <= 2: return "hard"
        elif score <= 4: return "medium"
        else: return "easy"

    df = df.copy()
    df["difficulty"] = df["CSAT Score"].apply(diff_bucket)
    selected = []

    for domain, quota in DOMAIN_QUOTA.items():
        pool = df[df["category"] == domain]
        n_hard   = quota // 3 + (1 if quota % 3 >= 1 else 0)
        n_medium = quota // 3 + (1 if quota % 3 >= 2 else 0)
        n_easy   = quota // 3

        for diff, n in [("hard", n_hard), ("medium", n_medium), ("easy", n_easy)]:
            sub = pool[pool["difficulty"] == diff]
            with_prod    = sub[sub["Product_category"].notna()]
            without_prod = sub[sub["Product_category"].isna()]
            take_with    = min(len(with_prod), n // 2)
            take_without = n - take_with
            if take_with > 0:
                selected.append(with_prod.sample(min(take_with, len(with_prod)), random_state=42))
            if take_without > 0 and len(without_prod) > 0:
                selected.append(without_prod.sample(min(take_without, len(without_prod)), random_state=42))

    result = pd.concat(selected).drop_duplicates(subset="Unique id").head(50).reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# Instruction generation
# ---------------------------------------------------------------------------
def generate_instruction(category: str, sub_category: str, product: str, difficulty: str) -> str:
    prompt = build_user_prompt(category, sub_category, str(product), difficulty)
    for attempt in range(5):
        try:
            resp = client.models.generate_content(
                model=GEN_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.9,
                    max_output_tokens=150,
                ),
            )
            return resp.text.strip()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                wait = 65
                print(f"    [rate limit] sleeping {wait}s (attempt {attempt+1}/5)...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Max retries exceeded")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"  {len(df):,} rows loaded")

    print("Running stratified sampling...")
    sample = stratified_sample(df)
    print(f"  {len(sample)} cases selected")
    print("  Domain:", dict(sample["category"].value_counts()))
    print("  Difficulty:", dict(sample["difficulty"].value_counts()))

    CHECKPOINT = OUT_JSON + ".checkpoint"
    print("\nGenerating instructions via Gemini...")
    # Resume from checkpoint if exists
    records = []
    done_ids: set[str] = set()
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, encoding="utf-8") as f:
            records = json.load(f)
        done_ids = {r["case_id"] for r in records}
        print(f"  Resuming from checkpoint: {len(records)} already done")

    for i, row in sample.iterrows():
        case_id = f"OOS_{i+1:03d}"
        if case_id in done_ids:
            continue
        category    = row["category"]
        sub_cat     = row["Sub-category"]
        product     = row["Product_category"]
        difficulty  = row["difficulty"]
        csat        = int(row["CSAT Score"])

        instruction = generate_instruction(category, sub_cat, str(product), difficulty)

        record = {
            "case_id":      case_id,
            "category":     category,
            "sub_category": sub_cat,
            "product":      str(product) if pd.notna(product) else None,
            "difficulty":   difficulty,
            "csat_score":   csat,
            "instruction":  instruction,
        }
        records.append(record)
        print(f"  [{case_id}] {category} / {sub_cat} ({difficulty}) → {instruction[:80]}...")
        # Save checkpoint after each record
        with open(CHECKPOINT, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        time.sleep(4.5)   # stay within 15 RPM

    # Save JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON → {OUT_JSON}")

    # Save CSV
    pd.DataFrame(records).to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"Saved CSV  → {OUT_CSV}")

    # Clean up checkpoint
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)

    print(f"\nDone. Total cases: {len(records)}")


if __name__ == "__main__":
    main()
