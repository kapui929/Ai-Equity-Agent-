"""
stock_fetcher.py - 股票数据获取器
从 Yahoo Finance 抓取股票数据
"""

import yfinance as yf


class StockFetcher:
    """股票数据获取器"""

    # 不同市场的后缀
    MARKET_SUFFIX = {
        "US": "",          # 美股：AAPL
        "TW": ".TW",      # 台股：2330.TW
        "HK": ".HK",      # 港股：0700.HK
        "CRYPTO": "-USD",  # 加密货币：BTC-USD
    }

    def _build_ticker(self, symbol: str, market: str) -> str:
        """组合完整的股票代码"""
        suffix = self.MARKET_SUFFIX.get(market.upper(), "")
        return f"{symbol}{suffix}"

    def fetch(self, symbol: str, market: str = "US") -> dict:
        """
        获取股票数据

        参数：
            symbol: 股票代码，例如 "AAPL", "2330"
            market: 市场，"US" / "TW" / "HK" / "CRYPTO"

        返回：
            包含股票信息的字典
        """
        try:
            ticker_str = self._build_ticker(symbol, market)
            stock = yf.Ticker(ticker_str)
            info = stock.info

            # 如果没有拿到数据，返回错误
            if not info or len(info) < 5:
                return {"error": f"找不到 {ticker_str} 的数据"}

            # 整理我们需要的数据，返回干净的字典
            return {
                "symbol": ticker_str,
                "name": info.get("shortName", "N/A"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "currency": info.get("currency", "N/A"),

                # 估值指标
                "pe_ratio": info.get("trailingPE"),           # 市盈率
                "forward_pe": info.get("forwardPE"),          # 预估市盈率
                "pb_ratio": info.get("priceToBook"),          # 市净率
                "ps_ratio": info.get("priceToSalesTrailing12Months"),  # 市销率

                # 质量指标
                "roe": info.get("returnOnEquity"),            # 股东权益报酬率
                "profit_margin": info.get("profitMargins"),   # 利润率
                "debt_to_equity": info.get("debtToEquity"),   # 负债权益比
                "free_cashflow": info.get("freeCashflow"),    # 自由现金流
                "revenue_growth": info.get("revenueGrowth"),  # 营收成长率

                # 其他
                "market_cap": info.get("marketCap"),          # 市值
                "dividend_yield": info.get("dividendYield"),  # 股息率
                "sector": info.get("sector", "N/A"),          # 产业
                "industry": info.get("industry", "N/A"),      # 行业
            }

        except Exception as e:
            return {"error": f"获取数据失败: {str(e)}"}
