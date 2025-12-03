from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
import os
import json
import traceback
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
JSON_DIR = os.path.join(BASE_DIR, "json")

# Indicators treated as NON-ADDITIVE
NON_ADDITIVE = {
    "PrEP_CT", "PrEP_CURR", "TX_CURR", "TX_CURR_ARVDisp_less_three_mo",
    "TX_CURR_ARVDisp_six_more_mo", "TX_CURR_ARVDisp_three_five_mo",
    "TX_PVLS", "OVC_SERV", "TX_TB"
}

# Helper field selectors
def pick(row, keys):
    for k in keys:
        if k in row:
            return row[k]
    return None

# Column name variants
INDICATOR_KEYS = ["Indicator", "indicator"]
COARSE_AGE_KEYS = ["Coarse Age", "Coarse_Age", "CoarseAge"]
SEX_KEYS = ["Sex", "sex"]
FISCAL_KEYS = ["Fiscal Year", "Fiscal_Year", "FY"]
TARGET_KEYS = ["Targets", "Target"]
PARTNER_KEYS = ["Partner Name", "Partner", "Partner_Name"]
MECH_KEYS = ["Mechanism Name", "Mechanism", "Mechanism_Name"]

# Quarter variants
Q1_KEYS = ["Quarter 1", "Quarter_1", "Q1"]
Q2_KEYS = ["Quarter 2", "Quarter_2", "Q2"]
Q3_KEYS = ["Quarter 3", "Quarter_3", "Q3"]
Q4_KEYS = ["Quarter 4", "Quarter_4", "Q4"]

def to_num(x):
    try:
        if x is None or x == "" or str(x).lower() == "nan":
            return None
        return float(x)
    except:
        return None

def last_non_null_quarter(row):
    for keys in [Q4_KEYS, Q3_KEYS, Q2_KEYS, Q1_KEYS]:
        v = to_num(pick(row, keys))
        if v is not None:
            return v
    return 0

def sum_quarters(row):
    vals = [
        to_num(pick(row, Q1_KEYS)) or 0,
        to_num(pick(row, Q2_KEYS)) or 0,
        to_num(pick(row, Q3_KEYS)) or 0,
        to_num(pick(row, Q4_KEYS)) or 0
    ]
    return sum(vals)


@app.get("/")
def serve_dashboard():
    dashboard_file = os.path.join(FRONTEND_DIR, "dashboard.html")
    return FileResponse(dashboard_file)


@app.get("/api/summary")
def get_summary():
    try:
        files = os.listdir(DATA_DIR)
        return {"data_path": DATA_DIR, "files": files}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/mechanisms")
def get_mechanisms(
    indicator: Optional[str] = Query(None),
    coarseAge: Optional[str] = Query(None),
    sex: Optional[str] = Query(None),
    fiscalYear: Optional[int] = Query(None),
    partner: Optional[str] = Query(None),
    mechanismName: Optional[str] = Query(None)
):
    json_file = os.path.join(JSON_DIR, "mech.json")

    if not os.path.exists(json_file):
        return {"error": "mech.json not found. Run converter.py first."}

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            rows = json.load(f)

        # --- FILTERING ---
        def equal(a, b):
            if b is None:
                return True
            if a is None:
                return False
            return str(a).strip().lower() == str(b).strip().lower()

        filtered = []
        for r in rows:
            ind = pick(r, INDICATOR_KEYS)
            ca = pick(r, COARSE_AGE_KEYS)
            sx = pick(r, SEX_KEYS)
            fy = pick(r, FISCAL_KEYS)
            pt = pick(r, PARTNER_KEYS)
            mech = pick(r, MECH_KEYS)

            try:
                fy_num = int(float(fy)) if fy not in (None, "") else None
            except:
                fy_num = None

            if not equal(ind, indicator): continue
            if not equal(ca, coarseAge): continue
            if not equal(sx, sex): continue
            if fiscalYear is not None and fy_num != fiscalYear: continue
            if not equal(pt, partner): continue
            if not equal(mech, mechanismName): continue

            filtered.append(r)

        # --- COMPUTATIONS ---
        processed = []
        for r in filtered:
            ind = pick(r, INDICATOR_KEYS)
            targets = to_num(pick(r, TARGET_KEYS))

            # Cum_Total calculation
            if ind in NON_ADDITIVE:
                cum_total = last_non_null_quarter(r)
            else:
                cum_total = sum_quarters(r)

            percent = None
            if targets not in (None, 0):
                percent = (cum_total / targets) * 100

            new_r = dict(r)
            new_r["_computed"] = {
                "cum_total": cum_total,
                "percent": percent
            }
            processed.append(new_r)

        # --- SUMMARY CARDS ---
        partners = {str(pick(r, PARTNER_KEYS)) for r in processed if pick(r, PARTNER_KEYS)}
        mechs = {str(pick(r, MECH_KEYS)) for r in processed if pick(r, MECH_KEYS)}

        summary = {
            "unique_partners": len(partners),
            "unique_mechanisms": len(mechs)
        }

        # --- AGGREGATES BY YEAR ---
        fy_map = {}
        for r in processed:
            fy = pick(r, FISCAL_KEYS)
            try:
                fy_num = int(float(fy))
            except:
                continue

            if fy_num not in fy_map:
                fy_map[fy_num] = {"targets": 0, "cum_total": 0}

            t = to_num(pick(r, TARGET_KEYS)) or 0
            c = r["_computed"]["cum_total"] or 0

            fy_map[fy_num]["targets"] += t
            fy_map[fy_num]["cum_total"] += c

        aggregates = []
        for y in sorted(fy_map.keys()):
            t = fy_map[y]["targets"]
            c = fy_map[y]["cum_total"]
            pct = (c / t * 100) if t else None
            aggregates.append({"fiscalYear": y, "targets": t, "cum_total": c, "percent": pct})

        # --- QUARTERLY TREND ---
        q1 = q2 = q3 = q4 = 0
        for r in processed:
            q1 += to_num(pick(r, Q1_KEYS)) or 0
            q2 += to_num(pick(r, Q2_KEYS)) or 0
            q3 += to_num(pick(r, Q3_KEYS)) or 0
            q4 += to_num(pick(r, Q4_KEYS)) or 0

        quarterly_trend = {
            "Q1": q1, "Q2": q2, "Q3": q3, "Q4": q4
        }

        # --- FILTER LISTS (from full dataset) ---
        all_indicators = sorted({str(pick(r, INDICATOR_KEYS)) for r in rows if pick(r, INDICATOR_KEYS)})
        all_coarse = sorted({str(pick(r, COARSE_AGE_KEYS)) for r in rows if pick(r, COARSE_AGE_KEYS)})
        all_sexes = sorted({str(pick(r, SEX_KEYS)) for r in rows if pick(r, SEX_KEYS)})
        all_years = sorted({int(float(pick(r, FISCAL_KEYS))) for r in rows if pick(r, FISCAL_KEYS)})
        all_partners = sorted({str(pick(r, PARTNER_KEYS)) for r in rows if pick(r, PARTNER_KEYS)})

        return JSONResponse({
            "summary": summary,
            "filters": {
                "indicators": all_indicators,
                "coarseAges": all_coarse,
                "sexes": all_sexes,
                "fiscalYears": all_years,
                "partners": all_partners
            },
            "aggregates_by_year": aggregates,
            "quarterly_trend": quarterly_trend,
            "records": processed
        })

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
