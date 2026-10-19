# -*- coding: utf-8 -*-
"""
02_clean.py —— 数据清洗与治理
=============================
全流程：
    1. 读取 data/raw/online_retail_II_raw_sample.csv（抽样后的原始数据）
    2. 类型与格式统一（日期/数值/字符串）
    3. 重复值去除
    4. 缺失值处理（Description 回填、客户缺失标记 GUEST）
    5. 异常值识别（取消订单、负数量、零单价、非商品费用、超阈值极值）
    6. 派生指标与维度（Revenue、年月季周、小时、商品品类）
    7. 构建星型模型事实表 + 维度表，并完成主外键一致性校验
    8. 导出 CSV / JSON / SQLite 三种格式到 data/clean/

每张表的角色：
    fact_order_items  事实表：订单行项目粒度（主表）
    dim_orders        维度表（退化）：订单头粒度
    dim_customers     维度表：客户
    dim_products      维度表：商品
    dim_date          维度表：日期

运行：
    python scripts/02_clean.py
"""

from __future__ import annotations

import gzip
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

# ---------------------------------------------------------------------------
# 商品品类派生规则（关键词 -> 品类）。
# 说明：源数据未提供品类字段，故基于商品描述（Description）做关键词派生。
# 规则按优先级依序遍历，第一个命中的关键词决定品类；未命中归入 Other。
# 该派生维度仅用于结构化分析（如树图、波士顿矩阵），不参与金额类指标的计算口径。
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Christmas & Seasonal", ["CHRISTMAS", "XMAS", "ADVENT", "EASTER", "SANTA", "REINDEER",
                              "SNOW", "NORDIC", "GINGERBREAD"]),
    ("Home Decor & Lighting", ["LIGHT", "LANTERN", "CANDLE", "T-LIGHT", "TEALIGHT", "HOLDER",
                               "FRAME", "MIRROR", "CLOCK", "VASE", "ORNAMENT", "PHOTOFRAME"]),
    ("Kitchen & Dining", ["MUG", "CUP", "PLATE", "BOWL", "CUTLERY", "FORK", "SPOON", "KNIFE",
                          "CAKE", "TEA", "COFFEE", "MILK", "JUG", "BOTTLE", "JAM", "SUGAR",
                          "CANISTER", "TEAPOT", "BREAD", "TRAY", "APRON", "OVEN", "COASTER"]),
    ("Bags & Storage", ["BAG", "TOTE", "SHOPPER", "BASKET", "BOX", "CRATE", "STORAGE", "HAMPER"]),
    ("Stationery & Wrap", ["CARD", "WRAP", "ENVELOPE", "NOTEBOOK", "PENCIL", "PEN", "TAPE",
                           "TISSUE", "PAPER", "BOOK", "RIBBON", "TAG"]),
    ("Toys & Games", ["TOY", "GAME", "PLAYHOUSE", "PUZZLE", "DOLL", "TEDDY", "BEAR", "RABBIT",
                      "SPACEBOY", "JUMPING", "SKIPPING"]),
    ("Garden & Outdoor", ["GARDEN", "PLANT", "FLOWER", "WATERING", "SEED", "DOORSTOP",
                          "BIRD", "PARASOL", "DECKCHAIR"]),
    ("Bath & Fragrance", ["SOAP", "BATH", "TOWEL", "SCENT", "FRAGRANCE", "PERFUME", "AIR FRESHENER"]),
    ("Jewellery & Accessory", ["NECKLACE", "BRACELET", "EARRING", "RING", "BROOCH", "HAIR",
                               "KEY", "PURSE", "GLOVE", "SCARF", "HAT", "UMBRELLA"]),
    ("Party & Occasion", ["PARTY", "BALLOON", "CAKE STAND", "CONFETTI", "BUNTING", "WEDDING",
                          "HEN", "INVITE", "BIRTHDAY"]),
]


def assign_category(desc: str) -> str:
    """依据商品描述关键词派生品类。"""
    d = desc.upper()
    for cat, kws in CATEGORY_RULES:
        for kw in kws:
            if kw in d:
                return cat
    return "Other Household"


# ---------------------------------------------------------------------------
def read_raw() -> pd.DataFrame:
    src = cfg.RAW_SAMPLE_CSV
    if not src.exists():
        # 仓库中只追踪 gzip 归档版（.csv.gz），克隆后自动解压出 .csv
        gz = src.with_suffix(src.suffix + ".gz")
        if gz.exists():
            iou.log(f"未找到 {src.name}，从归档 {gz.name} 解压中…")
            with gzip.open(gz, "rb") as fin, open(src, "wb") as fout:
                shutil.copyfileobj(fin, fout)
        else:
            raise FileNotFoundError(f"未找到 {src}，请先运行 scripts/01_load.py")
    df = pd.read_csv(src, dtype={"Invoice": str, "StockCode": str, "Customer ID": str})
    iou.log(f"读入原始数据：{len(df):,} 行 × {df.shape[1]} 列")
    return df


def unify_types(df: pd.DataFrame) -> pd.DataFrame:
    """类型与格式统一。"""
    df = df.copy()
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    df["Description"] = df["Description"].astype(str).str.strip().str.upper()
    df["Country"] = df["Country"].astype(str).str.strip().str.title()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").astype("Int64")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").astype(float)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Customer ID"] = df["Customer ID"].astype(str).str.strip()
    df["Customer ID"] = df["Customer ID"].replace({"NAN": np.nan, "NONE": np.nan, "": np.nan})
    return df


def handle_missing(df: pd.DataFrame, audit: dict) -> pd.DataFrame:
    """缺失值处理。"""
    df = df.copy()
    desc_missing = int(df["Description"].isna().sum())
    # 策略：缺失商品描述用 StockCode 回填，保证商品维表名称可用；
    #       同时标记 IsDescImputed 便于追溯。
    mask_desc = df["Description"].isna()
    df["IsDescImputed"] = mask_desc.astype(int)
    df.loc[mask_desc, "Description"] = "UNKNOWN-" + df.loc[mask_desc, "StockCode"].astype(str)

    cust_missing = int(df["Customer ID"].isna().sum())
    # 策略：客户缺失的行保留（真实决定了销售规模），标记 IsGuest；
    #       在 RFM / 同期群等需要客户主键的分析中予以剔除。
    mask_guest = df["Customer ID"].isna()
    df["IsGuest"] = mask_guest.astype(int)
    df["Customer ID"] = df["Customer ID"].fillna("GUEST")

    # 无法解析日期/单价的行直接剔除（关键字段，无法推断）
    bad = df["InvoiceDate"].isna() | df["Price"].isna() | df["Quantity"].isna()
    audit["drop_unparsable_rows"] = int(bad.sum())
    df = df[~bad].copy()

    audit["desc_missing_filled"] = desc_missing
    audit["customer_missing_marked_guest"] = cust_missing
    audit["customer_missing_pct"] = round(cust_missing / len(df) * 100, 3)
    return df


def remove_duplicates(df: pd.DataFrame, audit: dict) -> pd.DataFrame:
    """完全重复行去重。零售场景下同一发票同一商品可能出现多次（拆行发货），
    因此仅删除**所有字段完全一致**的记录，不做业务疑似重复合并。"""
    before = len(df)
    df = df.drop_duplicates(keep="first").copy()
    audit["duplicates_removed"] = before - len(df)
    return df


def detect_outliers(df: pd.DataFrame, audit: dict):
    """
    异常值识别（采用"标记 + 分流"而非粗暴删除，分流结果单独落盘便于审计）。

    规则与业务依据：
      R1 取消订单：Invoice 以 'C' 开头，代表冲销，计入 t02_cancelled_orders
      R2 负数量/零单价：Quantity<=0（退货/盘亏）或 Price<=0（赠品/系统占位），
         无法代表有效销售，计入 t02_outlier_rows
      R3 非商品费用：StockCode 属于 POST/DOT/M/AMAZONFEE/BANK CHARGES/CRUK 等，
         属物流与财务科目，非商品销售，计入 t02_nonproduct_costs
      R4 极值：Quantity > 100000 或 Price > 10000（远超同类目 99.99 分位），
         判定为录入/批处理异常，计入 t02_outlier_rows
    """
    # R1 取消订单
    m_cancel = df["Invoice"].str.startswith("C", na=False)
    cancelled = df[m_cancel].copy()

    # R3 非商品费用（在取消订单剔除后再判定）
    remain = df[~m_cancel].copy()
    non_std = remain["StockCode"].isin(cfg.NON_PRODUCT_CODES) | \
        remain["StockCode"].str.startswith("GIFT_", na=False) | remain["StockCode"].str.startswith("PADS", na=False)
    nonproduct = remain[non_std].copy()

    remain2 = remain[~non_std].copy()

    # R2 / R4 负数量、零单价、极值
    m_bad = (
        (remain2["Quantity"] <= 0)
        | (remain2["Price"] <= 0)
        | (remain2["Quantity"] > cfg.MAX_QUANTITY)
        | (remain2["Price"] > cfg.MAX_UNIT_PRICE)
    )
    outliers = remain2[m_bad].copy()
    clean = remain2[~m_bad].copy()

    audit.update({
        "outlier_rule_counts": {
            "R1_cancelled_orders": int(m_cancel.sum()),
            "R3_nonproduct_charges": int(non_std.sum()),
            "R2_R4_invalid_or_extreme": int(m_bad.sum()),
        },
        "rows_after_outlier_removal": int(len(clean)),
    })
    return clean, cancelled, nonproduct, outliers


def derive_fields(df: pd.DataFrame) -> pd.DataFrame:
    """派生指标与时间维度列。"""
    df = df.copy()
    df["Revenue"] = (df["Quantity"].astype(float) * df["Price"]).round(2)
    dt = df["InvoiceDate"]
    df["OrderDate"] = dt.dt.normalize()
    df["Year"] = dt.dt.year
    df["Month"] = dt.dt.month
    df["MonthPeriod"] = dt.dt.to_period("M").astype(str)
    df["Quarter"] = df["Year"].astype(str) + "Q" + dt.dt.quarter.astype(str)
    df["Weekday"] = dt.dt.dayofweek            # 0=周一
    df["WeekdayName"] = dt.dt.day_name()
    df["IsWeekend"] = (df["Weekday"] >= 5).astype(int)
    df["Hour"] = dt.dt.hour
    df["Week"] = dt.dt.isocalendar().week.astype(int)
    df["ISOYear"] = dt.dt.isocalendar().year.astype(int)
    df["ProductCategory"] = df["Description"].map(assign_category)
    return df


def check_consistency(df: pd.DataFrame, audit: dict) -> None:
    """订单头一致性校验：同一 Invoice 的日期/客户/国家应唯一。"""
    g = df.groupby("Invoice")
    conflict_date = int((g["OrderDate"].nunique() > 1).sum())
    conflict_cust = int((g["Customer ID"].nunique() > 1).sum())
    conflict_ctry = int((g["Country"].nunique() > 1).sum())
    audit["order_header_conflicts"] = {
        "invoice_with_multi_date": conflict_date,
        "invoice_with_multi_customer": conflict_cust,
        "invoice_with_multi_country": conflict_ctry,
    }


def build_star_schema(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """构建星型模型：1 张事实表 + 4 张维度表。"""
    # ---- 事实表（订单行项目粒度，主表）
    fact = df[[
        "Invoice", "StockCode", "Description", "Customer ID", "Country", "InvoiceDate",
        "OrderDate", "Quantity", "Price", "Revenue", "Year", "Month", "MonthPeriod",
        "Quarter", "Weekday", "WeekdayName", "IsWeekend", "Hour", "Week", "ISOYear",
        "IsGuest", "ProductCategory",
    ]].rename(columns={"Customer ID": "CustomerID", "InvoiceDate": "InvoiceTS"})
    fact.insert(0, "RowID", np.arange(1, len(fact) + 1))

    # ---- dim_orders（订单头）
    orders = (df.groupby("Invoice")
                .agg(InvoiceTS=("InvoiceDate", "min"),
                     OrderDate=("OrderDate", "min"),
                     CustomerID=("Customer ID", "first"),
                     Country=("Country", "first"),
                     ProductCategory=("ProductCategory", lambda s: s.mode().iloc[0]),
                     LineCount=("StockCode", "size"),
                     TotalQuantity=("Quantity", "sum"),
                     Revenue=("Revenue", "sum"))
                .reset_index())
    orders["Revenue"] = orders["Revenue"].round(2)

    # ---- dim_customers
    customers = (df[df["IsGuest"] == 0]
                 .groupby("Customer ID")
                 .agg(Country=("Country", lambda s: s.mode().iloc[0]),
                      FirstOrderDate=("OrderDate", "min"),
                      LastOrderDate=("OrderDate", "max"),
                      OrderCount=("Invoice", "nunique"),
                      LineCount=("Invoice", "size"),
                      TotalQuantity=("Quantity", "sum"),
                      Monetary=("Revenue", "sum"),
                      MainCategory=("ProductCategory", lambda s: s.mode().iloc[0]))
                 .reset_index()
                 .rename(columns={"Customer ID": "CustomerID"}))
    customers["Monetary"] = customers["Monetary"].round(2)
    customers["AOV"] = (customers["Monetary"] / customers["OrderCount"]).round(2)

    # ---- dim_products
    products = (df.groupby("StockCode")
                  .agg(Description=("Description", lambda s: s.mode().iloc[0]),
                       ProductCategory=("ProductCategory", lambda s: s.mode().iloc[0]),
                       UnitPriceMean=("Price", "mean"),
                       UnitPriceStd=("Price", "std"),
                       TimesSold=("Quantity", "size"),
                       TotalQuantity=("Quantity", "sum"),
                       Revenue=("Revenue", "sum"))
                  .reset_index())
    products["UnitPriceMean"] = products["UnitPriceMean"].round(4)
    products["UnitPriceStd"] = products["UnitPriceStd"].round(4)
    products["Revenue"] = products["Revenue"].round(2)

    # ---- dim_date
    all_days = pd.date_range(df["OrderDate"].min(), df["OrderDate"].max(), freq="D")
    dim_date = pd.DataFrame({"Date": all_days.strftime("%Y-%m-%d")})
    d = pd.to_datetime(dim_date["Date"])
    dim_date["Year"] = d.dt.year
    dim_date["Month"] = d.dt.month
    dim_date["MonthPeriod"] = d.dt.to_period("M").astype(str)
    dim_date["Quarter"] = d.dt.year.astype(str) + "Q" + d.dt.quarter.astype(str)
    dim_date["Weekday"] = d.dt.dayofweek
    dim_date["WeekdayName"] = d.dt.day_name()
    dim_date["IsWeekend"] = (dim_date["Weekday"] >= 5).astype(int)
    dim_date["MonthName"] = d.dt.month.map(
        {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul",
         8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"})

    return {
        "fact_order_items": fact,
        "dim_orders": orders,
        "dim_customers": customers,
        "dim_products": products,
        "dim_date": dim_date,
    }


def write_schema_docs(tables: dict[str, pd.DataFrame], audit: dict) -> None:
    """输出数据字典与 ER 说明到 data/schema/。"""
    rows = []
    dtype_map = {
        "Invoice": ("字符串", "订单号；以 C 开头为取消单"),
        "StockCode": ("字符串", "商品编码"),
        "CustomerID": ("字符串", "客户编号；缺失填 GUEST"),
        "Country": ("字符串", "客户所在国家"),
        "InvoiceTS": ("日期时间", "订单时间戳"),
        "OrderDate": ("日期", "订单日期（日粒度）"),
        "Quantity": ("整数", "销售数量（退货为负）"),
        "Price": ("浮点数", "单价（英镑 £）"),
        "Revenue": ("浮点数", "销售额 = Quantity × Price（£）"),
        "ProductCategory": ("字符串", "派生品类（关键词规则映射）"),
    }
    for tname, tdf in tables.items():
        for c in tdf.columns:
            dt, desc = dtype_map.get(c, ("-", "-"))
            rows.append({
                "表名": tname, "字段": c,
                "pandas类型": str(tdf[c].dtype),
                "逻辑类型": dt, "取值示例": str(tdf[c].dropna().iloc[0])[:30],
                "非空率": f"{tdf[c].notna().mean():.2%}",
                "说明": desc,
            })
    dict_df = pd.DataFrame(rows)
    dict_df.to_csv(cfg.SCHEMA_DIR / "data_dictionary.csv", index=False, encoding="utf-8-sig")

    er = {
        "model": "星型模型（Star Schema）",
        "fact_table": "fact_order_items",
        "grain": "一行 = 一张发票中的一个商品明细项",
        "dimensions": {
            "dim_orders": "订单头，主键 Invoice（1:N 关联 fact_order_items.Invoice）",
            "dim_customers": "客户维，主键 CustomerID（1:N 关联 dim_orders.CustomerID）",
            "dim_products": "商品维，主键 StockCode（1:N 关联 fact_order_items.StockCode）",
            "dim_date": "日期维，主键 Date（1:N 关联 fact_order_items.OrderDate）",
        },
        "foreign_keys": [
            "fact_order_items.Invoice  → dim_orders.Invoice",
            "fact_order_items.StockCode → dim_products.StockCode",
            "fact_order_items.OrderDate → dim_date.Date",
            "dim_orders.CustomerID → dim_customers.CustomerID",
        ],
        "row_counts": {k: int(len(v)) for k, v in tables.items()},
        "governance_audit": audit,
    }
    iou.save_json(er, cfg.SCHEMA_DIR / "star_schema.json")

    md = ["# 数据仓库 schema 说明\n",
          f"- 模型：**{er['model']}**",
          f"- 事实表：`{er['fact_table']}`，粒度：{er['grain']}",
          "- 维度表：" + "、".join(f"`{k}`" for k in er["dimensions"]),
          "\n## 主外键关系\n"]
    md += [f"{i+1}. `{fk}`" for i, fk in enumerate(er["foreign_keys"])]
    md += ["\n## 表行数\n| 表名 | 行数 |", "|---|---|"]
    md += [f"| {k} | {v:,} |" for k, v in er["row_counts"].items()]
    iou.write_text("\n".join(md), cfg.SCHEMA_DIR / "README_schema.md")


# ---------------------------------------------------------------------------
def main() -> None:
    print(cfg.banner("STEP 02 · 数据清洗与治理"))
    audit: dict = {"started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    df = read_raw()
    audit["rows_raw"] = int(len(df))

    df = unify_types(df)
    df = remove_duplicates(df, audit)
    df = handle_missing(df, audit)
    clean, cancelled, nonproduct, outliers = detect_outliers(df, audit)
    clean = derive_fields(clean)
    check_consistency(clean, audit)

    audit["rows_valid"] = int(len(clean))
    audit["retention_rate"] = round(len(clean) / audit["rows_raw"], 4)
    audit["date_range"] = [str(clean["OrderDate"].min().date()),
                           str(clean["OrderDate"].max().date())]
    audit["n_customers"] = int(clean.loc[clean["IsGuest"] == 0, "Customer ID"].nunique())
    audit["n_products"] = int(clean["StockCode"].nunique())
    audit["n_invoices"] = int(clean["Invoice"].nunique())
    audit["n_countries"] = int(clean["Country"].nunique())
    audit["total_revenue_gbp"] = round(float(clean["Revenue"].sum()), 2)

    # --- 异常/旁路表落盘（保证治理过程可审计）
    iou.save_table(cancelled, "02_cancelled_orders")
    iou.save_table(nonproduct, "02_nonproduct_costs")
    iou.save_table(outliers, "02_outlier_rows")

    # --- 星型模型
    tables = build_star_schema(clean)
    for name, tdf in tables.items():
        tdf.to_csv(cfg.CLEAN_DIR / f"{name}.csv", index=False, encoding="utf-8")
    iou.log("星型模型表已写入 data/clean/：" + ", ".join(tables))

    # --- 归档压缩版（.csv.gz / .sqlite.gz）
    # 说明：明细事实表与 SQLite 库体积较大（原始分别为 ~54MB / ~63MB），
    # 直接提交到 Git 会使仓库膨胀到 200MB 以上。这里同步输出 gzip 归档版本
    # （合计约 18MB）供仓库追踪，未压缩版本仍保留在本地便于直接用 Excel 查看。
    # .gitignore 只忽略未压缩的大文件，不影响任何人执行流水线重新生成。
    iou.gzip_archive(cfg.CLEAN_DIR / "fact_order_items.csv")
    iou.gzip_archive(cfg.CLEAN_DIR / "retail_clean.sqlite")

    # --- 多格式导出（CSV / JSON / SQLite）
    db = iou.to_sqlite(
        {**tables,
         "t02_cancelled_orders": cancelled,
         "t02_nonproduct_costs": nonproduct,
         "t02_outlier_rows": outliers},
        cfg.CLEAN_DIR / "retail_clean.sqlite",
    )
    iou.save_table(
        pd.DataFrame({
            "table": list(tables) + ["t02_cancelled_orders", "t02_nonproduct_costs", "t02_outlier_rows"],
            "rows": [len(t) for t in tables.values()] + [len(cancelled), len(nonproduct), len(outliers)],
        }), "02_clean_rowcounts", also_json=False)

    write_schema_docs(tables, audit)

    audit["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    iou.save_json(audit, cfg.TAB_DIR / "02_clean_audit.json")

    # --- 清洗前后质量对比报告
    q = pd.DataFrame({
        "治理环节": ["原始（抽样后）", "去除完全重复", "剔除无法解析关键字段",
                     "剔除取消/异常/非商品", "最终有效数据"],
        "剩余行数": [
            audit["rows_raw"],
            audit["rows_raw"] - audit["duplicates_removed"],
            audit["rows_raw"] - audit["duplicates_removed"] - audit["drop_unparsable_rows"],
            audit["rows_valid"] + len(cancelled),
            audit["rows_valid"],
        ],
    })
    q["占总行比"] = (q["剩余行数"] / audit["rows_raw"]).map(lambda x: f"{x:.2%}")
    iou.save_table(q, "02_data_quality_report", also_json=False)

    iou.log("清洗关键指标：" + json.dumps(audit, ensure_ascii=False, indent=2))
    iou.log(f"SQLite：{db}")
    iou.log("STEP 02 完成 ✓")


if __name__ == "__main__":
    main()
