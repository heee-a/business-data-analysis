# -*- coding: utf-8 -*-
"""
scripts/utils/chart_helpers.py
==============================
matplotlib 未内置的图表类型实现（全部为本项目手写，无任何 BI 工具参与）：

    squarify_treemap  矩形树图（经典 squarify 算法）
    waterfall_chart   瀑布图
    gauge_chart       仪表盘
    calendar_heatmap  日历热力图
    funnel_chart      漏斗图
    bullet_chart      子弹图
    slope_chart       坡度图
    donut_chart       环形图
    stacked_progress  百分比堆积条形图

设计原则：最小实现 + 完全可控样式，便于逐像素贴近
《Excel数据可视化——从图表到数据大屏》中的模板版式（标题、标签、
图例位置、配色、数据标签、单位标注）。
"""

from __future__ import annotations

from typing import Sequence

import matplotlib.patches as mpatches
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 矩形树图（squarified treemap）
# ---------------------------------------------------------------------------
def _normalize_sizes(sizes, dx, dy):
    total = float(np.sum(sizes))
    if total <= 0:
        return list(sizes)
    area = dx * dy
    return [float(s) * area / total for s in sizes]


def _worst(row, w):
    """给定条带宽度 w，返回行内最差矩形的长宽比（越小越好）。"""
    if not row:
        return float("inf")
    areas = np.array([r["area"] for r in row], dtype=float)
    s = areas.sum()
    if s <= 0:
        return float("inf")
    return float(max((w * w * areas.max()) / (s * s), (s * s) / (w * w * areas.min())))


def _layout_row(row, x, y, dx, dy):
    """把一行子块铺入 (x, y, dx, dy)，返回矩形列表与剩余空间矩形。"""
    s = sum(r["area"] for r in row)
    out = []
    if dx >= dy:                       # 剩余区域偏“宽”，沿竖向铺一条窄带
        w = s / dy if dy else dx
        cy = y
        for r in row:
            h = r["area"] / w if w else 0.0
            out.append((x, cy, w, h, r["idx"]))
            cy += h
        return out, (x + w, y, max(dx - w, 0.0), dy)
    else:                              # 沿横向铺一条带
        h = s / dx if dx else dy
        cx = x
        for r in row:
            w = r["area"] / h if h else 0.0
            out.append((cx, y, w, h, r["idx"]))
            cx += w
        return out, (x, y + h, dx, max(dy - h, 0.0))


def squarify_treemap(ax, sizes, labels=None, colors=None, alpha: float = 0.92,
                     pad: float = 0.004, fontsize: int = 9, min_show: float = 0.025,
                     extra_texts: Sequence[str] | None = None):
    """
    矩形树图。算法：始终沿当前剩余区域较短的一边铺一条带；持续向该条带追加子块，
    只要追加后条带内最差长宽比得到改善；否则输出该条带并在剩余空间重复。
    这样得到的矩形最接近正方形，读数性能最佳。

    参数
    ----
    sizes       : 各块数值（决定面积）
    labels      : 主标签
    extra_texts : 副标签（如占比），显示在标签下一行
    """
    sizes = np.asarray(sizes, dtype=float)
    order = np.argsort(-sizes)
    sizes_sorted = sizes[order]
    labels = np.asarray(list(labels), dtype=object)[order] if labels is not None else None
    extra = np.asarray(list(extra_texts), dtype=object)[order] if extra_texts is not None else None

    areas = _normalize_sizes(sizes_sorted, 1.0, 1.0)
    items = [{"area": a, "idx": i} for i, a in enumerate(areas)]

    x, y, dx, dy = 0.0, 0.0, 1.0, 1.0
    rects: list[tuple] = []
    row: list[dict] = []
    while items:
        cand = items[0]
        if not row or _worst(row + [cand], min(dx, dy)) <= _worst(row, min(dx, dy)):
            row.append(cand)
            items.pop(0)
        else:
            laid, (x, y, dx, dy) = _layout_row(row, x, y, dx, dy)
            rects.extend(laid)
            row = []
    if row:
        laid, _ = _layout_row(row, x, y, dx, dy)
        rects.extend(laid)

    for (rx, ry, rw, rh, i) in rects:
        if rw <= 0 or rh <= 0:
            continue
        face = colors[i % len(colors)] if colors else "#4472C4"
        ax.add_patch(mpatches.Rectangle(
            (rx + pad, ry + pad), max(rw - 2 * pad, 1e-4), max(rh - 2 * pad, 1e-4),
            facecolor=face, edgecolor="white", linewidth=1.1, alpha=alpha))
        share = sizes_sorted[i] / sizes.sum() if sizes.sum() else 0
        if share >= min_show and labels is not None:
            ay = ry + rh / 2 + (0.012 if extra is not None else 0)
            ax.text(rx + rw / 2, ay, str(labels[i]), ha="center", va="center",
                    fontsize=fontsize, color="white", fontweight="bold")
            if extra is not None:
                ax.text(rx + rw / 2, ry + rh / 2 - 0.018, str(extra[i]), ha="center",
                        va="center", fontsize=fontsize - 1.5, color="white", alpha=0.92)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    return rects


# ---------------------------------------------------------------------------
def waterfall_chart(ax, categories, values, start: float = 0.0, final_label: str = "合计",
                    pos_color: str = "#548235", neg_color: str = "#C0504D",
                    total_color: str = "#2E75B6", fmt: str = "{:,.0f}", fontsize: int = 9):
    """瀑布图：逐项累加，展示总量增减的来源与去向。"""
    cats = list(categories) + [final_label]
    vals = list(values)
    running = start
    bottoms, heights, colors = [], [], []
    for v in vals:
        bottoms.append(running if v >= 0 else running + v)
        heights.append(abs(v))
        colors.append(pos_color if v >= 0 else neg_color)
        running += v
    bottoms.append(0.0)
    heights.append(running)
    colors.append(total_color)

    x = np.arange(len(cats))
    ax.bar(x, heights, bottom=bottoms, color=colors, width=0.62, edgecolor="white", zorder=3)
    for i in range(1, len(cats)):
        ax.plot([i - 1 + 0.31, i - 0.31], [bottoms[i], bottoms[i]],
                color="#808080", linewidth=0.9, linestyle=":", zorder=2)
    for i, (b, h) in enumerate(zip(bottoms, heights)):
        label = running if i == len(cats) - 1 else heights[i]
        sign = "" if i == len(cats) - 1 else ("+" if vals[i] >= 0 else "-")
        ax.text(i, b + h, f"{sign}{fmt.format(abs(label))}", ha="center", va="bottom",
                fontsize=fontsize, color="#404040")
    ax.set_xticks(x)
    ax.set_xticklabels(cats, rotation=40, ha="right")
    ax.grid(axis="x", visible=False)
    return ax


# ---------------------------------------------------------------------------
def gauge_chart(ax, value: float, max_value: float = 100.0, title: str = "",
                bands: Sequence[tuple[float, float, str]] | None = None,
                unit: str = "%", color: str = "#2E75B6", fontsize: int = 11):
    """半圆仪表盘（用于 KPI 达成率等单值呈现）。"""
    bands = bands or [(0, 0.6, "#C0504D"), (0.6, 0.85, "#FFC000"), (0.85, 1.0, "#70AD47")]
    theta = np.linspace(np.pi, 0, 400)
    for lo, hi, c in bands:
        mask = (theta >= np.pi - hi * np.pi) & (theta <= np.pi - lo * np.pi)
        ax.fill_between(theta, 0.55, 0.95, where=mask, color=c, alpha=0.85)
    frac = min(value / max_value, 1.0)
    ang = np.pi - frac * np.pi
    ax.plot([ang, ang], [0.0, 0.95], color=color, linewidth=3.5, zorder=4)
    ax.add_patch(mpatches.Circle((0, 0), 0.07, color=color, zorder=5))
    ax.plot(theta, [0.95] * len(theta), color="#BFBFBF", linewidth=0.8)
    ax.text(0, 0.20, f"{value:,.1f}{unit}", ha="center", va="center",
            fontsize=fontsize + 9, fontweight="bold", color="#262626")
    if title:
        ax.text(0, -0.30, title, ha="center", va="center", fontsize=fontsize, color="#595959")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-0.38, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


# ---------------------------------------------------------------------------
def calendar_heatmap(ax, dates, values, cmap: str = "Blues", cbar_label: str = ""):
    """GitHub 风格日历热力图（列 = 周，行 = 星期）。"""
    s = pd.Series(np.asarray(values, dtype=float),
                  index=pd.to_datetime(pd.Index(dates)).date)
    if s.empty:
        return None
    grid: dict = {}
    for d, v in s.items():
        iso = d.isocalendar()
        grid[(iso[1], iso[2] - 1, iso[0])] = v

    weeks = sorted({k[0] for k in grid})
    min_week, max_week = weeks[0], weeks[-1]
    mat = np.full((7, max_week - min_week + 2), np.nan)
    for (wk, wd, _yr), v in grid.items():
        mat[wd, wk - min_week] = v

    masked = np.ma.array(mat, mask=np.isnan(mat))
    im = ax.imshow(masked, cmap=cmap, aspect="auto", interpolation="nearest",
                   vmin=np.nanpercentile(mat, 2), vmax=np.nanpercentile(mat, 98))
    ax.set_yticks(range(7))
    ax.set_yticklabels(["周一", "周二", "周三", "周四", "周五", "周六", "周日"][::-1], fontsize=9)

    ticks, labels = [], []
    prev_m = None
    base_year = int(sorted(s.index)[0].isocalendar()[0])
    for wk in range(min_week, max_week + 1):
        try:
            d = pd.Timestamp.fromisocalendar(base_year, wk, 1).date()
        except ValueError:                       # 某些年份第 53 周不存在
            continue
        if d.month != prev_m:
            ticks.append(wk - min_week)
            labels.append(f"{d.month}月")
            prev_m = d.month
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=9)
    ax.grid(False)
    if cbar_label:
        import matplotlib.pyplot as plt
        cb = plt.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
        cb.set_label(cbar_label, fontsize=9)
    return im


# ---------------------------------------------------------------------------
def funnel_chart(ax, stages, values, colors=None, fmt: str = "{:,.0f}",
                 title_col: str = "阶段 / 客户数", conv_col: str = "逐级转化率"):
    """梯形漏斗图，右侧标注逐级转化率。"""
    n = len(stages)
    vals = np.asarray(values, dtype=float)
    colors = colors or ["#2E75B6", "#5B9BD5", "#9DC3E6", "#BDD7EE", "#DEEBF7",
                        "#F2F2F2", "#D9D9D9", "#BFBFBF"]
    w_top = vals / vals.max()
    for i in range(n):
        w = max(w_top[i], 0.08)
        ax.fill_betweenx([-i - 0.42, -i + 0.42], [-w / 2, -w / 2], [w / 2, w / 2],
                         color=colors[i % len(colors)], alpha=0.94,
                         edgecolor="white", linewidth=1.2)
        ax.text(0, -i, f"{stages[i]}   {fmt.format(values[i])}", ha="center", va="center",
                fontsize=10, color="white" if w_top[i] > 0.34 else "#262626",
                fontweight="bold")
        if i == 0:
            ax.text(0.44, -i + 0.42, "100.0%", ha="left", va="center",
                    fontsize=9.5, color="#548235")
        else:
            conv = values[i] / values[i - 1] * 100
            ax.text(0.44, -i + 0.42, f"{conv:.1f}%", ha="left", va="center",
                    fontsize=9.5, color="#C0504D" if conv < 50 else "#548235")
    ax.set_xlim(-0.68, 0.62)
    ax.set_ylim(-n + 0.35, 0.6)
    ax.axis("off")
    ax.text(-0.66, 0.45, title_col, fontsize=9.5, color="#595959")
    ax.text(0.44, 0.45, conv_col, fontsize=9.5, color="#595959")
    return ax


# ---------------------------------------------------------------------------
def bullet_chart(ax, labels, values, targets, bar_color: str = "#4472C4",
                 bands: Sequence[float] = (0.5, 0.8, 1.0), fmt: str = "{:,.0f}"):
    """子弹图：实际值 vs 目标值 + 定性分档背景。"""
    y = np.arange(len(labels))[::-1]
    maxv = max(max(values), max(targets)) * 1.25
    for i, (lab, v, t) in enumerate(zip(labels, values, targets)):
        ax.barh(y[i], maxv * bands[2], color="#D9E2F3", height=0.66, alpha=0.9)
        ax.barh(y[i], maxv * bands[1], color="#B4C7E7", height=0.66, alpha=0.9)
        ax.barh(y[i], maxv * bands[0], color="#DEEAF6", height=0.66, alpha=0.9)
        if i == 0:
            ax.barh(y[i], maxv * bands[2], color="#D9E2F3", height=0.66, alpha=0.9,
                    label="定性分档背景")
        ax.barh(y[i], v, color=bar_color, height=0.30, label="实际值" if i == 0 else None)
        ax.plot([t, t], [y[i] - 0.24, y[i] + 0.24], color="#262626", linewidth=2.6,
                label="目标值" if i == 0 else None)
        gap = (v - t) / t * 100 if t else np.nan
        col = "#548235" if v >= t else "#C0504D"
        ax.text(maxv * 1.03, y[i], f"{fmt.format(v)} ｜ 目标 {fmt.format(t)} ｜ {gap:+.1f}%",
                va="center", fontsize=8.5, color=col)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlim(0, maxv * 1.75)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=9, frameon=True)
    return ax


# ---------------------------------------------------------------------------
def slope_chart(ax, left, right, labels, left_label: str, right_label: str,
                highlight_k: int = 3, palette: Sequence[str] | None = None,
                fmt: str = "{:,.0f}"):
    """坡度图：两个时点的对比，凸显变化方向与幅度。"""
    palette = palette or ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#70AD47",
                          "#5B9BD5", "#C00000", "#7030A0"]
    for i, (a, b, lab) in enumerate(zip(left, right, labels)):
        c = palette[i % len(palette)]
        main = i < highlight_k
        ax.plot([0, 1], [a, b], color=c, linewidth=2.0 if main else 1.1,
                alpha=0.95 if main else 0.6, marker="o", markersize=5.5, zorder=3)
        ax.text(-0.03, a, f"{lab}  {fmt.format(a)}", ha="right", va="center",
                fontsize=9.5, color="#404040", fontweight="bold" if main else "normal")
        ax.text(1.03, b, fmt.format(b), ha="left", va="center", fontsize=9.5,
                color="#262626", fontweight="bold")
        if main:
            chg = (b - a) / a * 100 if a else 0.0
            ax.text(0.5, (a + b) / 2 + (max(a, b) - min(a, b)) * 0.06,
                    f"{chg:+.1f}%", ha="center", va="bottom", fontsize=8.5,
                    color="#548235" if chg >= 0 else "#C0504D")
    ax.set_xlim(-0.42, 1.42)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([left_label, right_label], fontsize=11.5, fontweight="bold")
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(bottom=False)
    ax.axvspan(-0.42, 0.02, color="#F2F2F2", zorder=0)
    ax.axvspan(0.98, 1.42, color="#F2F2F2", zorder=0)
    return ax


# ---------------------------------------------------------------------------
def donut_chart(ax, sizes, labels, colors=None, donut_size: float = 0.62,
                fmt: str = "{:,.0f}", unit: str = "", center_text: str = "",
                pct_threshold: float = 2.0, fontsize: int = 9):
    """环形图（Donut）。"""
    colors = colors or ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5",
                        "#70AD47", "#264478", "#9E480E"]
    wedges, _texts, autotexts = ax.pie(
        sizes, labels=None, colors=colors, startangle=90,
        pctdistance=1 - (1 - donut_size) / 2,
        autopct=lambda p: f"{p:.1f}%" if p >= pct_threshold else "",
        wedgeprops=dict(width=donut_size, edgecolor="white", linewidth=1.5),
        counterclock=False)
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(fontsize)
        at.set_fontweight("bold")
    ax.legend(wedges, [f"{l}　{fmt.format(s)}{unit}" for l, s in zip(labels, sizes)],
              loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=fontsize, frameon=False)
    if center_text:
        ax.text(0, 0, center_text, ha="center", va="center", fontsize=13,
                fontweight="bold", color="#262626")
    ax.set(aspect="equal")
    return ax


# ---------------------------------------------------------------------------
def stacked_progress(ax, labels, parts, colors, part_names, fmt: str = "{:.1f}%"):
    """百分比堆积条形图：展示构成随时间的结构变化。"""
    parts = np.atleast_2d(np.asarray(parts, dtype=float))
    left = np.zeros(len(labels))
    y = np.arange(len(labels))
    for j in range(parts.shape[1]):
        ax.barh(y, parts[:, j], left=left, color=colors[j % len(colors)],
                label=part_names[j], height=0.68, edgecolor="white", linewidth=0.6)
        for i in range(len(labels)):
            if parts[i, j] >= 6:
                ax.text(left[i] + parts[i, j] / 2, i, fmt.format(parts[i, j]),
                        ha="center", va="center", fontsize=8, color="white")
        left += parts[:, j]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=len(part_names),
              frameon=False, fontsize=9)
    ax.grid(axis="y", visible=False)
    return ax
