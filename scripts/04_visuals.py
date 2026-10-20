# -*- coding: utf-8 -*-
"""
04_visuals.py —— 数据可视化（全 Python 实现）
============================================
产出 35 张静态图，分为两类：

  A. 模板复现类（fig01–fig25，共 25 种）
     对照《Excel数据可视化——从图表到数据大屏》中的典型模板，使用
     Matplotlib/Seaborn 还原其图表类型、布局结构、配色方案、标签样式、
     图例位置与标题设计。

  B. 业务模型类（fig26–fig35，共 10 张）
     与 03_analysis.py 中 9 类模型一一对应：
     M1 移动平均(fig25) → M2 RFM(fig26,27) → M3 同期群(fig28)
     → M4 帕累托/ABC(fig29) → M5 关联规则(fig30,31) → M6 波士顿矩阵(fig32)
     → M7 预测(fig33) → M8 K-Means(fig34) → M9 复购漏斗(fig35)

规范：中文字体正常显示；坐标轴与单位完整标注；统一配色；分辨率 200dpi；
      统一命名 figNN_<主题>.png；底部统一标注数据来源。
严禁使用 Power BI / Tableau / Fine BI 等 BI 软件，严禁 Excel 图表截图替代。

运行：
    python scripts/04_visuals.py
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import chart_helpers as ch  # noqa: E402
from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402
from utils import style as st  # noqa: E402

try:
    import seaborn as sns
    HAS_SNS = True
except Exception:  # noqa: BLE001
    HAS_SNS = False

GBP = "£"
FIGDIR = cfg.FIG_DIR
_INDEX: list[dict] = []          # 图索引，最后写出到 docs/图表索引.md

COUNTRY_CN = {
    "United Kingdom": "英国", "Netherlands": "荷兰", "Eire": "爱尔兰", "Germany": "德国",
    "France": "法国", "Australia": "澳大利亚", "Spain": "西班牙", "Belgium": "比利时",
    "Switzerland": "瑞士", "Japan": "日本", "Portugal": "葡萄牙", "Sweden": "瑞典",
    "Norway": "挪威", "Finland": "芬兰", "Denmark": "丹麦", "Austria": "奥地利",
    "Poland": "波兰", "Italy": "意大利", "Cyprus": "塞浦路斯", "Greece": "希腊",
    "Israel": "以色列", "Singapore": "新加坡", "Iceland": "冰岛", "Canada": "加拿大",
    "Malta": "马耳他", "Bahrain": "巴林", "Lebanon": "黎巴嫩", "Bermuda": "百慕大",
    "Usa": "美国", "Rsa": "南非", "Korea": "韩国", "Lithuania": "立陶宛",
    "United Arab Emirates": "阿联酋", "Channel Islands": "海峡群岛",
    "Unspecified": "未标注", "Hong Kong": "中国香港",
}


def _out(fig, name: str, dpi: int = cfg.FIG_DPI) -> Path:
    """统一保存 + 脚注 + 记录索引。"""
    st.source_note(fig)
    p = st.save_fig(fig, FIGDIR / f"{name}.png", dpi=dpi)
    iou.log(f"  图表 → {p.name}")
    return p


def _register(idx: int, name: str, kind: str, template: str, desc: str) -> None:
    _INDEX.append({"编号": f"fig{idx:02d}", "文件名": f"{name}.png",
                   "类别": kind, "模板/模型": template, "说明": desc})


def _load(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(cfg.TAB_DIR / name, **kw)


def _money(v: float) -> str:
    return f"{GBP}{v:,.0f}"


def _wrap(s: str, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(str(s), width))


# ===========================================================================
# ============================ A. 模板复现类 =================================
# ===========================================================================
def fig01_mom_yoy(monthly: pd.DataFrame) -> Path:
    """模板01：柱+折线双轴组合图（环比/同比，M1 模型主图）。"""
    m = monthly.copy()
    fig, ax = plt.subplots(figsize=(13, 5.6))
    colors = ["#C0504D" if (x is not np.nan and x >= 0) else "#548235"
              for x in m["Revenue_MoM"].fillna(0)]
    ax.bar(m["MonthPeriod"], m["Revenue"] / 1000, color="#4472C4", width=0.62,
           label="月度销售额（k£）", zorder=3)
    ax2 = ax.twinx()
    ax2.plot(m["MonthPeriod"], m["Revenue_MoM"], color="#548235", marker="o",
             markersize=4, linewidth=1.6, label="环比 MoM（%）")
    ax2.plot(m["MonthPeriod"], m["Revenue_YoY"], color="#ED7D31", marker="s",
             markersize=4, linewidth=1.6, linestyle="--", label="同比 YoY（%）")
    ax2.axhline(0, color="#808080", linewidth=1)
    ax2.set_ylabel("增长率（%）", color="#404040")
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_xlabel("月份")
    ax.set_title("图1  销售额月度走势与环比/同比分析（双轴组合图）", pad=16)
    ax.set_xticks(range(len(m)))
    ax.set_xticklabels(m["MonthPeriod"], rotation=60, ha="right", fontsize=8.5)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9.5, ncol=3)
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    _ = colors
    return _out(fig, "fig01_mom_yoy")


def fig02_trend_line(daily: pd.DataFrame) -> Path:
    """模板02：折线图（日销售额 + 年度均值参考线 + 峰值标注）。"""
    d = daily.copy()
    fig, ax = plt.subplots(figsize=(13.5, 5.4))
    ax.plot(d["OrderDate"], d["Revenue"] / 1000, color="#4472C4", linewidth=0.85,
            label="日销售额", zorder=3)
    ax.plot(d["OrderDate"], d["MA30"] / 1000, color="#ED7D31", linewidth=2.0,
            label="30 日移动平均", zorder=4)
    mean_all = d["Revenue"].mean() / 1000
    ax.axhline(mean_all, color="#A5A5A5", linewidth=1.2, linestyle="--",
               label=f"期间均值（{mean_all:.1f} k{GBP}）")
    top3 = d.nlargest(3, "Revenue")
    for _, r in top3.iterrows():
        ax.annotate(f"{r['OrderDate'].strftime('%Y-%m-%d')}\n{GBP}{r['Revenue']/1000:.0f}k",
                    xy=(r["OrderDate"], r["Revenue"] / 1000),
                    xytext=(0, 18), textcoords="offset points", ha="center",
                    fontsize=8.5, color="#C00000",
                    arrowprops=dict(arrowstyle="->", color="#C00000", linewidth=0.9))
    ax.set_title("图2  日销售额趋势（含移动平均与峰值标注）", pad=14)
    ax.set_xlabel("日期")
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.legend(loc="upper left", fontsize=9.5)
    return _out(fig, "fig02_revenue_trend_line")


def fig03_area(monthly: pd.DataFrame) -> Path:
    """模板03：面积图（月度销售额 + 订单量）双图 Template。"""
    m = monthly.copy()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    ax = axes[0]
    ax.fill_between(range(len(m)), m["Revenue"] / 1000, color="#5B9BD5", alpha=0.55,
                    edgecolor="#2E75B6", linewidth=1.6)
    ax.plot(range(len(m)), m["Revenue"] / 1000, color="#2E75B6", linewidth=1.6)
    ax.set_xticks(range(len(m)))
    ax.set_xticklabels(m["MonthPeriod"], rotation=60, ha="right", fontsize=8)
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_title("月度销售额（面积图）", fontsize=12)
    ax2 = axes[1]
    ax2.fill_between(range(len(m)), m["Orders"], color="#70AD47", alpha=0.55,
                     edgecolor="#548235", linewidth=1.6)
    ax2.plot(range(len(m)), m["Orders"], color="#548235", linewidth=1.6)
    ax2.set_xticks(range(len(m)))
    ax2.set_xticklabels(m["MonthPeriod"], rotation=60, ha="right", fontsize=8)
    ax2.set_ylabel("订单数（笔）")
    ax2.set_title("月度订单量（面积图）", fontsize=12)
    fig.suptitle("图3  月度销售额与订单量趋势（面积图）", fontsize=14, fontweight="bold", y=1.02)
    return _out(fig, "fig03_monthly_revenue_area")


def fig04_bar(country: pd.DataFrame) -> Path:
    """模板04：柱形图（国家销售额 TOP12）。"""
    c = country.head(cfg.TOP_N_COUNTRIES).copy()
    cols = ["#C00000" if i == 0 else "#4472C4" for i in range(len(c))]
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    bars = ax.bar(c["Country"], c["Revenue"] / 1000, color=cols, width=0.68, zorder=3)
    st.add_value_labels(ax, bars, fmt="{:,.1f}", fontsize=8.5)
    ax.set_title("图4  各国销售额排名 TOP12（柱形图）", pad=14)
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_xlabel("国家 / 地区")
    ax.set_xticklabels(c["Country"], rotation=40, ha="right")
    return _out(fig, "fig04_top_countries_bar")


def fig05_barh(products: pd.DataFrame) -> Path:
    """模板05：条形图（商品销售额 TOP15）。"""
    p = products.head(cfg.TOP_N_PRODUCTS).iloc[::-1].copy()
    p["ShortDesc"] = p["Description"].map(lambda s: _wrap(s, 34))
    fig, ax = plt.subplots(figsize=(11.5, 8))
    cols = st.excel_cycle(len(p))[::-1]
    bars = ax.barh(p["ShortDesc"], p["Revenue"] / 1000, color=cols, height=0.7, zorder=3)
    for bar, v in zip(bars, p["Revenue"] / 1000):
        ax.text(v + 0.3, bar.get_y() + bar.get_height() / 2, f"{v:,.1f}",
                va="center", fontsize=8.5, color="#404040")
    ax.set_title("图5  商品销售额 TOP15（条形图）", pad=14)
    ax.set_xlabel(f"销售额（千{GBP}）")
    ax.set_ylabel("商品")
    ax.tick_params(axis="y", labelsize=8.5)
    ax.grid(axis="x", alpha=0.25, linestyle="--")
    return _out(fig, "fig05_top_products_barh")


def fig06_donut(country: pd.DataFrame) -> Path:
    """模板06：环形图（国家销售结构）。"""
    c = country.copy()
    top = c.head(8)
    other = c.iloc[8:]["Revenue"].sum()
    labels = list(top["Country"]) + ["其他 28 国"]
    sizes = list(top["Revenue"]) + [other]
    total = sum(sizes)
    fig, ax = plt.subplots(figsize=(11, 6.4))
    ch.donut_chart(ax, sizes, labels, colors=st.EXCEL_PALETTE,
                   unit="", fmt="{:,.0f}",
                   center_text=f"总销售额\n{_money(total)}")
    ax.set_title("图6  各国销售额结构（环形图）", pad=14)
    return _out(fig, "fig06_country_donut")


def fig07_stacked(fact: pd.DataFrame, country: pd.DataFrame) -> Path:
    """模板07：堆积柱形图（月度 × TOP5 国家）。"""
    top5 = country.head(5)["Country"].tolist()
    d = fact[fact["Country"].isin(top5)].copy()
    d = d[d["OrderDate"] <= "2011-11-30"]
    piv = d.pivot_table(index="MonthPeriod", columns="Country", values="Revenue",
                        aggfunc="sum", fill_value=0) / 1000
    piv = piv[top5]
    fig, ax = plt.subplots(figsize=(13, 5.6))
    bottom = np.zeros(len(piv))
    for i, cname in enumerate(piv.columns):
        ax.bar(piv.index, piv[cname], bottom=bottom, label=cname,
               color=st.EXCEL_PALETTE[i], width=0.68, edgecolor="white", linewidth=0.5)
        bottom += piv[cname].values
    ax.set_title("图7  月度销售额的国别构成（堆积柱形图）", pad=14)
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_xlabel("月份")
    ax.set_xticklabels(piv.index, rotation=60, ha="right", fontsize=8.5)
    ax.legend(loc="upper left", fontsize=9.5, ncol=5)
    return _out(fig, "fig07_monthly_stacked_bar")


def fig08_pct_stacked(fact: pd.DataFrame) -> Path:
    """模板08：百分比堆积柱形图（月度品类结构）。"""
    d = fact[fact["OrderDate"] <= "2011-11-30"]
    piv = d.pivot_table(index="MonthPeriod", columns="ProductCategory", values="Revenue",
                        aggfunc="sum", fill_value=0)
    top_cats = piv.sum().sort_values(ascending=False).head(6).index.tolist()
    piv = piv[top_cats]
    piv = piv.div(piv.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(13, 5.6))
    bottom = np.zeros(len(piv))
    for i, c in enumerate(piv.columns):
        ax.bar(piv.index, piv[c], bottom=bottom, label=_wrap(c, 18),
               color=st.EXCEL_PALETTE[i], width=0.7, edgecolor="white", linewidth=0.5)
        bottom += piv[c].values
    ax.set_ylabel("占比（%）")
    ax.set_xlabel("月份")
    ax.set_ylim(0, 100)
    ax.set_title("图8  月度销售额品类结构占比变化（百分比堆积柱形图）", pad=14)
    ax.set_xticklabels(piv.index, rotation=60, ha="right", fontsize=8.5)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.55), ncol=3, fontsize=9, frameon=False)
    return _out(fig, "fig08_category_pct_stacked")


def fig09_scatter(rfm: pd.DataFrame) -> Path:
    """模板09：散点图（购买频次 vs 客单金额，含趋势线）。"""
    r = rfm[rfm["Frequency"] > 0].copy()
    r["_n"] = np.random.RandomState(cfg.RANDOM_SEED).normal(0, 0.09, len(r))
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    sc = ax.scatter(r["Frequency"] * np.exp(r["_n"]), r["Monetary"],
                    c=np.log1p(r["Recency"]), cmap="RdYlGn_r", s=26, alpha=0.72,
                    edgecolors="white", linewidths=0.4)
    # 趋势线
    z = np.polyfit(np.log10(r["Frequency"]), np.log10(r["Monetary"].clip(lower=1)), 1)
    xs = np.linspace(r["Frequency"].min(), r["Frequency"].quantile(0.99), 100)
    ys = 10 ** np.polyval(z, np.log10(xs))
    ax.plot(xs, ys, color="#C00000", linewidth=2, linestyle="--",
            label=f"幂律趋势线（斜率 {z[0]:.2f}）")
    ax.set_xscale("log")
    ax.set_yscale("log")
    cb = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Recency（对数色阶，越大越久未购）", fontsize=9)
    ax.set_xlabel("购买频次（次，对数轴）")
    ax.set_ylabel(f"累计消费金额（{GBP}，对数轴）")
    ax.set_title("图9  客户购买频次与累计消费金额散点图", pad=14)
    ax.legend(loc="upper left", fontsize=9.5)
    return _out(fig, "fig09_aov_frequency_scatter")


def fig10_bubble(country: pd.DataFrame) -> Path:
    """模板10：气泡图（国家三维度：客户数 × 客单价 × 销售额）。"""
    c = country.head(14).copy()
    c = c.sort_values("Revenue", ascending=False)
    fig, ax = plt.subplots(figsize=(12, 6.4))
    sizes = (c["Revenue"] / c["Revenue"].max() * 2600) + 60
    sc = ax.scatter(c["Customers"], c["AOV"], s=sizes, c=np.arange(len(c)),
                    cmap="tab20", alpha=0.72, edgecolors="#404040", linewidths=0.8)
    for _, r in c.iterrows():
        ax.annotate(f"{r['Country']}\n{_money(r['Revenue'])}",
                    xy=(r["Customers"], r["AOV"]), ha="center", va="center",
                    fontsize=8, color="#262626")
    ax.set_xlabel("客户数（人）")
    ax.set_ylabel(f"客单价 AOV（{GBP}）")
    ax.set_title("图10  主要市场的客户规模·客单价·销售额三维气泡图", pad=14)
    ax.grid(alpha=0.25, linestyle="--")
    _ = sc
    return _out(fig, "fig10_country_bubble")


def fig11_hist(orders: pd.DataFrame) -> Path:
    """模板11：直方图 + 密度曲线（订单金额分布）。"""
    v = orders["Revenue"].values
    v = v[v <= np.percentile(v, 98)]
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    n, bins, patches = ax.hist(v, bins=45, color="#5B9BD5", edgecolor="white", alpha=0.9)
    for i, p in enumerate(patches):
        p.set_facecolor(plt.cm.Blues(0.35 + 0.55 * i / len(patches)))
    if HAS_SNS:
        ax2 = ax.twinx()
        sns.kdeplot(v, ax=ax2, color="#C00000", linewidth=1.8)
        ax2.set_ylabel("核密度", fontsize=10)
        ax2.grid(False)
    med = float(np.median(v))
    ax.axvline(med, color="#548235", linewidth=1.8, linestyle="--",
               label=f"中位数 = {_money(med)}")
    ax.axvline(float(np.mean(v)), color="#FFC000", linewidth=1.8, linestyle=":",
               label=f"均值 = {_money(float(np.mean(v)))}")
    ax.set_title("图11  订单金额分布直方图（已剔除最高 2% 极值）", pad=14)
    ax.set_xlabel(f"单笔订单金额（{GBP}）")
    ax.set_ylabel("订单数（笔）")
    ax.legend(fontsize=9.5)
    return _out(fig, "fig11_order_value_histogram")


def fig12_boxplot(fact: pd.DataFrame, country: pd.DataFrame) -> Path:
    """模板12：箱线图（主要国家订单金额分布）。"""
    top9 = country.head(9)["Country"].tolist()
    d = fact[fact["Country"].isin(top9)]
    inv = d.groupby(["Invoice", "Country"])["Revenue"].sum().reset_index()
    data = [inv.loc[inv["Country"] == c, "Revenue"].values for c in top9]
    labels = top9
    fig, ax = plt.subplots(figsize=(12.5, 5.8))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, showmeans=True,
                    medianprops=dict(color="#C00000", linewidth=2),
                    meanprops=dict(marker="D", markerfacecolor="#FFC000", markersize=5))
    for patch, color in zip(bp["boxes"], st.EXCEL_PALETTE):
        patch.set_facecolor(color)
        patch.set_alpha(0.72)
    ax.set_yscale("log")
    ax.set_ylabel(f"单笔订单金额（{GBP}，对数轴）")
    ax.set_xlabel("国家 / 地区")
    ax.set_title("图12  主要国家订单金额分布箱线图", pad=14)
    ax.legend([bp["medians"][0], bp["means"][0]], ["中位数", "均值"], fontsize=9.5)
    return _out(fig, "fig12_boxplot_country")


def fig13_heatmap(heat: pd.DataFrame) -> Path:
    """模板13：热力图（星期 × 时段 销售额）。"""
    piv = heat.pivot(index="Hour", columns="Weekday", values="Revenue").fillna(0) / 1000
    piv = piv.reindex(range(6, 22)).fillna(0)
    piv.columns = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][:piv.shape[1]]
    fig, ax = plt.subplots(figsize=(11, 6.4))
    im = ax.imshow(piv.values, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(piv.shape[1]))
    ax.set_xticklabels(piv.columns)
    ax.set_yticks(range(piv.shape[0]))
    ax.set_yticklabels([f"{h}:00" for h in piv.index])
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if v > 0:
                ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=8,
                        color="white" if v > piv.values.max() * 0.45 else "#262626")
    cb = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label(f"销售额（千{GBP}）", fontsize=9)
    ax.set_title("图13  星期 × 时段 销售额热力图", pad=14)
    ax.grid(False)
    return _out(fig, "fig13_weekday_hour_heatmap")


def fig14_radar(country: pd.DataFrame, fact: pd.DataFrame) -> Path:
    """模板14：雷达图（TOP5 国家多指标对比）。"""
    top5 = country.head(5)["Country"].tolist()
    d = fact[fact["Country"].isin(top5)]
    agg = d.groupby("Country").agg(
        Revenue=("Revenue", "sum"), Orders=("Invoice", "nunique"),
        Customers=("CustomerID", lambda s: s[s != "GUEST"].nunique()),
        Items=("Quantity", "sum"), AOV=("Revenue", "mean")).reset_index()
    metrics = ["Revenue", "Orders", "Customers", "Items", "AOV"]
    labels = ["销售额", "订单数", "客户数", "销量", "平均客单价"]
    norm = agg.set_index("Country")[metrics].copy()
    norm = norm.div(norm.max(axis=0), axis=1)
    ang = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    ang += ang[:1]
    fig, ax = plt.subplots(figsize=(8.6, 8), subplot_kw=dict(polar=True))
    for i, cname in enumerate([c for c in top5 if c in norm.index]):
        vals = norm.loc[cname].tolist()
        vals += vals[:1]
        ax.plot(ang, vals, color=st.EXCEL_PALETTE[i], linewidth=2, label=cname)
        ax.fill(ang, vals, color=st.EXCEL_PALETTE[i], alpha=0.12)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_title("图14  TOP5 国家多维度对比雷达图", pad=24, fontsize=13)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12), fontsize=9.5, frameon=False)
    return _out(fig, "fig14_country_radar")


def fig15_waterfall(monthly: pd.DataFrame) -> Path:
    """模板15：瀑布图（近 12 个月销售额累计增量链路）。"""
    m = monthly.tail(13).copy()
    base = m["Revenue"].iloc[0] / 1000
    deltas = [(m["Revenue"].iloc[i] - m["Revenue"].iloc[i - 1]) / 1000
              for i in range(1, len(m))]
    cats = m["MonthPeriod"].iloc[1:].tolist()
    fig, ax = plt.subplots(figsize=(13.5, 5.6))
    ch.waterfall_chart(ax, cats, deltas, start=base, final_label="期末",
                       fmt="{:,.0f}")
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_title("图15  近 12 个月销售额增量链路瀑布图", pad=14)
    return _out(fig, "fig15_monthly_waterfall")


def fig16_gauge(monthly: pd.DataFrame) -> Path:
    """模板16：仪表盘（年度销售目标达成率）。"""
    m = monthly.copy()
    m["Year"] = m["MonthPeriod"].str[:4].astype(int)
    y = m.groupby("Year")["Revenue"].sum() / 1000
    cur_year, prev_year = int(y.index[-1]), int(y.index[-2])
    target = y.loc[prev_year] * 1.15            # 业务假设：年目标 = 上年 × (1 + 15%)
    actual = y.loc[cur_year]
    rate = actual / target * 100
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    ch.gauge_chart(axes[0], rate, title=f"{cur_year} 年销售目标达成率\n目标 {target:,.0f} k{GBP} ｜ "
                                        f"实际 {actual:,.0f} k{GBP}")
    axes[0].set_title("目标达成情况", fontsize=12)
    ax = axes[1]
    yrs = y.index.astype(str).tolist()
    bars = ax.bar(yrs, y.values, color=["#A5A5A5", "#4472C4"], width=0.55, zorder=3)
    if len(y) >= 2:
        ax.plot([0, 1], [y.values[-2], target], color="#C00000", linestyle="--",
                marker="o", linewidth=1.6, label="增长率目标 +15%")
    st.add_value_labels(ax, bars, fmt="{:,.0f}")
    ax.axhline(target, color="#FFC000", linewidth=1.4, linestyle=":",
               label=f"目标 {target:,.0f} k{GBP}")
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_title("年度销售额 vs 目标", fontsize=12)
    ax.legend(fontsize=9)
    fig.suptitle("图16  KPI 仪表盘与目标达成分析", fontsize=14, fontweight="bold", y=1.02)
    return _out(fig, "fig16_gauge_target")


def fig17_calendar(daily: pd.DataFrame) -> Path:
    """模板17：日历热力图。"""
    d = daily.copy()
    fig, ax = plt.subplots(figsize=(14, 5.2))
    ch.calendar_heatmap(ax, d["OrderDate"], d["Revenue"] / 1000, cmap="YlOrRd")
    ax.set_title("图17  日销售额日历热力图（单位：千£）", pad=14)
    return _out(fig, "fig17_calendar_heatmap")


def fig18_slope(fact: pd.DataFrame, country: pd.DataFrame) -> Path:
    """模板18：坡度图（2010 vs 2011 国别销售额变化）。"""
    d = fact[fact["OrderDate"] <= "2011-11-30"]
    d = d.copy()
    d["Year"] = pd.to_datetime(d["OrderDate"]).dt.year
    top8 = country.head(8)["Country"].tolist()
    p = (d[d["Country"].isin(top8)].pivot_table(index="Country", columns="Year",
                                                values="Revenue", aggfunc="sum")
         .reindex(top8).fillna(0) / 1000)
    years = sorted([c for c in p.columns if c in (2010, 2011)])
    if len(years) < 2:
        years = list(p.columns)[-2:]
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    ch.slope_chart(ax, list(p[years[0]].values), list(p[years[1]].values),
                   [f"{COUNTRY_CN.get(c, c)}" for c in p.index],
                   f"{years[0]} 年", f"{years[1]} 年", highlight_k=4)
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_title(f"图18  TOP8 国家 {years[0]} → {years[1]} 年销售额变化坡度图", pad=14)
    return _out(fig, "fig18_slope_top_countries")


def fig19_dual_axis(monthly: pd.DataFrame) -> Path:
    """模板19：组合图（销售额柱 + 订单数折线 + 客单价折线）。"""
    m = monthly.copy()
    fig, ax = plt.subplots(figsize=(13, 5.6))
    ax.bar(m["MonthPeriod"], m["Revenue"] / 1000, color="#BDD7EE", width=0.66,
           label="销售额", zorder=2)
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_xlabel("月份")
    ax2 = ax.twinx()
    ax2.plot(m["MonthPeriod"], m["Orders"], color="#ED7D31", marker="o", markersize=4,
             linewidth=1.8, label="订单数")
    ax2.set_ylabel("订单数（笔）")
    ax3 = ax.twinx()
    ax3.spines["right"].set_position(("outward", 60))
    ax3.plot(m["MonthPeriod"], m["AOV"], color="#7030A0", marker="^", markersize=4,
             linewidth=1.6, linestyle="--", label="客单价")
    ax3.set_ylabel(f"客单价（{GBP}）")
    ax.set_xticks(range(len(m)))
    ax.set_xticklabels(m["MonthPeriod"], rotation=60, ha="right", fontsize=8.5)
    hs = ax.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0] + \
        ax3.get_legend_handles_labels()[0]
    ls = ax.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1] + \
        ax3.get_legend_handles_labels()[1]
    ax.legend(hs, ls, loc="upper left", fontsize=9.5, ncol=3)
    ax.set_title("图19  销售额·订单数·客单价三轴组合图", pad=14)
    return _out(fig, "fig19_dual_axis_revenue_orders")


def fig20_rose(cat: pd.DataFrame) -> Path:
    """模板20：玫瑰图 / 南丁格尔图（品类销售结构）。"""
    c = cat.head(10).copy()
    n = len(c)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    width = 2 * np.pi / n * 0.92
    fig, ax = plt.subplots(figsize=(9.5, 8.4), subplot_kw=dict(polar=True))
    radii = np.sqrt(c["Revenue"] / c["Revenue"].max())
    bars = ax.bar(theta, radii * 0.95, width=width, bottom=0.12,
                  color=st.EXCEL_PALETTE[:n], alpha=0.88, edgecolor="white", linewidth=1.2)
    for b, r, catname, share in zip(bars, radii, c["ProductCategory"], c["RevenueShare"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.16,
                f"{_wrap(catname, 14)}\n{share:.1f}%", ha="center", va="center", fontsize=8.5)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_ylim(0, 1.3)
    ax.set_title("图20  商品品类销售额结构玫瑰图", pad=22, fontsize=13)
    ax.grid(False)
    return _out(fig, "fig20_rose_category")


def fig21_bullet(cat: pd.DataFrame) -> Path:
    """模板21：子弹图（各品类实际销售额 vs 目标）。"""
    c = cat.head(9).copy()
    # 业务假设：目标 = 该品类均值 × 1.10（作为稳健增长目标）
    targets = [c["Revenue"].mean() * 1.10] * len(c)
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    ch.bullet_chart(ax, c["ProductCategory"].map(lambda s: _wrap(s, 16)).tolist(),
                    (c["Revenue"] / 1000).tolist(), [t / 1000 for t in targets],
                    bands=(0.4, 0.75, 1.0), fmt="{:,.0f}")
    ax.set_xlabel(f"销售额（千{GBP}）")
    ax.set_title("图21  品类销售额子弹图（目标 = 品类均值×1.10）", pad=14)
    return _out(fig, "fig21_bullet_category")


def fig22_violin(orders: pd.DataFrame) -> Path:
    """模板22：小提琴图（各季度订单金额分布）。"""
    o = orders.copy()
    o["Quarter"] = pd.to_datetime(o["OrderDate"]).dt.to_period("Q").astype(str)
    o = o[o["Revenue"] <= o["Revenue"].quantile(0.97)]
    fig, ax = plt.subplots(figsize=(13, 5.6))
    groups = [g["Revenue"].values for _, g in o.groupby("Quarter")]
    labels = list(dict.fromkeys(o.sort_values("Quarter")["Quarter"]))
    if HAS_SNS:
        sns.violinplot(data=o, x="Quarter", y="Revenue", inner="quartile",
                       palette="Blues", ax=ax, linewidth=0.9, cut=0)
    else:
        parts = ax.violinplot(groups, showmedians=True)
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(st.EXCEL_PALETTE[i % len(st.EXCEL_PALETTE)])
    ax.set_xlabel("季度")
    ax.set_ylabel(f"单笔订单金额（{GBP}）")
    ax.set_title("图22  各季度订单金额分布小提琴图", pad=14)
    _ = labels
    return _out(fig, "fig22_violin_order_value")


def fig23_treemap(abc: pd.DataFrame, cat: pd.DataFrame) -> Path:
    """模板23：矩形树图（品类销售额构成）。"""
    sizes = cat["Revenue"].values
    labels = cat["ProductCategory"].tolist()
    extra = [f"{s:.1f}%\n{_money(v)}" for s, v in zip(cat["RevenueShare"], cat["Revenue"])]
    fig, ax = plt.subplots(figsize=(13, 7))
    ch.squarify_treemap(ax, sizes, labels=labels, extra_texts=extra,
                        colors=st.EXCEL_PALETTE, fontsize=10, min_show=0.035)
    ax.set_title("图23  商品品类销售额矩形树图（面积=销售额）", pad=14)
    return _out(fig, "fig23_treemap_category")


def fig24_wordcloud(products: pd.DataFrame) -> Path:
    """模板24：词云图（热销商品描述词频）。"""
    from wordcloud import WordCloud
    text = " ".join(products["Description"].astype(str).tolist()).upper()
    stop = set("""OF SET THE AND WITH IN A TO FOR PCS PACK BOX SETS 3 6 12
                  ASSORTED COLOUR COLOURS DESIGN DESIGNS RETROSPOT LOVE HEART
                  JUMBO GIFT WRAP BAG OF SMALL LARGE XL """.split())
    # random_state 固定，保证词云布局跨运行完全一致（可复现性要求）
    wc = WordCloud(width=1500, height=760, background_color="white",
                   font_path=None, colormap="tab20", max_words=170,
                   stopwords=stop, collocations=False,
                   prefer_horizontal=0.72, random_state=cfg.RANDOM_SEED).generate(text)
    fig, ax = plt.subplots(figsize=(13, 6.6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("图24  热销商品描述词云图（字号 = 出现频次）", pad=14)
    return _out(fig, "fig24_wordcloud_products")


def fig25_moving_average(daily: pd.DataFrame) -> Path:
    """模板25 + M1：多线图（7/30/90 日移动平均）。"""
    d = daily.copy()
    d["MA90"] = d["Revenue"].rolling(90).mean()
    fig, ax = plt.subplots(figsize=(13.5, 5.4))
    ax.plot(d["OrderDate"], d["Revenue"] / 1000, color="#BFBFBF", linewidth=0.7,
            label="日销售额", zorder=2)
    ax.plot(d["OrderDate"], d["MA7"] / 1000, color="#4472C4", linewidth=1.3,
            label="MA7（周移动平均）", zorder=3)
    ax.plot(d["OrderDate"], d["MA30"] / 1000, color="#ED7D31", linewidth=1.9,
            label="MA30（月移动平均）", zorder=4)
    ax.plot(d["OrderDate"], d["MA90"] / 1000, color="#C00000", linewidth=2.2,
            label="MA90（季移动平均）", zorder=5)
    ax.set_title("图25  多重移动平均线：消除噪声后的销售趋势（M1 趋势与对比）", pad=14)
    ax.set_xlabel("日期")
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.legend(loc="upper left", fontsize=9.5, ncol=4)
    return _out(fig, "fig25_moving_average")


# ===========================================================================
# ============================ B. 业务模型类 =================================
# ===========================================================================
_SEG_COLORS = {
    "重要价值客户": "#C00000", "重要保持客户": "#E36C0A", "重要发展客户": "#FFC000",
    "重要挽留客户": "#7030A0", "一般价值客户": "#4472C4", "一般保持客户": "#5B9BD5",
    "一般发展客户": "#70AD47", "一般挽留客户": "#A5A5A5",
}


def fig26_rfm_scatter(rfm: pd.DataFrame) -> Path:
    """M2：RFM 气泡散点图（Recency × Monetary，气泡=Frequency，颜色=八分类）。"""
    r = rfm.copy()
    fig, ax = plt.subplots(figsize=(12.5, 7))
    for seg, sub in r.groupby("Segment", observed=True):
        sizes = np.clip(sub["Frequency"] * 9 + 14, 14, 460)
        ax.scatter(sub["Frequency"], sub["Monetary"], s=sizes, label=seg,
                   color=_SEG_COLORS.get(seg, "#4472C4"), alpha=0.72,
                   edgecolors="white", linewidths=0.5)
    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency 购买频次（次，对数轴）")
    ax.set_ylabel(f"Monetary 累计消费金额（{GBP}，对数轴）")
    ax.set_title("图26  RFM 客户价值气泡矩阵（气泡大小 = 购买频次，共八类客群）", pad=14)
    ax.legend(title="RFM 八分类", loc="upper left", fontsize=9.5,
              bbox_to_anchor=(1.02, 1.0), title_fontsize=10.5, frameon=False)
    ax.grid(alpha=0.25, linestyle="--")
    return _out(fig, "fig26_rfm_scatter_ch8")


def fig27_rfm_segments(seg: pd.DataFrame) -> Path:
    """M2：RFM 八分类——客户数占比 vs 金额贡献的双柱与帕累托式对比。"""
    s = seg.copy()
    s["Segment"] = s["Segment"].astype(str)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    ax = axes[0]
    colors = [_SEG_COLORS.get(x, "#4472C4") for x in s["Segment"]]
    bars = ax.barh(s["Segment"], s["Customers"], color=colors, height=0.68, zorder=3)
    ax.set_xlabel("客户数（人）")
    ax.set_title("各分群客户规模", fontsize=12)
    for bar, v, sh in zip(bars, s["Customers"], s["CustomerShare"]):
        ax.text(v * 1.02, bar.get_y() + bar.get_height() / 2, f"{v:,}（{sh}%）",
                va="center", fontsize=8.5, color="#404040")
    ax2 = axes[1]
    bars2 = ax2.barh(s["Segment"], s["Monetary"] / 1000, color=colors, height=0.68, zorder=3)
    ax2.set_xlabel(f"贡献销售额（千{GBP}）")
    ax2.set_title("各分群金额贡献", fontsize=12)
    for bar, v, sh in zip(bars2, s["Monetary"] / 1000, s["RevenueShare"]):
        ax2.text(v * 1.02, bar.get_y() + bar.get_height() / 2, f"{v:,.1f}（{sh}%）",
                 va="center", fontsize=8.5, color="#404040")
    fig.suptitle("图27  RFM 八分类客户规模与金额贡献对比", fontsize=14, fontweight="bold", y=1.03)
    return _out(fig, "fig27_rfm_segment_bar")


def fig28_cohort(rate: pd.DataFrame) -> Path:
    """M3：同期群留存热力图。"""
    cols = [c for c in rate.columns if str(c).isdigit()]
    mat = rate[cols].astype(float).values
    idx = rate["CohortMonth"].astype(str).tolist()
    fig, ax = plt.subplots(figsize=(14, 8))
    masked = np.ma.array(mat, mask=mat == 0)
    im = ax.imshow(masked, cmap="YlGnBu", aspect="auto", vmin=0, vmax=60)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([f"M{c}" for c in cols])
    ax.set_yticks(range(len(idx)))
    ax.set_yticklabels(idx)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if v > 0:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if v > 28 else "#262626")
    cb = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("留存率（%）", fontsize=9)
    ax.set_xlabel("距首次购买的月数（Cohort Index）")
    ax.set_ylabel("首购月份（Cohort）")
    ax.set_title("图28  客户同期群月度留存率热力图（%）", pad=14)
    ax.grid(False)
    return _out(fig, "fig28_cohort_retention_heatmap")


def fig29_pareto(top30: pd.DataFrame, abc_sum: pd.DataFrame) -> Path:
    """M4：帕累托图（销售额降序柱 + 累计占比折线 + ABC 分界线）。"""
    p = top30.copy()
    fig, ax = plt.subplots(figsize=(13.5, 5.8))
    colors = {"A": "#C00000", "B": "#FFC000", "C": "#A5A5A5"}
    bars = ax.bar(p["Description"].map(lambda s: _wrap(s, 17)), p["Revenue"] / 1000,
                  color=[colors.get(a, "#4472C4") for a in p["ABCCategory"]],
                  width=0.66, zorder=3)
    ax.set_ylabel(f"销售额（千{GBP}）")
    ax.set_xticklabels(p["Description"].map(lambda s: _wrap(s, 17)), rotation=60,
                       ha="right", fontsize=7.6)
    ax2 = ax.twinx()
    ax2.plot(range(len(p)), p["CumulativeShare"], color="#2E75B6", marker="o",
             markersize=4, linewidth=2, label="累计占比")
    ax2.axhline(80, color="#C00000", linewidth=1.4, linestyle="--", label="A 类边界 80%")
    ax2.set_ylabel("累计占比（%）")
    ax2.set_ylim(0, 105)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in ("A", "B", "C")]
    ax.legend(handles, ["A 类（累计 ≤80%）", "B 类（≤95%）", "C 类（>95%）"],
              loc="upper left", fontsize=9.5)
    ax2.legend(loc="lower right", fontsize=9.5)
    ax.set_title("图29  TOP30 商品销售额帕累托图（80/20 法则与 ABC 分类）", pad=14)
    return _out(fig, "fig29_pareto_abc")


def fig30_apriori_scatter(rules: pd.DataFrame) -> Path:
    """M5：关联规则散点图（support × confidence，颜色/气泡 = lift）。"""
    r = rules.copy()
    fig, ax = plt.subplots(figsize=(12, 6.8))
    sc = ax.scatter(r["support"] * 100, r["confidence"] * 100,
                    s=np.clip((r["lift"] - 1) * 900 + 30, 30, 620),
                    c=r["lift"], cmap="YlOrRd", alpha=0.78,
                    edgecolors="#595959", linewidths=0.5)
    cb = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("提升度 Lift", fontsize=9)
    top = r.head(6)
    for _, row in top.iterrows():
        ax.annotate(f"{row['AntecedentNames'][:26]} → {row['ConsequentNames'][:20]}",
                    xy=(row["support"] * 100, row["confidence"] * 100),
                    xytext=(7, 6), textcoords="offset points", fontsize=8,
                    color="#404040",
                    arrowprops=dict(arrowstyle="-", color="#BFBFBF", linewidth=0.7))
    ax.axhline(cfg.APRIORI_MIN_CONF * 100, color="#808080", linestyle=":", linewidth=1.2,
               label=f"最小置信度 {cfg.APRIORI_MIN_CONF:.0%}")
    ax.axvline(cfg.APRIORI_MIN_SUPPORT * 100, color="#808080", linestyle="--", linewidth=1.2,
               label=f"最小支持度 {cfg.APRIORI_MIN_SUPPORT:.0%}")
    ax.axhline(1, color="#C00000", linestyle=":", linewidth=1.2)
    ax.set_xlabel("支持度 Support（%）")
    ax.set_ylabel("置信度 Confidence（%）")
    ax.set_title("图30  购物篮关联规则分布（气泡大小与颜色 = 提升度 Lift）", pad=14)
    ax.legend(fontsize=9.5, loc="lower right")
    return _out(fig, "fig30_apriori_rules_scatter")


def fig31_apriori_network(rules: pd.DataFrame) -> Path:
    """M5：关联规则网络图（环形布局，边宽 = 提升度）。"""
    r = rules.head(24).copy()
    nodes = sorted({c.strip() for row in r["antecedents"] for c in row.split(",")} |
                   {c.strip() for row in r["consequents"] for c in row.split(",")})
    if len(nodes) < 3:
        nodes = list(nodes)
    n = max(len(nodes), 1)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos = {node: (np.cos(a), np.sin(a)) for node, a in zip(nodes, ang)}
    fig, ax = plt.subplots(figsize=(11, 9.5))
    max_lift = max(r["lift"].max(), 1.01)
    for _, row in r.iterrows():
        srcs = [c.strip() for c in row["antecedents"].split(",")]
        dsts = [c.strip() for c in row["consequents"].split(",")]
        for s in srcs:
            for d in dsts:
                if s not in pos or d not in pos:
                    continue
                x1, y1 = pos[s]
                x2, y2 = pos[d]
                lw = 0.8 + (row["lift"] - 1) / (max_lift - 1) * 4.2
                alpha = 0.25 + (row["lift"] - 1) / (max_lift - 1) * 0.45
                ax.plot([x1, x2], [y1, y2], color="#4472C4", linewidth=lw, alpha=alpha,
                        solid_capstyle="round", zorder=1)
    deg = {}
    for _, row in r.iterrows():
        for c in [c.strip() for c in row["antecedents"].split(",")] + \
                 [c.strip() for c in row["consequents"].split(",")]:
            deg[c] = deg.get(c, 0) + 1
    for i, node in enumerate(nodes):
        x, y = pos[node]
        size = 260 + deg.get(node, 1) * 130
        ax.scatter([x], [y], s=size, color=st.EXCEL_PALETTE[i % len(st.EXCEL_PALETTE)],
                   alpha=0.9, edgecolors="white", linewidths=1.4, zorder=3)
        ax.text(x * 1.16, y * 1.16, node, ha="center", va="center", fontsize=8.5,
                color="#262626", fontweight="bold", zorder=4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("图31  TOP24 关联规则商品共现网络图（连线粗细 = 提升度）", pad=16)
    return _out(fig, "fig31_apriori_network")


def fig32_bcg(bcg: pd.DataFrame, params: dict) -> Path:
    """M6：波士顿矩阵四象限图。"""
    b = bcg.copy()
    x_cut, y_cut = 1.0, params["growth_threshold"]
    fig, ax = plt.subplots(figsize=(12.5, 7.6))
    xmin = min(b["RelativeShare"].min() * 0.75, 0.4)
    xmax = b["RelativeShare"].max() * 1.15
    ax.axvspan(xmin, x_cut, ymin=0, ymax=1, color="#F2F2F2", alpha=0.55, zorder=0)
    ax.axvline(x_cut, color="#808080", linewidth=1.3, linestyle="--", zorder=1)
    ax.axhline(y_cut, color="#808080", linewidth=1.3, linestyle="--", zorder=1)
    qcolors = {"明星 Stars": "#C00000", "金牛 Cash Cows": "#4472C4",
               "问题 Question Marks": "#FFC000", "瘦狗 Dogs": "#A5A5A5"}
    sizes = (b["Revenue_Last12M"] / b["Revenue_Last12M"].max() * 3600) + 260
    for q, sub in b.groupby("Quadrant"):
        ax.scatter(sub["RelativeShare"], sub["YoY_Growth"],
                   s=[sizes[i] for i in sub.index], color=qcolors.get(q, "#4472C4"),
                   alpha=0.78, edgecolors="white", linewidths=1.2, label=q, zorder=3)
    for _, row in b.iterrows():
        ax.annotate(f"{row['ProductCategory']}\n{row['RevenueShare']:.1f}%",
                    xy=(row["RelativeShare"], row["YoY_Growth"]), ha="center", va="center",
                    fontsize=8.5, color="white" if row["RevenueShare"] > 8 else "#262626",
                    fontweight="bold", zorder=4)
    pad_x = (xmax - xmin) * 0.035
    pad_y = (b["YoY_Growth"].max() - b["YoY_Growth"].min()) * 0.06
    ax.text(xmin + pad_x, b["YoY_Growth"].max() - pad_y, "明星 Stars", fontsize=11,
            color="#C00000", fontweight="bold", va="top", ha="left")
    ax.text(xmax - pad_x, b["YoY_Growth"].max() - pad_y, "金牛 Cash Cows", fontsize=11,
            color="#2E75B6", fontweight="bold", va="top", ha="right")
    ax.text(xmin + pad_x, b["YoY_Growth"].min() + pad_y, "瘦狗 Dogs", fontsize=11,
            color="#808080", fontweight="bold", va="bottom", ha="left")
    ax.text(xmax - pad_x, b["YoY_Growth"].min() + pad_y, "问题 Question Marks", fontsize=11,
            color="#997300", fontweight="bold", va="bottom", ha="right")
    ax.set_xlabel("相对市场份额（该品类销售额 / 其余品类平均销售额，虚线 = 1.0）")
    ax.set_ylabel(f"销售额同比增速（%，虚线 = 市场平均 {y_cut:.1f}%）")
    ax.set_title("图32  商品品类组合的波士顿矩阵（BCG）分析", pad=16)
    ax.legend(loc="lower left", fontsize=9.5, frameon=True)
    ax.grid(alpha=0.2, linestyle="--")
    return _out(fig, "fig32_bcg_matrix")


def fig33_forecast(hist: pd.DataFrame, bt: pd.DataFrame, future: pd.DataFrame,
                   summary: dict) -> Path:
    """M7：时间序列预测图（历史 + 回测对比 + 未来点预测与 95% 置信区间）。"""
    h = pd.to_datetime(hist["OrderDate"])
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(h, hist["Revenue"] / 1000, color="#BFBFBF", linewidth=0.9, label="历史实际销售额")
    f = pd.to_datetime(future["OrderDate"])
    ax.plot(f, future["Forecast"] / 1000, color="#C00000", linewidth=2.2, marker="o",
            markersize=3.5, label="未来 30 天点预测")
    ax.fill_between(f, future["CI95_Lower"].clip(lower=0) / 1000,
                    future["CI95_Upper"] / 1000, color="#C00000", alpha=0.16,
                    label="95% 置信区间")
    act = future.dropna(subset=["Actual"])
    if len(act):
        ax.plot(pd.to_datetime(act["OrderDate"]), act["Actual"] / 1000, color="#548235",
                linewidth=2.0, marker="s", markersize=4.5, label="实际值（用于验证）")
    bt_h = bt[bt["Model"] == bt["Model"].unique()[0]]
    btd = pd.to_datetime(bt_h["OrderDate"])
    ax.plot(btd, bt_h["Predicted"] / 1000, color="#5B9BD5", linewidth=1.6, linestyle="--",
            label=f"回测期预测（{summary['best_model']}）")
    ax.axvspan(btd.min(), btd.max(), color="#FFC000", alpha=0.10, zorder=0)
    m = summary["metrics"][summary["best_model"]]
    ax.text(0.015, 0.95, f"最优模型：{summary['best_model']}\n回测 MAPE = {m['MAPE']}%\n"
                         f"回测 RMSE = {m['RMSE']:,.0f} {GBP}",
            transform=ax.transAxes, va="top", ha="left", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="#BFBFBF", alpha=0.92))
    ax.set_xlabel("日期")
    ax.set_ylabel(f"日销售额（千{GBP}）")
    ax.set_title("图33  日销售额时间序列预测（含回测区间与 95% 置信带）", pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=5, fontsize=9.5,
              frameon=False)
    return _out(fig, "fig33_forecast_ci")


def fig34_kmeans(labels: pd.DataFrame, prof: pd.DataFrame) -> Path:
    """M8：K-Means 客户分群（散点 + 分群画像）。"""
    l = labels.copy()
    fig = plt.figure(figsize=(14, 5.8))
    ax = fig.add_subplot(1, 2, 1)
    for i, (cl, sub) in enumerate(l.groupby("ClusterName")):
        ax.scatter(sub["Frequency"], sub["Monetary"], s=26, alpha=0.72,
                   color=st.EXCEL_PALETTE[i % len(st.EXCEL_PALETTE)], label=cl,
                   edgecolors="white", linewidths=0.4)
    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.set_xlabel("购买频次（次，对数轴）")
    ax.set_ylabel(f"累计消费金额（{GBP}，对数轴）")
    ax.set_title("客户分群散点图", fontsize=12)
    ax.legend(fontsize=9, loc="lower right", frameon=True)
    ax2 = fig.add_subplot(1, 2, 2)
    x = np.arange(len(prof))
    w = 0.36
    ax2.bar(x - w / 2, prof["CustomerShare"], w, color="#5B9BD5", label="客户占比（%）")
    ax2.bar(x + w / 2, prof["RevenueShare"], w, color="#ED7D31", label="金额占比（%）")
    ax2.set_xticks(x)
    ax2.set_xticklabels(prof["ClusterName"], fontsize=9, rotation=18, ha="right")
    ax2.set_ylabel("占比（%）")
    ax2.set_title("分群画像：客户占比 vs 金额贡献", fontsize=12)
    for i, (cs, rs) in enumerate(zip(prof["CustomerShare"], prof["RevenueShare"])):
        ax2.text(i - w / 2, cs + 0.6, f"{cs}%", ha="center", fontsize=8.5)
        ax2.text(i + w / 2, rs + 0.6, f"{rs}%", ha="center", fontsize=8.5)
    ax2.legend(fontsize=9)
    fig.suptitle("图34  K-Means 客户分群结果与分群画像", fontsize=14, fontweight="bold", y=1.02)
    return _out(fig, "fig34_kmeans_clusters")


def fig35_funnel(funnel: pd.DataFrame) -> Path:
    """M9：复购漏斗图。"""
    f = funnel.copy()
    fig, ax = plt.subplots(figsize=(11.5, 6.6))
    ch.funnel_chart(ax, f["Stage"].tolist(), f["Customers"].tolist(),
                    colors=["#2E75B6", "#4472C4", "#5B9BD5", "#9DC3E6", "#BDD7EE"])
    ax.set_title("图35  客户复购转化漏斗图", pad=14)
    return _out(fig, "fig35_repurchase_funnel")


# ===========================================================================
def main() -> None:
    print(cfg.banner("STEP 04 · 数据可视化（35 张图，全 Python 实现）"))
    iou.log(f"字体设置：{st.CHOSEN_FONT}")

    monthly = _load("03_mom_yoy_monthly.csv")
    daily = _load("03_daily_series.csv", parse_dates=["OrderDate"])
    cat = _load("03_category_summary.csv")
    country = _load("03_country_summary.csv")
    heat = _load("03_weekday_hour_matrix.csv")
    products = _load("03_top_products.csv")
    rfm = _load("03_rfm_customer.csv")
    seg = _load("03_rfm_segment_summary.csv")
    cohort_rate = _load("03_cohort_retention_rate.csv")
    abc = _load("03_abc_products.csv")
    abc_sum = _load("03_abc_summary.csv")
    top30 = _load("03_pareto_top30.csv")
    rules = _load("03_apriori_rules.csv")
    bcg = _load("03_bcg_matrix.csv")
    bcg_params = (cfg.TAB_DIR / "03_bcg_params.json").read_text(encoding="utf-8")
    import json as _json
    bcg_params = _json.loads(bcg_params)
    hist = _load("03_forecast_history.csv")
    bt = _load("03_forecast_backtest.csv")
    future = _load("03_forecast_future.csv")
    fc_summary = _json.loads((cfg.TAB_DIR / "03_forecast_summary.json").read_text(encoding="utf-8"))
    klabels = _load("03_kmeans_customer_labels.csv")
    kprof = _load("03_kmeans_cluster_profile.csv")
    funnel = _load("03_repurchase_funnel.csv")
    orders = pd.read_csv(cfg.CLEAN_DIR / "dim_orders.csv", parse_dates=["OrderDate"])
    fact = pd.read_csv(cfg.CLEAN_DIR / "fact_order_items.csv", parse_dates=["OrderDate"],
                       low_memory=False)

    iou.log("—— A. 模板复现类（fig01–fig25）——")
    _register(1, "fig01_mom_yoy", "模板/模型", "组合图·环比同比", "月度销售额柱 + MoM/YoY 双轴折线")
    fig01_mom_yoy(monthly)
    _register(2, "fig02_revenue_trend_line", "模板复现", "折线图", "日销售额趋势 + MA30 + 峰值标注")
    fig02_trend_line(daily)
    _register(3, "fig03_monthly_revenue_area", "模板复现", "面积图", "月度销售额与订单量双面积图")
    fig03_area(monthly)
    _register(4, "fig04_top_countries_bar", "模板复现", "柱形图", "国家销售额 TOP12 + 数据标签")
    fig04_bar(country)
    _register(5, "fig05_top_products_barh", "模板复现", "条形图", "商品销售额 TOP15 横向条形")
    fig05_barh(products)
    _register(6, "fig06_country_donut", "模板复现", "环形图", "国家销售额结构 + 中心总计")
    fig06_donut(country)
    _register(7, "fig07_monthly_stacked_bar", "模板复现", "堆积柱形图", "月度销售额国别构成")
    fig07_stacked(fact, country)
    _register(8, "fig08_category_pct_stacked", "模板复现", "百分比堆积柱形图", "月度品类结构占比")
    fig08_pct_stacked(fact)
    _register(9, "fig09_aov_frequency_scatter", "模板复现", "散点图", "频次 × 金额 + 幂律趋势线")
    fig09_scatter(rfm)
    _register(10, "fig10_country_bubble", "模板复现", "气泡图", "客户数 × 客单价 × 销售额")
    fig10_bubble(country)
    _register(11, "fig11_order_value_histogram", "模板复现", "直方图", "订单金额分布 + KDE + 均值/中位数线")
    fig11_hist(orders)
    _register(12, "fig12_boxplot_country", "模板复现", "箱线图", "主要国家订单金额分布")
    fig12_boxplot(fact, country)
    _register(13, "fig13_weekday_hour_heatmap", "模板复现", "热力图", "星期 × 时段销售额")
    fig13_heatmap(heat)
    _register(14, "fig14_country_radar", "模板复现", "雷达图", "TOP5 国家五维指标对比")
    fig14_radar(country, fact)
    _register(15, "fig15_monthly_waterfall", "模板复现", "瀑布图", "近 12 个月销售额增量链路")
    fig15_waterfall(monthly)
    _register(16, "fig16_gauge_target", "模板复现", "仪表盘", "年度目标达成率 + 年度对比")
    fig16_gauge(monthly)
    _register(17, "fig17_calendar_heatmap", "模板复现", "日历热力图", "日销售额日历视图")
    fig17_calendar(daily)
    _register(18, "fig18_slope_top_countries", "模板复现", "坡度图", "TOP8 国家年度规模变化")
    fig18_slope(fact, country)
    _register(19, "fig19_dual_axis_revenue_orders", "模板复现", "三轴组合图", "销售额 + 订单数 + 客单价")
    fig19_dual_axis(monthly)
    _register(20, "fig20_rose_category", "模板复现", "玫瑰图", "品类销售额南丁格尔玫瑰图")
    fig20_rose(cat)
    _register(21, "fig21_bullet_category", "模板复现", "子弹图", "品类实际 vs 目标")
    fig21_bullet(cat)
    _register(22, "fig22_violin_order_value", "模板复现", "小提琴图", "各季度订单金额分布")
    fig22_violin(orders)
    _register(23, "fig23_treemap_category", "模板复现", "矩形树图", "品类销售额面积占比")
    fig23_treemap(abc, cat)
    _register(24, "fig24_wordcloud_products", "模板复现", "词云图", "热门商品描述词频")
    fig24_wordcloud(products)
    _register(25, "fig25_moving_average", "模板/模型", "多重折线图", "MA7/MA30/MA90 趋势平滑")
    fig25_moving_average(daily)

    iou.log("—— B. 业务模型类（fig26–fig35）——")
    _register(26, "fig26_rfm_scatter_ch8", "业务模型图", "M2 RFM 模型", "RFM 八分类气泡矩阵")
    fig26_rfm_scatter(rfm)
    _register(27, "fig27_rfm_segment_bar", "业务模型图", "M2 RFM 模型", "八分群客户规模 vs 金额贡献")
    fig27_rfm_segments(seg)
    _register(28, "fig28_cohort_retention_heatmap", "业务模型图", "M3 同期群留存", "月度同期群留存热力图")
    fig28_cohort(cohort_rate)
    _register(29, "fig29_pareto_abc", "业务模型图", "M4 帕累托/ABC", "TOP30 商品帕累托 + ABC 分界")
    fig29_pareto(top30, abc_sum)
    _register(30, "fig30_apriori_rules_scatter", "业务模型图", "M5 关联规则", "支持度 × 置信度 × 提升度")
    fig30_apriori_scatter(rules)
    _register(31, "fig31_apriori_network", "业务模型图", "M5 关联规则", "商品共现网络图")
    fig31_apriori_network(rules)
    _register(32, "fig32_bcg_matrix", "业务模型图", "M6 波士顿矩阵", "相对份额 × 增速四象限")
    fig32_bcg(bcg, bcg_params)
    _register(33, "fig33_forecast_ci", "业务模型图", "M7 时间序列预测", "点预测 + 95% 置信区间 + 回测")
    fig33_forecast(hist, bt, future, fc_summary)
    _register(34, "fig34_kmeans_clusters", "业务模型图", "M8 K-Means 分群", "散点 + 分群画像对比")
    fig34_kmeans(klabels, kprof)
    _register(35, "fig35_repurchase_funnel", "业务模型图", "M9 复购漏斗", "五级复购转化漏斗")
    fig35_funnel(funnel)

    # ---- 图表索引（CSV 中间件；完整的 Markdown 索引含大屏组件，由 06_report.py 汇总生成）
    idx_df = pd.DataFrame(_INDEX)
    idx_df.to_csv(cfg.TAB_DIR / "04_figure_index.csv", index=False, encoding="utf-8-sig")
    iou.log(f"STEP 04 完成 ✓ 共输出 {len(idx_df)} 张图 → {cfg.FIG_DIR}")


if __name__ == "__main__":
    main()
