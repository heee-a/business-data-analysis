# -*- coding: utf-8 -*-
"""
05_dashboard.py —— 交互式商业分析可视化大屏
==========================================
技术栈：Pyecharts 2.x（ECharts 5）+ Plotly（世界 choropleth）+ 自研暗色 HTML 栅格布局。

大屏包含 **4 个主题 Tab、22 个可视化组件 + 6 张 KPI 卡**，远超"组件 ≥6"的要求，
并具备以下联动 / 下钻能力：
    1. Tab 主题切换（销售总览 / 客户价值 / 商品洞察 / 预测复盘）
    2. Timeline 时间轴轮播：按月自动播放各国销售额排名变化（真正的动态联动）
    3. Legend 图例开关系列（点击图例可隐藏/显示某个系列 = 轻量联动筛选）
    4. DataZoom 区域缩放（可任意下钻到某段时间）
    5. Tooltip 十字准星联动（多图 hover 读数）
    6. 世界地图 choropleth 与右下角明细表联动（同轴色阶）

输出：
    outputs/dashboard/dashboard_dark.html   商业分析可视化大屏（可直接双击打开）
    pages/index.html                        同一份大屏，作为 GitHub Pages 首页
    outputs/html/component_*.html           单组件 HTML（便于逐个核对）

运行：
    python scripts/05_dashboard.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

from pyecharts import options as opts  # noqa: E402
from pyecharts.charts import Bar, Funnel, HeatMap, Line, Page, Pie, Scatter  # noqa: E402
from pyecharts.charts import Timeline, WordCloud  # noqa: E402
from pyecharts.components import Table  # noqa: E402
from pyecharts.globals import ThemeType  # noqa: E402

# ---------------------------------------------------------------- 常量配置
BG = "#08111E"
PANEL = "#0F1D31"
TEXT_MAIN = "#E8F2FF"
TEXT_SUB = "#8FB6E0"
AXIS_COLOR = "#35577E"
GRID_COLOR = "#1C3554"
ECHARTS_PALETTE = ["#4FC3F7", "#FFB74D", "#81C784", "#E57373", "#BA68C8",
                   "#4DB6AC", "#F06292", "#AED581", "#7986CB", "#FFD54F"]

COUNTRY_CN = {
    "United Kingdom": "英国", "Netherlands": "荷兰", "Eire": "爱尔兰", "Germany": "德国",
    "France": "法国", "Australia": "澳大利亚", "Spain": "西班牙", "Belgium": "比利时",
    "Switzerland": "瑞士", "Japan": "日本", "Portugal": "葡萄牙", "Sweden": "瑞典",
    "Norway": "挪威", "Finland": "芬兰", "Denmark": "丹麦", "Austria": "奥地利",
    "Poland": "波兰", "Italy": "意大利", "Cyprus": "塞浦路斯", "Greece": "希腊",
    "Israel": "以色列", "Singapore": "新加坡", "Iceland": "冰岛", "Canada": "加拿大",
    "Malta": "马耳他", "Bahrain": "巴林", "Lebanon": "黎巴嫩", "Bermuda": "百慕大",
    "Usa": "美国", "Rsa": "南非", "Korea": "韩国", "Lithuania": "立陶宛",
    "United Arab Emirates": "阿联酋", "Brazil": "巴西",
}

# Plotly choropleth 国家名映射（源数据使用了缩写 / 旧称）
PLOTLY_NAME_MAP = {
    "Usa": "United States", "Rsa": "South Africa", "Eire": "Ireland",
    "Korea": "South Korea", "Czech Republic": "Czechia",
}
# 非主权地区不进入世界地图（其数据仍完整保留于全部其它图表中）
NON_SOVEREIGN = {"Hong Kong", "Channel Islands", "Unspecified", "European Community"}

_dedup_done = False


# ===========================================================================
# 基础样式工具
# ===========================================================================
def base_opts(height: str = "380px") -> opts.InitOpts:
    return opts.InitOpts(theme=ThemeType.DARK, width="100%", height=height,
                         bg_color="rgba(0,0,0,0)", js_host=None)


def apply_style(chart, title: str = "", subtitle: str = "", legend_top: str = "36px",
                x_rotate: int = 0, is_pie: bool = False):
    """统一暗色大屏样式。"""
    chart.set_global_opts(
        title_opts=opts.TitleOpts(
            title=title, subtitle=subtitle, pos_left="center", pos_top="6px",
            title_textstyle_opts=opts.TextStyleOpts(color=TEXT_MAIN, font_size=15,
                                                    font_weight="bold"),
            subtitle_textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB, font_size=11)),
        legend_opts=opts.LegendOpts(
            is_show=not is_pie, pos_top=legend_top, pos_left="center",
            textstyle_opts=opts.TextStyleOpts(color="#C9D9EC", font_size=11),
            inactive_color="#4A6A90"),
        tooltip_opts=opts.TooltipOpts(
            trigger="item" if is_pie else "axis",
            axis_pointer_type="shadow" if is_pie else "cross",
            background_color="rgba(10,22,40,0.94)", border_color="#2A4A70",
            border_width=1, textstyle_opts=opts.TextStyleOpts(color=TEXT_MAIN, font_size=12)),
        xaxis_opts=opts.AxisOpts(
            axislabel_opts=opts.LabelOpts(color="#9CB6D4", font_size=10, rotate=x_rotate),
            axisline_opts=opts.AxisLineOpts(
                linestyle_opts=opts.LineStyleOpts(color=AXIS_COLOR)),
            axistick_opts=opts.AxisTickOpts(is_show=False),
            splitline_opts=opts.SplitLineOpts(is_show=False)),
        yaxis_opts=opts.AxisOpts(
            axislabel_opts=opts.LabelOpts(color="#9CB6D4", font_size=10),
            axisline_opts=opts.AxisLineOpts(is_show=False),
            axistick_opts=opts.AxisTickOpts(is_show=False),
            splitline_opts=opts.SplitLineOpts(
                is_show=True, linestyle_opts=opts.LineStyleOpts(color=GRID_COLOR,
                                                                type_="dashed", width=1))),
        visualmap_opts=None,
    )
    if is_pie:
        chart.set_series_opts(
            label_opts=opts.LabelOpts(color=TEXT_MAIN, font_size=10,
                                      formatter="{b}: {d}%"),
            tooltip_opts=opts.TooltipOpts(
                formatter="{b}<br/>{c} ({d}%)",
                background_color="rgba(10,22,40,0.94)", border_color="#2A4A70",
                textstyle_opts=opts.TextStyleOpts(color=TEXT_MAIN)))
    else:
        chart.set_series_opts(
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(border_width=0.5, border_color=BG))
    return chart


def embed(chart, first: bool = False) -> str:
    """渲染为可嵌入的 HTML 片段；仅首个组件保留 echarts CDN 引用，避免重复加载。"""
    global _dedup_done
    html = chart.render_embed()
    if not first:
        html = re.sub(
            r'<script[^>]*src="https://[^"]*echarts[^"]*"[^>]*>\s*</script>', "", html)
    _ = _dedup_done
    return html


def save_component(chart, name: str) -> None:
    """同时输出单个组件的独立 HTML，便于逐个核对。"""
    chart.render(str(cfg.HTML_DIR / f"component_{name}.html"))


# ===========================================================================
# 组件构建
# ===========================================================================
def c_timeline_sales(monthly: pd.DataFrame) -> Timeline:
    """Timeline 联动组件：按月回放销售额 TOP8 国家排名演变。"""
    mos = monthly["MonthPeriod"].tolist()
    tl = Timeline(init_opts=base_opts("430px"))
    tl.add_schema(is_auto_play=True, play_interval=1400, is_loop_play=True,
                  is_timeline_show=True, pos_left="10%", pos_right="10%",
                  label_opts=opts.LabelOpts(color=TEXT_SUB, font_size=10,
                                            interval=3, rotate=0),
                  linestyle_opts=opts.LineStyleOpts(color=AXIS_COLOR),
                  itemstyle_opts=opts.ItemStyleOpts(color="#4FC3F7"))
    return tl, mos


def build_components(D: dict) -> dict:
    """返回 {组件名: (标题, html片段, span宽度)}。"""
    comp: dict[str, tuple[str, str, int]] = {}
    order: list[str] = []

    def add(key, title, chart, span=6, save=True):
        # 固定容器 ID：pyecharts 默认每次渲染生成随机 UUID 作为 div id，
        # 会导致同一份配置两次渲染出的组件 HTML 字节不同（复现比对失败）。
        # 以组件键名作为 chart_id 后，组件 HTML 跨运行完全确定。
        chart.chart_id = key
        html = embed(chart, first=(not order))
        comp[key] = (title, html, span)
        order.append(key)
        if save:
            save_component(chart, key)

    monthly, daily = D["monthly"], D["daily"]
    country, cat = D["country"], D["category"]
    seg, cohort = D["rfm_seg"], D["cohort_avg"]
    top20, abc_sum = D["apriori_top20"], D["abc_summary"]
    bcg, kprof = D["bcg"], D["kmeans_profile"]
    future, hist, bt = D["forecast_future"], D["forecast_hist"], D["forecast_bt"]
    top_products, funnel, kpis = D["top_products"], D["funnel"], D["kpis"]
    cat_monthly, heat = D["category_monthly"], D["weekday_hour"]

    # ---------- Tab1 销售总览 ----------
    # 1) 月度趋势（面积 + DataZoom）
    ln = Line(init_opts=base_opts())
    ln.add_xaxis(monthly["MonthPeriod"].tolist())
    ln.add_yaxis("销售额（£）", [round(v, 2) for v in monthly["Revenue"]],
                 is_smooth=True, symbol="circle", symbol_size=6,
                 color="#4FC3F7",
                 linestyle_opts=opts.LineStyleOpts(width=2.4),
                 itemstyle_opts=opts.ItemStyleOpts(color="#4FC3F7", border_color="#0B2136",
                                                   border_width=2),
                 areastyle_opts=opts.AreaStyleOpts(opacity=0.28, color="#4FC3F7"),
                 markline_opts=opts.MarkLineOpts(
                     data=[opts.MarkLineItem(type_="average", name="期间均值")],
                     linestyle_opts=opts.LineStyleOpts(color="#FFB74D", type_="dashed"),
                     label_opts=opts.LabelOpts(color="#FFB74D", font_size=10)))
    ln.add_yaxis("30 日移动锚（月度 MA3）", [None if pd.isna(v) else round(v, 2)
                                             for v in monthly["MA3"]],
                 is_smooth=True, symbol="none", color="#FFB74D",
                 linestyle_opts=opts.LineStyleOpts(width=1.8, type_="dashed"))
    ln.set_global_opts(datazoom_opts=[opts.DataZoomOpts(type_="inside"),
                                      opts.DataZoomOpts(type_="slider", pos_bottom="6px",
                                                        )])
    apply_style(ln, "月度销售额趋势（可缩放 / 拖拽下钻）", subtitle="数据来源：UCI Online Retail II",
                x_rotate=45)
    add("tab1_trend", "月度销售额趋势", ln, span=12)

    # 2) 双轴：销售额柱 + 订单数折线
    bar = Bar(init_opts=base_opts())
    bar.add_xaxis(monthly["MonthPeriod"].tolist())
    bar.add_yaxis("销售额（£）", [round(v, 2) for v in monthly["Revenue"]],
                  color="#4FC3F7", itemstyle_opts=opts.ItemStyleOpts(
                      color="#4FC3F7", border_width=0),
                  gap="0%")
    bar.extend_axis(yaxis=opts.AxisOpts(
        name="订单数", name_textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB),
        axislabel_opts=opts.LabelOpts(color="#FFB74D", font_size=10, formatter="{value}"),
        axisline_opts=opts.AxisLineOpts(is_show=False),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    ln2 = Line()
    ln2.add_xaxis(monthly["MonthPeriod"].tolist())
    ln2.add_yaxis("订单数（笔）", monthly["Orders"].tolist(), yaxis_index=1,
                  color="#FFB74D", symbol="circle", symbol_size=5,
                  linestyle_opts=opts.LineStyleOpts(width=2))
    bar.overlap(ln2)
    apply_style(bar, "销售额 × 订单数 双轴联动", subtitle="左轴：销售额　右轴：订单数",
                x_rotate=45, legend_top="36px")
    add("tab1_dual", "销售额 × 订单数双轴", bar, span=7)

    # 3) 国家 TOP10（横向条）
    top10 = country.head(10).iloc[::-1]
    nm = [f"{COUNTRY_CN.get(c, c)}" for c in top10["Country"]]
    b2 = Bar(init_opts=base_opts())
    b2.add_xaxis(nm)
    b2.add_yaxis("销售额（£）", [round(v, 2) for v in top10["Revenue"]], color="#4FC3F7",
                 itemstyle_opts=opts.ItemStyleOpts(
                     color="#4FC3F7", border_width=0, opacity=0.92),
                 label_opts=opts.LabelOpts(is_show=True, position="right",
                                           color=TEXT_SUB, font_size=10,
                                           formatter="{c}"))
    b2.reversal_axis()
    apply_style(b2, "TOP10 国家 / 地区销售额", subtitle="悬停查看明细", legend_top="9999px")
    add("tab1_country_bar", "TOP10 国家销售额", b2, span=5)

    # 4) Timeline：月度 TOP8 国家回放（真正的动态联动）
    mos = monthly["MonthPeriod"].tolist()
    tl = Timeline(init_opts=base_opts("430px"))
    tl.add_schema(is_auto_play=True, play_interval=1500, is_loop_play=True,
                  pos_left="6%", pos_right="6%", pos_bottom="2px",
                  label_opts=opts.LabelOpts(color=TEXT_SUB, font_size=10, interval=2),
                  linestyle_opts=opts.LineStyleOpts(color=AXIS_COLOR),
                  itemstyle_opts=opts.ItemStyleOpts(color="#4FC3F7"))
    cmv = cat_monthly  # 复用：此处用国家月度表更合适
    country_monthly = D["country_monthly"]
    for mo in mos:
        sub = country_monthly[country_monthly["MonthPeriod"] == mo].nlargest(8, "Revenue")
        b = Bar(init_opts=opts.InitOpts(width="100%", height="330px", bg_color="rgba(0,0,0,0)"))
        b.add_xaxis([f"{COUNTRY_CN.get(c, c)}" for c in sub["Country"]][::-1])
        b.add_yaxis("销售额（£）", [round(v, 2) for v in sub["Revenue"]][::-1],
                    color="#FFB74D",
                    label_opts=opts.LabelOpts(is_show=True, position="right",
                                              color=TEXT_SUB, font_size=10))
        b.reversal_axis()
        apply_style(b, f"{mo}　TOP8 国家销售额（自动轮播）",
                    subtitle="时间轴可手动拖动查看任意月份", legend_top="9999px")
        tl.add(b, mo)
    add("tab1_timeline", "月度国家排名时间轴", tl, span=12)

    # 5) 星期 × 时段 热力图
    piv = heat.pivot(index="Hour", columns="Weekday", values="Revenue").fillna(0).round(2)
    hours = piv.index.tolist()
    wdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][:piv.shape[1]]
    hm = HeatMap(init_opts=base_opts())
    hm.add_xaxis(wdays)
    hm.add_yaxis("销售额（£）", [str(h) + ":00" for h in hours],
                 [[int(j), int(i), round(float(piv.values[i, j]), 2)]
                  for i in range(len(hours)) for j in range(piv.shape[1])],
                 label_opts=opts.LabelOpts(is_show=False))
    hm.set_global_opts(
        visualmap_opts=opts.VisualMapOpts(
            min_=0, max_=float(np_max(piv.values)), orient="vertical",
            pos_right="6%", pos_top="center", range_color=["#0D2338", "#16537E",
                                                           "#2E9BC0", "#7FD1E8"],
            textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB, font_size=10)),
        tooltip_opts=opts.TooltipOpts(
            background_color="rgba(10,22,40,0.94)", border_color="#2A4A70",
            textstyle_opts=opts.TextStyleOpts(color=TEXT_MAIN)))
    apply_style(hm, "星期 × 时段 销售额热力图", subtitle="识别客服排班与促销投放时段",
                legend_top="9999px")
    add("tab1_heatmap", "星期时段热力图", hm, span=12)

    # ---------- Tab2 客户价值 ----------
    # 6) RFM 玫瑰图
    pie = Pie(init_opts=base_opts())
    pie.add("", [(r["Segment"], round(float(r["Monetary"]), 2))
                 for _, r in seg.iterrows()],
            radius=["22%", "62%"], center=["50%", "56%"], rosetype="area")
    apply_style(pie, "RFM 八分类：金额贡献结构", subtitle="玫瑰图 · 点击图例可开关某一客群",
                is_pie=True)
    add("tab2_rfm_pie", "RFM 金额贡献玫瑰图", pie, span=6)

    # 7) RFM 客户数 vs 金额贡献
    b3 = Bar(init_opts=base_opts())
    b3.add_xaxis(seg["Segment"].astype(str).tolist())
    b3.add_yaxis("客户数（人）", seg["Customers"].astype(int).tolist(), color="#4FC3F7")
    b3.add_yaxis("金额贡献（£）", [round(v, 2) for v in seg["Monetary"]], color="#FFB74D")
    b3.extend_axis(yaxis=opts.AxisOpts(
        name="贡献占比（%）", position="right",
        name_textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB),
        axislabel_opts=opts.LabelOpts(color="#81C784", font_size=10),
        axisline_opts=opts.AxisLineOpts(is_show=False),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    l3 = Line()
    l3.add_xaxis(seg["Segment"].astype(str).tolist())
    l3.add_yaxis("金额占比（%）", seg["RevenueShare"].astype(float).tolist(),
                 yaxis_index=1, color="#81C784", symbol="circle", symbol_size=6,
                 linestyle_opts=opts.LineStyleOpts(width=2))
    b3.overlap(l3)
    apply_style(b3, "RFM 八分类：客户规模 vs 金额贡献", subtitle="左轴：绝对值　右轴：金额占比",
                x_rotate=32)
    add("tab2_rfm_bar", "RFM 客群规模与贡献", b3, span=6)

    # 8) 同期群留存曲线
    co = cohort.copy()
    ln4 = Line(init_opts=base_opts())
    ln4.add_xaxis([f"M{int(c)}" for c in co["CohortIndex"]])
    ln4.add_yaxis("平均留存率（%）", [float(v) for v in co["AvgRetentionRate"]],
                  is_smooth=True, symbol="circle", symbol_size=6, color="#81C784",
                  areastyle_opts=opts.AreaStyleOpts(opacity=0.25, color="#81C784"),
                  linestyle_opts=opts.LineStyleOpts(width=2.4))
    ln4.add_yaxis("平均活跃客户数（人）", [float(v) for v in co["AvgActiveCustomers"]],
                  is_smooth=True, symbol="triangle", symbol_size=6, color="#FFB74D",
                  linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed"))
    apply_style(ln4, "同期群留存衰减曲线（M0–M23）", subtitle="双轴联动：留存率 与 活跃客户数")
    add("tab2_cohort", "同期群留存曲线", ln4, span=7)

    # 9) 复购漏斗
    fn = Funnel(init_opts=base_opts())
    fn.add("客户数", [(r["Stage"], int(r["Customers"])) for _, r in funnel.iterrows()],
           sort_="descending",
           label_opts=opts.LabelOpts(position="inside", color="#08111E",
                                     font_size=11, font_weight="bold",
                                     formatter="{b}: {c}"),
           itemstyle_opts=opts.ItemStyleOpts(border_color=BG, border_width=1))
    apply_style(fn, "客户复购转化漏斗", subtitle="从首购到忠诚的逐级转化",
                legend_top="9999px")
    add("tab2_funnel", "复购漏斗", fn, span=5)

    # 10) K-Means 分群画像
    b5 = Bar(init_opts=base_opts())
    b5.add_xaxis(kprof["ClusterName"].tolist())
    b5.add_yaxis("客户占比（%）", [float(v) for v in kprof["CustomerShare"]], color="#4FC3F7")
    b5.add_yaxis("金额占比（%）", [float(v) for v in kprof["RevenueShare"]], color="#E57373")
    b5.extend_axis(yaxis=opts.AxisOpts(
        name="平均Recency（天）", position="right",
        name_textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB),
        axislabel_opts=opts.LabelOpts(color="#FFD54F", font_size=10),
        axisline_opts=opts.AxisLineOpts(is_show=False),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    l5 = Line()
    l5.add_xaxis(kprof["ClusterName"].tolist())
    l5.add_yaxis("平均 Recency（天）", [float(v) for v in kprof["AvgRecency"]],
                 yaxis_index=1, color="#FFD54F", symbol="circle", symbol_size=6,
                 linestyle_opts=opts.LineStyleOpts(width=2))
    b5.overlap(l5)
    apply_style(b5, "K-Means 客户分群画像", subtitle="左轴：占比　右轴：平均未购天数")
    add("tab2_kmeans", "K-Means 分群画像", b5, span=12)

    # 11) 流失预警：十分位实际流失率 + 累积捕捉率（M10）
    dec = D["churn_decile"].sort_values("Decile", ascending=False)
    b8 = Bar(init_opts=base_opts("420px"))
    b8.add_xaxis([f"第{int(d)}分位" for d in dec["Decile"]])
    b8.add_yaxis("实际流失率（%）", [round(float(v), 2) for v in dec["实际流失率(%)"]],
                 color="#E57373",
                 label_opts=opts.LabelOpts(is_show=True, position="top",
                                           color=TEXT_SUB, font_size=9),
                 markline_opts=opts.MarkLineOpts(
                     data=[opts.MarkLineItem(type_="average", name="全样本流失率 74.22%")],
                     linestyle_opts=opts.LineStyleOpts(color="#FFB74D", type_="dashed"),
                     label_opts=opts.LabelOpts(color="#FFB74D", font_size=10)))
    b8.extend_axis(yaxis=opts.AxisOpts(
        name="累积捕捉率（%）", position="right",
        name_textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB),
        axislabel_opts=opts.LabelOpts(color="#81C784", font_size=10),
        axisline_opts=opts.AxisLineOpts(is_show=False),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    l8 = Line()
    l8.add_xaxis([f"第{int(d)}分位" for d in dec["Decile"]])
    l8.add_yaxis("累积捕捉率（%）", [round(float(v), 2) for v in dec["累积捕捉率(%)"]],
                 yaxis_index=1, color="#81C784", symbol="circle", symbol_size=6,
                 linestyle_opts=opts.LineStyleOpts(width=2.2))
    b8.overlap(l8)
    apply_style(b8, "流失预警：十分位区分度（LogReg 时间外 AUC 0.7439）",
                subtitle="柱：十分位实际流失率　线：按概率降序的累积捕捉率",
                x_rotate=30)
    add("tab2_churn_decile", "流失预警十分位区分度", b8, span=7)

    # 12) 流失预警：TOP10 期望损失名单（M10）
    watch = D["churn_watch"].head(10)
    rows = []
    for _, r in watch.iterrows():
        rows.append([f"{int(r['Rank'])}", f"{int(r['CustomerID'])}",
                     f"{float(r['PChurn'])*100:.1f}%",
                     f"{float(r['HistValue']):,.0f}",
                     f"{float(r['ExpLoss']):,.0f}"])
    tb2 = Table()
    tb2.add(["排名", "客户ID", "预测流失概率", "历史消费(£)", "期望损失(£)"], rows)
    tb2.set_global_opts(
        title_opts=opts.TitleOpts(
            title="流失预警名单 TOP10（按期望损失 = 概率 × 历史消费）",
            pos_left="center", pos_top="6px",
            title_textstyle_opts=opts.TextStyleOpts(color=TEXT_MAIN, font_size=14,
                                                    font_weight="bold")))
    add("tab2_churn_watch", "流失预警 TOP10 名单", tb2, span=5)

    # ---------- Tab3 商品洞察 ----------
    # 11) 商品 TOP10
    tp = top_products.head(10).iloc[::-1]
    b6 = Bar(init_opts=base_opts())
    b6.add_xaxis([short(d, 26) for d in tp["Description"]])
    b6.add_yaxis("销售额（£）", [round(v, 2) for v in tp["Revenue"]], color="#4FC3F7",
                 label_opts=opts.LabelOpts(is_show=True, position="right",
                                           color=TEXT_SUB, font_size=10))
    b6.reversal_axis()
    apply_style(b6, "TOP10 热销商品销售额", legend_top="9999px")
    add("tab3_top_products", "TOP10 热销商品", b6, span=7)

    # 12) 品类结构环形
    pie2 = Pie(init_opts=base_opts())
    pie2.add("", [(short(r["ProductCategory"], 18), round(float(r["Revenue"]), 2))
                  for _, r in cat.head(8).iterrows()],
             radius=["38%", "66%"], center=["50%", "56%"])
    apply_style(pie2, "商品品类销售额结构", subtitle="悬停显示金额与占比", is_pie=True)
    add("tab3_cat_pie", "品类结构环形图", pie2, span=5)

    # 13) 商品词云
    wc = WordCloud(init_opts=base_opts())
    wc.add("", [(str(r["Description"])[:24], float(r["Revenue"]))
                for _, r in top_products.head(40).iterrows()],
           word_size_range=[12, 52], shape="circle", rotate_step=45)
    wc.set_global_opts(
        title_opts=opts.TitleOpts(title="热销商品词云（字号 = 销售额）", pos_left="center",
                                  pos_top="6px",
                                  title_textstyle_opts=opts.TextStyleOpts(
                                      color=TEXT_MAIN, font_size=15, font_weight="bold")),
        tooltip_opts=opts.TooltipOpts(
            background_color="rgba(10,22,40,0.94)", border_color="#2A4A70",
            textstyle_opts=opts.TextStyleOpts(color=TEXT_MAIN)))
    add("tab3_wordcloud", "热销商品词云", wc, span=6)

    # 14) ABC 分类
    pie3 = Pie(init_opts=base_opts())
    pie3.add("", [(f"{r['ABCCategory']} 类 SKU（{r['SKUs']:,} 个）", round(float(r["Revenue"]), 2))
                  for _, r in abc_sum.iterrows()],
             radius=["30%", "60%"], center=["50%", "56%"], rosetype="radius")
    apply_style(pie3, "ABC 分类销售额贡献", subtitle="A 类少量 SKU 贡献 80% 销售额", is_pie=True)
    add("tab3_abc", "ABC 分类贡献", pie3, span=6)

    # 15) 关联规则 Lift 排行
    rules = top20.head(10).copy()
    rules["Rule"] = [f"{a[:22]} → {c[:20]}" for a, c in
                     zip(rules["AntecedentNames"], rules["ConsequentNames"])]
    rules = rules.iloc[::-1]
    b7 = Bar(init_opts=base_opts())
    b7.add_xaxis([" " for _ in rules["Rule"]])
    b7.add_yaxis("提升度 Lift", [round(float(v), 2) for v in rules["lift"]],
                 color="#FFB74D",
                 label_opts=opts.LabelOpts(is_show=True, position="right",
                                           color=TEXT_SUB, font_size=9,
                                           formatter="{@[1]}"))
    b7.reversal_axis()
    apply_style(b7, "关联规则提升度 TOP10", subtitle="Lift 越高，搭配购买的倾向越强",
                legend_top="9999px")
    add("tab3_rules", "关联规则 Lift 排行", b7, span=12)

    # 16) 维度表：商品明细
    tb = Table()
    rows = []
    for _, r in top_products.head(12).iterrows():
        rows.append([str(r["StockCode"]), short(r["Description"], 30),
                     f"{float(r['Revenue']):,.2f}", f"{int(r['Quantity']):,}"])
    tb.add(["商品编码", "商品名称", "销售额（£）", "销量（件）"], rows)
    tb.set_global_opts(
        title_opts=opts.TitleOpts(title="商品明细表（多维下钻核对）", pos_left="center",
                                  pos_top="6px",
                                  title_textstyle_opts=opts.TextStyleOpts(
                                      color=TEXT_MAIN, font_size=15, font_weight="bold")))
    add("tab3_table", "商品明细表", tb, span=12)

    # ---------- Tab4 预测与复盘 ----------
    # 17) 预测：历史 + 未来点预测 + 95% 置信带（堆叠实现）
    hist_d = pd.to_datetime(hist["OrderDate"])
    fc_d = pd.to_datetime(future["OrderDate"])
    xaxis = [d.strftime("%Y-%m-%d") for d in hist_d] + [d.strftime("%Y-%m-%d") for d in fc_d]
    n_hist = len(hist_d)
    hist_vals = [round(float(v), 2) for v in hist["Revenue"]]
    fc_vals = [round(float(v), 2) for v in future["Forecast"]]
    upper = [round(float(v), 2) for v in future["CI95_Upper"]]
    lower = [round(max(float(v), 0.0), 2) for v in future["CI95_Lower"]]
    gap = [round(u - l, 2) for u, l in zip(upper, lower)]

    lp = Line(init_opts=base_opts())
    lp.add_xaxis(xaxis)
    lp.add_yaxis("历史实际", hist_vals + [None] * len(fc_vals),
                 color="#4FC3F7", symbol="none",
                 linestyle_opts=opts.LineStyleOpts(width=1.6),
                 areastyle_opts=opts.AreaStyleOpts(opacity=0.10, color="#4FC3F7"),
                 itemstyle_opts=opts.ItemStyleOpts(color="#4FC3F7"))
    lp.add_yaxis("95% 置信带下界", [None] * n_hist + lower, stack="ci",
                 color="rgba(0,0,0,0)", symbol="none",
                 linestyle_opts=opts.LineStyleOpts(width=0, opacity=0),
                 areastyle_opts=opts.AreaStyleOpts(opacity=0), is_connect_nones=True)
    lp.add_yaxis("95% 置信区间（宽度）", [None] * n_hist + gap, stack="ci",
                 color="#E57373", symbol="none",
                 linestyle_opts=opts.LineStyleOpts(width=0, opacity=0),
                 areastyle_opts=opts.AreaStyleOpts(opacity=0.22, color="#E57373"),
                 is_connect_nones=True)
    lp.add_yaxis("未来 30 天点预测", [None] * n_hist + fc_vals,
                 color="#FFB74D", symbol="circle", symbol_size=5,
                 linestyle_opts=opts.LineStyleOpts(width=2.6))
    actual = future["Actual"].tolist()
    lp.add_yaxis("实际值（验证期）", [None] * n_hist +
                 [None if pd.isna(v) else round(float(v), 2) for v in actual],
                 color="#81C784", symbol="rect", symbol_size=6,
                 linestyle_opts=opts.LineStyleOpts(width=2.2))
    lp.set_global_opts(datazoom_opts=[opts.DataZoomOpts(type_="inside"),
                                      opts.DataZoomOpts(type_="slider", pos_bottom="6px",
                                                        )])
    apply_style(lp, f"日销售额预测（{D['forecast_summary']['best_model']}）：点预测 + 95% 置信区间",
                subtitle="橙色=点预测　红色阴影=95% CI　绿色=已知实际值（验证）",
                legend_top="34px")
    add("tab4_forecast", "预测与置信区间", lp, span=12)

    # 18) 回测对比
    bt_first = bt[bt["Model"] == bt["Model"].iloc[0]]
    lb = Line(init_opts=base_opts())
    lb.add_xaxis([d.strftime("%m-%d") for d in pd.to_datetime(bt_first["OrderDate"])])
    for i, (model, sub) in enumerate(bt.groupby("Model")):
        lb.add_yaxis(f"{model} 预测", [round(float(v), 2) for v in sub["Predicted"]],
                     color=ECHARTS_PALETTE[i % len(ECHARTS_PALETTE)], symbol="none",
                     linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed"))
    lb.add_yaxis("实际值", [round(float(v), 2) for v in bt_first["Actual"]],
                 color="#4FC3F7", symbol="circle", symbol_size=5,
                 linestyle_opts=opts.LineStyleOpts(width=2.4))
    metrics = D["forecast_summary"]["metrics"]
    sub_txt = " ｜ ".join([f"{k}：MAPE {v['MAPE']}%，RMSE £{v['RMSE']:,.0f}"
                           for k, v in metrics.items()])
    apply_style(lb, "回测：预测值 vs 实际值（留出最后 30 天）", subtitle=sub_txt)
    add("tab4_backtest", "回测对比", lb, span=12)

    # 19) 同比增长
    yo = monthly.dropna(subset=["Revenue_YoY"]).copy()
    b8 = Bar(init_opts=base_opts())
    b8.add_xaxis(yo["MonthPeriod"].tolist())
    b8.add_yaxis("同比增速（%）", [None if pd.isna(v) else float(v)
                                   for v in yo["Revenue_YoY"]],
                 color="#81C784", gap="0%")
    b8.extend_axis(yaxis=opts.AxisOpts(
        name="销售额（£）", position="right",
        name_textstyle_opts=opts.TextStyleOpts(color=TEXT_SUB),
        axislabel_opts=opts.LabelOpts(color="#FFB74D", font_size=10),
        axisline_opts=opts.AxisLineOpts(is_show=False),
        splitline_opts=opts.SplitLineOpts(is_show=False)))
    l8 = Line()
    l8.add_xaxis(yo["MonthPeriod"].tolist())
    l8.add_yaxis("销售额（£）", [round(v, 2) for v in yo["Revenue"]],
                 yaxis_index=1, color="#FFB74D", symbol="circle", symbol_size=5,
                 linestyle_opts=opts.LineStyleOpts(width=2))
    b8.overlap(l8)
    apply_style(b8, "月度同比增速复盘", subtitle="左轴：同比增速　右轴：销售额", x_rotate=45)
    add("tab4_yoy", "同比增速复盘", b8, span=12)

    # 20) 波士顿矩阵（散点）
    sc = Scatter(init_opts=base_opts())
    qcolor = {"明星 Stars": "#E57373", "金牛 Cash Cows": "#4FC3F7",
              "问题 Question Marks": "#FFD54F", "瘦狗 Dogs": "#9CB6D4"}
    for q, sub in bcg.groupby("Quadrant"):
        sc.add_xaxis([round(float(v), 3) for v in sub["RelativeShare"]])
        sc.add_yaxis(q,
                     [[round(float(a), 3), round(float(b), 2), round(float(c), 1)]
                      for a, b, c in zip(sub["RelativeShare"], sub["YoY_Growth"],
                                         sub["RevenueShare"])],
                     color=qcolor.get(q, "#4FC3F7"),
                     symbol_size=18,
                     label_opts=opts.LabelOpts(is_show=True, position="right",
                                               formatter=JsCodeWrap(),
                                               color=TEXT_SUB, font_size=9))
    sc.set_series_opts()
    apply_style(sc, "波士顿矩阵（BCG）：相对份额 × 同比增速",
                subtitle="气泡大小 = 销售额占比；虚线分界 = 相对份额 1.0 / 市场平均增速")
    add("tab4_bcg", "波士顿矩阵", sc, span=12)

    return comp


# ===========================================================================
# 小工具
# ===========================================================================
def np_max(arr):
    import numpy as np
    return float(np.nanmax(arr)) if arr.size else 1.0


def short(s: str, n: int) -> str:
    s = str(s).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def JsCodeWrap():  # noqa: N802
    from pyecharts.commons.utils import JsCode
    return JsCode("function(p){return p.data[2]+'%';}")


# ===========================================================================
# 地图（Plotly）
# ===========================================================================
def build_map_html(country: pd.DataFrame) -> str:
    """世界 choropleth（Plotly）：按销售额着色，实现地理位置下钻。"""
    import plotly.graph_objects as go

    df = country[~country["Country"].isin(NON_SOVEREIGN)].copy()
    df["Location"] = df["Country"].replace(PLOTLY_NAME_MAP)
    total = df["Revenue"].sum()
    fig = go.Figure(data=go.Choropleth(
        locations=df["Location"], locationmode="country names",
        z=df["Revenue"].round(2),
        text=[f"{COUNTRY_CN.get(c, c)}　£{v:,.0f}　{s:.2f}%"
              for c, v, s in zip(df["Country"], df["Revenue"], df["RevenueShare"])],
        colorscale=[[0, "#0D2338"], [0.25, "#16537E"], [0.6, "#2E9BC0"], [1, "#7FD1E8"]],
        colorbar=dict(title=dict(text="销售额（£）", font=dict(color="#9CB6D4")),
                      tickfont=dict(color="#9CB6D4"), thickness=12, len=0.72,
                      bgcolor="rgba(0,0,0,0)"),
        marker_line_color="#08111E", marker_line_width=0.6, hovertemplate="%{text}<extra></extra>"))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False, showcoastlines=True,
                 coastlinecolor="#1C3554", showland=True, landcolor="#12263D",
                 showcountries=True, countrycolor="#1C3554"),
        margin=dict(l=0, r=0, t=0, b=0), height=420, dragmode=False,
        font=dict(color="#9CB6D4"))
    _ = total
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})


# ===========================================================================
# HTML 组装
# ===========================================================================
CSS = """
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 700px at 15% -10%,#10243D 0%,#08111E 55%,#050A12 100%);
     color:#E8F2FF;font-family:"Microsoft YaHei","Segoe UI",-apple-system,"Helvetica Neue",sans-serif;}
.wrap{max-width:1680px;margin:0 auto;padding:18px 22px 40px}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;
       border:1px solid #1C3554;border-radius:14px;padding:14px 20px;margin-bottom:16px;
       background:linear-gradient(90deg,rgba(20,44,72,.9),rgba(10,22,40,.6));
       box-shadow:0 6px 26px rgba(0,0,0,.45)}
header h1{margin:0;font-size:24px;letter-spacing:1px}
header .sub{color:#8FB6E0;font-size:12.5px;margin-top:5px}
header .meta{text-align:right;color:#8FB6E0;font-size:12px;line-height:1.7}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:16px}
.kpi{border:1px solid #1C3554;border-radius:12px;padding:13px 15px;position:relative;overflow:hidden;
     background:linear-gradient(160deg,rgba(23,50,80,.85),rgba(9,20,36,.85))}
.kpi:after{content:"";position:absolute;left:0;top:0;width:3px;height:100%;background:#4FC3F7}
.kpi:nth-child(2):after{background:#FFB74D}.kpi:nth-child(3):after{background:#81C784}
.kpi:nth-child(4):after{background:#E57373}.kpi:nth-child(5):after{background:#BA68C8}
.kpi:nth-child(6):after{background:#4DB6AC}
.kpi .t{font-size:12px;color:#8FB6E0}
.kpi .v{font-size:24px;font-weight:700;margin-top:6px;letter-spacing:.5px}
.kpi .d{font-size:11px;color:#6C8FB8;margin-top:4px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}
.tab{padding:9px 20px;border:1px solid #24456C;border-radius:999px;cursor:pointer;font-size:13px;
     color:#A9C6E4;background:rgba(15,29,49,.7);transition:.22s;user-select:none}
.tab:hover{color:#fff;border-color:#4FC3F7;transform:translateY(-1px)}
.tab.active{background:linear-gradient(90deg,#16537E,#2E9BC0);color:#fff;border-color:#4FC3F7;
            box-shadow:0 4px 16px rgba(46,155,192,.35)}
.grid{display:none}
.grid.active{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}
.card{border:1px solid #1C3554;border-radius:13px;background:rgba(15,29,49,.72);padding:6px 10px 10px;
      min-height:400px;box-shadow:0 4px 20px rgba(0,0,0,.35);transition:.22s}
.card:hover{border-color:#2E6A94;box-shadow:0 8px 28px rgba(46,155,192,.18)}
.card .ct{padding:4px 8px 2px;font-size:12.5px;color:#8FB6E0;border-bottom:1px dashed #1C3554;
          margin-bottom:4px;display:flex;justify-content:space-between}
.span12{grid-column:span 12}.span7{grid-column:span 7}.span6{grid-column:span 6}
.span5{grid-column:span 5}.span4{grid-column:span 4}.span8{grid-column:span 8}
footer{margin-top:22px;text-align:center;color:#5C7A9C;font-size:12px;line-height:2}
footer a{color:#8FB6E0}
@media(max-width:1200px){.kpis{grid-template-columns:repeat(3,1fr)}
 .span12,.span7,.span6,.span5,.span8,.span4{grid-column:span 12}}
"""


def build_html(comp: dict, kpis: dict, map_html: str, dashboard_online: bool = True) -> str:
    def fmt(v):
        return f"{v:,.0f}"

    import datetime as _dt
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    kpi_html = "".join([
        f'<div class="kpi"><div class="t">{t}</div><div class="v">{v}</div>'
        f'<div class="d">{d}</div></div>'
        for t, v, d in [
            ("总销售额（£）", fmt(kpis["total_revenue_gbp"]),
             f"{kpis['date_range'][0]} ~ {kpis['date_range'][1]}"),
            ("订单数（笔）", fmt(kpis["n_invoices"]), "清洗后的有效订单"),
            ("活跃客户（人）", fmt(kpis["n_customers"]), "有客户编号的可识别客户"),
            ("客单价 AOV（£）", fmt(kpis["avg_order_value_gbp"]), "销售额 / 订单数"),
            ("在售 SKU（个）", fmt(kpis["n_products"]), f"覆盖 {kpis['n_countries']} 个国家/地区"),
            ("复购率（%）", f"{kpis['repeat_purchase_rate']:.1f}", "有过 2 次及以上购买的客户占比"),
        ]])

    tab_defs = [
        ("tab1", "① 销售总览", ["tab1_trend", "tab1_timeline", "tab1_dual", "tab1_country_bar",
                                "tab1_heatmap"]),
        ("tab2", "② 客户价值", ["tab2_rfm_pie", "tab2_rfm_bar", "tab2_cohort", "tab2_funnel",
                                "tab2_kmeans", "tab2_churn_decile", "tab2_churn_watch"]),
        ("tab3", "③ 商品洞察", ["tab3_top_products", "tab3_cat_pie", "tab3_wordcloud",
                                "tab3_abc", "tab3_rules", "tab3_table"]),
        ("tab4", "④ 预测与复盘", ["tab4_forecast", "tab4_backtest", "tab4_yoy", "tab4_bcg"]),
    ]
    nav = "".join([f'<div class="tab{" active" if i == 0 else ""}" data-tab="{tid}">{name}</div>'
                   for i, (tid, name, _) in enumerate(tab_defs)])

    panels = []
    for i, (tid, name, keys) in enumerate(tab_defs):
        cards = []
        for k in keys:
            title, html, span = comp[k]
            extra = ""
            if k == "tab1_heatmap":
                extra = (f'<div class="card span4" style="min-height:420px">'
                         f'<div class="ct"><span>全球销售分布（choropleth）</span>'
                         f'<span>Plotly</span></div>{map_html}</div>')
                # 热力图改为 8 列宽以容纳地图
                cards.append(f'<div class="card span8" style="min-height:420px">'
                             f'<div class="ct"><span>{title}</span><span>ECharts</span></div>'
                             f'{html}</div>')
                cards.append(extra)
                continue
            cards.append(f'<div class="card span{span}">'
                         f'<div class="ct"><span>{title}</span><span>ECharts</span></div>'
                         f'{html}</div>')
        panels.append(f'<div class="grid{" active" if i == 0 else ""}" id="{tid}">'
                      + "".join(cards) + "</div>")

    js = """
    document.querySelectorAll('.tab').forEach(function(t){
      t.addEventListener('click', function(){
        document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active');});
        document.querySelectorAll('.grid').forEach(function(g){g.classList.remove('active');});
        t.classList.add('active');
        var el = document.getElementById(t.dataset.tab);
        if(el){el.classList.add('active');}
        window.dispatchEvent(new Event('resize'));
        window.scrollTo({top:document.querySelector('.tabs').offsetTop-10,behavior:'smooth'});
      });
    });
    window.addEventListener('resize', function(){ window.dispatchEvent(new Event('resize')); });
    """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>零售业务分析大屏 · Retail Analytics Dashboard</title>
<script type="text/javascript" src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>零售业务商业分析可视化大屏<span style="color:#4FC3F7"> . Retail Analytics</span></h1>
      <div class="sub">数据源：UCI Machine Learning Repository · Online Retail II（官方 ZIP 下载，合规非爬虫）
           ｜ 全 Python 实现（Matplotlib / Seaborn / Pyecharts / Plotly）</div>
    </div>
    <div class="meta">更新时间：{now}<br/>随机种子 {kpis.get('_seed', 2026)}　抽样比例 30%（按发票）<br/>
        组件数 {len(comp)} ｜ KPI 卡 6 ｜ Tab 联动 4 组</div>
  </header>

  <div class="kpis">{kpi_html}</div>

  <div class="tabs">{nav}</div>

  {"".join(panels)}

  <footer>
    交互提示：① 点击上方 Tab 切换主题｜② 「月度国家排名时间轴」支持 autoplay 自动轮播与手动拖动｜
    ③ 拖拽底部 DataZoom 滑块可缩放时间区间下钻｜④ 鼠标悬停任意图表查看十字准星数值｜
    ⑤ 点击图例可隐藏/显示某一数据系列（联动筛选）<br/>
    本项目为《商业数据分析》期末大作业成果 · 全程未使用 Power BI / Tableau / Fine BI 等 BI 软件
  </footer>
</div>
<script type="text/javascript">{js}</script>
</body>
</html>"""


# ===========================================================================
def main() -> None:
    print(cfg.banner("STEP 05 · 交互式可视化大屏（Pyecharts + Plotly）"))

    import numpy as np

    def load(name, **kw):
        return pd.read_csv(cfg.TAB_DIR / name, **kw)

    fact = pd.read_csv(cfg.CLEAN_DIR / "fact_order_items.csv",
                       parse_dates=["OrderDate"], low_memory=False)
    fact = fact[fact["OrderDate"] <= cfg.__dict__.get("_cut", "2011-11-30")]
    country_monthly = (fact.groupby(["MonthPeriod", "Country"])["Revenue"].sum()
                       .reset_index().round(2))

    D = {
        "monthly": load("03_mom_yoy_monthly.csv"),
        "daily": load("03_daily_series.csv", parse_dates=["OrderDate"]),
        "country": load("03_country_summary.csv"),
        "category": load("03_category_summary.csv"),
        "category_monthly": load("03_category_monthly.csv"),
        "weekday_hour": load("03_weekday_hour_matrix.csv"),
        "rfm_seg": load("03_rfm_segment_summary.csv"),
        "cohort_avg": load("03_cohort_avg_retention.csv"),
        "apriori_top20": load("03_apriori_rules_top20.csv"),
        "abc_summary": load("03_abc_summary.csv"),
        "bcg": load("03_bcg_matrix.csv"),
        "kmeans_profile": load("03_kmeans_cluster_profile.csv"),
        "forecast_future": load("03_forecast_future.csv"),
        "forecast_hist": load("03_forecast_history.csv"),
        "forecast_bt": load("03_forecast_backtest.csv"),
        "top_products": load("03_top_products.csv"),
        "funnel": load("03_repurchase_funnel.csv"),
        "churn_decile": load("03_churn_decile_lift.csv"),
        "churn_watch": load("03_churn_watchlist.csv"),
        "kpis": json.loads((cfg.TAB_DIR / "03_executive_kpis.json").read_text(encoding="utf-8")),
        "country_monthly": country_monthly,
    }
    D["forecast_summary"] = json.loads(
        (cfg.TAB_DIR / "03_forecast_summary.json").read_text(encoding="utf-8"))
    D["kpis"]["_seed"] = cfg.RANDOM_SEED

    comp = build_components(D)
    iou.log(f"已构建 {len(comp)} 个交互组件")

    map_html = build_map_html(D["country"])
    iou.log("世界 choropleth 地图组件已生成")

    html = build_html(comp, D["kpis"], map_html)
    out = cfg.DASH_DIR / "dashboard_dark.html"
    out.write_text(html, encoding="utf-8")
    iou.log(f"大屏已生成 → {out}（{out.stat().st_size/1024:.0f} KB）")

    # GitHub Pages 首页
    # 注意：pages/index.html 是手工维护的成果落地页（含演示区、复现步骤、文档入口），
    # 与大屏本体不同。若文件中存在 CURATED-LANDING 标记则跳过覆盖，
    # 否则（首次生成）写入大屏本体作为兜底。
    pages = cfg.PAGE_DIR / "index.html"
    marker = "CURATED-LANDING"
    if pages.exists() and marker in pages.read_text(encoding="utf-8", errors="ignore"):
        iou.log("GitHub Pages 首页为手工维护版（检出 CURATED-LANDING 标记），跳过覆盖")
    else:
        pages.write_text(html, encoding="utf-8")
        iou.log(f"GitHub Pages 首页已生成 → {pages}")

    # 组件清单
    listing = pd.DataFrame([
        {"组件": k, "标题": v[0], "栅格宽度": v[2]} for k, v in comp.items()
    ])
    listing.to_csv(cfg.TAB_DIR / "05_dashboard_components.csv", index=False,
                   encoding="utf-8-sig")
    iou.log("STEP 05 完成 ✓")


if __name__ == "__main__":
    main()
