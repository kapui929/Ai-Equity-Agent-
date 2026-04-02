from openai import OpenAI


class AIAnalyst:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )

    def generate_report(self, stock_data: dict) -> str:
        if "error" in stock_data:
            return "Unable to generate report"

        quality = stock_data.get("quality", {})
        valuation = stock_data.get("valuation", {})

        prompt = f"""Analyze this stock briefly:
Stock: {stock_data.get("symbol")} - {stock_data.get("name")}
Price: {stock_data.get("price")}
Quality Score: {quality.get("score", "N/A")} / 100
Valuation Score: {valuation.get("score", "N/A")} / 100
Overall: {stock_data.get("overall_score", "N/A")} / 100

Give: 1) Summary 2) Strengths 3) Risks 4) Buy/Hold/Sell recommendation"""

        try:
            response = self.client.chat.completions.create(
                model="meta/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI report failed: {str(e)}"
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIAnalyst:
    def __init__(self):
        # 這裡改用你提供的 Gemini API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY in .env file")
        
        genai.configure(api_key=api_key)
        # 使用 pro 模型以支持複雜的金融邏輯推理
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    async def generate_report(self, ticker_data, news_summary):
        """
        實施 Harness Engineering：將分析拆解為五個專業階段
        """
        # 這裡就是把原本 Nvidia 的簡單 Prompt 替換成具備決策鏈的專業 Prompt
        prompt = f"""
        # Role: Senior Equity Research Analyst (CFA Track)
        
        # Input Data:
        - Ticker: {ticker_data.get('symbol')}
        - Fundamentals: ROE: {ticker_data.get('roe')}%, P/E: {ticker_data.get('pe')}, D/E: {ticker_data.get('de')}
        - Recent News: {news_summary}

        # Task: Execute the following Decision Pipeline (Harness Engineering)
        
        PHASE 1: Data Sanity Check - 評估財務數據是否存在異常（如 ROE 過高）。
        PHASE 2: Profitability Analysis - 基於利潤率判斷競爭護城河。
        PHASE 3: Sentiment Integration - 將新聞情緒與基本面結合。
        PHASE 4: Risk Assessment - 識別最致命的一個下行風險。
        PHASE 5: Final Verdict - 給出 0-100 評分與投資建議。

        請以專業金融報告格式輸出，確保邏輯嚴密。
        """
        
        response = self.model.generate_content(prompt)
        return response.text
    