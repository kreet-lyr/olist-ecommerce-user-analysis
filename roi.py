"""营销 ROI 情景模拟与敏感性分析。

注意：公开 Olist 数据没有真实投放实验标签，结果仅为参数化模拟，不能表述为实际营销提升。
"""
from __future__ import annotations

from typing import Dict, Iterable
import numpy as np
import pandas as pd

DEFAULT_SCENARIOS: Dict[str, Dict[str, float | str]] = {
    "核心VIP": {
        "campaign": "会员权益与高客单推荐",
        "coverage_rate": 0.60,
        "conversion_uplift": 0.035,
        "coupon_cost": 8.0,
        "contact_cost": 0.35,
    },
    "高价值待挽回": {
        "campaign": "限时召回券与个性化推荐",
        "coverage_rate": 0.70,
        "conversion_uplift": 0.080,
        "coupon_cost": 15.0,
        "contact_cost": 0.45,
    },
    "高潜新客": {
        "campaign": "二单券与跨品类推荐",
        "coverage_rate": 0.75,
        "conversion_uplift": 0.065,
        "coupon_cost": 10.0,
        "contact_cost": 0.30,
    },
    "潜力复购客": {
        "campaign": "阶梯满减与补货提醒",
        "coverage_rate": 0.65,
        "conversion_uplift": 0.050,
        "coupon_cost": 10.0,
        "contact_cost": 0.30,
    },
    "高客单低频客": {
        "campaign": "高端品类定向推荐",
        "coverage_rate": 0.50,
        "conversion_uplift": 0.040,
        "coupon_cost": 12.0,
        "contact_cost": 0.35,
    },
    "一般活跃客": {
        "campaign": "日常促销与品类推荐",
        "coverage_rate": 0.45,
        "conversion_uplift": 0.025,
        "coupon_cost": 6.0,
        "contact_cost": 0.25,
    },
}


def build_roi_scenarios(
    customer_segment: pd.DataFrame,
    gross_margin: float = 0.25,
    scenarios: Dict[str, Dict[str, float | str]] | None = None,
) -> pd.DataFrame:
    """按客群生成增量订单、增量 GMV、营销成本与 ROI 模拟结果。"""
    if not 0 < gross_margin < 1:
        raise ValueError("gross_margin 必须在 0 和 1 之间。")

    scenarios = scenarios or DEFAULT_SCENARIOS
    rows = []
    for segment, config in scenarios.items():
        subset = customer_segment.loc[customer_segment["segment"] == segment]
        if subset.empty:
            continue

        target_users = int(subset["customer_unique_id"].nunique())
        avg_aov = float(subset["avg_order_value"].mean())
        coverage = float(config["coverage_rate"])
        uplift = float(config["conversion_uplift"])
        coupon_cost = float(config["coupon_cost"])
        contact_cost = float(config["contact_cost"])

        reached_users = target_users * coverage
        incremental_orders = reached_users * uplift
        incremental_gmv = incremental_orders * avg_aov
        incremental_gross_profit = incremental_gmv * gross_margin
        coupon_total_cost = incremental_orders * coupon_cost
        contact_total_cost = reached_users * contact_cost
        campaign_cost = coupon_total_cost + contact_total_cost
        roi = np.nan if campaign_cost == 0 else (incremental_gross_profit - campaign_cost) / campaign_cost

        rows.append(
            {
                "segment": segment,
                "campaign": str(config["campaign"]),
                "target_users": target_users,
                "coverage_rate": coverage,
                "reached_users": reached_users,
                "conversion_uplift": uplift,
                "avg_order_value": avg_aov,
                "incremental_orders": incremental_orders,
                "incremental_gmv": incremental_gmv,
                "gross_margin": gross_margin,
                "incremental_gross_profit": incremental_gross_profit,
                "coupon_total_cost": coupon_total_cost,
                "contact_total_cost": contact_total_cost,
                "campaign_cost": campaign_cost,
                "roi": roi,
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        numeric_cols = result.select_dtypes(include="number").columns
        result[numeric_cols] = result[numeric_cols].round(4)
        result = result.sort_values("roi", ascending=False).reset_index(drop=True)
    return result


def build_sensitivity_table(
    customer_segment: pd.DataFrame,
    target_segment: str = "高价值待挽回",
    coverage_rate: float = 0.70,
    gross_margin: float = 0.25,
    contact_cost: float = 0.45,
    uplift_values: Iterable[float] = (0.02, 0.05, 0.08, 0.10),
    coupon_values: Iterable[float] = (5.0, 10.0, 15.0, 20.0),
) -> pd.DataFrame:
    """输出转化提升与券成本的 ROI 敏感性矩阵（宽表）。"""
    subset = customer_segment.loc[customer_segment["segment"] == target_segment]
    if subset.empty:
        return pd.DataFrame()

    target_users = float(subset["customer_unique_id"].nunique())
    avg_aov = float(subset["avg_order_value"].mean())
    reached_users = target_users * coverage_rate

    matrix = []
    for uplift in uplift_values:
        row = {"conversion_uplift": uplift}
        incremental_orders = reached_users * uplift
        incremental_gmv = incremental_orders * avg_aov
        incremental_profit = incremental_gmv * gross_margin
        for coupon in coupon_values:
            cost = incremental_orders * coupon + reached_users * contact_cost
            row[f"coupon_{coupon:g}"] = np.nan if cost == 0 else (incremental_profit - cost) / cost
        matrix.append(row)

    return pd.DataFrame(matrix)
