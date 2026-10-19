# -*- coding: utf-8 -*-
"""
scripts/utils/style.py
======================
matplotlib 中文显示、统一配色方案与出图规范。

规范要求：
  * 中文字体正常显示
  * 坐标轴与单位标注完整
  * 配色协调统一
  * 图片分辨率 >= 150dpi（本项目统一 200dpi）
  * 图表统一命名 fig01_xxx.png
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------- 字体
# 依次尝试常见中文字体（Windows / macOS / Linux 通用），第一个命中即用
CJK_FONT_CANDIDATES = [
    "Microsoft YaHei",      # Win10/11 微软雅黑
    "Microsoft JhengHei",
    "SimHei",               # 黑体
    "DengXian",             # 等线
    "KaiTi",
    "Source Han Sans SC",   # 思源黑体
    "Noto Sans CJK SC",     # Linux 常见
    "Noto Sans SC",
    "Arial Unicode MS",     # macOS
    "Heiti SC",
]


def setup_chinese_font() -> str:
    """注册并返回可用的中文字体名；若全部缺失则回退到 DejaVu Sans 并给出提示。"""
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_FONT_CANDIDATES:
        if name in available:
            chosen = name
            break
    else:  # 未找到，尝试扫描系统字体文件
        chosen = "DejaVu Sans"
        for cand in ("msyh.ttc", "msyh.ttf", "simhei.ttf", "wqy-zenhei.ttc"):
            for base in (Path("C:/Windows/Fonts"), Path("/System/Library/Fonts"),
                         Path("/usr/share/fonts")):
                p = base / cand
                if p.exists():
                    font_manager.fontManager.addfont(str(p))
                    chosen = font_manager.FontProperties(fname=str(p)).get_name()
                    break
            if chosen != "DejaVu Sans":
                break

    plt.rcParams["font.sans-serif"] = [chosen, "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False       # 解决负号显示为方块
    plt.rcParams["figure.autolayout"] = False
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelsize"] = 11
    plt.rcParams["xtick.labelsize"] = 10
    plt.rcParams["ytick.labelsize"] = 10
    plt.rcParams["legend.fontsize"] = 10
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    return chosen


def get_font_prop(size: int = 11):
    """返回一个绑定了中文字体的 FontProperties（用于水印/差异标注）。"""
    return font_manager.FontProperties(
        family=plt.rcParams["font.sans-serif"][0], size=size
    )


# ---------------------------------------------------------------- 配色
# 方案一：Excel 2013+ 默认办公主题（用于“模板复现”类图表，贴近 Excel 观感）
EXCEL_PALETTE = [
    "#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5",
    "#70AD47", "#264478", "#9E480E", "#636363", "#997300",
    "#2E75B6", "#548235", "#BF9000", "#C55A11", "#833C0C",
]

# 方案二：商务单色渐变（用于强调序列强弱）
BLUE_GRADIENT = ["#D6E4F7", "#A9C5E8", "#7FA8D6", "#5B84BE", "#3D63A0", "#2B4A7D", "#1C3762"]
ORANGE_GRADIENT = ["#FCE4CC", "#F8C286", "#F3A25C", "#EE8538", "#D06A1E", "#A8510F"]

# 方案三：暗色大屏配色（Pyecharts 大屏与深色背景图使用）
DARK_BG = "#0B1524"
DARK_PALETTE = ["#00E5FF", "#7C4DFF", "#FFB74D", "#00E676", "#FF4081", "#B2EBF2", "#FFD740"]

# 语义色
POSITIVE = "#C00000"    # 中国习惯：增长/正向用红色（财务语境此处仅作“上升”标识）
NEGATIVE = "#2E7D32"
UP_COLOR = "#C0504D"
DOWN_COLOR = "#4F81BD"


def excel_cycle(n: int) -> list[str]:
    """从 Excel 配色中循环取 n 个颜色。"""
    return [EXCEL_PALETTE[i % len(EXCEL_PALETTE)] for i in range(n)]


def add_value_labels(
    ax, bars, fmt: str = "{:,.0f}", fontsize: int = 9, offset_ratio: float = 0.02, **kw
):
    """为柱状图/条形图添加数值标签（贴近 Excel 数据标签样式）。"""
    for bar in bars:
        v = bar.get_height() if bar.get_height() != 0 else bar.get_width()
        ax.annotate(
            fmt.format(v),
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            ha="center", va="bottom", fontsize=fontsize, color="#404040", **kw
        )


def polish_axes(ax, grid_axis: str = "y", title_pad: int = 14):
    """统一坐标轴样式：网格线、刻度方向。"""
    ax.grid(axis=grid_axis, alpha=0.25, linestyle="--", linewidth=0.8, color="#8C8C8C")
    ax.set_axisbelow(True)
    ax.tick_params(colors="#404040")
    if ax.get_title():
        ax.title.set_position((0.5, 1.02))
    return ax


def source_note(fig_or_ax, text: str = "数据源：UCI ML Repository · Online Retail II", fontsize: int = 8):
    """在图表底部添加数据来源脚注（学术规范）。"""
    fig = getattr(fig_or_ax, "figure", fig_or_ax)
    fig.text(
        0.99, 0.005, text, ha="right", va="bottom", fontsize=fontsize,
        color="#808080", style="italic",
    )


def save_fig(fig, path, dpi: int = 200, close: bool = True):
    """统一保存：路径自动建目录 + 固定分辨率 + 统一白色底。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor="white", format=path.suffix.lstrip(".") or "png")
    if close:
        plt.close(fig)
    return path


def new_fig(figsize=(11, 6)):
    """创建一张符合规范的图。"""
    return plt.subplots(figsize=figsize)


# 模块被 import 时自动应用字体设置
CHOSEN_FONT = setup_chinese_font()
