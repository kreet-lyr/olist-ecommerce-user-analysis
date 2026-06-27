"""RFM-E 客户分层、体验风险标签与策略建议。"""
from __future__ import annotations

import numpy as np
import pandas as pd

SEGMENT_STRATEGY = {
    "核心VIP": {
        "business_goal": "维持高价值客户关系并提升客单价",
        "recommended_action": "会员权益、专属客服、提前购与高毛利关联推荐",
        "primary_metric": "90天复购率、客单价、VIP留存率",
    },
    "高价值待挽回": {
        "business_goal": "召回曾高消费、高频但近期不活跃客户",
        "recommended_action": "限时召回券、个性化选品、客服关怀",
        "primary_metric": "30天回购率、增量GMV、召回ROI",
    },
    "高潜新客": {
        "business_goal": "推动首购用户完成第二次购买",
        "recommended_action": "二单券、跨品类搭配推荐、购买后自动化触达",
        "primary_metric": "二购转化率、首次复购间隔",
    },
    "潜力复购客": {
        "business_goal": "提升复购频率与生命周期价值",
        "recommended_action": "阶梯满减、订阅补货提醒、积分任务",
        "primary_metric": "复购率、订单频次、CLV",
    },
    "高客单低频客": {
        "business_goal": "提升高消费能力用户的购买频次",
        "recommended_action": "高端商品定向推荐、服务保障与大额满减",
        "primary_metric": "复购间隔、复购客单价",
    },
    "一般活跃客": {
        "business_goal": "保持活跃并向高价值层转化",
        "recommended_action": "日常促销、浏览品类推荐、积分激励",
        "primary_metric": "月活跃购买客户、客单价",
    },
    "沉睡低价值客": {
        "business_goal": "低成本验证是否具备重新激活价值",
        "recommended_action": "低成本邮件触达、轻量优惠、再营销人群测试",
        "primary_metric": "低成本回流率、触达成本",
    },
    "普通用户": {
        "business_goal": "沉淀行为数据并识别价值提升机会",
        "recommended_action": "基础优惠、品类偏好收集、下次购提醒",
        "primary_metric": "活跃率、转化率",
    },
}


def _assign_segment(row: pd.Series) -> str:
    r, f, m = int(row["r_score"]), int(row["f_score"]), int(row["m_score"])
    frequency = float(row["frequency"])

    if r >= 4 and f >= 4 and m >= 4:
        return "核心VIP"
    if r <= 2 and f >= 4 and m >= 4:
        return "高价值待挽回"
    if r >= 4 and frequency <= 1 and m >= 3:
        return "高潜新客"
    if r >= 4 and f >= 3 and m >= 3:
        return "潜力复购客"
    if m >= 4 and f <= 2:
        return "高客单低频客"
    if r <= 2 and f <= 2 and m <= 2:
        return "沉睡低价值客"
    if r >= 3:
        return "一般活跃客"
    return "普通用户"


def _build_experience_tag(row: pd.Series, freight_threshold: float) -> str:
    tags: list[str] = []
    high_value = row["segment"] in {"核心VIP", "高价值待挽回", "高客单低频客"}

    if pd.isna(row["avg_review_score"]) or row["review_coverage"] < 0.20:
        tags.append("评价覆盖不足")
    if pd.notna(row["experience_score"]) and row["experience_score"] < 40 and high_value:
        tags.append("高价值履约风险")
    if (
        (pd.notna(row["on_time_rate"]) and row["on_time_rate"] < 0.75)
        or (pd.notna(row["avg_review_score"]) and row["avg_review_score"] < 3.5)
    ):
        tags.append("物流体验预警")
    if pd.notna(row["avg_freight_share"]) and row["avg_freight_share"] >= freight_threshold:
        tags.append("高运费负担")
    if row["segment"] == "核心VIP" and pd.notna(row["experience_score"]) and row["experience_score"] >= 80:
        tags.append("口碑标杆")

    return "｜".join(tags) if tags else "体验稳定"


def _priority(row: pd.Series) -> str:
    tag = row["experience_tag"]
    if "高价值履约风险" in tag or row["segment"] == "高价值待挽回":
        return "P0-优先干预"
    if row["segment"] in {"核心VIP", "高潜新客", "潜力复购客"}:
        return "P1-重点运营"
    if "高运费负担" in tag or "物流体验预警" in tag:
        return "P2-体验优化"
    return "P3-常规运营"


def apply_segmentation(rfm_customer_mart: pd.DataFrame) -> pd.DataFrame:
    """在 RFM 客户表上增加细分、人群标签、策略与优先级。"""
    df = rfm_customer_mart.copy()
    df["segment"] = df.apply(_assign_segment, axis=1)

    freight_threshold = df["avg_freight_share"].quantile(0.75)
    df["experience_tag"] = df.apply(_build_experience_tag, axis=1, freight_threshold=freight_threshold)
    df["priority"] = df.apply(_priority, axis=1)
    df["business_goal"] = df["segment"].map(lambda x: SEGMENT_STRATEGY[x]["business_goal"])
    df["recommended_action"] = df["segment"].map(lambda x: SEGMENT_STRATEGY[x]["recommended_action"])
    df["primary_metric"] = df["segment"].map(lambda x: SEGMENT_STRATEGY[x]["primary_metric"])

    value_order = [
        "核心VIP",
        "高价值待挽回",
        "潜力复购客",
        "高潜新客",
        "高客单低频客",
        "一般活跃客",
        "普通用户",
        "沉睡低价值客",
    ]
    df["segment_rank"] = pd.Categorical(df["segment"], categories=value_order, ordered=True).codes + 1
    return df


def build_segment_summary(customer_segment: pd.DataFrame) -> pd.DataFrame:
    """输出人群规模、GMV、体验与复购等分层画像。"""
    summary = (
        customer_segment.groupby("segment", as_index=False)
        .agg(
            customers=("customer_unique_id", "nunique"),
            gmv=("monetary", "sum"),
            avg_order_value=("avg_order_value", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_value_score=("customer_value_score", "mean"),
            avg_experience_score=("experience_score", "mean"),
            avg_review_score=("avg_review_score", "mean"),
            on_time_rate=("on_time_rate", "mean"),
        )
    )
    summary["customer_share"] = summary["customers"] / summary["customers"].sum()
    summary["gmv_share"] = summary["gmv"] / summary["gmv"].sum()
    return summary.sort_values("gmv", ascending=False).reset_index(drop=True)
