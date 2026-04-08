import asyncio
import json
import yfinance as yf
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 導入 AI 與 DCF 服務
from app.services.ai_analyst import AIAnalyst
from app.services.dcf_model import DCFModel

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 初始化服務
analyst = AIAnalyst()
dcf_engine = DCFModel()

@app.get("/")
def index():
    return FileResponse("app/static/index.html")

# ==========================================
# 評分邏輯函數 (負責驅動前端的 UI 面板)
# ==========================================
def score_quality(info):
    breakdown, total = {}, 0
    roe = info.get("returnOnEquity")
    if roe is not None:
        roe_pct = round(roe * 100, 2) if abs(roe) < 10 else round(roe, 2)
        s = min(30, max(0, int(roe_pct * 1.5))) if roe_pct > 0 else 0
        breakdown["roe"] = {"value": roe_pct, "score": s}; total += s
    else: breakdown["roe"] = {"value": "N/A", "score": 0}

    margin = info.get("profitMargins")
    if margin is not None:
        margin_pct = round(margin * 100, 2) if abs(margin) < 10 else round(margin, 2)
        s = min(25, max(0, int(margin_pct * 1.0))) if margin_pct > 0 else 0
        breakdown["profit_margin"] = {"value": margin_pct, "score": s}; total += s
    else: breakdown["profit_margin"] = {"value": "N/A", "score": 0}

    de = info.get("debtToEquity")
    if de is not None:
        de_val = round(de, 2)
        if de_val < 50: s = 25
        elif de_val < 100: s = 20
        elif de_val < 200: s = 10
        else: s = 0
        breakdown["debt_to_equity"] = {"value": de_val, "score": s}; total += s
    else: breakdown["debt_to_equity"] = {"value": "N/A", "score": 15}; total += 15

    rg = info.get("revenueGrowth")
    if rg is not None:
        rg_pct = round(rg * 100, 2) if abs(rg) < 10 else round(rg, 2)
        s = min(20, max(0, int(rg_pct * 1.0))) if rg_pct > 0 else 0
        breakdown["revenue_growth"] = {"value": rg_pct, "score": s}; total += s
    else: breakdown["revenue_growth"] = {"value": "N/A", "score": 0}

    return {"score": min(total, 100), "breakdown": breakdown}

def score_valuation(info):
    breakdown, total = {}, 0
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
        breakdown["pe_ratio"] = {"value": pe, "score": s}; total += s
    else: breakdown["pe_ratio"] = {"value": "N/A", "score": 0}

    pb = info.get("priceToBook")
    if pb is not None:
        pb = round(pb, 2)
        if pb < 1: s = 30
        elif pb < 2: s = 25
        elif pb < 3: s = 20
        elif pb < 5: s = 10
        else: s = 0
        breakdown["pb_ratio"] = {"value": pb, "score": s}; total += s
    else: breakdown["pb_ratio"] = {"value": "N/A", "score": 0}

    dy = info.get("dividendYield")
    if dy is not None:
        dy_pct = round(dy * 100, 2) if dy < 1 else round(dy, 2)
        s = min(30, max(0, int(dy_pct * 8)))
        breakdown["dividend_yield"] = {"value": dy_pct, "score": s}; total += s
    else: breakdown["dividend_yield"] = {"value": "N/A", "score": 0}

    return {"score": min(total, 100), "breakdown": breakdown}

# ==========================================
# 主 API 端點 (已整合併行處理 DCF 與 AI)
# ==========================================
@app.get("/analyze")
async def analyze(symbol: str = Query(...), market: str = Query("US"), ai_report: bool = Query(False)):
    if market == "TW": ticker_symbol = f"{symbol}.TW"
    elif market == "HK": ticker_symbol = f"{symbol.zfill(4)}.HK"
    elif market == "CRYPTO": ticker_symbol = f"{symbol}-USD"
    else: ticker_symbol = symbol.upper()

    try:
        # 已復原為最乾淨的 Ticker
        tk = yf.Ticker(ticker_symbol)
        
        # 抓取圖表數據
        hist = tk.history(period="1y")
        
        # 過濾掉 Yahoo Finance 傳回來的空值 (NaN) 行，防止 JSON 崩潰
        hist = hist.dropna(subset=['Close'])
        
        if hist.empty:
            return {"error": f"Cannot find any data for {ticker_symbol}"}
            
        chart_dates = [d.strftime('%Y-%m-%d') for d in hist.index]
        chart_prices = [round(p, 2) for p in hist['Close']]
        real_price = chart_prices[-1]

        currency_map = {"HK": "HKD", "TW": "TWD", "US": "USD", "CRYPTO": "USD"}
        display_currency = currency_map.get(market, "USD")

        # 抓取基本面數據
        try:
            info = tk.info
            quality = score_quality(info)
            valuation = score_valuation(info)
            overall = round(quality["score"] * 0.55 + valuation["score"] * 0.45)
            name = info.get("shortName") or info.get("longName") or ticker_symbol
            sector = info.get("sector") or "N/A"
        except Exception:
            quality = {"score": "-", "breakdown": {"roe": {"value": "Rate Limited", "score": 0}}}
            valuation = {"score": "-", "breakdown": {"pe_ratio": {"value": "Rate Limited", "score": 0}}}
            overall = "-"
            name = f"{ticker_symbol} (Live Chart, API Limited)"
            sector = "N/A"

        # 抓取新聞
        raw_news = tk.news
        news_list = []
        news_summary = "暫無新聞"
        if raw_news:
            for n in raw_news:
                title = n.get("content", {}).get("title", "") or n.get("title", "")
                link_obj = n.get("content", {}).get("clickThroughUrl", {}) or n.get("link", "")
                link = link_obj.get("url", "") if isinstance(link_obj, dict) else link_obj
                publisher = n.get("content", {}).get("provider", {}).get("displayName", "") or n.get("publisher", "")
                if title and link: news_list.append({"title": title, "link": link, "publisher": publisher})
                if len(news_list) >= 3: break
            if news_list:
                news_summary = " | ".join([n["title"] for n in news_list])

        # 準備基礎返回結果
        result = {
            "symbol": ticker_symbol,
            "name": name,
            "sector": sector,
            "price": real_price,
            "currency": display_currency,
            "quality": quality,
            "valuation": valuation,
            "overall_score": overall,
            "chart_data": {"dates": chart_dates, "prices": chart_prices},
            "news": news_list
        }
        
        # ==========================================
        # 同步啟動 DCF 計算與 AI 分析 (背景並行處理不卡畫面)
        # ==========================================
        dcf_task = asyncio.to_thread(dcf_engine.calculate, symbol, market)
        ai_task = None

        if ai_report: 
            ticker_data = {
                "symbol": ticker_symbol,
                "roe": quality.get("breakdown", {}).get("roe", {}).get("value", "N/A"),
                "pe": valuation.get("breakdown", {}).get("pe_ratio", {}).get("value", "N/A"),
                "debt_to_equity": quality.get("breakdown", {}).get("debt_to_equity", {}).get("value", "N/A")
            }
            ai_task = analyst.generate_report(ticker_data, news_summary)

        # 等待 DCF 任務完成
        try:
            result["dcf_valuation"] = await dcf_task
        except Exception as e:
            result["dcf_valuation"] = {"error": f"DCF 失敗: {str(e)}"}

        # 等待 AI 任務完成 (如果有觸發)
        if ai_task:
            raw_ai_response = await ai_task
            try:
                result["ai_report"] = json.loads(raw_ai_response)
            except json.JSONDecodeError:
                result["ai_report"] = {"error": "AI 返回格式解析失敗", "raw_output": raw_ai_response}

        return result

    except Exception as e:
        return {"error": f"API 發生錯誤: {str(e)}"}