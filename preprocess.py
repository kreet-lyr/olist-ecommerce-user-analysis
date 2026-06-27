"""Olist 电商数据预处理与客户数据集市构建。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import logging

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

REQUIRED_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
    "items": ["shipping_limit_date"],
}


def _read_csv(path: Path) -> pd.DataFrame:
    """兼容常见编码读取 CSV。"""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def load_raw_data(data_dir: str | Path) -> Dict[str, pd.DataFrame]:
    """读取 Olist 原始数据并完成基础类型转换。"""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"未找到数据目录：{data_dir.resolve()}")

    missing = [filename for filename in REQUIRED_FILES.values() if not (data_dir / filename).exists()]
    if missing:
        raise FileNotFoundError(
            "data 目录缺少以下文件：\n- " + "\n- ".join(missing)
        )

    tables: Dict[str, pd.DataFrame] = {}
    for name, filename in REQUIRED_FILES.items():
        file_path = data_dir / filename
        tables[name] = _read_csv(file_path)
        LOGGER.info("读取 %-12s %s 行 × %s 列", name, len(tables[name]), len(tables[name].columns))

    for table_name, columns in DATE_COLUMNS.items():
        frame = tables[table_name]
        for column in columns:
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column], errors="coerce")

    return tables


def build_data_quality_report(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """输出各原始表的行数、重复行与缺失值概览。"""
    rows = []
    for table_name, df in tables.items():
        rows.append(
            {
                "table_name": table_name,
                "rows": len(df),
                "columns": len(df.columns),
                "duplicate_rows": int(df.duplicated().sum()),
                "missing_cells": int(df.isna().sum().sum()),
                "missing_rate": round(float(df.isna().mean().mean()), 6),
            }
        )
    return pd.DataFrame(rows).sort_values("table_name").reset_index(drop=True)


def _build_item_aggregate(items: pd.DataFrame) -> pd.DataFrame:
    """将一对多订单明细聚合到订单粒度。"""
    item_agg = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            distinct_product_count=("product_id", "nunique"),
            distinct_seller_count=("seller_id", "nunique"),
            product_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
        )
    )
    item_agg["gross_value"] = item_agg["product_value"] + item_agg["freight_value"]
    item_agg["freight_share"] = np.where(
        item_agg["gross_value"] > 0,
        item_agg["freight_value"] / item_agg["gross_value"],
        np.nan,
    )
    return item_agg


def _build_payment_aggregate(payments: pd.DataFrame) -> pd.DataFrame:
    """支付表按订单聚合，避免一笔订单多次支付导致重复。"""
    return (
        payments.groupby("order_id", as_index=False)
        .agg(
            payment_value=("payment_value", "sum"),
            payment_type_count=("payment_type", "nunique"),
            max_installments=("payment_installments", "max"),
        )
    )


def _build_review_aggregate(reviews: pd.DataFrame) -> pd.DataFrame:
    """评价表按订单聚合，保留评分与评价覆盖信息。"""
    return (
        reviews.groupby("order_id", as_index=False)
        .agg(
            review_score=("review_score", "mean"),
            review_count=("review_id", "nunique"),
            review_comment_count=("review_comment_message", lambda x: int(x.notna().sum())),
        )
    )


def build_order_mart(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """构建订单粒度分析宽表。"""
    orders = tables["orders"].copy()
    customers = tables["customers"].copy()
    item_agg = _build_item_aggregate(tables["items"])
    payment_agg = _build_payment_aggregate(tables["payments"])
    review_agg = _build_review_aggregate(tables["reviews"])

    order_mart = (
        orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(item_agg, on="order_id", how="left", validate="one_to_one")
        .merge(payment_agg, on="order_id", how="left", validate="one_to_one")
        .merge(review_agg, on="order_id", how="left", validate="one_to_one")
    )

    numeric_columns = [
        "item_count",
        "distinct_product_count",
        "distinct_seller_count",
        "product_value",
        "freight_value",
        "gross_value",
        "payment_value",
        "payment_type_count",
        "max_installments",
        "review_count",
        "review_comment_count",
    ]
    for column in numeric_columns:
        if column in order_mart.columns:
            order_mart[column] = order_mart[column].fillna(0)

    order_mart["is_delivered"] = (order_mart["order_status"] == "delivered").astype(int)
    order_mart["delivery_days"] = (
        order_mart["order_delivered_customer_date"] - order_mart["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    order_mart["delivery_delay_days"] = (
        order_mart["order_delivered_customer_date"] - order_mart["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    order_mart["on_time_flag"] = np.where(
        order_mart["order_delivered_customer_date"].notna()
        & order_mart["order_estimated_delivery_date"].notna(),
        (order_mart["delivery_delay_days"] <= 0).astype(float),
        np.nan,
    )
    order_mart["purchase_month"] = order_mart["order_purchase_timestamp"].dt.to_period("M").astype(str)
    order_mart["purchase_weekday"] = order_mart["order_purchase_timestamp"].dt.day_name()
    order_mart["purchase_hour"] = order_mart["order_purchase_timestamp"].dt.hour

    return order_mart


def _weighted_experience_score(customer_mart: pd.DataFrame) -> pd.Series:
    """按可用字段动态计算体验分，避免评价缺失时将分数错误地记为 0。"""
    satisfaction_score = customer_mart["avg_review_score"] / 5 * 100
    delivery_score = customer_mart["on_time_rate"] * 100

    freight_rank = customer_mart["avg_freight_share"].rank(pct=True, ascending=True)
    freight_score = (1 - freight_rank) * 100

    components = pd.DataFrame(
        {
            "satisfaction": satisfaction_score,
            "delivery": delivery_score,
            "freight": freight_score,
        },
        index=customer_mart.index,
    )
    weights = pd.Series({"satisfaction": 0.50, "delivery": 0.30, "freight": 0.20})
    usable_weight = components.notna().mul(weights, axis=1).sum(axis=1)
    score = components.fillna(0).mul(weights, axis=1).sum(axis=1).div(usable_weight.replace(0, np.nan))
    return score.clip(lower=0, upper=100)


def build_customer_mart(order_mart: pd.DataFrame) -> pd.DataFrame:
    """构建客户粒度数据集市，仅将已送达订单计入客户价值。"""
    delivered = order_mart.loc[order_mart["is_delivered"] == 1].copy()
    if delivered.empty:
        raise ValueError("没有 status=delivered 的订单，无法计算客户价值。")

    analysis_date = delivered["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)

    customer_mart = (
        delivered.groupby("customer_unique_id", as_index=False)
        .agg(
            first_purchase_date=("order_purchase_timestamp", "min"),
            last_purchase_date=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            monetary=("gross_value", "sum"),
            avg_order_value=("gross_value", "mean"),
            avg_review_score=("review_score", "mean"),
            review_coverage=("review_score", lambda x: float(x.notna().mean())),
            on_time_rate=("on_time_flag", "mean"),
            avg_delivery_days=("delivery_days", "mean"),
            avg_delivery_delay_days=("delivery_delay_days", "mean"),
            avg_freight_share=("freight_share", "mean"),
            avg_installments=("max_installments", "mean"),
            customer_state=("customer_state", "first"),
            customer_city=("customer_city", "first"),
        )
    )

    customer_mart["recency_days"] = (
        analysis_date - customer_mart["last_purchase_date"].dt.normalize()
    ).dt.days
    customer_mart["customer_lifetime_days"] = (
        customer_mart["last_purchase_date"].dt.normalize()
        - customer_mart["first_purchase_date"].dt.normalize()
    ).dt.days
    customer_mart["experience_score"] = _weighted_experience_score(customer_mart)
    customer_mart["analysis_date"] = analysis_date

    # 为便于展示与异常检查保留精度可读性。
    decimal_columns = [
        "monetary",
        "avg_order_value",
        "avg_review_score",
        "review_coverage",
        "on_time_rate",
        "avg_delivery_days",
        "avg_delivery_delay_days",
        "avg_freight_share",
        "avg_installments",
        "experience_score",
    ]
    customer_mart[decimal_columns] = customer_mart[decimal_columns].round(4)
    return customer_mart


def build_reporting_tables(
    tables: Dict[str, pd.DataFrame], order_mart: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """构建月度、州、品类和履约体验等汇总表。"""
    delivered = order_mart.loc[order_mart["is_delivered"] == 1].copy()

    monthly = (
        delivered.groupby("purchase_month", as_index=False)
        .agg(
            delivered_orders=("order_id", "nunique"),
            active_customers=("customer_unique_id", "nunique"),
            gmv=("gross_value", "sum"),
            avg_order_value=("gross_value", "mean"),
            on_time_rate=("on_time_flag", "mean"),
            avg_review_score=("review_score", "mean"),
        )
        .sort_values("purchase_month")
    )

    state = (
        delivered.groupby("customer_state", as_index=False)
        .agg(
            delivered_orders=("order_id", "nunique"),
            active_customers=("customer_unique_id", "nunique"),
            gmv=("gross_value", "sum"),
            avg_review_score=("review_score", "mean"),
            on_time_rate=("on_time_flag", "mean"),
            avg_delivery_days=("delivery_days", "mean"),
        )
        .sort_values("gmv", ascending=False)
    )

    products = tables["products"].copy()
    translation = tables["translation"].copy()
    items = tables["items"].copy()
    delivered_orders = delivered[["order_id"]].drop_duplicates()

    product_category = products.merge(
        translation,
        on="product_category_name",
        how="left",
        validate="many_to_one",
    )
    item_category = (
        items.merge(delivered_orders, on="order_id", how="inner")
        .merge(
            product_category[["product_id", "product_category_name_english"]],
            on="product_id",
            how="left",
            validate="many_to_one",
        )
    )
    item_category["category_name"] = item_category["product_category_name_english"].fillna("unknown")
    item_category["item_gross_value"] = item_category["price"] + item_category["freight_value"]
    category = (
        item_category.groupby("category_name", as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            orders=("order_id", "nunique"),
            gmv=("item_gross_value", "sum"),
            avg_item_price=("price", "mean"),
            avg_freight_share=("freight_value", lambda x: np.nan),
        )
    )
    # 需要用分组总运费/总金额，而不是平均单项比例。
    category_base = (
        item_category.groupby("category_name", as_index=False)
        .agg(total_freight=("freight_value", "sum"), total_gross=("item_gross_value", "sum"))
    )
    category = category.drop(columns="avg_freight_share").merge(category_base, on="category_name", how="left")
    category["avg_freight_share"] = np.where(
        category["total_gross"] > 0,
        category["total_freight"] / category["total_gross"],
        np.nan,
    )
    category = category.drop(columns=["total_freight", "total_gross"]).sort_values("gmv", ascending=False)

    delivery_review = delivered[
        [
            "order_id",
            "customer_unique_id",
            "delivery_delay_days",
            "delivery_days",
            "on_time_flag",
            "review_score",
            "gross_value",
        ]
    ].copy()

    return {
        "monthly_performance": monthly,
        "state_performance": state,
        "category_performance": category,
        "delivery_review_detail": delivery_review,
    }


def prepare_data(data_dir: str | Path) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """主入口：读取数据、做质检、构建订单与客户数据集市。"""
    tables = load_raw_data(data_dir)
    quality_report = build_data_quality_report(tables)
    order_mart = build_order_mart(tables)
    customer_mart = build_customer_mart(order_mart)

    LOGGER.info("订单数据集市：%s 行；客户数据集市：%s 行", len(order_mart), len(customer_mart))
    return tables, quality_report, order_mart, customer_mart
