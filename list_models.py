import requests

def list_ollama_models():
    url = "http://localhost:11434/api/tags"
    print("Listing available Ollama models:")
    try:
        response = requests.get(url)
        response.raise_for_status()
        models = response.json().get('models', [])
        if not models:
            print("No models found in Ollama.")
            return
        for m in models:
            name = m.get('name')
            size = m.get('size', 0) / (1024**3) # GB
            modified = m.get('modified_at', '')
            print(f"- {name} (Size: {size:.2f} GB, Modified: {modified})")
    except Exception as e:
        print(f"Error listing models from Ollama: {e}")
        print("Make sure Ollama server is running at http://localhost:11434")

if __name__ == "__main__":
    list_ollama_models()
