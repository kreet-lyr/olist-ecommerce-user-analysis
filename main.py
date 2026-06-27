"""Olist 电商客户价值分层与精准增长策略项目主程序。"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from preprocess import build_reporting_tables, prepare_data
from rfm import calculate_rfm_scores
from roi import build_roi_scenarios, build_sensitivity_table
from segmentation import apply_segmentation, build_segment_summary
from visualization import generate_all_figures

PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Olist 电商客户价值分层、履约体验诊断与精准增长策略分析"
    )
    parser.add_argument(
        "--data-dir",
        default=str(PROJECT_ROOT / "data"),
        help="Olist CSV 数据目录，默认：项目根目录/data",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs"),
        help="结果输出目录，默认：项目根目录/outputs",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="只生成数据表和报告，不生成 PNG 图表",
    )
    parser.add_argument(
        "--gross-margin",
        type=float,
        default=0.25,
        help="ROI 情景模拟毛利率，默认 0.25",
    )
    return parser.parse_args()


def configure_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(output_dir / "pipeline.log", encoding="utf-8"),
        ],
    )


def _save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _safe_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 4)


def build_executive_summary(
    order_mart: pd.DataFrame,
    customer_segment: pd.DataFrame,
    segment_summary: pd.DataFrame,
    roi_table: pd.DataFrame,
) -> dict[str, Any]:
    """生成适合 README、汇报和面试讲述的经营摘要。"""
    delivered = order_mart.loc[order_mart["is_delivered"] == 1].copy()
    vip = segment_summary.loc[segment_summary["segment"] == "核心VIP"]
    risk = customer_segment.loc[
        customer_segment["experience_tag"].str.contains("高价值履约风险", na=False)
    ]
    late = delivered.loc[delivered["delivery_delay_days"] > 0, "review_score"].mean()
    ontime = delivered.loc[delivered["delivery_delay_days"] <= 0, "review_score"].mean()
    best_roi = roi_table.iloc[0].to_dict() if not roi_table.empty else {}

    summary = {
        "project_name": "Olist 电商客户价值分层、履约体验诊断与精准增长策略",
        "delivered_orders": int(delivered["order_id"].nunique()),
        "active_customers": int(customer_segment["customer_unique_id"].nunique()),
        "delivered_gmv_brl": round(float(delivered["gross_value"].sum()), 2),
        "average_order_value_brl": round(float(delivered["gross_value"].mean()), 2),
        "repeat_purchase_rate": _safe_float((customer_segment["frequency"] >= 2).mean()),
        "on_time_delivery_rate": _safe_float(delivered["on_time_flag"].mean()),
        "average_review_score": _safe_float(delivered["review_score"].mean()),
        "core_vip_customer_count": int(vip["customers"].sum()) if not vip.empty else 0,
        "core_vip_gmv_share": _safe_float(vip["gmv_share"].sum()) if not vip.empty else 0,
        "high_value_experience_risk_customers": int(risk["customer_unique_id"].nunique()),
        "late_order_avg_review_score": _safe_float(late),
        "on_time_order_avg_review_score": _safe_float(ontime),
        "best_roi_scenario": {
            "segment": best_roi.get("segment"),
            "campaign": best_roi.get("campaign"),
            "roi": _safe_float(best_roi.get("roi")),
            "incremental_gmv": _safe_float(best_roi.get("incremental_gmv")),
        },
        "important_note": "ROI 为基于公开数据的参数化情景模拟，不代表真实投放效果。",
    }
    return summary


def write_markdown_report(summary: dict[str, Any], segment_summary: pd.DataFrame, report_path: Path) -> None:
    """输出一份可直接用于项目汇报的简版 Markdown 报告。"""
    rows = []
    for _, row in segment_summary.iterrows():
        rows.append(
            f"| {row['segment']} | {int(row['customers']):,} | {row['customer_share']:.1%} | "
            f"R$ {row['gmv']:,.0f} | {row['gmv_share']:.1%} | {row['avg_experience_score']:.1f} |"
        )

    best = summary["best_roi_scenario"]
    late_review = summary["late_order_avg_review_score"]
    ontime_review = summary["on_time_order_avg_review_score"]
    late_review_text = "N/A" if late_review is None else f"{late_review:.2f} / 5"
    ontime_review_text = "N/A" if ontime_review is None else f"{ontime_review:.2f} / 5"
    best_roi = best.get("roi")
    best_gmv = best.get("incremental_gmv")
    best_roi_text = "N/A" if best_roi is None else f"{best_roi:.1%}"
    best_gmv_text = "N/A" if best_gmv is None else f"R$ {best_gmv:,.2f}"
    content = f"""# Olist 电商客户价值分层与精准增长策略分析报告

## 1. 项目定位

本项目基于 Olist 电商多表数据，构建订单级与客户级数据集市，完成 RFM-E 客户价值分层、物流履约体验诊断、分层运营策略与营销 ROI 情景模拟。

## 2. 核心经营指标

- 已送达订单数：**{summary['delivered_orders']:,}**
- 活跃客户数：**{summary['active_customers']:,}**
- 已送达 GMV：**R$ {summary['delivered_gmv_brl']:,.2f}**
- 平均客单价：**R$ {summary['average_order_value_brl']:,.2f}**
- 复购率：**{summary['repeat_purchase_rate']:.1%}**
- 准时送达率：**{summary['on_time_delivery_rate']:.1%}**
- 平均评价分：**{summary['average_review_score']:.2f} / 5**

## 3. 客户分层画像

| 客群 | 客户数 | 客户占比 | GMV | GMV 占比 | 平均体验分 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## 4. 履约体验观察

- 高价值履约风险客户数：**{summary['high_value_experience_risk_customers']:,}**
- 延迟订单平均评价：**{late_review_text}**
- 准时/提前订单平均评价：**{ontime_review_text}**

该结果仅描述统计关联，不直接宣称物流延迟是低评分的因果原因。

## 5. ROI 情景模拟

当前参数下 ROI 最高的策略为：**{best.get('segment')}｜{best.get('campaign')}**，
模拟 ROI 为 **{best_roi_text}**，预计增量 GMV 为 **{best_gmv_text}**。

> {summary['important_note']}

## 6. 项目技术亮点

1. 构建订单级、客户级和品类/区域级分析宽表，解决多表一对多汇总中的重复计算问题。
2. 在传统 RFM 中加入体验维度（评价、准时率、运费负担），形成 RFM-E 客户分层体系。
3. 输出面向运营的客群优先级、策略动作与可量化评估指标。
4. 针对公开数据缺少真实投放标签的限制，采用参数化 ROI 模拟并提供敏感性分析。
"""
    report_path.write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)
    configure_logging(output_dir)
    logger = logging.getLogger("main")

    output_data_dir = output_dir / "data"
    figure_dir = output_dir / "figures"
    report_dir = output_dir / "reports"

    logger.info("开始执行 Olist 全流程分析")
    logger.info("数据目录：%s", data_dir.resolve())
    logger.info("输出目录：%s", output_dir.resolve())

    tables, quality_report, order_mart, customer_mart = prepare_data(data_dir)
    customer_rfm = calculate_rfm_scores(customer_mart)
    customer_segment = apply_segmentation(customer_rfm)
    segment_summary = build_segment_summary(customer_segment)
    reporting_tables = build_reporting_tables(tables, order_mart)
    roi_table = build_roi_scenarios(customer_segment, gross_margin=args.gross_margin)
    sensitivity_target = "高价值待挽回"
    if sensitivity_target not in set(customer_segment["segment"]):
        sensitivity_target = "核心VIP" if "核心VIP" in set(customer_segment["segment"]) else customer_segment["segment"].iloc[0]
    sensitivity = build_sensitivity_table(customer_segment, target_segment=sensitivity_target)

    _save_csv(quality_report, output_data_dir / "data_quality_report.csv")
    _save_csv(order_mart, output_data_dir / "order_mart.csv")
    _save_csv(customer_segment, output_data_dir / "customer_segment_mart.csv")
    _save_csv(segment_summary, output_data_dir / "segment_summary.csv")
    _save_csv(roi_table, output_data_dir / "roi_scenario_simulation.csv")
    _save_csv(sensitivity, output_data_dir / "roi_sensitivity_table.csv")
    for name, table in reporting_tables.items():
        _save_csv(table, output_data_dir / f"{name}.csv")

    summary = build_executive_summary(order_mart, customer_segment, segment_summary, roi_table)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "executive_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_markdown_report(summary, segment_summary, report_dir / "project_report.md")

    if not args.skip_figures:
        logger.info("开始生成图表")
        generate_all_figures(
            customer_segment=customer_segment,
            order_mart=order_mart,
            reporting_tables=reporting_tables,
            segment_summary=segment_summary,
            roi_table=roi_table,
            sensitivity=sensitivity,
            output_dir=figure_dir,
        )

    logger.info("分析完成。关键结果：")
    logger.info("已送达订单数：%s", f"{summary['delivered_orders']:,}")
    logger.info("活跃客户数：%s", f"{summary['active_customers']:,}")
    logger.info("已送达 GMV：R$ %s", f"{summary['delivered_gmv_brl']:,.2f}")
    logger.info("复购率：%.2f%%", summary["repeat_purchase_rate"] * 100)
    logger.info("结果目录：%s", output_dir.resolve())


if __name__ == "__main__":
    main()
