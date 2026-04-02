import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

class AIAnalyst:
    def __init__(self):
        # 1. 密鑰管理：從環境變數讀取 (絕對不要寫死在程式碼裡)
        # ⚠️ 請記得在 .env 和 Render 的環境變數中設定 NVIDIA_API_KEY
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("在 .env 檔案中找不到 NVIDIA_API_KEY，請確認是否設定正確。")
        
        # 2. 初始化 OpenAI 相容的非同步客戶端，並指向 NVIDIA 的伺服器
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model_name = "z-ai/glm4.7"

    async def generate_report(self, ticker_data, news_summary):
        """
        實施 Harness Engineering (決策流水線)
        """
        symbol = ticker_data.get('symbol', 'Unknown')
        roe = ticker_data.get('roe', 'N/A')
        pe = ticker_data.get('pe', 'N/A')
        de = ticker_data.get('debt_to_equity', 'N/A')
        
        prompt = f"""
        # Role: Senior Equity Research Analyst (CFA Track)
        
        # Input Data:
        - Ticker: {symbol}
        - Fundamentals: 
          - ROE: {roe}%
          - P/E Ratio: {pe}
          - Debt to Equity: {de}
        - Recent News Summary: {news_summary}

        # Task: Execute the Decision Pipeline (Harness Engineering)
        請嚴格按照以下五個階段進行分析。因為這是一個 API 服務，請你**務必僅輸出 JSON 格式**，確保我的前端系統可以正確解析。不要輸出任何 Markdown 標記，直接給 JSON。

        請輸出以下 JSON 結構：
        {{
            "phase_1_sanity_check": "評估財務數據是否合理（例如 ROE 是否異常高、P/E 是否為負），給出 1-2 句話的結論。",
            "phase_2_profitability": "基於上述數據判斷該公司的盈利質量與競爭護城河。",
            "phase_3_sentiment": "結合新聞，提取 1 個看多催化劑與 1 個看空風險。",
            "phase_4_risk_assessment": "指出如果投資這家公司，最致命的一個下行風險（Downside Risk）是什麼？",
            "phase_5_final_verdict": {{
                "score": 0到100的整數評分,
                "recommendation": "BUY / HOLD / SELL",
                "reasoning": "一句話總結你的投資建議核心邏輯。"
            }}
        }}
        """
        
        try:
            # 呼叫 NVIDIA API 進行推理 (取消 Stream，一次性獲取完整 JSON)
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, # 降低溫度以確保 JSON 格式穩定
                max_tokens=4096
            )
            
            raw_content = response.choices[0].message.content
            
            # 清理有時候大模型會自作聰明加上的 Markdown JSON 標籤
            if raw_content.startswith("```json"):
                raw_content = raw_content.replace("```json", "", 1).replace("```", "").strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content.replace("```", "").strip()
                
            return raw_content
            
        except Exception as e:
            return f'{{"error": "NVIDIA API 推理過程中發生錯誤: {str(e)}"}}'