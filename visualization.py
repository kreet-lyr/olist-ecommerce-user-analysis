"""项目图表输出。所有图表写入 outputs/figures，不依赖图形界面。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


def _configure_font() -> None:
    """优先选择 Windows 常见中文字体；不存在时保持 Matplotlib 默认字体。"""
    available = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"):
        if font_name in available:
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False


_configure_font()


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_kpi_summary(customer_segment: pd.DataFrame, order_mart: pd.DataFrame, output_dir: Path) -> None:
    delivered = order_mart.loc[order_mart["is_delivered"] == 1]
    total_gmv = delivered["gross_value"].sum()
    total_orders = delivered["order_id"].nunique()
    customers = customer_segment["customer_unique_id"].nunique()
    repeat_rate = (customer_segment["frequency"] >= 2).mean()
    on_time_rate = delivered["on_time_flag"].mean()
    review_score = delivered["review_score"].mean()

    kpis = [
        ("Delivered GMV", f"R$ {total_gmv:,.0f}"),
        ("Delivered Orders", f"{total_orders:,}"),
        ("Active Customers", f"{customers:,}"),
        ("Repeat Purchase Rate", f"{repeat_rate:.1%}"),
        ("On-time Delivery Rate", f"{on_time_rate:.1%}"),
        ("Average Review Score", f"{review_score:.2f} / 5"),
    ]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    for idx, (label, value) in enumerate(kpis):
        row, col = divmod(idx, 3)
        x, y = 0.18 + col * 0.33, 0.72 - row * 0.43
        ax.text(x, y + 0.10, label, ha="center", va="center", fontsize=12)
        ax.text(x, y, value, ha="center", va="center", fontsize=20, fontweight="bold")
        ax.axhline(y - 0.12, xmin=col / 3 + 0.03, xmax=(col + 1) / 3 - 0.03, linewidth=1)
    ax.set_title("Olist Ecommerce Executive KPI Summary", fontsize=17, pad=20)
    _save(fig, output_dir / "01_kpi_summary.png")


def plot_monthly_performance(monthly: pd.DataFrame, output_dir: Path) -> None:
    data = monthly.copy()
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(data["purchase_month"], data["gmv"], marker="o")
    ax.set_title("Monthly Delivered GMV Trend")
    ax.set_xlabel("Purchase Month")
    ax.set_ylabel("GMV (R$)")
    ax.tick_params(axis="x", rotation=45)
    _save(fig, output_dir / "02_monthly_gmv_trend.png")

    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(data["purchase_month"], data["delivered_orders"], marker="o")
    ax.set_title("Monthly Delivered Orders Trend")
    ax.set_xlabel("Purchase Month")
    ax.set_ylabel("Orders")
    ax.tick_params(axis="x", rotation=45)
    _save(fig, output_dir / "03_monthly_order_trend.png")


def plot_segment_summary(segment_summary: pd.DataFrame, output_dir: Path) -> None:
    data = segment_summary.sort_values("customers", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(data["segment"], data["customers"])
    ax.set_title("Customer Volume by Segment")
    ax.set_xlabel("Customers")
    ax.set_ylabel("Segment")
    _save(fig, output_dir / "04_segment_customer_volume.png")

    data = segment_summary.sort_values("gmv", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(data["segment"], data["gmv"])
    ax.set_title("Delivered GMV Contribution by Segment")
    ax.set_xlabel("GMV (R$)")
    ax.set_ylabel("Segment")
    _save(fig, output_dir / "05_segment_gmv_contribution.png")


def plot_pareto(customer_segment: pd.DataFrame, output_dir: Path) -> None:
    data = customer_segment.sort_values("monetary", ascending=False).reset_index(drop=True).copy()
    data["cum_gmv_share"] = data["monetary"].cumsum() / data["monetary"].sum()
    data["customer_share"] = (data.index + 1) / len(data)
    sample = data.iloc[::max(1, len(data) // 1000)]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(sample["customer_share"], sample["cum_gmv_share"])
    ax.axvline(0.20, linestyle="--")
    ax.axhline(float(data.loc[(data["customer_share"] - 0.20).abs().idxmin(), "cum_gmv_share"]), linestyle="--")
    ax.set_title("Customer GMV Pareto Curve")
    ax.set_xlabel("Cumulative Customer Share")
    ax.set_ylabel("Cumulative GMV Share")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _save(fig, output_dir / "06_customer_pareto.png")


def plot_value_experience(customer_segment: pd.DataFrame, output_dir: Path) -> None:
    data = customer_segment.dropna(subset=["customer_value_score", "experience_score"])
    sample_size = min(len(data), 12000)
    sample = data.sample(sample_size, random_state=42) if len(data) > sample_size else data
    size = np.clip(np.sqrt(sample["monetary"].clip(lower=0)) * 1.5, 5, 90)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.scatter(sample["customer_value_score"], sample["experience_score"], s=size, alpha=0.35)
    ax.axhline(40, linestyle="--")
    ax.axvline(70, linestyle="--")
    ax.set_title("Customer Value vs. Experience Score")
    ax.set_xlabel("Customer Value Score (RFM)")
    ax.set_ylabel("Experience Score")
    _save(fig, output_dir / "07_value_experience_scatter.png")


def plot_delivery_review(delivery_review: pd.DataFrame, output_dir: Path) -> None:
    data = delivery_review.dropna(subset=["delivery_delay_days", "review_score"]).copy()
    if data.empty:
        return
    bins = [-np.inf, -3, 0, 3, 7, np.inf]
    labels = ["Early >3d", "Early/On-time", "Late 1-3d", "Late 4-7d", "Late >7d"]
    data["delivery_group"] = pd.cut(data["delivery_delay_days"], bins=bins, labels=labels)
    plot_data = data.groupby("delivery_group", observed=False)["review_score"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(plot_data["delivery_group"].astype(str), plot_data["review_score"])
    ax.set_title("Average Review Score by Delivery Timeliness")
    ax.set_xlabel("Delivery Timeliness")
    ax.set_ylabel("Average Review Score")
    ax.set_ylim(0, 5)
    ax.tick_params(axis="x", rotation=20)
    _save(fig, output_dir / "08_delivery_timeliness_review.png")


def plot_state_performance(state: pd.DataFrame, output_dir: Path) -> None:
    data = state.head(15).sort_values("gmv", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.barh(data["customer_state"], data["gmv"])
    ax.set_title("Top 15 States by Delivered GMV")
    ax.set_xlabel("GMV (R$)")
    ax.set_ylabel("Customer State")
    _save(fig, output_dir / "09_top_states_gmv.png")


def plot_category_performance(category: pd.DataFrame, output_dir: Path) -> None:
    data = category.head(15).sort_values("gmv", ascending=True)
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(data["category_name"], data["gmv"])
    ax.set_title("Top 15 Product Categories by Delivered GMV")
    ax.set_xlabel("GMV (R$)")
    ax.set_ylabel("Product Category")
    _save(fig, output_dir / "10_top_categories_gmv.png")


def plot_roi(roi_table: pd.DataFrame, output_dir: Path) -> None:
    if roi_table.empty:
        return
    data = roi_table.sort_values("roi", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(data["segment"], data["roi"])
    ax.axvline(0, linewidth=1)
    ax.set_title("Campaign ROI Scenario Simulation")
    ax.set_xlabel("ROI")
    ax.set_ylabel("Target Segment")
    _save(fig, output_dir / "11_roi_scenario.png")


def plot_sensitivity(sensitivity: pd.DataFrame, output_dir: Path) -> None:
    if sensitivity.empty:
        return
    value_cols = [col for col in sensitivity.columns if col.startswith("coupon_")]
    values = sensitivity[value_cols].to_numpy()

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    image = ax.imshow(values, aspect="auto")
    ax.set_title("ROI Sensitivity: Conversion Uplift vs Coupon Cost")
    ax.set_xlabel("Coupon Cost (R$)")
    ax.set_ylabel("Conversion Uplift")
    ax.set_xticks(np.arange(len(value_cols)), [col.replace("coupon_", "") for col in value_cols])
    ax.set_yticks(np.arange(len(sensitivity)), [f"{x:.0%}" for x in sensitivity["conversion_uplift"]])
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, f"{values[i, j]:.1%}", ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=ax, label="ROI")
    _save(fig, output_dir / "12_roi_sensitivity.png")


def generate_all_figures(
    customer_segment: pd.DataFrame,
    order_mart: pd.DataFrame,
    reporting_tables: Dict[str, pd.DataFrame],
    segment_summary: pd.DataFrame,
    roi_table: pd.DataFrame,
    sensitivity: pd.DataFrame,
    output_dir: str | Path,
) -> None:
    """统一生成全部静态图表。"""
    output_dir = Path(output_dir)
    plot_kpi_summary(customer_segment, order_mart, output_dir)
    plot_monthly_performance(reporting_tables["monthly_performance"], output_dir)
    plot_segment_summary(segment_summary, output_dir)
    plot_pareto(customer_segment, output_dir)
    plot_value_experience(customer_segment, output_dir)
    plot_delivery_review(reporting_tables["delivery_review_detail"], output_dir)
    plot_state_performance(reporting_tables["state_performance"], output_dir)
    plot_category_performance(reporting_tables["category_performance"], output_dir)
    plot_roi(roi_table, output_dir)
    plot_sensitivity(sensitivity, output_dir)
