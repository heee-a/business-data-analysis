# -*- coding: utf-8 -*-
"""
01_load.py —— 数据获取（合规·非爬虫）
=====================================
功能：
    1. 从 UCI Machine Learning Repository 官方地址下载 Online Retail II 数据集
       （白名单方式：官方一次性下载文件 ZIP，未使用任何爬虫技术）；
    2. 解析压缩包内的 online_retail_II.xlsx（两个工作表：Year 2009-2010 / Year 2010-2011）；
    3. 记录数据来源溯源信息（URL、获取日期、License、SHA256 校验值）；
    4. 按「发票」随机抽样（随机种子固定），在保留完整购物篮结构的前提下降低数据规模；
    5. 输出 data/raw/online_retail_II_raw_sample.csv 与从溯源文件 provenance.json。

抽样方法的业务/技术依据：
    源数据共 1,067,371 行明细。若按「行」随机抽样，同一张发票的明细可能被拆散，
    导致购物篮被撕裂、Apriori 关联规则失真。因此本项目按「发票（Invoice）」抽样，
    选中发票保留其全部明细行 —— 抽样单元 = 交易，而非明细行。

运行：
    python scripts/01_load.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402


# ---------------------------------------------------------------------------
def download_raw(force: bool = False) -> Path:
    """下载并解压官方 ZIP 文件。已存在则跳过下载（幂等设计）。"""
    if not cfg.RAW_XLSX.exists() or force:
        if not cfg.RAW_ZIP.exists() or force:
            iou.log(f"正在从官方地址下载：{cfg.DATA_SOURCE['download_url']}")
            iou.download_file(cfg.DATA_SOURCE["download_url"], cfg.RAW_ZIP)
        iou.log(f"正在解压到 {cfg.RAW_DIR}")
        with zipfile.ZipFile(cfg.RAW_ZIP, "r") as z:
            z.extractall(cfg.RAW_DIR)
    return cfg.RAW_XLSX


def load_full_excel(xlsx_path: Path) -> pd.DataFrame:
    """读取两个年度工作表并纵向合并，保留 SourceSheet 以区分来源。"""
    iou.log("读取 online_retail_II.xlsx（两个工作表）…")
    frames = []
    for sheet in ["Year 2009-2010", "Year 2010-2011"]:
        df = pd.read_excel(xlsx_path, sheet_name=sheet, engine="openpyxl")
        df["SourceSheet"] = sheet.replace("Year ", "")
        frames.append(df)
        iou.log(f"  · {sheet}: {len(df):,} 行 × {df.shape[1]} 列")
    full = pd.concat(frames, ignore_index=True)
    iou.log(f"合并后总行数：{len(full):,}")
    return full


def profile_raw(df: pd.DataFrame) -> pd.DataFrame:
    """生成原始数据概览报告（行数、缺失率、唯一值数、类型）。"""
    report = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "non_null": [int(df[c].notna().sum()) for c in df.columns],
        "missing": [int(df[c].isna().sum()) for c in df.columns],
        "missing_pct": [round(df[c].isna().mean() * 100, 3) for c in df.columns],
        "n_unique": [int(df[c].nunique(dropna=True)) for c in df.columns],
        "sample_value": [str(df[c].dropna().iloc[0])[:40] if df[c].notna().any() else ""
                         for c in df.columns],
    })
    return report


def sample_by_invoice(df: pd.DataFrame, frac: float, seed: int):
    """
    按发票随机抽样：随机抽取 frac 比例的 Invoice，保留这些发票的全部明细行。

    Returns
    -------
    sampled_df : DataFrame  抽样后的明细数据
    audit : dict            抽样审计信息
    """
    rng = np.random.default_rng(seed)
    invoices = df["Invoice"].dropna().astype(str).unique()
    n_total = len(invoices)
    n_keep = max(1, int(round(n_total * frac)))
    keep_ids = rng.choice(invoices, size=n_keep, replace=False)

    before_rows = len(df)
    sampled = df[df["Invoice"].astype(str).isin(set(keep_ids))].copy()
    sampled = sampled.sort_values(["Invoice", "InvoiceDate"]).reset_index(drop=True)

    audit = {
        "method": "按发票（Invoice）随机抽样，保留选中发票的全部明细行",
        "reason": "保持购物篮完整性，避免按行抽样撕裂同一订单的明细",
        "random_seed": int(seed),
        "sample_fraction": frac,
        "n_invoices_total": int(n_total),
        "n_invoices_sampled": int(n_keep),
        "n_rows_total": int(before_rows),
        "n_rows_after": int(len(sampled)),
        "retained_row_ratio": round(len(sampled) / before_rows, 4),
        "date_min": str(pd.to_datetime(sampled["InvoiceDate"]).min()),
        "date_max": str(pd.to_datetime(sampled["InvoiceDate"]).max()),
    }
    return sampled, pd.DataFrame({"Invoice": keep_ids}), audit


# ---------------------------------------------------------------------------
def main() -> None:
    print(cfg.banner("STEP 01 · 数据获取（UCI 官方下载 · 合规非爬虫）"))

    # 1. 下载 / 解压
    xlsx = download_raw()

    # 2. 读取源数据
    full = load_full_excel(xlsx)

    # 3. 原始概览（抽样前）
    prof = profile_raw(full)
    prof_path = cfg.TAB_DIR / "01_raw_profile_before_sampling.csv"
    prof.to_csv(prof_path, index=False, encoding="utf-8-sig")
    iou.log(f"原始字段概览已写出 → {prof_path}")

    # 4. 抽样
    sampled, invoice_ids, audit = sample_by_invoice(full, cfg.SAMPLE_FRAC, cfg.RANDOM_SEED)
    iou.log("抽样结果：" + json.dumps(audit, ensure_ascii=False, indent=2))

    # 5. 写出抽样后的"原始数据"
    sampled.to_csv(cfg.RAW_SAMPLE_CSV, index=False, encoding="utf-8")
    invoice_ids.to_csv(cfg.SAMPLED_INVOICES_CSV, index=False, encoding="utf-8")
    iou.log(f"抽样后原始数据已保存 → {cfg.RAW_SAMPLE_CSV} （{len(sampled):,} 行）")
    # 同步输出 gzip 归档版（31MB → 4.7MB）供仓库追踪，见 io_utils.gzip_archive 注释
    iou.gzip_archive(cfg.RAW_SAMPLE_CSV)

    # 6. 溯源信息（合规声明的核心证据）
    provenance = {
        **cfg.DATA_SOURCE,
        "file_sha256": iou.sha256_of(cfg.RAW_ZIP) if cfg.RAW_ZIP.exists() else None,
        "downloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sampling": audit,
        "columns": list(sampled.columns),
        "n_rows_raw_sample": int(len(sampled)),
        "crawler_declaration": (
            "本项目数据获取全程未使用任何爬虫技术（未使用 Scrapy / Selenium / "
            "requests+网页解析 / 模拟登录抓取等），仅通过 UCI 官方提供的一次性"
            "下载文件（ZIP）获取，符合课程附件A白名单要求。"
        ),
    }
    cfg.PROVENANCE_JSON.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    iou.log(f"溯源信息已写出 → {cfg.PROVENANCE_JSON}")

    # 7. 抽样后概览
    prof_after = profile_raw(sampled)
    prof_after.to_csv(cfg.TAB_DIR / "01_raw_profile_after_sampling.csv",
                      index=False, encoding="utf-8-sig")
    iou.log("STEP 01 完成 ✓")


if __name__ == "__main__":
    main()
