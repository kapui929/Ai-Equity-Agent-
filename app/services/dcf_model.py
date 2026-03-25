import yfinance as yf


class DCFModel:
    def __init__(self, discount_rate=0.10, growth_years=5, terminal_growth=0.03):
        self.discount_rate = discount_rate
        self.growth_years = growth_years
        self.terminal_growth = terminal_growth

    def calculate(self, symbol: str, market: str = "US") -> dict:
        try:
            suffix = {"US": "", "TW": ".TW", "HK": ".HK", "CRYPTO": "-USD"}
            ticker_str = f"{symbol}{suffix.get(market.upper(), '')}"
            stock = yf.Ticker(ticker_str)
            info = stock.info

            fcf = info.get("freeCashflow")
            shares = info.get("sharesOutstanding")
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            growth = info.get("revenueGrowth") or 0.05

            if not fcf or not shares or not price:
                return {"error": "Insufficient data for DCF"}

            if fcf <= 0:
                return {"error": "Negative FCF, DCF not applicable"}

            future_fcf = []
            current_fcf = fcf
            for year in range(1, self.growth_years + 1):
                current_fcf = current_fcf * (1 + growth)
                discounted = current_fcf / (1 + self.discount_rate) ** year
                future_fcf.append({
                    "year": year,
                    "fcf": round(current_fcf),
                    "discounted": round(discounted),
                })

            terminal_value = (
                current_fcf * (1 + self.terminal_growth)
                / (self.discount_rate - self.terminal_growth)
            )
            discounted_terminal = terminal_value / (1 + self.discount_rate) ** self.growth_years

            total_dcf = sum(f["discounted"] for f in future_fcf) + discounted_terminal
            target_price = total_dcf / shares
            upside = (target_price - price) / price * 100

            if upside > 20:
                verdict = "Strongly Undervalued"
            elif upside > 5:
                verdict = "Undervalued"
            elif upside > -5:
                verdict = "Fair Value"
            elif upside > -20:
                verdict = "Overvalued"
            else:
                verdict = "Strongly Overvalued"

            return {
                "current_price": round(price, 2),
                "target_price": round(target_price, 2),
                "upside": f"{upside:+.1f}%",
                "verdict": verdict,
                "assumptions": {
                    "free_cashflow": fcf,
                    "growth_rate": f"{growth*100:.1f}%",
                    "discount_rate": f"{self.discount_rate*100:.1f}%",
                    "terminal_growth": f"{self.terminal_growth*100:.1f}%",
                    "projection_years": self.growth_years,
                },
                "yearly_projection": future_fcf,
                "terminal_value": round(discounted_terminal),
                "enterprise_value": round(total_dcf),
            }

        except Exception as e:
            return {"error": f"DCF calculation failed: {str(e)}"}
