import yfinance as yf
import numpy as np

class DCFModel:
    MARKET_PARAMS = {
        "US": {"rf": 0.043, "erp": 0.055, "tax": 0.21, "tg": 0.035},
        "HK": {"rf": 0.028, "erp": 0.065, "tax": 0.165, "tg": 0.040},
        "TW": {"rf": 0.015, "erp": 0.060, "tax": 0.20, "tg": 0.030},
        "CRYPTO": {"rf": 0.043, "erp": 0.150, "tax": 0.00, "tg": 0.030},
    }
    SUFFIXES = {"US": "", "HK": ".HK", "TW": ".TW", "CRYPTO": "-USD"}

    def calculate(self, symbol, market="US"):
        try:
            mkt = market.upper()
            p = self.MARKET_PARAMS.get(mkt, self.MARKET_PARAMS["US"])
            sfx = self.SUFFIXES.get(mkt, "")
            stock = yf.Ticker(f"{symbol}{sfx}")
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            shares = info.get("sharesOutstanding") or 0
            if not price or not shares:
                return {"error": "No price/shares data"}
            fcf, fcf_hist = self._get_fcf(stock, info)
            if not fcf or fcf <= 0:
                return {"error": "No positive FCF"}
            beta = info.get("beta") or 1.0
            beta = max(0.5, min(beta, 1.8))
            ke = p["rf"] + beta * p["erp"]
            total_debt = info.get("totalDebt") or 0
            mcap = price * shares
            if total_debt > 0 and mcap > 0:
                wd = total_debt / (total_debt + mcap)
                we = 1 - wd
                wacc = we * ke + wd * 0.05 * (1 - p["tax"])
            else:
                wacc = ke; wd = 0; we = 1
            wacc = max(0.06, min(wacc, 0.25))
            signals = []
            pos = [h for h in fcf_hist if h["fcf"] > 0]
            if len(pos) >= 3:
                yoy = []
                for i in range(1, len(pos)):
                    if pos[i-1]["fcf"] > 0:
                        yoy.append(pos[i]["fcf"] / pos[i-1]["fcf"] - 1)
                if yoy:
                    med = float(np.median(yoy))
                    med = max(-0.20, min(med, 0.25))
                    w = 1.2 if med > 0 else 0.3
                    signals.append(("FCF CAGR (median)", med, w))
            rg = info.get("revenueGrowth")
            if rg and -0.5 < rg < 1.0:
                signals.append(("Revenue Growth", rg, 1.0))
            eg = info.get("earningsGrowth")
            if eg and -0.5 < eg < 1.0:
                signals.append(("Earnings Growth", min(eg, 0.25), 1.0))
            roe = info.get("returnOnEquity")
            pay = info.get("payoutRatio")
            if roe and roe > 0 and pay and 0 < pay < 1:
                sg = roe * (1 - pay)
                if 0 < sg < 0.35:
                    signals.append(("Sustainable Growth", sg, 0.7))
            try:
                fins = stock.financials
                if fins is not None and not fins.empty:
                    rk = None
                    for lbl in fins.index:
                        if "total revenue" in str(lbl).lower():
                            rk = lbl; break
                    if rk:
                        rv = []
                        for col in fins.columns:
                            v = fins.loc[rk, col]
                            if v and not (isinstance(v, float) and np.isnan(v)) and float(v) > 0:
                                rv.append({"y": str(col)[:4], "r": float(v)})
                        rv = sorted(rv, key=lambda x: x["y"])
                        if len(rv) >= 3:
                            n = len(rv) - 1
                            rc = (rv[-1]["r"] / rv[0]["r"]) ** (1/n) - 1
                            rc = max(-0.10, min(rc, 0.25))
                            signals.append(("Revenue CAGR (hist)", rc, 1.0))
            except: pass
            # Buyback signal for mature companies
            bb = info.get("sharesPercentSharesOut")
            if not bb:
                try:
                    bs = stock.balance_sheet
                    if bs is not None and not bs.empty:
                        for lbl in bs.index:
                            if "treasury" in str(lbl).lower():
                                vals = []
                                for col in bs.columns:
                                    v = bs.loc[lbl, col]
                                    if v and not (isinstance(v, float) and np.isnan(v)):
                                        vals.append(abs(float(v)))
                                if len(vals) >= 2 and vals[0] > vals[-1]:
                                    bb_rate = (vals[0] - vals[-1]) / mcap if mcap > 0 else 0
                                    if bb_rate > 0.01:
                                        signals.append(("Buyback Yield", min(bb_rate, 0.06), 0.5))
                                break
                except: pass
            if signals:
                tw = sum(s[2] for s in signals)
                g_high = sum(s[1] * s[2] for s in signals) / tw
                vals = [s[1] for s in signals if s[1] > 0]
                if vals:
                    med_s = float(np.median(vals))
                    g_high = min(g_high, med_s * 1.5)
            else:
                g_high = 0.05
            # Buyback boost: if company buys back shares, per-share value grows faster
            bb_boost = 0
            try:
                bs = stock.balance_sheet
                if bs is not None and not bs.empty:
                    for lbl in bs.index:
                        if "ordinary shares" in str(lbl).lower() or "common stock" in str(lbl).lower() or "share issued" in str(lbl).lower():
                            share_counts = []
                            for col in bs.columns:
                                v = bs.loc[lbl, col]
                                if v and not (isinstance(v, float) and np.isnan(v)) and float(v) > 0:
                                    share_counts.append(float(v))
                            if len(share_counts) >= 2:
                                newest_shares = share_counts[0]
                                oldest_shares = share_counts[-1]
                                if oldest_shares > newest_shares:
                                    annual_bb = 1 - (newest_shares / oldest_shares) ** (1 / (len(share_counts)-1))
                                    bb_boost = max(0, min(annual_bb, 0.05))
                                    if bb_boost > 0.005:
                                        signals.append(("Buyback Yield", bb_boost, 0.8))
                            break
            except: pass
            if signals:
                tw = sum(s[2] for s in signals)
                g_high = sum(s[1] * s[2] for s in signals) / tw
                vals = [s[1] for s in signals if s[1] > 0]
                if vals:
                    med_s = float(np.median(vals))
                    g_high = min(g_high, med_s * 1.5)
            else:
                g_high = 0.05
            g_high = max(0.03, min(g_high, 0.20))
            tg = min(p["tg"], wacc - 0.015)
            tg = max(0.02, tg)
            if len(pos) >= 3:
                avg_f = np.mean([h["fcf"] for h in pos])
                if fcf > avg_f * 1.5:
                    fcf_base = (fcf + avg_f) / 2
                    fcf_note = f"Blended (latest too high vs avg)"
                else:
                    fcf_base = fcf; fcf_note = "Using latest FCF"
            else:
                fcf_base = fcf; fcf_note = "Limited history"
            projs = []; pv_sum = 0; f = fcf_base
            for yr in range(1, 11):
                if yr <= 5: g = g_high
                else:
                    fade = (yr - 5) / 5.0
                    g = g_high + (tg - g_high) * fade
                f = f * (1 + g)
                df = 1 / ((1 + wacc) ** yr)
                pv = f * df; pv_sum += pv
                projs.append({"year": yr, "fcf": round(f), "growth": round(g*100, 1), "pv": round(pv)})
            last_f = projs[-1]["fcf"]
            tv = last_f * (1 + tg) / (wacc - tg)
            pv_tv = tv / ((1 + wacc) ** 10)
            cash = info.get("totalCash") or 0
            ev = pv_sum + pv_tv
            eq = ev + cash - total_debt
            target = eq / shares if shares > 0 else 0
            if target <= 0:
                return {"error": "Negative DCF value"}
            upside = ((target - price) / price) * 100
            if upside > 30: verdict = "Strongly Undervalued"
            elif upside > 10: verdict = "Undervalued"
            elif upside > -10: verdict = "Fairly Valued"
            elif upside > -30: verdict = "Overvalued"
            else: verdict = "Strongly Overvalued"
            cs = {"HKD":"HK$","TWD":"NT$","USD":"$"}.get(info.get("currency","USD"), "$")
            sens = []
            for dw in [-0.02, -0.01, 0, 0.01, 0.02]:
                row = {"wacc": f"{(wacc+dw)*100:.1f}%"}
                for dg in [-0.01, -0.005, 0, 0.005, 0.01]:
                    w2 = wacc + dw; g2 = tg + dg
                    if w2 <= g2 + 0.005:
                        row[f"g={g2*100:.1f}%"] = "N/A"; continue
                    tv2 = last_f * (1+g2) / (w2 - g2)
                    pv2 = tv2 / ((1+w2)**10)
                    eq2 = pv_sum + pv2 + cash - total_debt
                    row[f"g={g2*100:.1f}%"] = round(eq2 / shares)
                sens.append(row)
            gd = [{"signal": s[0], "value": f"{s[1]*100:.1f}%", "weight": s[2]} for s in signals]
            return {
                "current_price": round(price, 2), "target_price": round(target, 2),
                "upside": f"{upside:+.1f}%", "verdict": verdict, "currency": cs,
                "growth_analysis": {"blended": f"{g_high*100:.1f}%", "signals": gd},
                "fcf_history": {"current": f"{cs}{fcf:,.0f}", "base_used": f"{cs}{fcf_base:,.0f}", "note": fcf_note,
                    "data": [{"year": h.get("year","?"), "fcf": f"{cs}{h['fcf']:,.0f}"} for h in fcf_hist]},
                "wacc_detail": {"wacc": f"{wacc*100:.2f}%", "cost_of_equity": f"{ke*100:.2f}%",
                    "beta": round(beta, 2), "risk_free": f"{p['rf']*100:.1f}%", "erp": f"{p['erp']*100:.1f}%",
                    "debt_weight": f"{wd*100:.1f}%", "equity_weight": f"{we*100:.1f}%"},
                "projections": projs[:5] + [projs[-1]],
                "components": {"pv_fcf": f"{cs}{pv_sum:,.0f}", "terminal_value": f"{cs}{tv:,.0f}",
                    "pv_terminal": f"{cs}{pv_tv:,.0f}", "enterprise_value": f"{cs}{ev:,.0f}",
                    "cash": f"{cs}{cash:,.0f}", "debt": f"{cs}{total_debt:,.0f}",
                    "equity_value": f"{cs}{eq:,.0f}", "shares": f"{shares/1e6:,.0f}M",
                    "terminal_pct": f"{pv_tv/ev*100:.0f}%" if ev > 0 else "N/A"},
                "assumptions": {"growth_high": f"{g_high*100:.1f}%", "terminal_growth": f"{tg*100:.1f}%",
                    "wacc": f"{wacc*100:.2f}%", "years": 10},
                "sensitivity": sens,
            }
        except Exception as e:
            return {"error": f"DCF failed: {str(e)}"}

    def _get_fcf(self, stock, info):
        hist = []
        try:
            cf = stock.cashflow
            if cf is not None and not cf.empty:
                ocf_key = capex_key = fcf_key = None
                for lbl in cf.index:
                    ll = str(lbl).lower().replace("_", " ")
                    if "free cash flow" in ll: fcf_key = lbl
                    if ocf_key is None and "operating cash" in ll: ocf_key = lbl
                    if capex_key is None and "capital expenditure" in ll: capex_key = lbl
                use_key = fcf_key or ocf_key
                if use_key:
                    for col in cf.columns:
                        yr = str(col)[:4]
                        val = cf.loc[use_key, col]
                        if val is None or (isinstance(val, float) and np.isnan(val)): continue
                        val = float(val)
                        if fcf_key:
                            hist.append({"year": yr, "fcf": round(val)})
                        else:
                            capex = 0
                            if capex_key:
                                cv = cf.loc[capex_key, col]
                                if cv is not None and not (isinstance(cv, float) and np.isnan(cv)):
                                    capex = abs(float(cv))
                            hist.append({"year": yr, "fcf": round(val - capex)})
        except: pass
        hist = sorted(hist, key=lambda x: x["year"])
        if hist:
            pos_fcfs = [h["fcf"] for h in hist if h["fcf"] > 0]
            if pos_fcfs:
                latest = hist[-1]["fcf"]
                import numpy as np
                median_fcf = float(np.median(pos_fcfs))
                if latest <= 0 or latest < median_fcf * 0.5:
                    return round(median_fcf), hist
                return latest, hist
        fi = info.get("freeCashflow")
        if fi and fi > 0: return fi, [{"year": "TTM", "fcf": fi}]
        ocf = info.get("operatingCashflow") or 0
        cap = abs(info.get("capitalExpenditures") or 0)
        if ocf - cap > 0: return ocf - cap, [{"year": "TTM", "fcf": round(ocf - cap)}]
        return None, []
