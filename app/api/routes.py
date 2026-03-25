from fastapi import APIRouter, Query
from app.data.stock_fetcher import StockFetcher
from app.services.scoring_engine import ScoringEngine
from app.services.dcf_model import DCFModel
from app.services.ai_analyst import AIAnalyst
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()
fetcher = StockFetcher()
scorer = ScoringEngine()
dcf = DCFModel()

api_key = os.getenv("NVIDIA_API_KEY", "")
analyst = AIAnalyst(api_key=api_key) if api_key else None


@router.get("/analyze")
def analyze_stock(
    symbol: str = Query(..., description="Stock symbol"),
    market: str = Query("US", description="Market: US, TW, HK, CRYPTO"),
    ai_report: bool = Query(False, description="Generate AI report"),
):
    data = fetcher.fetch(symbol, market)
    result = scorer.calculate(data)

    # 加入 DCF 估值
    result["dcf"] = dcf.calculate(symbol, market)

    if ai_report and analyst:
        result["ai_report"] = analyst.generate_report(result)
    elif ai_report and not analyst:
        result["ai_report"] = "NVIDIA API key not configured"

    return result


@router.get("/dcf")
def dcf_only(
    symbol: str = Query(..., description="Stock symbol"),
    market: str = Query("US", description="Market: US, TW, HK, CRYPTO"),
):
    """單獨查 DCF 估值"""
    return dcf.calculate(symbol, market)
