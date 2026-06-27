"""RFM 客户价值评分。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _quantile_score(series: pd.Series, higher_is_better: bool, bins: int = 5) -> pd.Series:
    """按并列值友好的百分位排名映射 1~5 分，避免同一频次被人为拆分。"""
    valid = series.dropna()
    result = pd.Series(pd.NA, index=series.index, dtype="Int64")
    if valid.empty:
        return result

    if valid.nunique() == 1:
        result.loc[valid.index] = 3
        return result

    # higher_is_better=True 时大值对应更高百分位；反之小值对应更高百分位。
    percentile = valid.rank(
        method="average",
        pct=True,
        ascending=higher_is_better,
    )
    scores = np.ceil(percentile * bins).clip(1, bins).astype(int)
    result.loc[valid.index] = scores
    return result


def calculate_rfm_scores(customer_mart: pd.DataFrame) -> pd.DataFrame:
    """为客户表增加 R、F、M 三项分数与综合价值分。"""
    df = customer_mart.copy()
    required = {"recency_days", "frequency", "monetary"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"客户表缺少 RFM 字段：{sorted(missing)}")

    df["r_score"] = _quantile_score(df["recency_days"], higher_is_better=False)
    df["f_score"] = _quantile_score(df["frequency"], higher_is_better=True)
    df["m_score"] = _quantile_score(df["monetary"], higher_is_better=True)

    df[["r_score", "f_score", "m_score"]] = df[["r_score", "f_score", "m_score"]].fillna(1).astype(int)
    df["rfm_code"] = df[["r_score", "f_score", "m_score"]].astype(str).agg("".join, axis=1)
    df["rfm_total_score"] = df[["r_score", "f_score", "m_score"]].sum(axis=1)

    # 消费金额的业务权重略高于活跃度和频率。
    df["customer_value_score"] = (
        0.30 * df["r_score"] + 0.30 * df["f_score"] + 0.40 * df["m_score"]
    ) / 5 * 100
    df["customer_value_score"] = df["customer_value_score"].round(2)
    return df
