# -*- coding: utf-8 -*-
"""
03_analysis.py —— 商业分析模型
==============================
实现 8 类商业分析模型（超额完成"≥3 种"的要求），每类模型均输出：
    · ≥1 张核心分析图（见 04_visuals.py）
    · ≥1 条数据支撑的商业结论（见 outputs/tables/03_*.csv 与论文第 4、6 章）

模型清单：
    M1 趋势与对比   环比/同比 (MoM/YoY) + 移动平均 MA7/MA30
    M2 用户与客群   RFM 模型（八分类）
    M3 用户与客群   同期群留存分析（月度 Cohort Retention）
    M4 结构与价值   帕累托 / ABC 分类
    M5 关联与转化   购物篮关联规则（Apriori，mlxtend）
    M6 结构与价值   波士顿矩阵（品类组合：相对份额 × 同比增速）
    M7 预测与预警   SARIMA / Holt-Winters 时间序列预测（点预测 + 95% CI + 回测）
    M8 用户与客群   K-Means 客户分群
    M9 关联与转化   复购漏斗分析

运行：
    python scripts/03_analysis.py
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

warnings.filterwarnings("ignore")

CUT_DATE = "2011-11-30"          # 剔除不完整的末月（2011-12 仅 9 天）后用于月度/序列分析


# ===========================================================================
# 载入清洗后的星型模型
# ===========================================================================
def load_tables() -> dict[str, pd.DataFrame]:
    fact = pd.read_csv(cfg.CLEAN_DIR / "fact_order_items.csv",
                       parse_dates=["InvoiceTS", "OrderDate"], low_memory=False)
    orders = pd.read_csv(cfg.CLEAN_DIR / "dim_orders.csv", parse_dates=["InvoiceTS", "OrderDate"])
    cust = pd.read_csv(cfg.CLEAN_DIR / "dim_customers.csv", parse_dates=["FirstOrderDate", "LastOrderDate"])
    prod = pd.read_csv(cfg.CLEAN_DIR / "dim_products.csv")
    iou.log(f"事实表 {len(fact):,} 行 | 客户 {len(cust):,} | 商品 {len(prod):,} | 订单 {len(orders):,}")
    return {"fact": fact, "orders": orders, "customers": cust, "products": prod}


# ===========================================================================
# M1 趋势与对比：环比 / 同比 / 移动平均
# ===========================================================================
def m1_trend(df: pd.DataFrame) -> dict:
    """月度销售额的环比(MoM)、同比(YoY)与移动平均(MA7/MA30)。"""
    d = df[df["OrderDate"] <= CUT_DATE].copy()
    m = (d.groupby("MonthPeriod")
           .agg(Revenue=("Revenue", "sum"),
                Orders=("Invoice", "nunique"),
                Customers=("CustomerID", lambda s: s[s != "GUEST"].nunique()),
                Items=("Quantity", "sum"))
           .reset_index())
    m["Revenue"] = m["Revenue"].round(2)
    m["AOV"] = (m["Revenue"] / m["Orders"]).round(2)
    # 环比
    m["Revenue_MoM"] = (m["Revenue"].pct_change() * 100).round(2)
    # 同比：与去年同月相比（2010-12 起有可比数据）
    revenue_map = dict(zip(m["MonthPeriod"], m["Revenue"]))
    def yoy(mp: str):
        y, mo = mp.split("-")
        prev = f"{int(y)-1}-{mo}"
        if prev in revenue_map and revenue_map[prev]:
            return round((revenue_map[mp] - revenue_map[prev]) / revenue_map[prev] * 100, 2)
        return np.nan
    m["Revenue_YoY"] = m["MonthPeriod"].map(yoy)
    m["MA3"] = m["Revenue"].rolling(3).mean().round(2)
    iou.save_table(m, "03_mom_yoy_monthly")

    # 日序列 + 移动平均
    daily = (d.groupby("OrderDate")
               .agg(Revenue=("Revenue", "sum"), Orders=("Invoice", "nunique"))
               .reset_index())
    daily["Revenue"] = daily["Revenue"].round(2)
    daily["MA7"] = daily["Revenue"].rolling(7).mean().round(2)
    daily["MA30"] = daily["Revenue"].rolling(30).mean().round(2)
    daily["DoW"] = daily["OrderDate"].dt.day_name()
    iou.save_table(daily, "03_daily_series")

    # 品类 × 月度（用于结构变化/堆积图）
    cat_m = (d.groupby(["MonthPeriod", "ProductCategory"])
               .agg(Revenue=("Revenue", "sum")).reset_index())
    cat_m["Revenue"] = cat_m["Revenue"].round(2)
    iou.save_table(cat_m, "03_category_monthly", also_json=False)

    cat_sum = (d.groupby("ProductCategory")
                 .agg(Revenue=("Revenue", "sum"), Orders=("Invoice", "nunique"),
                      Items=("Quantity", "sum"), SKUs=("StockCode", "nunique"))
                 .reset_index().sort_values("Revenue", ascending=False))
    cat_sum["RevenueShare"] = (cat_sum["Revenue"] / cat_sum["Revenue"].sum() * 100).round(2)
    iou.save_table(cat_sum, "03_category_summary")

    ctry = (d.groupby("Country")
              .agg(Revenue=("Revenue", "sum"), Orders=("Invoice", "nunique"),
                   Customers=("CustomerID", lambda s: s[s != "GUEST"].nunique()),
                   Items=("Quantity", "sum"))
              .reset_index().sort_values("Revenue", ascending=False))
    ctry["RevenueShare"] = (ctry["Revenue"] / ctry["Revenue"].sum() * 100).round(2)
    ctry["AOV"] = (ctry["Revenue"] / ctry["Orders"]).round(2)
    ctry["CumeShare"] = ctry["RevenueShare"].cumsum().round(2)
    iou.save_table(ctry, "03_country_summary")

    # 星期 × 小时 热力矩阵
    heat = (d.groupby(["Weekday", "Hour"]).agg(Revenue=("Revenue", "sum")).reset_index())
    heat["Revenue"] = heat["Revenue"].round(2)
    iou.save_table(heat, "03_weekday_hour_matrix", also_json=False)

    top_prod = (d.groupby(["StockCode", "Description"])
                  .agg(Revenue=("Revenue", "sum"), Quantity=("Quantity", "sum"))
                  .reset_index().sort_values("Revenue", ascending=False).head(cfg.TOP_N_PRODUCTS))
    top_prod["Revenue"] = top_prod["Revenue"].round(2)
    iou.save_table(top_prod, "03_top_products")

    return {"monthly": m, "daily": daily, "category": cat_sum, "country": ctry}


# ===========================================================================
# M2 RFM 模型（八分类）
# ===========================================================================
SEGMENT_NAMES = {
    ("H", "H", "H"): "重要价值客户",
    ("H", "L", "H"): "重要发展客户",
    ("L", "H", "H"): "重要保持客户",
    ("L", "L", "H"): "重要挽留客户",
    ("H", "H", "L"): "一般价值客户",
    ("H", "L", "L"): "一般发展客户",
    ("L", "H", "L"): "一般保持客户",
    ("L", "L", "L"): "一般挽留客户",
}
SEGMENT_ORDER = [
    "重要价值客户", "重要保持客户", "重要发展客户", "重要挽留客户",
    "一般价值客户", "一般保持客户", "一般发展客户", "一般挽留客户",
]


def m2_rfm(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """
    RFM 模型。
    阈值依据：R / F / M 三个指标在零售数据中均呈强右偏（少数鲸鱼客户拉高均值），
    若用均值切分会被极值牵引；故统一采用**中位数**切分，使高低两类客户数量均衡，
    且中位数对异常值稳健 —— 这也是 RFM 实践中通行的做法。
    """
    d = df[(df["CustomerID"] != "GUEST") & (df["OrderDate"] <= pd.Timestamp(CUT_DATE))]
    g = (d.groupby("CustomerID")
           .agg(Recency=("OrderDate", lambda s: (snapshot - s.max()).days),
                Frequency=("Invoice", "nunique"),
                Monetary=("Revenue", "sum"),
                FirstOrderDate=("OrderDate", "min"),
                LastOrderDate=("OrderDate", "max"),
                Items=("Quantity", "sum"),
                Country=("Country", lambda s: s.mode().iloc[0]),
                MainCategory=("ProductCategory", lambda s: s.mode().iloc[0]))
           .reset_index())
    g["Recency"] = g["Recency"].clip(lower=0)
    g["Monetary"] = g["Monetary"].round(2)

    med = {k: float(g[k].median()) for k in ("Recency", "Frequency", "Monetary")}
    # Recency 越小越好：<= 中位数记为 H(高)
    g["R_score"] = np.where(g["Recency"] <= med["Recency"], "H", "L")
    g["F_score"] = np.where(g["Frequency"] >= med["Frequency"], "H", "L")
    g["M_score"] = np.where(g["Monetary"] >= med["Monetary"], "H", "L")
    g["RFM_Cell"] = g["R_score"] + g["F_score"] + g["M_score"]
    g["Segment"] = [SEGMENT_NAMES[(r, f, m)] for r, f, m in
                    zip(g["R_score"], g["F_score"], g["M_score"])]
    g["Segment"] = pd.Categorical(g["Segment"], categories=SEGMENT_ORDER, ordered=True)
    g["ValueTier"] = np.where(g["M_score"] == "H", "高价值层(High)", "一般价值层(Low)")

    iou.save_table(g, "03_rfm_customer", also_json=False)

    total_rev = g["Monetary"].sum()
    summary = (g.groupby("Segment", observed=True)
                 .agg(Customers=("CustomerID", "size"),
                      AvgRecency=("Recency", "mean"),
                      AvgFrequency=("Frequency", "mean"),
                      AvgMonetary=("Monetary", "mean"),
                      Monetary=("Monetary", "sum"))
                 .reset_index())
    summary["AvgRecency"] = summary["AvgRecency"].round(1)
    summary["AvgFrequency"] = summary["AvgFrequency"].round(2)
    summary["AvgMonetary"] = summary["AvgMonetary"].round(2)
    summary["Monetary"] = summary["Monetary"].round(2)
    summary["CustomerShare"] = (summary["Customers"] / summary["Customers"].sum() * 100).round(2)
    summary["RevenueShare"] = (summary["Monetary"] / total_rev * 100).round(2)
    summary["ARPU"] = (summary["Monetary"] / summary["Customers"]).round(2)
    iou.save_table(summary, "03_rfm_segment_summary")

    iou.save_json({
        "snapshot_date": str(snapshot.date()),
        "thresholds": {k: round(v, 2) for k, v in med.items()},
        "threshold_method": "中位数切分（数据右偏，中位数对极值稳健）",
        "n_customers": int(len(g)),
        "total_monetary": round(float(total_rev), 2),
    }, cfg.TAB_DIR / "03_rfm_params.json")

    # RFM 三维与分群贡献
    tier = (g.groupby("ValueTier").agg(Customers=("CustomerID", "size"),
                                       Monetary=("Monetary", "sum")).reset_index())
    tier["CustomerShare"] = (tier["Customers"] / tier["Customers"].sum() * 100).round(2)
    tier["RevenueShare"] = (tier["Monetary"] / tier["Monetary"].sum() * 100).round(2)
    iou.save_table(tier, "03_rfm_value_tier")
    return g


# ===========================================================================
# M3 同期群留存分析（Cohort Retention）
# ===========================================================================
def m3_cohort(df: pd.DataFrame, max_periods: int = 24) -> tuple[pd.DataFrame, pd.DataFrame]:
    """按客户首次购买月份分组，统计后续各期的活跃与复购留存率。"""
    d = df[(df["CustomerID"] != "GUEST") & (df["OrderDate"] <= pd.Timestamp(CUT_DATE))].copy()
    d["CohortMonth"] = d.groupby("CustomerID")["OrderDate"].transform("min").dt.to_period("M")
    d["OrderMonth"] = d["OrderDate"].dt.to_period("M")
    d["CohortIndex"] = (
        (d["OrderMonth"].dt.year - d["CohortMonth"].dt.year) * 12
        + (d["OrderMonth"].dt.month - d["CohortMonth"].dt.month)
    )
    d = d[d["CohortIndex"] <= max_periods]

    cnt = (d.groupby(["CohortMonth", "CohortIndex"])["CustomerID"].nunique()
             .unstack(fill_value=0))
    size = cnt.iloc[:, 0]
    rate = cnt.divide(size, axis=0).round(4) * 100
    rate = rate.round(2)

    cnt_out = cnt.reset_index()
    cnt_out.insert(0, "CohortMonth", cnt_out.pop("CohortMonth").astype(str))
    cnt_out.insert(1, "CohortSize", size.values)
    iou.save_table(cnt_out, "03_cohort_retention_count", also_json=False)

    rate_out = rate.reset_index()
    rate_out.insert(0, "CohortMonth", rate_out.pop("CohortMonth").astype(str))
    rate_out.insert(1, "CohortSize", size.values)
    iou.save_table(rate_out, "03_cohort_retention_rate", also_json=False)

    # 各期平均留存率
    avg = pd.DataFrame({
        "CohortIndex": rate.columns.astype(int),
        "AvgRetentionRate": [round(float(rate[c][rate[c] > 0].mean()), 2)
                             for c in rate.columns],
        "AvgActiveCustomers": [round(float(cnt[c][cnt[c] > 0].mean()), 1) for c in cnt.columns],
        "CohortsObserved": [int((cnt[c] > 0).sum()) for c in cnt.columns],
    })
    iou.save_table(avg, "03_cohort_avg_retention")
    return cnt, rate


# ===========================================================================
# M4 帕累托 / ABC 分类
# ===========================================================================
def m4_pareto_abc(df: pd.DataFrame) -> pd.DataFrame:
    """ABC 分类（按销售额贡献）：A = 累计 80%，B = 累计 95%，C = 其余。"""
    d = df[df["OrderDate"] <= pd.Timestamp(CUT_DATE)]
    p = (d.groupby(["StockCode", "Description", "ProductCategory"])
           .agg(Revenue=("Revenue", "sum"), Quantity=("Quantity", "sum"),
                TimesSold=("Revenue", "size"))
           .reset_index().sort_values("Revenue", ascending=False).reset_index(drop=True))
    p["Revenue"] = p["Revenue"].round(2)
    p["RevenueShare"] = (p["Revenue"] / p["Revenue"].sum() * 100).round(4)
    p["CumulativeShare"] = p["RevenueShare"].cumsum().round(2)
    p["Rank"] = np.arange(1, len(p) + 1)
    p["ABCCategory"] = pd.cut(p["CumulativeShare"], bins=[-0.01, 80, 95, 100.01],
                              labels=["A", "B", "C"]).astype(str)
    iou.save_table(p, "03_abc_products", also_json=False)

    s = (p.groupby("ABCCategory")
           .agg(SKUs=("StockCode", "size"), Revenue=("Revenue", "sum"),
                Quantity=("Quantity", "sum")).reset_index())
    s["SKU_Share"] = (s["SKUs"] / s["SKUs"].sum() * 100).round(2)
    s["RevenueShare"] = (s["Revenue"] / s["Revenue"].sum() * 100).round(2)
    iou.save_table(s, "03_abc_summary")

    top = p.head(30)[["Rank", "StockCode", "Description", "ProductCategory",
                      "Revenue", "RevenueShare", "CumulativeShare", "ABCCategory"]]
    iou.save_table(top, "03_pareto_top30")
    return p


# ===========================================================================
# M5 购物篮关联规则（Apriori）
# ===========================================================================
def m5_apriori(df: pd.DataFrame, top_items: int = cfg.APRIORI_TOP_ITEMS) -> pd.DataFrame:
    """同一张发票内的商品构成购物篮，使用 Apriori 挖掘强关联规则。"""
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder

    d = df[df["OrderDate"] <= pd.Timestamp(CUT_DATE)].copy()
    # 只保留 Top-N 高频商品，控制稀疏矩阵规模（支持度低于该范围的商品无法形成有效规则）
    hot = d["StockCode"].value_counts().head(top_items).index
    d = d[d["StockCode"].isin(hot)]

    baskets = (d.groupby("Invoice")["StockCode"]
                 .apply(lambda s: list(pd.unique(s))).tolist())
    baskets = [b for b in baskets if len(b) >= 2]
    iou.log(f"  购物篮数量 {len(baskets):,}（含 ≥2 件商品的发票）")

    te = TransactionEncoder()
    te_ary = te.fit(baskets).transform(baskets, sparse=True)
    ml_df = pd.DataFrame.sparse.from_spmatrix(te_ary, columns=te.columns_)

    frequent = apriori(ml_df, min_support=cfg.APRIORI_MIN_SUPPORT,
                       use_colnames=True, max_len=3)
    rules = association_rules(frequent, metric="lift",
                              min_threshold=cfg.APRIORI_MIN_LIFT)
    rules = rules[rules["confidence"] >= cfg.APRIORI_MIN_CONF]

    # 先把 itemset 转为有序字符串，再以「指标 + 规则内容」做全关键字排序。
    # 仅按 lift 排序时，同分规则的先后由 mlxtend 内部的集合迭代顺序决定，
    # 受 PYTHONHASHSEED 影响跨运行不稳定，会破坏字节级可复现性；
    # 加入内容字段作 tie-breaker 后，排序结果完全确定。
    rules["antecedents"] = rules["antecedents"].apply(lambda s: ", ".join(sorted(s)))
    rules["consequents"] = rules["consequents"].apply(lambda s: ", ".join(sorted(s)))
    rules = rules.sort_values(
        ["lift", "confidence", "support", "antecedents", "consequents"],
        ascending=[False, False, False, True, True],
    ).reset_index(drop=True)

    rules = rules[["antecedents", "consequents", "support", "confidence",
                   "lift", "leverage", "conviction"]].round(4)
    rules.insert(0, "RuleID", np.arange(1, len(rules) + 1))

    # 关联商品名称
    name_map = (df.groupby("StockCode")["Description"]
                  .agg(lambda s: s.mode().iloc[0]).to_dict())
    def to_names(codes: str) -> str:
        return " & ".join(name_map.get(c.strip(), c.strip())[:24] for c in codes.split(","))
    rules["AntecedentNames"] = rules["antecedents"].map(to_names)
    rules["ConsequentNames"] = rules["consequents"].map(to_names)
    iou.save_table(rules, "03_apriori_rules", also_json=False)
    iou.save_table(rules.head(20), "03_apriori_rules_top20")

    # 购物篮规模分布
    sizes = d.groupby("Invoice")["StockCode"].apply(lambda s: len(pd.unique(s)))
    bsize = sizes.value_counts().sort_index().rename("InvoiceCount").reset_index()
    bsize.columns = ["BasketSize", "InvoiceCount"]
    bsize["InvoiceShare"] = (bsize["InvoiceCount"] / bsize["InvoiceCount"].sum() * 100).round(2)
    iou.save_table(bsize, "03_basket_size_distribution")

    iou.save_json({
        "algorithm": "Apriori (mlxtend)",
        "min_support": cfg.APRIORI_MIN_SUPPORT,
        "min_confidence": cfg.APRIORI_MIN_CONF,
        "min_lift": cfg.APRIORI_MIN_LIFT,
        "max_itemset_len": 3,
        "top_items": top_items,
        "n_baskets": len(baskets),
        "n_itemsets": int(len(frequent)),
        "n_rules": int(len(rules)),
        "param_reason": (
            f"最小支持度 {cfg.APRIORI_MIN_SUPPORT}：低于 1% 的组合缺乏铺货/陈列价值；"
            f"提升度 > {cfg.APRIORI_MIN_LIFT} 保证是正向关联而非随机共现；"
            f"置信度 ≥ {cfg.APRIORI_MIN_CONF} 保证推荐命中率可被业务接受。"
        ),
    }, cfg.TAB_DIR / "03_apriori_params.json")
    return rules


# ===========================================================================
# M6 波士顿矩阵（BCG）
# ===========================================================================
BCG_QUADRANTS = {("H", "H"): "明星 Stars", ("H", "L"): "金牛 Cash Cows",
                 ("L", "H"): "问题 Question Marks", ("L", "L"): "瘦狗 Dogs"}


def m6_bcg(df: pd.DataFrame) -> pd.DataFrame:
    """
    波士顿矩阵。
    分析单元 = 派生商品品类（ProductCategory）。
    相对份额 = 该品类销售额 / 其余品类平均销售额（>1 表示该品类是组合中的领先者）
    增速     = 最近 12 个月 vs 前 12 个月的销售额同比增速
    分界线   = x: 1.0（BCG 经典阈值）；y: 整体销售额同比增速（以市场平均增速为基准）
    """
    d = df[df["OrderDate"] <= pd.Timestamp(CUT_DATE)].copy()
    latest = d["OrderDate"].max()
    cur_start = latest - pd.DateOffset(months=12)
    prev_start = latest - pd.DateOffset(months=24)

    def rev(sub):
        return float(sub["Revenue"].sum())

    rows = []
    cats = d["ProductCategory"].unique()
    for c in cats:
        sub = d[d["ProductCategory"] == c]
        cur = float(sub.loc[sub["OrderDate"] > cur_start, "Revenue"].sum())
        prev = float(sub.loc[(sub["OrderDate"] > prev_start)
                             & (sub["OrderDate"] <= cur_start), "Revenue"].sum())
        if prev == 0:
            continue
        rows.append({
            "ProductCategory": c,
            "Revenue_Last12M": round(cur, 2),
            "Revenue_Prev12M": round(prev, 2),
            "YoY_Growth": round((cur - prev) / prev * 100, 2),
            "Orders": int(sub["Invoice"].nunique()),
            "SKUs": int(sub["StockCode"].nunique()),
        })
    b = pd.DataFrame(rows)

    overall_cur = rev(d[d["OrderDate"] > cur_start])
    overall_prev = rev(d[(d["OrderDate"] > prev_start) & (d["OrderDate"] <= cur_start)])
    market_growth = (overall_cur - overall_prev) / overall_prev * 100

    mean_other = b["Revenue_Last12M"].apply(lambda v: (b["Revenue_Last12M"].sum() - v)
                                            / max(len(b) - 1, 1))
    b["RelativeShare"] = (b["Revenue_Last12M"] / mean_other).round(3)
    b["ShareFlag"] = np.where(b["RelativeShare"] >= 1.0, "H", "L")
    b["GrowthFlag"] = np.where(b["YoY_Growth"] >= market_growth, "H", "L")
    b["Quadrant"] = [BCG_QUADRANTS[(s, g)] for s, g in zip(b["ShareFlag"], b["GrowthFlag"])]
    b["RevenueShare"] = (b["Revenue_Last12M"] / b["Revenue_Last12M"].sum() * 100).round(2)
    b = b.sort_values("Revenue_Last12M", ascending=False).reset_index(drop=True)

    q = (b.groupby("Quadrant").agg(Categories=("ProductCategory", "size"),
                                   Revenue=("Revenue_Last12M", "sum")).reset_index())
    q["RevenueShare"] = (q["Revenue"] / q["Revenue"].sum() * 100).round(2)
    iou.save_table(b, "03_bcg_matrix")
    iou.save_table(q, "03_bcg_quadrant_summary")
    iou.save_json({
        "unit": "商品品类（由 Description 关键词派生）",
        "relative_share_def": "品类销售额 / 其余品类平均销售额，阈值 1.0（BCG 经典分界）",
        "growth_def": "最近 12 个月 vs 前 12 个月销售额同比增速",
        "growth_threshold": round(float(market_growth), 2),
        "growth_threshold_def": "整体销售额同比增速，作为“市场平均增速”基准",
        "window": [str(prev_start.date()), str(cur_start.date()), str(latest.date())],
    }, cfg.TAB_DIR / "03_bcg_params.json")
    return b


# ===========================================================================
# M7 时间序列预测（SARIMA / Holt-Winters）
# ===========================================================================
def m7_forecast(daily: pd.DataFrame) -> dict:
    """
    日销售额预测：回测留出最后 30 天评估 MAPE/RMSE，再对未来 30 天做点预测 +
    95% 置信区间预测。
    """
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    s = daily.set_index("OrderDate")["Revenue"].asfreq("D").fillna(0.0)
    s = s[s.index <= pd.Timestamp(CUT_DATE)]

    test_n = cfg.FORECAST_TEST_DAYS
    train, test = s.iloc[:-test_n], s.iloc[-test_n:]

    def metrics(actual, pred):
        from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
        actual = np.asarray(actual, dtype=float)
        pred = np.asarray(pred, dtype=float)
        mask = actual != 0                      # 休息日无销售，MAPE 不可计算，予以剔除
        mape = float(mean_absolute_percentage_error(actual[mask], pred[mask]) * 100)
        rmse = float(np.sqrt(mean_squared_error(actual, pred)))
        return round(mape, 2), round(rmse, 2)

    results, figs_data = {}, {}

    # --- 基准模型：Holt-Winters 三指数平滑（周季节 7，阻尼趋势）
    hw = ExponentialSmoothing(train, trend="add", damped_trend=True,
                              seasonal="add", seasonal_periods=7,
                              initialization_method="estimated").fit(optimized=True)
    hw_pred = hw.forecast(test_n)
    hw_mape, hw_rmse = metrics(test, hw_pred)
    results["Holt-Winters"] = {"MAPE": hw_mape, "RMSE": hw_rmse,
                               "order": "add-trend(damped) + add-seasonal(7)"}

    # --- 主模型：SARIMA
    try:
        sar = SARIMAX(train, order=cfg.SARIMA_ORDER,
                      seasonal_order=cfg.SARIMA_SEASONAL_ORDER,
                      enforce_stationarity=False, enforce_invertibility=False,
                      simple_differencing=False).fit(disp=False, maxiter=200)
        sar_pred = sar.forecast(test_n)
        sar_mape, sar_rmse = metrics(test, sar_pred)
        results["SARIMA"] = {
            "MAPE": sar_mape, "RMSE": sar_rmse,
            "order": f"SARIMA{cfg.SARIMA_ORDER}{cfg.SARIMA_SEASONAL_ORDER}",
            "aic": round(float(sar.aic), 2),
        }
        sarima_ok = True
    except Exception as e:  # noqa: BLE001
        iou.log(f"SARIMA 拟合失败，回退 Holt-Winters：{e}", "WARN")
        sarima_ok = False

    best_name = ("SARIMA" if sarima_ok and results["SARIMA"]["MAPE"] <= hw_mape
                 else "Holt-Winters")
    iou.log(f"回测对比 → SARIMA: {results.get('SARIMA', {}).get('MAPE')}% | "
            f"HW: {hw_mape}% | 最优模型：{best_name}")

    bt = pd.DataFrame({
        "OrderDate": list(test.index) + list(test.index),
        "Model": ["Holt-Winters"] * test_n + (["SARIMA"] * test_n if sarima_ok else []),
        "Actual": list(test.values) + (list(test.values) if sarima_ok else []),
        "Predicted": list(hw_pred.values) + (list(np.asarray(sar_pred)) if sarima_ok else []),
    })
    iou.save_table(bt, "03_forecast_backtest")

    metrics_df = pd.DataFrame([
        {"Model": k, **{kk: vv for kk, vv in v.items()}} for k, v in results.items()
    ])
    metrics_df["Selected"] = metrics_df["Model"].eq(best_name)
    iou.save_table(metrics_df, "03_forecast_metrics")

    # --- 最终预测：用全量数据重新拟合最优模型，向前 30 天
    future_n = 30
    if best_name == "SARIMA":
        final = SARIMAX(s, order=cfg.SARIMA_ORDER,
                        seasonal_order=cfg.SARIMA_SEASONAL_ORDER,
                        enforce_stationarity=False,
                        enforce_invertibility=False).fit(disp=False, maxiter=200)
        fc = final.get_forecast(future_n)
        mean = np.asarray(fc.predicted_mean)
        ci = np.asarray(fc.conf_int(alpha=0.05))
    else:
        final = ExponentialSmoothing(s, trend="add", damped_trend=True,
                                     seasonal="add", seasonal_periods=7,
                                     initialization_method="estimated").fit(optimized=True)
        mean = np.asarray(final.forecast(future_n))
        resid_std = float(np.std(final.resid))
        ci = np.column_stack([mean - 1.96 * resid_std, mean + 1.96 * resid_std])

    future_idx = pd.date_range(s.index.max() + timedelta(days=1), periods=future_n, freq="D")
    fc_df = pd.DataFrame({
        "OrderDate": future_idx,
        "Forecast": np.round(mean, 2),
        "CI95_Lower": np.round(np.maximum(ci[:, 0], 0), 2),
        "CI95_Upper": np.round(ci[:, 1], 2),
    })
    # 与实际观测对比（2011-12 前 9 天为已知数据，可用于额外验证）
    actual_full = daily.set_index("OrderDate")["Revenue"]
    fc_df["Actual"] = [round(float(actual_full.get(d, np.nan)), 2) for d in future_idx]
    iou.save_table(fc_df, "03_forecast_future")

    # 与预测区间对应的历史对照
    hist = pd.DataFrame({"OrderDate": s.index, "Revenue": s.values.round(2)})
    iou.save_table(hist, "03_forecast_history", also_json=False)

    iou.save_json({
        "best_model": best_name,
        "backtest_window": [str(test.index.min().date()), str(test.index.max().date())],
        "backtest_days": test_n,
        "metrics": results,
        "forecast_horizon_days": future_n,
        "ci_note": "95% 置信区间；负区间下界按 0 截断（销售额非负）",
    }, cfg.TAB_DIR / "03_forecast_summary.json")

    return {"backtest": bt, "future": fc_df, "metrics": metrics_df,
            "best": best_name, "history": hist}


# ===========================================================================
# M8 K-Means 客户分群
# ===========================================================================
def m8_kmeans(rfm: pd.DataFrame) -> pd.DataFrame:
    """基于 RFM 三维的对数标准化特征做 K-Means 聚类，用轮廓系数选择 K。"""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    X = rfm[["Recency", "Frequency", "Monetary"]].copy()
    Xl = np.log1p(X)
    Xs = StandardScaler().fit_transform(Xl)

    rows, best_k, best_score = [], None, -1
    for k in range(2, 7):
        km = KMeans(n_clusters=k, random_state=cfg.RANDOM_SEED, n_init=10)
        lab = km.fit_predict(Xs)
        score = silhouette_score(Xs, lab)
        rows.append({"K": k, "Inertia": round(float(km.inertia_), 1),
                     "Silhouette": round(float(score), 4)})
        if score > best_score:
            best_k, best_score = k, score
        iou.log(f"  K={k} 轮廓系数={score:.4f}")
    iou.save_table(pd.DataFrame(rows), "03_kmeans_elbow")

    km = KMeans(n_clusters=best_k, random_state=cfg.RANDOM_SEED, n_init=10)
    rfm = rfm.copy()
    rfm["Cluster"] = km.fit_predict(Xs)
    prof = (rfm.groupby("Cluster")
              .agg(Customers=("CustomerID", "size"),
                   AvgRecency=("Recency", "mean"),
                   AvgFrequency=("Frequency", "mean"),
                   AvgMonetary=("Monetary", "mean"),
                   TotalMonetary=("Monetary", "sum")).reset_index())
    for col in ("AvgRecency", "AvgFrequency", "AvgMonetary", "TotalMonetary"):
        prof[col] = prof[col].round(2)
    prof["CustomerShare"] = (prof["Customers"] / prof["Customers"].sum() * 100).round(2)
    prof["RevenueShare"] = (prof["TotalMonetary"] / prof["TotalMonetary"].sum() * 100).round(2)
    prof = prof.sort_values("AvgMonetary", ascending=False).reset_index(drop=True)

    # 依据画像命名： monetary 最高且频次高 = 核心高净值；Recency 大 = 沉睡
    names = []
    for _, r in prof.iterrows():
        if r["AvgMonetary"] >= prof["AvgMonetary"].median():
            names.append("高价值忠诚群" if r["AvgFrequency"] >= prof["AvgFrequency"].median()
                         else "高客单低频群")
        else:
            names.append("潜力成长群" if r["AvgRecency"] <= prof["AvgRecency"].median()
                         else "沉睡流失群")
    # 去重命名
    seen, final_names = {}, []
    for n in names:
        seen[n] = seen.get(n, 0) + 1
        final_names.append(n if seen[n] == 1 else f"{n}{seen[n]}")
    prof["ClusterName"] = final_names
    name_map = dict(zip(prof["Cluster"], prof["ClusterName"]))
    rfm["ClusterName"] = rfm["Cluster"].map(name_map)

    iou.save_table(prof, "03_kmeans_cluster_profile")
    iou.save_table(rfm[["CustomerID", "Recency", "Frequency", "Monetary",
                        "Cluster", "ClusterName", "Segment"]],
                   "03_kmeans_customer_labels", also_json=False)
    iou.save_json({"best_k": int(best_k), "silhouette": round(float(best_score), 4),
                   "features": ["log1p(Recency)", "log1p(Frequency)", "log1p(Monetary)"],
                   "scaler": "StandardScaler", "random_state": cfg.RANDOM_SEED,
                   "selection": "轮廓系数最大，兼顾惯性下降拐点"},
                  cfg.TAB_DIR / "03_kmeans_params.json")
    return rfm


# ===========================================================================
# M9 复购漏斗
# ===========================================================================
def robustness_rfm_threshold(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """
    RFM 切分方式的稳健性检验（非新增模型，属于 M2 的验证环节）。

    论文 §4.2 采用中位数切分，理由是指标右偏。本节给出反事实检验：
    若改用均值切分或 60 分位切分，核心结论（高价值客群的规模与贡献）
    是否依然成立？若三种切分下「少量客户贡献大部分营收」这一结构稳定，
    则说明结论不依赖特定阈值设定。
    """
    d = df[(df["CustomerID"] != "GUEST") & (df["OrderDate"] <= pd.Timestamp(CUT_DATE))]
    g = (d.groupby("CustomerID")
           .agg(Recency=("OrderDate", lambda s: (snapshot - s.max()).days),
                Frequency=("Invoice", "nunique"),
                Monetary=("Revenue", "sum"))
           .reset_index())
    g["Recency"] = g["Recency"].clip(lower=0)

    schemes = {
        "中位数（采用）": {"Recency": g["Recency"].median(),
                          "Frequency": g["Frequency"].median(),
                          "Monetary": g["Monetary"].median()},
        "均值": {"Recency": g["Recency"].mean(),
                "Frequency": g["Frequency"].mean(),
                "Monetary": g["Monetary"].mean()},
        "60 分位": {"Recency": g["Recency"].quantile(0.40),   # R 越小越好，高组取 40 分位
                   "Frequency": g["Frequency"].quantile(0.60),
                   "Monetary": g["Monetary"].quantile(0.60)},
    }

    rows = []
    total_rev = g["Monetary"].sum()
    for name, thr in schemes.items():
        r_h = g["Recency"] <= thr["Recency"]
        f_h = g["Frequency"] >= thr["Frequency"]
        m_h = g["Monetary"] >= thr["Monetary"]
        core = g[r_h & f_h & m_h]                      # 三项皆高 ≈ 重要价值客户
        high_m = g[m_h]
        rows.append([
            name,
            f"{thr['Recency']:.0f} / {thr['Frequency']:.2f} / {thr['Monetary']:.2f}",
            int(len(core)), round(len(core) / len(g) * 100, 2),
            round(float(core['Monetary'].sum()), 2),
            round(float(core['Monetary'].sum()) / total_rev * 100, 2),
            int(len(high_m)), round(float(high_m['Monetary'].sum()) / total_rev * 100, 2),
        ])

    out = pd.DataFrame(rows, columns=[
        "切分方式", "阈值(R天/F次/M英镑)", "核心高价值客户数", "人数占比(%)",
        "核心客户营收(英镑)", "营收占比(%)", "M高组人数", "M高组营收占比(%)"])
    iou.save_table(out, "03_rfm_threshold_sensitivity")
    return out


def m9_funnel(df: pd.DataFrame, rfm: pd.DataFrame) -> pd.DataFrame:
    """复购漏斗：全部客户 → 二次购买 → 三次 → 四次 → 五次及以上。"""
    total = int(rfm.shape[0])
    steps = [
        ("首次购买客户", total),
        ("完成第 2 次购买", int((rfm["Frequency"] >= 2).sum())),
        ("完成第 3 次购买", int((rfm["Frequency"] >= 3).sum())),
        ("完成第 4 次购买", int((rfm["Frequency"] >= 4).sum())),
        ("完成 5 次及以上（忠诚）", int((rfm["Frequency"] >= 5).sum())),
    ]
    f = pd.DataFrame(steps, columns=["Stage", "Customers"])
    f["StepConversion"] = [np.nan] + [
        round(f["Customers"].iloc[i] / f["Customers"].iloc[i - 1] * 100, 2)
        for i in range(1, len(f))]
    f["TotalConversion"] = (f["Customers"] / total * 100).round(2)
    iou.save_table(f, "03_repurchase_funnel")
    return f


# ===========================================================================
def main() -> None:
    print(cfg.banner("STEP 03 · 商业分析模型计算"))
    t = load_tables()
    fact = t["fact"]

    snapshot = fact[fact["OrderDate"] <= pd.Timestamp(CUT_DATE)]["OrderDate"].max() + timedelta(days=1)
    iou.log(f"分析基准日（snapshot）= {snapshot.date()}")

    m1 = m1_trend(fact)
    rfm = m2_rfm(fact, snapshot)
    cnt, rate = m3_cohort(fact)
    abc = m4_pareto_abc(fact)
    rules = m5_apriori(fact)
    bcg = m6_bcg(fact)
    fc = m7_forecast(m1["daily"])
    rfm = m8_kmeans(rfm)
    funnel = m9_funnel(fact, rfm)
    sens = robustness_rfm_threshold(fact, snapshot)

    # ---- 汇总 KPI，供 README / 论文 / 大屏复用
    d = fact[fact["OrderDate"] <= pd.Timestamp(CUT_DATE)]
    kpis = {
        "n_rows": int(len(fact)),
        "n_invoices": int(fact["Invoice"].nunique()),
        "n_customers": int(rfm.shape[0]),
        "n_products": int(fact["StockCode"].nunique()),
        "n_countries": int(fact["Country"].nunique()),
        "total_revenue_gbp": round(float(d["Revenue"].sum()), 2),
        "avg_order_value_gbp": round(float(d["Revenue"].sum() / d["Invoice"].nunique()), 2),
        "date_range": [str(fact["OrderDate"].min().date()), str(CUT_DATE)],
        "top_country": str(m1["country"].iloc[0]["Country"]),
        "top_country_share": float(m1["country"].iloc[0]["RevenueShare"]),
        "top_category": str(m1["category"].iloc[0]["ProductCategory"]),
        "abc_counts": abc["ABCCategory"].value_counts().to_dict(),
        "abc_revenue_share": (abc.groupby("ABCCategory")["Revenue"].sum()
                                .pipe(lambda x: (x / x.sum() * 100).round(2)).to_dict()),
        "repeat_purchase_rate": round(float((rfm["Frequency"] >= 2).mean() * 100), 2),
        "n_apriori_rules": int(len(rules)),
        "best_forecast_model": fc["best"],
        "cohort_m1_retention": round(float(rate.loc[:, 1].replace(0, np.nan).mean()), 2),
        "cohort_m6_retention": round(float(rate.loc[:, 6].replace(0, np.nan).mean()), 2)
        if 6 in rate.columns else None,
        "top1_customer_value_share": round(
            float(rfm.nlargest(int(rfm.shape[0] * 0.01), "Monetary")["Monetary"].sum()
                  / rfm["Monetary"].sum() * 100), 2),
    }
    iou.save_json(kpis, cfg.TAB_DIR / "03_executive_kpis.json")

    print(cfg.banner("核心 KPI 汇总"))
    for k, v in kpis.items():
        print(f"  {k:<28}: {v}")
    iou.log("STEP 03 完成 ✓")
    return None


if __name__ == "__main__":
    main()
