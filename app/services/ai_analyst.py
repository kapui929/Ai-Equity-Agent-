import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

class AIAnalyst:
    def __init__(self):
        # 1. 密鑰管理：從環境變數讀取
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("在 .env 檔案中找不到 NVIDIA_API_KEY，請確認是否設定正確。")
        
        # 2. 初始化客戶端
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        # 根據之前官網截圖，這裡使用 v3.2
        self.model_name = "deepseek-ai/deepseek-v3.2"

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
        # Task: Execute the Decision Pipeline (Harness Engineering)
        
        # Input Data:
        - Ticker: {symbol}
        - Fundamentals: 
          - ROE: {roe}%
          - P/E Ratio: {pe}
          - Debt to Equity: {de}
        - Recent News Summary: {news_summary}

        請嚴格按照以下五個階段進行分析。因為這是一個 API 服務，請你**務必僅輸出 JSON 格式**，確保我的前端系統可以正確解析。不要輸出任何 Markdown 標記，直接給 JSON。

        請輸出以下 JSON 結構：
        {{
            "phase_1_sanity_check": "...",
            "phase_2_profitability": "...",
            "phase_3_sentiment": "...",
            "phase_4_risk_assessment": "...",
            "phase_5_final_verdict": {{
                "score": 0到100,
                "recommendation": "BUY / HOLD / SELL",
                "reasoning": "..."
            }}
        }}
        """
        
        try:
            # 🚀 這裡修正了縮排並優化參數
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, 
                max_tokens=2048, # 限制長度提速
                extra_body={
                    "chat_template_kwargs": {"thinking": False} # 👈 強制跳過思考過程
                }
            )
            
            raw_content = response.choices[0].message.content
            
            # 清理 Markdown JSON 標籤
            if raw_content.startswith("```json"):
                raw_content = raw_content.replace("```json", "", 1).replace("```", "").strip()
            elif raw_content.startswith("```"):
                raw_content = raw_content.replace("```", "").strip()
                
            return raw_content
            
        except Exception as e:
            return f'{{"error": "NVIDIA API 推理過程中發生錯誤: {str(e)}"}}'