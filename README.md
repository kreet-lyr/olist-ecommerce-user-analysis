# Olist 电商客户价值分层、履约体验诊断与精准增长策略

> 基于 Olist 巴西电商公开数据集构建的端到端数据分析项目。
> 聚焦客户价值分层、物流履约体验、用户运营策略与营销 ROI 情景模拟。

## 项目背景

电商运营中，仅依靠订单金额或购买次数难以完整判断客户价值。高消费用户可能因为配送延迟、运费负担或服务体验下降而流失；新用户则可能具备较高复购潜力但尚未形成稳定消费行为。

本项目基于 Olist 电商平台的订单、客户、商品、支付、评价、卖家及物流相关数据，完成从数据清洗、多表建模到客户分层、体验风险识别和增长策略设计的完整分析流程。

```text
数据质量检查
→ 多表关联建模
→ 订单级与客户级数据集市
→ RFM-E 客户价值分层
→ 履约体验诊断
→ 客群运营策略
→ ROI 情景模拟
→ 可视化汇报
```

---

## 项目亮点

* **RFM-E 客户分层模型**：在传统 RFM 的基础上加入履约体验维度，综合消费价值、复购行为、评价、准时送达率和运费负担进行用户画像。
* **解决多表重复汇总问题**：订单金额统一以订单明细中的 `price + freight_value` 汇总，避免支付表一对多记录导致 GMV 重复计算。
* **履约体验风险识别**：自动标记高价值履约风险、物流体验预警、高运费负担、口碑标杆和评价覆盖不足用户。
* **可执行运营策略**：为不同客群输出业务目标、推荐动作及核心评估指标。
* **ROI 参数化模拟**：公开数据没有真实营销投放实验标签，因此采用转化提升、优惠券成本和毛利率参数构建情景模拟与敏感性分析。
* **自动化结果输出**：一键生成分析数据表、经营图表、日志、经营摘要和 Markdown 报告。

---

## 数据来源

本项目使用 Kaggle 的 **Brazilian E-Commerce Public Dataset by Olist**。

数据集下载地址：

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

下载后，将以下 CSV 文件放入项目根目录下的 `data/` 文件夹：

```text
data/
├── olist_customers_dataset.csv
├── olist_geolocation_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_orders_dataset.csv
├── olist_products_dataset.csv
├── olist_sellers_dataset.csv
└── product_category_name_translation.csv
```

> 原始数据文件未上传至仓库，请自行下载并放入 `data/` 目录。

---

## 项目结构

```text
olist-ecommerce-user-analysis/
├── data/                         # Olist 原始 CSV 数据
├── outputs/                      # 自动生成的分析结果
│   ├── data/
│   ├── figures/
│   └── reports/
│
├── main.py                       # 项目主程序，一键执行分析流程
├── preprocess.py                 # 数据读取、清洗、多表关联与数据集市构建
├── rfm.py                        # RFM 指标与客户价值评分
├── segmentation.py               # 客户分层、体验标签、运营策略
├── roi.py                        # ROI 情景模拟与敏感性分析
├── visualization.py              # 自动化静态图表生成
├── requirements.txt              # Python 依赖
├── run.bat                       # Windows 一键运行脚本
├── README.md
└── .gitignore
```

---

## 技术栈

* Python
* Pandas
* NumPy
* Matplotlib
* 数据清洗与多表关联
* RFM 客户价值分析
* 用户分层与运营策略设计
* 营销 ROI 情景模拟
* 数据可视化与自动化报告输出

---

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/kreet-lyr/olist-ecommerce-user-analysis.git
cd olist-ecommerce-user-analysis
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 放入数据集

将 Olist 数据集中的 9 个 CSV 文件放到：

```text
data/
```

### 4. 运行项目

```bash
python main.py
```

Windows 用户也可以直接双击：

```text
run.bat
```

---

## 可选运行参数

仅生成分析数据表和报告，不生成图表：

```bash
python main.py --skip-figures
```

指定数据目录：

```bash
python main.py --data-dir "D:\your_path\data"
```

指定结果输出目录：

```bash
python main.py --output-dir "D:\your_path\outputs"
```

调整 ROI 模拟中的毛利率，默认值为 `0.25`：

```bash
python main.py --gross-margin 0.30
```

---

## 核心分析口径

### 1. GMV 口径

订单 GMV 定义为：

```text
GMV = Σ(price + freight_value)
```

使用订单明细表进行汇总，而不是直接汇总支付表中的 `payment_value`，避免同一订单存在多笔支付记录时产生重复计算。

---

### 2. RFM 指标

| 指标        | 定义                  | 业务含义       |
| --------- | ------------------- | ---------- |
| Recency   | 分析基准日距离最近一次已送达订单的天数 | 越近代表近期越活跃  |
| Frequency | 已送达订单数              | 越多代表复购能力越强 |
| Monetary  | 累计消费金额              | 越高代表历史价值越高 |

R、F、M 均按照 1—5 分进行评分：

* Recency 越小，得分越高；
* Frequency 越高，得分越高；
* Monetary 越高，得分越高。

---

### 3. Experience Score：履约体验分

在传统 RFM 外，项目进一步构建用户体验分：

```text
Experience Score
= 50% × 满意度得分
+ 30% × 准时送达率
+ 20% × 运费效率分
```

其中：

| 指标    | 含义                        |
| ----- | ------------------------- |
| 满意度得分 | 基于订单评价分 `review_score` 计算 |
| 准时送达率 | 实际送达日期不晚于预计送达日期的订单占比      |
| 运费效率分 | 根据用户运费占订单总额比例的相对位置计算      |
| 评价覆盖率 | 用于识别评价信息不足的用户             |

对于评价数据缺失或覆盖率较低的客户，系统会标记为“评价覆盖不足”，而不是直接将其判定为低体验用户。

---

## 客户分层体系

| 客群     | 规则摘要         | 运营重点             |
| ------ | ------------ | ---------------- |
| 核心 VIP | R、F、M 均较高    | 会员维护、提升客单价、增强留存  |
| 高价值待挽回 | F、M 高，但近期不活跃 | 召回优惠、个性化推荐、客服关怀  |
| 高潜新客   | 最近首购且具备消费潜力  | 二单券、跨品类推荐、自动化触达  |
| 潜力复购客  | 最近活跃且已形成一定复购 | 提升购买频次与生命周期价值    |
| 高客单低频客 | 消费金额高但购买频率低  | 高端商品推荐、大额满减、服务保障 |
| 一般活跃客  | 最近仍有活跃行为     | 日常促销、积分激励、品类推荐   |
| 普通用户   | 未满足特殊客群条件    | 基础营销与行为沉淀        |
| 沉睡低价值客 | R、F、M 均低     | 低成本召回测试          |

---

## 履约体验标签

除客户价值分层外，项目会为用户自动生成体验风险标签：

| 标签      | 判定逻辑            | 业务意义              |
| ------- | --------------- | ----------------- |
| 高价值履约风险 | 高价值用户且体验分较低     | 优先处理，避免高价值客户流失    |
| 物流体验预警  | 准时率低或平均评价较低     | 需要关注配送、售后或服务体验    |
| 高运费负担   | 运费占比高于客户群体高分位阈值 | 适合包邮、运费券或满额免邮策略   |
| 口碑标杆    | 核心 VIP 且体验分较高   | 可用于会员维护、推荐激励与口碑运营 |
| 评价覆盖不足  | 评价数据缺失或覆盖率不足    | 避免基于不完整数据做错误判断    |

同时为客户分配运营优先级：

```text
P0：优先干预
P1：重点运营
P2：体验优化
P3：常规运营
```

---

## 输出结果

项目运行后会自动在 `outputs/` 目录下生成结果。

### 数据表

```text
outputs/data/
├── data_quality_report.csv
├── order_mart.csv
├── customer_segment_mart.csv
├── segment_summary.csv
├── monthly_performance.csv
├── state_performance.csv
├── category_performance.csv
├── roi_scenario_simulation.csv
└── roi_sensitivity_table.csv
```

### 图表

```text
outputs/figures/
├── 01_kpi_summary.png
├── 02_monthly_gmv_trend.png
├── 03_monthly_order_trend.png
├── 04_segment_customer_volume.png
├── 05_segment_gmv_contribution.png
├── 06_customer_pareto.png
├── 07_value_experience_scatter.png
├── 08_delivery_timeliness_review.png
├── 09_top_states_gmv.png
├── 10_top_categories_gmv.png
├── 11_roi_scenario.png
└── 12_roi_sensitivity.png
```

### 自动化报告

```text
outputs/reports/
├── executive_summary.json
└── project_report.md
```

---

## 分析图表说明

项目会自动输出以下核心可视化内容：

1. 电商经营 KPI 总览：GMV、订单量、活跃客户数、复购率、准时送达率、平均评价分。
2. 月度 GMV 与订单趋势分析。
3. 不同客户分层的人数分布与 GMV 贡献。
4. 客户累计 GMV 帕累托曲线。
5. 客户价值分与履约体验分散点图。
6. 配送时效与平均评价分关系分析。
7. Top 15 客户州 GMV 分布。
8. Top 15 商品品类 GMV 分布。
9. 分客群营销 ROI 情景模拟。
10. 转化提升幅度与优惠券成本的 ROI 敏感性热力图。

---

## ROI 情景模拟说明

Olist 公开数据中不包含真实投放预算、实验组、对照组和营销转化标签，因此本项目中的 ROI 结果属于参数化情景模拟，而非真实投放收益。

计算逻辑如下：

```text
增量订单数
= 目标用户数 × 转化提升幅度

增量 GMV
= 增量订单数 × 平均客单价

增量毛利
= 增量 GMV × 毛利率

ROI
= (增量毛利 - 营销成本) / 营销成本
```

该部分主要用于帮助运营人员比较不同客群、不同优惠券成本和不同转化提升假设下的策略优先级。

---

## 项目结论使用边界

本项目遵循以下分析原则：

* 物流时效与评价分之间的结果仅代表统计关联，不直接说明因果关系。
* ROI 结果为情景模拟，不能表述为真实投放提升效果。
* 公开数据不包含浏览、点击、广告曝光等行为数据，因此项目重点分析交易、履约和评价维度。
* 用户分层规则可以结合企业实际业务目标、利润率和运营资源进一步调整。

---

## 简历项目描述参考

> **Olist 电商客户价值分层与精准增长策略分析｜Python、Pandas、Matplotlib**
> 基于 Olist 电商订单、客户、支付、评价、商品及物流多表数据，构建订单级和客户级分析数据集市，完成数据质量检查、交易金额口径统一及客户价值分析。
> 设计 RFM-E 客户分层模型，将消费价值、复购频次、评价满意度、准时送达率和运费负担纳入用户画像，识别核心 VIP、高价值待挽回、高潜新客及高价值履约风险用户。
> 自动生成经营 KPI、用户分层贡献、履约体验、品类表现和 ROI 敏感性分析图表，并输出分客群运营策略，为召回、二购激励和运费补贴决策提供量化依据。

---

## 后续优化方向

* 引入 Cohort 留存分析，观察不同首购月份用户的长期留存差异。
* 基于商品类别构建关联购买推荐策略。
* 增加卖家维度的履约质量排名与风险预警。
* 引入机器学习模型预测用户复购概率或流失风险。
* 使用 Streamlit 或 Power BI 搭建交互式经营仪表盘。
* 接入真实营销活动数据，使用 A/B 测试验证 ROI 模型。

---

## License

本项目采用仓库中的 License 协议，仅用于学习、作品集展示和数据分析实践。

## Author

GitHub: [kreet-lyr](https://github.com/kreet-lyr)
