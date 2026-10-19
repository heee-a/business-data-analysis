# -*- coding: utf-8 -*-
"""
scripts/utils/config.py
=======================
全局路径、常量与数据源元信息配置。

集中管理路径的好处：任何人 clone 仓库后无需修改代码即可在任意机器上
复现全部结果（所有脚本均基于本文件计算相对路径）。

作者：商业数据分析 期末大作业
数据源：UCI Machine Learning Repository - Online Retail II (Dataset #502)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

# ---------------------------------------------------------------- 路径配置
# ROOT = 仓库根目录（business-data-analysis/）
ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
SCHEMA_DIR = DATA_DIR / "schema"

OUT_DIR = ROOT / "outputs"
FIG_DIR = OUT_DIR / "figures"
TAB_DIR = OUT_DIR / "tables"
DASH_DIR = OUT_DIR / "dashboard"
HTML_DIR = OUT_DIR / "html"

DOC_DIR = ROOT / "docs"
PAGE_DIR = ROOT / "pages"

for _d in (RAW_DIR, CLEAN_DIR, SCHEMA_DIR, FIG_DIR, TAB_DIR, DASH_DIR, HTML_DIR, PAGE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- 数据源元信息
DATA_SOURCE = {
    "name": "Online Retail II (Online Retail Data Set)",
    "publisher": "UCI Machine Learning Repository (University of California, Irvine)",
    "dataset_id": 502,
    "url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
    "download_url": "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip",
    "access_type": "官方一次性下载文件（ZIP，内含 XLSX）",
    "is_crawler": False,          # 本项目未使用任何爬虫技术
    "license": (
        "UCI ML Repository 数据集默认遵循 Creative Commons Attribution 4.0 "
        "International (CC BY 4.0) 许可，允许在教学/科研/商业分析中署名转载与再分发。"
    ),
    "acquired_date": "2026-10-19",
    "cite": (
        "Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. "
        "https://doi.org/10.24432/C60H6D"
    ),
}

RAW_ZIP = RAW_DIR / "online_retail_II.zip"
RAW_XLSX = RAW_DIR / "online_retail_II.xlsx"
RAW_SAMPLE_CSV = RAW_DIR / "online_retail_II_raw_sample.csv"
PROVENANCE_JSON = RAW_DIR / "provenance.json"
SAMPLED_INVOICES_CSV = RAW_DIR / "sampled_invoice_ids.csv"

# ---------------------------------------------------------------- 抽样参数
# 说明：源数据共 1,067,371 行（约 5.4 万张发票）。为控制仓库体积与分析耗时，
# 采用「按发票随机抽样」而非「按明细行抽样」——这样能完整保留每一笔订单的
# 购物篮结构，保证后续 Apriori 关联规则分析的真实性（若按行抽样会撕裂购物篮）。
RANDOM_SEED = 2026          # 固定随机种子，保证结果完全可复现
SAMPLE_FRAC = 0.30          # 抽取 30% 的发票（保留其全部明细行）

# ---------------------------------------------------------------- 清洗参数
# 分析基准日：源数据最后一笔交易日期 + 1 天，作为 Recency 计算的“现在”
ANALYSIS_SNAPSHOT_DATE = "2011-12-10"

# 非商品类 StockCode（运费/手续费/慈善/手工调整/邮费等），需单列治理
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "M/2", "AMAZONFEE", "BANK CHARGES", "CRUK", "D", "PADS", "S",
}

# 异常值阈值（业务依据见 02_clean.py 注释）
MAX_QUANTITY = 100_000      # 单笔明细数量上限
MAX_UNIT_PRICE = 10_000     # 单价上限（英镑）

# ---------------------------------------------------------------- 分析参数
RFM_METHOD = "median"       # 高/低切分方式：中位数（数据右偏，抗极值稳健）
TOP_N_COUNTRIES = 12
TOP_N_PRODUCTS = 15
COHORT_PERIOD = "M"         # 同期群粒度：月度

# 购物篮分析
APRIORI_MIN_SUPPORT = 0.01      # 最小支持度（业务：低于 1% 的项集缺乏铺货价值）
APRIORI_MIN_LIFT = 1.0          # 提升度阈值：>1 表示正相关，具备搭配价值
APRIORI_MIN_CONF = 0.15
APRIORI_TOP_ITEMS = 120         # 参与编码的高频商品数（控制稀疏矩阵规模）

# 时间序列预测
FORECAST_FREQ = "D"             # 日频
FORECAST_TEST_DAYS = 30         # 回测留出最后 30 天作为测试集
SARIMA_ORDER = (1, 1, 1)
SARIMA_SEASONAL_ORDER = (1, 0, 1, 7)   # 周周期（零售典型的周内效应）

# ---------------------------------------------------------------- 输出规范
FIG_DPI = 200               # 图片分辨率（要求 ≥150dpi）
FIG_FORMAT = "png"

print_prefix = "[bda]"


def banner(msg: str) -> str:
    """统一的控制台分隔横幅，便于观察 run_all.py 的执行进度。"""
    line = "=" * 72
    return f"\n{line}\n{msg}\n{line}"
