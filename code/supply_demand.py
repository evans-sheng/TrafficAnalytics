import pandas as pd
import numpy as np
import math
from typing import Any, Dict, Optional, Tuple, Union

# ===========================================================
#  Beijing timezone helpers
# ===========================================================
BJ_TZ = "Asia/Shanghai"

def _parse_beijing_time(value: Optional[Union[str, pd.Timestamp]]) -> Optional[pd.Timestamp]:
    """
    Parse 'YYYY-MM-DD HH:mm:ss' as tz-aware Asia/Shanghai timestamp.
    If already Timestamp, ensure tz-aware in Asia/Shanghai.
    """
    if value is None or value == "" or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, pd.Timestamp):
        ts = value
    else:
        ts = pd.to_datetime(value, format="%Y-%m-%d %H:%M:%S", errors="raise")
    if ts.tzinfo is None:
        ts = ts.tz_localize(BJ_TZ)
    else:
        ts = ts.tz_convert(BJ_TZ)
    return ts

def _to_beijing_aware(series: pd.Series) -> pd.Series:
    """
    Convert a datetime-like Series to tz-aware Asia/Shanghai.
    - If tz-naive: assume it's already Beijing local time, localize.
    - If tz-aware: convert to Beijing.
    """
    s = pd.to_datetime(series, errors="coerce")
    if getattr(s.dt, "tz", None) is None:
        return s.dt.tz_localize(BJ_TZ)
    return s.dt.tz_convert(BJ_TZ)

def _normalize_direction_movement(
    direction: Union[str, int, None],
    movement: Union[str, int, None],
) -> Tuple[Union[str, int], Union[str, int]]:
    """
    Accept:
      - direction = -1 (all)
      - direction like 'S-L' (PDF D-T format): parse into ('S', 'Left Turn')
      - direction like 'S' with movement = 'L'/'T'/'R' or full names
    """
    if direction is None:
        direction = -1
    if movement is None:
        movement = -1

    # If direction is combined like "S-L"
    if isinstance(direction, str) and "-" in direction and (movement == -1 or movement is None):
        parts = direction.split("-", 1)
        d = parts[0].strip()
        m = parts[1].strip()
        direction = d if d else direction
        movement = m if m else movement

    # Normalize movement short codes
    if isinstance(movement, str):
        m = movement.strip()
        map_short = {
            "L": "Left Turn",
            "T": "Through",
            "R": "Right Turn",
            "LT": "Left Turn",
            "TH": "Through",
            "RT": "Right Turn",
        }
        movement = map_short.get(m.upper(), m)

    # Normalize direction short codes (keep as-is if already)
    if isinstance(direction, str):
        direction = direction.strip()
    return direction, movement

def _force_flat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hard guarantee:
      - no index levels (MultiIndex or named index) remain
      - columns are unique (resolve duplicates by keeping the last occurrence)
    This prevents pandas ambiguity errors like:
      ValueError: 'direction' is both an index level and a column label
    """
    if df is None:
        return df
    # Reset until no named index and not MultiIndex
    while isinstance(df.index, pd.MultiIndex) or df.index.name is not None or any(n is not None for n in getattr(df.index, "names", []) if n is not None):
        df = df.reset_index()
        # after reset, index is RangeIndex but could still have a name; clear it
        df.index.name = None
        # break if now clean
        if not isinstance(df.index, pd.MultiIndex) and df.index.name is None:
            break

    # If direction somehow still appears as index name (rare), reset again
    if "direction" in getattr(df.index, "names", []):
        df = df.reset_index()

    # Ensure columns unique: if duplicates exist, keep the last one
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated(keep="last")].copy()

    return df

def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    except Exception:
        return None

def _format_time(ts: pd.Timestamp) -> str:
    """
    Output time as 'YYYY-MM-DD HH:mm:ss' in Beijing local time.
    """
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is None:
            # assume it's Beijing local
            ts = ts.tz_localize(BJ_TZ)
        else:
            ts = ts.tz_convert(BJ_TZ)
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    # fallback
    return pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M:%S")


# ===========================================================
# 1) Backlog + Utilized Supply
# ===========================================================
def compute_utilized_supply_with_backlog(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("time_bin").copy()
    unsatisfied = 0.0
    utilized_list = []
    backlog_list = []

    for _, row in df.iterrows():
        total_demand = float(row.get("smoothed_demand", 0.0) or 0.0) + unsatisfied
        # Keep your original scaling behavior from reference code
        capacity = float(row.get("cleaned_capacity", 0.0) or 0.0) * 1.5

        utilized = min(capacity, total_demand)
        unsatisfied = max(0.0, total_demand - capacity)

        utilized_list.append(utilized)
        backlog_list.append(unsatisfied)

    df["utilized_supply"] = utilized_list
    df["unsatisfied_demand"] = backlog_list
    return df


# ===========================================================
# 2) Resilience metrics (same as reference supply_demand.py)
# ===========================================================
def compute_resilience_metrics(df: pd.DataFrame) -> dict:
    """
    计算韧性指标（兼容新旧字段）：
    - 新字段：ef_utilized_cap
    - 旧字段：utilized_supply（若存在则兼容）
    """

    if df is None or df.empty:
        return {
            "OR_operational": None,
            "DR_design": None,
            "RR_recovery": None,
        }

    df = df.copy()
    df = df.sort_values("time_bin").reset_index(drop=True)

    # -------- 1. 选择“实际利用量”字段 --------
    if "ef_utilized_cap" in df.columns:
        utilized = df["ef_utilized_cap"].fillna(0)
    elif "utilized_supply" in df.columns:
        utilized = df["utilized_supply"].fillna(0)
    else:
        # 最兜底：完全没有就当 0
        utilized = 0

    demand = df["smoothed_demand"].fillna(0)

    # -------- 2. gap --------
    df["gap"] = demand - utilized

    # -------- 3. baseline（05:00） --------
    baseline_df = df[df["time_bin"].dt.hour == 5]

    if baseline_df.empty:
        baseline_gap = df["gap"].mean()
    else:
        baseline_gap = baseline_df["gap"].mean()

    if baseline_gap is None or baseline_gap == 0:
        return {
            "OR_operational": None,
            "DR_design": None,
            "RR_recovery": None,
        }

    # -------- 4. 韧性指标计算（保持你原始逻辑） --------
    OR_operational = 1 - (df["gap"].mean() / baseline_gap)
    DR_design = 1 - (df["gap"].max() / baseline_gap)
    RR_recovery = OR_operational  # 若你原逻辑如此，保持不变

    return {
        "OR_operational": float(OR_operational) if pd.notna(OR_operational) else None,
        "DR_design": float(DR_design) if pd.notna(DR_design) else None,
        "RR_recovery": float(RR_recovery) if pd.notna(RR_recovery) else None,
    }



# ===========================================================
# 3) Main pipeline (ref-based), but v2-compatible
# ===========================================================
def run_resilience_analysis(
    capacity_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    start_hour: int | None = None,
    end_hour: int | None = None,
    beginTime: str | None = None,
    endTime: str | None = None,
    direction=-1,
    movement=-1,
):
    """
    纯 column 版本：
    - 不使用 set_index
    - 不使用 groupby(level=...)
    - direction / movement / time_bin 只存在于 columns
    """

    # ---------- 0. 防御性复制 ----------
    capacity_df = capacity_df.copy() if capacity_df is not None else pd.DataFrame()
    demand_df = demand_df.copy() if demand_df is not None else pd.DataFrame()

    # ---------- 1. 时间解析（北京时间，tz-aware） ----------
    def _parse_beijing(ts):
        if ts is None:
            return None
        t = pd.to_datetime(ts, format="%Y-%m-%d %H:%M:%S", errors="raise")
        if t.tzinfo is None:
            t = t.tz_localize("Asia/Shanghai")
        return t

    begin_ts = _parse_beijing(beginTime)
    end_ts = _parse_beijing(endTime)

    # ---------- 2. 统一字段存在 ----------
    for df in (capacity_df, demand_df):
        if not df.empty:
            df.index.name = None  # 永远不允许 index 带语义
            if "direction" not in df.columns:
                df["direction"] = None
            if "movement" not in df.columns:
                df["movement"] = None


    # ---------- 2.5 统一 time_bin 为北京时间（tz-aware） ----------
    def _ensure_beijing_tz(df):
        if df.empty or "time_bin" not in df.columns:
            return df
        if not pd.api.types.is_datetime64_any_dtype(df["time_bin"]):
            return df

        # 如果 time_bin 是 tz-naive，补上 Asia/Shanghai
        if df["time_bin"].dt.tz is None:
            df["time_bin"] = df["time_bin"].dt.tz_localize("Asia/Shanghai")
        return df

    capacity_df = _ensure_beijing_tz(capacity_df)
    demand_df   = _ensure_beijing_tz(demand_df)


    # ---------- 3. 时间过滤 ----------
    def _time_filter(df):
        if df.empty or "time_bin" not in df.columns:
            return df
        out = df
        if begin_ts is not None:
            out = out[out["time_bin"] >= begin_ts]
        if end_ts is not None:
            out = out[out["time_bin"] <= end_ts]
        return out

    capacity_df = _time_filter(capacity_df)
    demand_df = _time_filter(demand_df)

    # ---------- 4. 方向 / 动作过滤 ----------
    def _dm_filter(df):
        if df.empty:
            return df
        out = df
        if direction != -1:
            out = out[out["direction"] == direction]
        if movement != -1:
            out = out[out["movement"] == movement]
        return out

    capacity_df = _dm_filter(capacity_df)
    demand_df = _dm_filter(demand_df)

    # ---------- 5. merge（column → column，不碰 index） ----------
    if capacity_df.empty:
        supply_demand = demand_df.copy()
        supply_demand["cleaned_capacity"] = pd.NA
    else:
        supply_demand = pd.merge(
            demand_df,
            capacity_df,
            on=["time_bin", "direction", "movement"],
            how="left",
        )

    # ---------- 6. 兜底字段 ----------
    if "smoothed_demand" not in supply_demand.columns:
        supply_demand["smoothed_demand"] = 0

    if "cleaned_capacity" not in supply_demand.columns:
        supply_demand["cleaned_capacity"] = 0

    supply_demand["smoothed_demand"] = (
        supply_demand["smoothed_demand"].fillna(0)
    )
    supply_demand["cleaned_capacity"] = (
        supply_demand["cleaned_capacity"].fillna(0)
    )

    # ---------- 7. 有效利用供给 ----------
    supply_demand["ef_utilized_cap"] = supply_demand[
        ["smoothed_demand", "cleaned_capacity"]
    ].min(axis=1)

    # ---------- 8. 计算韧性指标（纯 column groupby） ----------
    metrics_rows = []

    if supply_demand.empty:
        metrics_df = pd.DataFrame(
            columns=[
                "direction",
                "movement",
                "OR_operational",
                "DR_design",
                "RR_recovery",
            ]
        )
        return metrics_df, supply_demand

    for (d, m), g in supply_demand.groupby(
        ["direction", "movement"], dropna=False
    ):
        metrics = compute_resilience_metrics(g)
        metrics_rows.append(
            {
                "direction": d,
                "movement": m,
                "OR_operational": metrics.get("OR_operational"),
                "DR_design": metrics.get("DR_design"),
                "RR_recovery": metrics.get("RR_recovery"),
            }
        )

    metrics_df = pd.DataFrame(metrics_rows)

    return metrics_df, supply_demand



# ===========================================================
# 4) PDF output: /api/static/queryAll
# ===========================================================
def build_queryAll_response(
    capacity_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    beginTime: str,
    endTime: str,
    direction: Union[str, int, None] = -1,
    movement: Union[str, int, None] = -1,
    frequency: int = 2,
    metrics_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    输出结构（PDF + 扩展）：
      {
        "code": 0,
        "success": true,
        "data": {
          "actualVolume": [...],
          "trafficDemand": [...],
          "trafficCap": [...],
          "efUtilizedCap": [...],

          # 四阶段韧性（阴影带）
          "prepareResil": [...],
          "operateResil": [...],
          "designResil":  [...],
          "recoverResil": [...],

          # 综合韧性（单值）
          "generalResilience": 1234.56
        },
        "timestamp": 1723003200000
      }
    """

    # -------- 0. 方向 / 动作标准化 --------
    direction, movement = _normalize_direction_movement(direction, movement)

    # -------- 1. 计算韧性 & 合并序列 --------
    if metrics_df is None:
        metrics_df, merged_df = run_resilience_analysis(
            capacity_df=capacity_df,
            demand_df=demand_df,
            beginTime=beginTime,
            endTime=endTime,
            direction=direction,
            movement=movement,
        )
    else:
        _, merged_df = run_resilience_analysis(
            capacity_df=capacity_df,
            demand_df=demand_df,
            beginTime=beginTime,
            endTime=endTime,
            direction=direction,
            movement=movement,
        )

    if merged_df is None or merged_df.empty:
        empty_data = {
            "actualVolume": [],
            "trafficDemand": [],
            "trafficCap": [],
            "efUtilizedCap": [],
            "prepareResil": [],
            "operateResil": [],
            "designResil": [],
            "recoverResil": [],
            "generalResilience": None,
        }
        return {
            "code": 0,
            "success": True,
            "data": empty_data,
            "timestamp": int(pd.Timestamp.now(tz=BJ_TZ).timestamp() * 1000),
        }

    merged_df = _force_flat(merged_df)

    # -------- 2. 频率 --------
    rule = "5min" if int(frequency) == 1 else "15min"

    # -------- 3. 时间序列 --------
    ts = merged_df.sort_values("time_bin").set_index("time_bin")

    demand_series = ts["smoothed_demand"].resample(rule).mean()

    cap_series = (
        ts["cleaned_capacity"].resample(rule).mean()
        if "cleaned_capacity" in ts.columns
        else demand_series * 0
    )

    ef_series = np.minimum(demand_series, cap_series)
    actual_series = ef_series.copy()

    def series_to_points(s: pd.Series) -> list:
        return [
            {"time": _format_time(t), "value": _safe_float(v)}
            for t, v in s.items()
        ]

    # -------- 4. 从 metrics 提取韧性指标 --------
    prepare = operate = design = recover = general = None

    if metrics_df is not None and not metrics_df.empty:
        prepare = (
            _safe_float(metrics_df["PR_preparation"].mean())
            if "PR_preparation" in metrics_df.columns
            else None
        )
        operate = (
            _safe_float(metrics_df["OR_operational"].mean())
            if "OR_operational" in metrics_df.columns
            else None
        )
        design = (
            _safe_float(metrics_df["DR_design"].mean())
            if "DR_design" in metrics_df.columns
            else None
        )
        recover = (
            _safe_float(metrics_df["RR_recovery"].mean())
            if "RR_recovery" in metrics_df.columns
            else None
        )
        general = (
            _safe_float(metrics_df["General_Resilience"].mean())
            if "General_Resilience" in metrics_df.columns
            else None
        )

    def band_points(index: pd.DatetimeIndex, upper: Optional[float]) -> list:
        return [
            {"time": _format_time(t), "Lower": 0.0, "Upper": upper}
            for t in index
        ]

    idx = demand_series.index

    data = {
        "actualVolume": series_to_points(actual_series),
        "trafficDemand": series_to_points(demand_series),
        "trafficCap": series_to_points(cap_series),
        "efUtilizedCap": series_to_points(ef_series),

        # 四阶段韧性
        "prepareResil": band_points(idx, prepare),
        "operateResil": band_points(idx, operate),
        "designResil": band_points(idx, design),
        "recoverResil": band_points(idx, recover),

        # 综合韧性（单值）
        "generalResilience": general,
    }

    return {
        "code": 0,
        "success": True,
        "data": data,
        "timestamp": int(pd.Timestamp.now(tz=BJ_TZ).timestamp() * 1000),
    }

