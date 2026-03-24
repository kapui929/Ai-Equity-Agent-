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
