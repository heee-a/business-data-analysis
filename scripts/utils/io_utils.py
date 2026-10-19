# -*- coding: utf-8 -*-
"""
scripts/utils/io_utils.py
=========================
通用输入输出工具：日志、下载（带进度与重试）、哈希校验、
多格式导出（CSV / JSON / SQLite）、结果表落盘。
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

from . import config as cfg


# ---------------------------------------------------------------- 日志
def log(msg: str, level: str = "INFO") -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {cfg.print_prefix} {level:<5} | {msg}", flush=True)


# ---------------------------------------------------------------- 下载
def download_file(url: str, dest: Path, retries: int = 3, timeout: int = 120) -> Path:
    """从官方地址下载文件（带 UA 伪装以通过部分静态服务器的校验，非爬虫行为）。"""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "business-data-analysis-course/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
                total = int(resp.headers.get("Content-Length") or 0)
                downloaded = 0
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        sys.stdout.write(f"\r  下载进度 {pct:6.2f}%  "
                                         f"({downloaded/1_048_576:.1f}/{total/1_048_576:.1f} MB)")
                        sys.stdout.flush()
                sys.stdout.write("\n")
            log(f"下载完成 → {dest} ({dest.stat().st_size/1_048_576:.2f} MB)")
            return dest
        except Exception as e:  # noqa: BLE001
            last_err = e
            log(f"第 {attempt}/{retries} 次下载失败：{e}", "WARN")
            time.sleep(2 * attempt)
    raise RuntimeError(f"下载失败：{url}") from last_err


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    """计算文件 SHA256（用于数据完整性校验与溯源）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


# ---------------------------------------------------------------- 导出
def save_table(df: pd.DataFrame, name: str, also_json: bool = True) -> list[Path]:
    """
    保存结果表：CSV（主）+ JSON（可选）。统一 UTF-8(BOM) 以便 Excel 直接打开不乱码。
    """
    paths: list[Path] = []
    csv_path = cfg.TAB_DIR / f"{name}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    paths.append(csv_path)
    if also_json and len(df) <= 200_000:
        js_path = cfg.TAB_DIR / f"{name}.json"
        df.to_json(js_path, orient="records", force_ascii=False, indent=1)
        paths.append(js_path)
    log(f"结果表已写出 → {csv_path.name}  ({len(df):,} 行 × {df.shape[1]} 列)")
    return paths


def to_sqlite(tables: dict[str, pd.DataFrame], db_path: Path) -> Path:
    """将多张符合主外键关系的表写入同一个 SQLite 数据库，便于复用与验证。"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as con:
        for tname, tdf in tables.items():
            tdf.to_sql(tname, con, index=False, if_exists="replace")
        con.commit()
    size_mb = db_path.stat().st_size / 1_048_576
    log(f"SQLite 数据库已写出 → {db_path} ({size_mb:.2f} MB, {len(tables)} 张表)")
    return db_path


def gzip_archive(path: Path, level: int = 6) -> Path:
    """
    生成 gzip 归档版本（*.gz），用于仓库体积控制。

    用途：明细事实表（~54MB）与 SQLite 库（~63MB）体积过大，直接提交 Git
    会让仓库膨胀到 200MB 以上。压缩后二者合计约 18MB，克隆与 Pages 部署都更快。
    未压缩版本依然保留在本地，便于直接用 Excel / DB Browser 打开核对。
    """
    path = Path(path)
    if not path.exists():
        return path
    gz_path = path.with_suffix(path.suffix + ".gz")
    with open(path, "rb") as fin, gzip.GzipFile(
        gz_path, "wb", compresslevel=level, mtime=0
    ) as fout:                       # mtime=0 → 内容不变时压缩包字节一致，避免 Git 无意义 diff
        shutil.copyfileobj(fin, fout)
    ratio = gz_path.stat().st_size / max(path.stat().st_size, 1) * 100
    log(f"归档 {path.name} → {gz_path.name} "
        f"({gz_path.stat().st_size/1_048_576:.2f} MB, 压缩至 {ratio:.0f}%)")
    return gz_path


def save_json(obj: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8")
    return path


def write_text(text: str, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
