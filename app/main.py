from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def index():
    return FileResponse("app/static/index.html")

def score_quality(info):
    breakdown = {}
    total = 0
    
    roe = info.get("returnOnEquity")
    if roe is not None:
        roe_pct = round(roe * 100, 2) if abs(roe) < 10 else round(roe, 2)
        s = min(30, max(0, int(roe_pct * 1.5))) if roe_pct > 0 else 0
        breakdown["roe"] = {"value": roe_pct, "score": s}
        total += s
    else:
        breakdown["roe"] = {"value": "N/A", "score": 0}

    margin = info.get("profitMargins")
    if margin is not None:
        margin_pct = round(margin * 100, 2) if abs(margin) < 10 else round(margin, 2)
        s = min(25, max(0, int(margin_pct * 1.0))) if margin_pct > 0 else 0
        breakdown["profit_margin"] = {"value": margin_pct, "score": s}
        total += s
    else:
        breakdown["profit_margin"] = {"value": "N/A", "score": 0}

    de = info.get("debtToEquity")
    if de is not None:
        de_val = round(de, 2)
        if de_val < 50: s = 25
        elif de_val < 100: s = 20
        elif de_val < 200: s = 10
        else: s = 0
        breakdown["debt_to_equity"] = {"value": de_val, "score": s}
        total += s
    else:
        breakdown["debt_to_equity"] = {"value": "N/A", "score": 15}
        total += 15

    rg = info.get("revenueGrowth")
    if rg is not None:
        rg_pct = round(rg * 100, 2) if abs(rg) < 10 else round(rg, 2)
        s = min(20, max(0, int(rg_pct * 1.0))) if rg_pct > 0 else 0
        breakdown["revenue_growth"] = {"value": rg_pct, "score": s}
        total += s
    else:
        breakdown["revenue_growth"] = {"value": "N/A", "score": 0}

    return {"score": min(total, 100), "breakdown": breakdown}

def score_valuation(info):
    breakdown = {}
    total = 0

    pe = info.get("trailingPE") or info.get("forwardPE")
    if pe is not None:
        pe = round(pe, 2)
        if pe < 0: s = 0
        elif pe < 10: s = 40
        elif pe < 15: s = 35
        elif pe < 20: s = 25
        elif pe < 30: s = 15
        elif pe < 50: s = 5
        else: s = 0
        breakdown["pe_ratio"] = {"value": pe, "score": s}
        total += s
    else:
        breakdown["pe_ratio"] = {"value": "N/A", "score": 0}

    pb = info.get("priceToBook")
    if pb is not None:
        pb = round(pb, 2)
        if pb < 1: s = 30
        elif pb < 2: s = 25
        elif pb < 3: s = 20
        elif pb < 5: s = 10
        else: s = 0
        breakdown["pb_ratio"] = {"value": pb, "score": s}
        total += s
    else:
        breakdown["pb_ratio"] = {"value": "N/A", "score": 0}

    dy = info.get("dividendYield")
    if dy is not None:
        dy_pct = round(dy * 100, 2) if dy < 1 else round(dy, 2)
        s = min(30, max(0, int(dy_pct * 8)))
        breakdown["dividend_yield"] = {"value": dy_pct, "score": s}
        total += s
    else:
        breakdown["dividend_yield"] = {"value": "N/A", "score": 0}

    return {"score": min(total, 100), "breakdown": breakdown}

@app.get("/analyze")
def analyze(symbol: str = Query(...), market: str = Query("US"), ai_report: bool = Query(False)):
    try:
        if market == "TW": ticker_symbol = f"{symbol}.TW"
        elif market == "HK": ticker_symbol = f"{symbol.zfill(4)}.HK"
        elif market == "CRYPTO": ticker_symbol = f"{symbol}-USD"
        else: ticker_symbol = symbol.upper()

        tk = yf.Ticker(ticker_symbol)
        info = tk.info

        if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
            return {"error": f"Cannot find data for {ticker_symbol}"}

        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        currency = info.get("currency") or "USD"
        currency_map = {"HKD": "HKD", "TWD": "TWD", "USD": "USD"}
        display_currency = currency_map.get(currency, currency)

        quality = score_quality(info)
        valuation = score_valuation(info)
        overall = round(quality["score"] * 0.55 + valuation["score"] * 0.45)

        # 抓取過去一年的歷史股價
        hist = tk.history(period="1y")
        chart_dates = [d.strftime('%Y-%m-%d') for d in hist.index]
        chart_prices = [round(p, 2) for p in hist['Close']]

        # 抓取最新新聞 (相容 Yahoo 新舊 API 格式)
        raw_news = tk.news
        news_list = []
        if raw_news:
            for n in raw_news:
                if "content" in n: # 新版 API 格式
                    title = n["content"].get("title", "")
                    link_obj = n["content"].get("clickThroughUrl", {}) or n["content"].get("canonicalUrl", {})
                    link = link_obj.get("url", "") if isinstance(link_obj, dict) else ""
                    publisher = n["content"].get("provider", {}).get("displayName", "")
                else: # 舊版 API 格式
                    title = n.get("title", "")
                    link = n.get("link", "")
                    publisher = n.get("publisher", "")
                
                if title and link:
                    news_list.append({"title": title, "link": link, "publisher": publisher})
                
                if len(news_list) >= 3:
                    break

        result = {
            "symbol": ticker_symbol,
            "name": info.get("shortName") or info.get("longName") or ticker_symbol,
            "sector": info.get("sector") or "N/A",
            "price": price,
            "currency": display_currency,
            "quality": quality,
            "valuation": valuation,
            "overall_score": overall,
            "chart_data": {"dates": chart_dates, "prices": chart_prices},
            "news": news_list
        }

        if ai_report:
            result["ai_report"] = generate_ai_report(info, quality, valuation, overall)

        return result
    except Exception as e:
        return {"error": str(e)}

def generate_ai_report(info, quality, valuation, overall):
    name = info.get("shortName") or "Unknown"
    sector = info.get("sector") or "Unknown"
    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

    report = f"""
{'='*50}
AI EQUITY RESEARCH REPORT
{'='*50}

Company: {name}
Sector: {sector}
Current Price: ${price}

QUALITY ANALYSIS (Score: {quality['score']}/100)
{'─'*40}
"""
    for k, v in quality["breakdown"].items():
        report += f"  {k.upper()}: {v['value']} (Score: {v['score']})\n"

    report += f"""
VALUATION ANALYSIS (Score: {valuation['score']}/100)
{'─'*40}
"""
    for k, v in valuation["breakdown"].items():
        report += f"  {k.upper()}: {v['value']} (Score: {v['score']})\n"

    report += f"""
OVERALL SCORE: {overall}/100
{'─'*40}
"""
    if overall >= 75:
        report += "RECOMMENDATION: STRONG BUY - Excellent quality and valuation.\n"
    elif overall >= 60:
        report += "RECOMMENDATION: BUY - Good fundamentals with reasonable valuation.\n"
    elif overall >= 45:
        report += "RECOMMENDATION: HOLD - Mixed signals, monitor closely.\n"
    else:
        report += "RECOMMENDATION: SELL - Weak fundamentals or expensive valuation.\n"

    return report
