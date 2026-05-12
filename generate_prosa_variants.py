import json
import yaml
import os

def load_fact_sheets(path="data/fact_sheets.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_templates(path="prompts/prosa_templates.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_variants():
    fact_sheets = load_fact_sheets()
    templates = load_templates()
    
    prosa_data = {}
    
    for case_id, case_content in fact_sheets.items():
        original = case_content.get("agent_input", "")
        if not original:
            continue
            
        case_variants = {
            "simple_input": templates["simple_input"]["template"].format(original_instruction=original),
            "emotional_support": templates["emotional_support"]["templates"][0].format(original_instruction=original),
            "role_player": templates["role_player"]["templates"][0].format(original_instruction=original),
            "output_requirement": templates["output_requirement"]["templates"][0].format(original_instruction=original)
        }
        
        # Use case index to cycle through templates if there are multiple
        case_idx = int(case_id.split("_")[1])
        
        case_variants["emotional_support"] = templates["emotional_support"]["templates"][case_idx % len(templates["emotional_support"]["templates"])].format(original_instruction=original)
        case_variants["role_player"] = templates["role_player"]["templates"][case_idx % len(templates["role_player"]["templates"])].format(original_instruction=original)
        case_variants["output_requirement"] = templates["output_requirement"]["templates"][case_idx % len(templates["output_requirement"]["templates"])].format(original_instruction=original)
        
        prosa_data[case_id] = {
            "original_instruction": original,
            "variants": case_variants
        }
        
    output_path = "data/prosa_variants.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prosa_data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully generated ProSA variants for {len(prosa_data)} cases.")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    generate_variants()
