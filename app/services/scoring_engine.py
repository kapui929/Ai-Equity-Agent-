class ScoringEngine:
    def calculate(self, data: dict) -> dict:
        if "error" in data:
            return data
        quality = self._quality_score(data)
        valuation = self._valuation_score(data)
        overall = round(quality["score"] * 0.6 + valuation["score"] * 0.4, 1)
        return {
            "symbol": data.get("symbol"),
            "name": data.get("name"),
            "price": data.get("price"),
            "currency": data.get("currency"),
            "sector": data.get("sector"),
            "quality": quality,
            "valuation": valuation,
            "overall_score": overall,
        }

    def _quality_score(self, data: dict) -> dict:
        score = 0
        breakdown = {}
        roe = data.get("roe")
        if roe is not None:
            roe_pct = roe * 100
            if roe_pct > 20: s = 30
            elif roe_pct > 15: s = 25
            elif roe_pct > 10: s = 20
            elif roe_pct > 5: s = 10
            else: s = 0
            score += s
            breakdown["roe"] = {"value": round(roe_pct, 2), "score": s}
        margin = data.get("profit_margin")
        if margin is not None:
            margin_pct = margin * 100
            if margin_pct > 20: s = 25
            elif margin_pct > 10: s = 20
            elif margin_pct > 5: s = 15
            elif margin_pct > 0: s = 5
            else: s = 0
            score += s
            breakdown["profit_margin"] = {"value": round(margin_pct, 2), "score": s}
        debt = data.get("debt_to_equity")
        if debt is not None:
            if debt < 30: s = 25
            elif debt < 50: s = 20
            elif debt < 100: s = 15
            elif debt < 200: s = 10
            else: s = 0
            score += s
            breakdown["debt_to_equity"] = {"value": round(debt, 2), "score": s}
        growth = data.get("revenue_growth")
        if growth is not None:
            growth_pct = growth * 100
            if growth_pct > 20: s = 20
            elif growth_pct > 10: s = 15
            elif growth_pct > 5: s = 10
            elif growth_pct > 0: s = 5
            else: s = 0
            score += s
            breakdown["revenue_growth"] = {"value": round(growth_pct, 2), "score": s}
        return {"score": score, "max": 100, "breakdown": breakdown}

    def _valuation_score(self, data: dict) -> dict:
        score = 0
        breakdown = {}
        pe = data.get("pe_ratio")
        if pe is not None and pe > 0:
            if pe < 10: s = 35
            elif pe < 15: s = 30
            elif pe < 20: s = 25
            elif pe < 30: s = 15
            elif pe < 50: s = 5
            else: s = 0
            score += s
            breakdown["pe_ratio"] = {"value": round(pe, 2), "score": s}
        pb = data.get("pb_ratio")
        if pb is not None and pb > 0:
            if pb < 1: s = 35
            elif pb < 2: s = 30
            elif pb < 3: s = 25
            elif pb < 5: s = 15
            else: s = 0
            score += s
            breakdown["pb_ratio"] = {"value": round(pb, 2), "score": s}
        div = data.get("dividend_yield")
        if div is not None:
            div_pct = div * 100
            if div_pct > 5: s = 30
            elif div_pct > 3: s = 25
            elif div_pct > 2: s = 20
            elif div_pct > 1: s = 10
            else: s = 5
            score += s
            breakdown["dividend_yield"] = {"value": round(div_pct, 2), "score": s}
        return {"score": score, "max": 100, "breakdown": breakdown}
