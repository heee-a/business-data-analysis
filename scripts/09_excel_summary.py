# -*- coding: utf-8 -*-
"""
STEP 09 —— 关键结果 Excel 汇总

把散落在 outputs/tables/ 的 69 个结果文件中的关键表汇总为一个多 Sheet 工作簿
`outputs/tables/00_关键结果汇总.xlsx`，便于核对与二次引用。

Sheet 构成（按业务顺序）：
    00 说明            口径、数据窗口、生成方式
    01 核心指标        KPI 一览
    02 月度趋势        销售额 / 订单量 / 环比 / 同比
    03 国家市场        各国销售额与占比
    04 品类结构        品类汇总
    05 商品 TOP15      销售额前列商品
    06 RFM 八分群      各分群规模与贡献
    07 同期群留存      首购月份 × 留存月份
    08 帕累托 ABC      ABC 汇总
    09 关联规则 Top20  Apriori 高置信规则
    10 波士顿矩阵      品类份额 × 增速
    11 K-Means 画像    聚类中心与规模
    12 复购漏斗        五级转化
    13 预测回测        回测误差 + 未来 30 天
    14 图表索引        35 张图
    15 大屏组件        20 个组件

用法：  python scripts/09_excel_summary.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

OUT = cfg.TAB_DIR / "00_关键结果汇总.xlsx"

# (Sheet 名, 源文件, 读取方式, 说明)
SHEETS: list[tuple[str, str, str, str]] = [
    ("01_核心指标", "03_executive_kpis.json", "json", "清洗后数据的总体 KPI"),
    ("02_月度趋势", "03_mom_yoy_monthly.csv", "csv", "月度销售额、订单量、环比 MoM、同比 YoY"),
    ("03_国家市场", "03_country_summary.csv", "csv", "各国销售额、订单数、客户数、占比"),
    ("04_品类结构", "03_category_summary.csv", "csv", "按商品类别的销售汇总"),
    ("05_商品TOP15", "03_top_products.csv", "csv", "销售额前 15 的商品"),
    ("06_RFM八分群", "03_rfm_segment_summary.csv", "csv", "RFM 八分群的规模、营收与人均值"),
    ("07_同期群留存", "03_cohort_retention_rate.csv", "csv", "首购月份队列 × 留存率（%）"),
    ("07b_同期群人数", "03_cohort_retention_count.csv", "csv", "首购月份队列 × 留存人数"),
    ("07c_平均留存曲线", "03_cohort_avg_retention.csv", "csv", "各留存月份的平均留存率"),
    ("08_帕累托ABC", "03_abc_summary.csv", "csv", "ABC 三类 SKU 与营收占比"),
    ("09_关联规则Top20", "03_apriori_rules_top20.csv", "csv", "支持度/置信度/提升度最高的规则"),
    ("10_波士顿矩阵", "03_bcg_matrix.csv", "csv", "品类市场份额 × 同比增速"),
    ("11_KMeans画像", "03_kmeans_cluster_profile.csv", "csv", "各聚类的 RFM 均值与规模"),
    ("12_复购漏斗", "03_repurchase_funnel.csv", "csv", "五级复购转化人数与转化率"),
    ("12b_阈值稳健性", "03_rfm_threshold_sensitivity.csv", "csv", "RFM 中位数/均值/60 分位切分对比"),
    ("13_预测回测", "03_forecast_backtest.csv", "csv", "SARIMA 回测：实际 vs 预测 vs 误差"),
    ("14_未来30天预测", "03_forecast_future.csv", "csv", "SARIMA 未来 30 天点预测与置信区间"),
    ("15_图表索引", "04_figure_index.csv", "csv", "35 张图的编号、类别与说明"),
    ("16_大屏组件", "05_dashboard_components.csv", "csv", "交互大屏 20 个组件"),
]


def _frame(path: Path, kind: str) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        if kind == "json":
            obj = pd.read_json(path, orient="index")
            obj.index.name = "指标"
            obj.columns = ["数值"]
            return obj.reset_index()
        df = pd.read_csv(path, encoding="utf-8-sig")
        return df if len(df) else None
    except Exception as exc:  # pragma: no cover
        iou.log(f"[WARN] 读取失败 {path.name}：{exc}")
        return None


def main() -> int:
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for sheet, fname, kind, _ in SHEETS:
        df = _frame(cfg.TAB_DIR / fname, kind)
        if df is None:
            missing.append(fname)
        else:
            frames[sheet] = df

    if not frames:
        iou.log("[ERROR] 没有可汇总的数据，请先运行 scripts/03_analysis.py")
        return 1

    intro = pd.DataFrame({
        "项目": [
            "工作簿名称", "生成方式", "数据源", "分析窗口", "抽样方法",
            "有效明细", "注册客户", "总销售额", "可复现入口", "配套论文",
        ],
        "内容": [
            "商业数据分析 · 关键结果汇总",
            "scripts/09_excel_summary.py 自动生成（Python + openpyxl）",
            "UCI Machine Learning Repository — Online Retail II (#502)，CC BY 4.0",
            "2009-12-01 ~ 2011-11-30（剔除不完整的末月）",
            "按发票整单随机抽样 30%，随机种子 2026",
            "302,786 行", "3,763 人", "£5,676,163",
            "python run_all.py（8 阶段流水线）",
            "docs/《商业数据分析》期末大论文.docx / .pdf",
        ],
    })

    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        intro.to_excel(writer, sheet_name="00_说明", index=False)
        for sheet, df in frames.items():
            df.to_excel(writer, sheet_name=sheet, index=False)

        # ---- 统一美化
        from openpyxl.styles import Alignment, Font, PatternFill
        wb = writer.book
        header_fill = PatternFill("solid", fgColor="1F4E79")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for col in ws.columns:
                letter = col[0].column_letter
                width = max((len(str(c.value)) for c in col if c.value is not None),
                            default=8)
                ws.column_dimensions[letter].width = min(max(width * 1.6 + 2, 9), 46)
            ws.auto_filter.ref = ws.dimensions

    size = OUT.stat().st_size / 1024
    iou.log(f"STEP 09 完成 ✓ 汇总工作簿 → {OUT}（{len(frames) + 1} 个 Sheet，{size:.0f} KB）")
    if missing:
        iou.log(f"[提示] 以下源文件缺失，对应 Sheet 未生成：{', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
