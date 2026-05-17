"""
診斷工具：檢查本地 Ollama (Llama 3) API 可用性
"""
import requests
import json
import time

def diagnose():
    print("=" * 60)
    print("本地 Ollama (Llama 3) API 診斷工具")
    print("=" * 60)
    
    url = "http://localhost:11434/v1/chat/completions"
    model = "llama3.1:8b"
    
    # 1. 檢查 Ollama 伺服器
    print(f"正在檢查 Ollama 伺服器: {url}")
    try:
        # 測試簡單的 chat completion
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a diagnostic tool."},
                {"role": "user", "content": "Say 'Ollama is ready' if you can read this."}
            ],
            "temperature": 0.0,
            "max_tokens": 20
        }
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=30)
        end_time = time.time()
        
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        latency = end_time - start_time
        
        print(f"✓ 連線成功！")
        print(f"✓ 模型回應: {content.strip()}")
        print(f"✓ 回應延遲: {latency:.2f} 秒")
        
        # 2. 檢查 Token 使用情況 (如果 Ollama 有提供)
        usage = result.get('usage', {})
        if usage:
            print(f"✓ Token 使用情況: {usage.get('total_tokens')} total")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 錯誤：無法連線到 Ollama 伺服器。")
        print(f"   請確保 Ollama 已啟動，且運行在 http://localhost:11434")
    except requests.exceptions.Timeout:
        print(f"❌ 錯誤：請求超時 (30秒)。模型可能正在加載或硬體負載過高。")
    except requests.exceptions.HTTPError as e:
        print(f"❌ 錯誤：HTTP {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ 錯誤：發生未知錯誤 - {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("診斷結論:")
    print("=" * 60)
    print(f"""
本地 LLM 狀態：
  - 如果連線成功：恭喜！專案現在可以使用本地 {model} 運行，徹底告別 503/500 錯誤。
  - 如果連線失敗：請檢查 Ollama 是否已安裝並運行。
  - 如果超時：
    1. 第一次啟動模型可能需要時間加載到顯存/記憶體。
    2. 檢查本地電腦資源（CPU/GPU）是否充足。

專案配置建議：
  - 專案已重構為呼叫 http://localhost:11434/v1/chat/completions
  - 無需 GEMINI_API_KEY，且不再受限於 Google API 的配額或穩定性。
    """)

if __name__ == "__main__":
    diagnose()
