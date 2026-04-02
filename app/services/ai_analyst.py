import os
import google.generativeai as genai
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

class AIAnalyst:
    def __init__(self):
        # 1. 密鑰管理：從環境變數讀取，確保安全
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("在 .env 檔案中找不到 GEMINI_API_KEY，請確認是否設定正確。")
        
        genai.configure(api_key=api_key)
        
        # 2. 模型設定：使用 Gemini 1.5 Pro，並強制輸出 JSON 格式 (這對 Fintech 應用極度重要)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            generation_config={"response_mime_type": "application/json"}
        )

    async def generate_report(self, ticker_data, news_summary):
        """
        實施 Harness Engineering (決策流水線)：將分析拆解為五個專業階段
        """
        
        # 確保傳入的數據有預設值，避免 KeyError
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
        請嚴格按照以下五個階段進行分析。因為這是一個 API 服務，請你**務必僅輸出 JSON 格式**，確保我的前端系統可以正確解析。

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
            # 呼叫 Gemini 進行推理
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            # 錯誤處理機制，防止系統崩潰
            return f'{{"error": "AI 推理過程中發生錯誤: {str(e)}"}}'