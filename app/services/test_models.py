import os
import google.generativeai as genai
from dotenv import load_dotenv

# 載入 API 金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("找不到 API 金鑰！")
else:
    genai.configure(api_key=api_key)
    print("可用模型清單：")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"取得模型清單失敗：{e}")