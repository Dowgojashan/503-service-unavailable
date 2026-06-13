import os

def create_structure():
    directories = [
        "prompts/system_instructions",
        "src/agents",
        "src/tools",
        "src/core",
        "eval",
        "outputs/logs",
        "outputs/reports",
    ]

    for d in directories:
        os.makedirs(d, exist_ok=True)
        print(f"Created directory: {d}")
        
        # Add __init__.py to python packages
        if d.startswith("src/") or d == "eval":
            init_file = os.path.join(d, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    pass
                print(f"Created file: {init_file}")

    # Create placeholder files
    files = [
        "main.py",
        "prompts/prosa_templates.yaml",
        "prompts/system_instructions/common.txt",
        "prompts/system_instructions/react_scaffold.txt",
        "prompts/system_instructions/reflection_scaffold.txt",
        "src/agents/base.py",
        "src/agents/single_slot.py",
        "src/agents/react_agent.py",
        "src/agents/reflection_agent.py",
        "src/agents/plan_execute_agent.py",
        "src/core/factory.py",
        "src/core/runner.py",
        "eval/llm_judge.py",
        "eval/metrics.py",
        "eval/prosa_analyzer.py",
    ]

    for file_path in files:
        if not os.path.exists(file_path):
            # Ensure parent directory exists (already handled by directories loop but just in case)
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(file_path, "w") as f:
                pass
            print(f"Created file: {file_path}")

if __name__ == "__main__":
    create_structure()
