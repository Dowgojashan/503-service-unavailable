"""
診斷工具：檢查 Google Gemini API 和模型可用性
"""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

def diagnose():
    print("=" * 60)
    print("Google Gemini API 診斷工具")
    print("=" * 60)
    
    # 1. 檢查 API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：GEMINI_API_KEY 未設定")
        return
    else:
        print(f"✓ API Key 已設定: {api_key[:20]}...{api_key[-5:]}")
    
    # 2. 初始化客戶端
    try:
        client = genai.Client(api_key=api_key)
        print("✓ Google Genai Client 初始化成功")
    except Exception as e:
        print(f"❌ Client 初始化失敗: {e}")
        return
    
    # 3. 列出可用的模型
    print("\n📋 可用的模型列表:")
    print("-" * 60)
    try:
        # 注意：gemini-2.0-flash-exp 是新的模型
        # gemma-7b, gemma2-27b 等是老模型，可能不再支持
        models_to_test = [
            "gemini-3.1-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemma-3-27b-it",
            "gemini-2.5-flash",
            "gemma2-27b-it",
        ]
        
        for model in models_to_test:
            try:
                # 嘗試一個簡單的 API 呼叫
                print(f"\n測試模型: {model}")
                response = client.models.generate_content(
                    model=model,
                    contents="Say 'test' only.",
                    config={"max_output_tokens": 10, "temperature": 0.0}
                )
                print(f"  ✓ 可用 (Response length: {len(response.text)} chars)")
                print(f"    Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} completion")
            except errors.NotFoundError:
                print(f"  ❌ 不存在或無權限")
            except errors.ServerError as e:
                if "500" in str(e):
                    print(f"  ❌ 500 Server Error - API 伺服器問題")
                elif "503" in str(e):
                    print(f"  ❌ 503 Service Unavailable - API 伺服器過載")
                else:
                    print(f"  ❌ Server Error: {str(e)[:100]}")
            except errors.ClientError as e:
                if "429" in str(e):
                    print(f"  ❌ 429 Rate Limit - 請求頻率過高")
                else:
                    print(f"  ❌ Client Error: {str(e)[:100]}")
            except Exception as e:
                print(f"  ❌ 未知錯誤: {type(e).__name__} - {str(e)[:100]}")
    
    except Exception as e:
        print(f"❌ 列表模型失敗: {e}")
    
    print("\n" + "=" * 60)
    print("診斷結論:")
    print("=" * 60)
    print("""
如果看到 500 錯誤：
  1. ✓ 這通常是 Google API 伺服器的暫時問題
  2. ✓ 重試通常會成功
  3. ✗ 不是你的系統環境問題
  
如果看到 503 錯誤：
  1. ✓ API 過載，稍後重試
  
如果看到 NotFoundError：
  1. ✗ 模型名稱錯誤或無權限
  2. ✗ 檢查 API Key 所關聯的專案設定

推薦使用的模型：
  - gemini-3.1-flash-lite (最新、速度快、適合此專案)
  - gemini-2.0-flash (最新、免費配額充足)
  - gemini-1.5-flash (穩定、廉價)
  - gemini-1.5-pro (精準度高但更貴)
    """)

if __name__ == "__main__":
    diagnose()
