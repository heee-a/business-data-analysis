# -*- coding: utf-8 -*-
"""
STEP 08 —— 交付物归档

把散落在 docs/、outputs/、data/ 下的全部生成物，按「提交类别」重新组织，
复制到作业提交目录（默认：桌面 / 商业数据分析/），并生成《提交清单.md》。

归档结构
--------
    01_期末大论文/      Word + PDF
    02_交互大屏/        离线自包含版（双击即开）+ 在线 CDN 版 + 演示截图/GIF
    03_图表/            模板复现图 25 张 · 业务模型图 10 张
    04_结果表/          明细表 CSV 38 个 · 参数与指标 JSON 30 个
    05_数据与字典/      清洗后数据（压缩）+ 维表 + 数据字典 + 星型模型
    06_源代码/          scripts/ + run_all.py + requirements.txt
    07_项目文档/        README + 图表索引 + 合规声明 + 在线地址
    提交清单.md         全部文件清单一览

幂等：重复运行时先清空本次生成的目录，再重新复制。

用法：  python scripts/08_deliver.py [目标目录]
"""
from __future__ import annotations

import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

DEFAULT_DEST = Path(r"D:/Users/HP/Desktop/商业数据分析")

PAGES_URL = "https://heee-a.github.io/business-data-analysis/"
REPO_URL = "https://github.com/heee-a/business-data-analysis"

FAILED: list[Path] = []   # 因被占用等原因未能更新的目标文件


def reset_dir(path: Path) -> Path:
    """确保目录存在。优先清空旧内容（幂等）；若旧文件被占用（如正在预览）
    则跳过清空，靠后续同名覆盖保持最新——不阻断归档。"""
    if path.exists():
        try:
            shutil.rmtree(path)
        except OSError as exc:
            iou.log(f"[WARN] 目录清理失败（将采用同名覆盖）：{path.name} — {exc}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        iou.log(f"[WARN] 缺失，跳过：{src.name}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            if dst.exists():
                dst.unlink()
            shutil.copy2(src, dst)
            return True
        except PermissionError:
            if attempt < 2:
                time.sleep(1.0)
    FAILED.append(dst)
    iou.log(f"[WARN] 目标被占用，暂未更新（稍后可单独重跑）：{dst}")
    return False


def human(size: int) -> str:
    return f"{size / 1048576:.2f} MB" if size >= 1048576 else f"{size / 1024:.0f} KB"


def main() -> int:
    dest = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_DEST
    if not dest.exists():
        iou.log(f"[ERROR] 目标目录不存在：{dest}")
        return 1

    root = cfg.ROOT
    manifest: list[tuple[str, str, str]] = []   # (相对路径, 大小, 说明)
    iou.log(f"归档目标：{dest}")

    # ---------------------------------------------------------- 01 期末大论文
    d01 = reset_dir(dest / "01_期末大论文")
    for name, note in [("《商业数据分析》期末大论文.docx", "可编辑版，含 14 张嵌入图"),
                       ("《商业数据分析》期末大论文.pdf", "打印/提交版，29 页")]:
        p = copy(root / "docs" / name, d01 / name)
        if p:
            manifest.append((f"01_期末大论文/{name}", human((d01 / name).stat().st_size), note))

    # ---------------------------------------------------------- 02 交互大屏
    d02 = reset_dir(dest / "02_交互大屏")
    pairs = [
        ("dashboard_offline.html", "大屏_离线版(双击打开).html",
         "echarts+plotly 已内联，无需联网，推荐提交"),
        ("dashboard_dark.html", "大屏_在线版(需联网).html",
         "引用 CDN，体积小，需联网加载图表库"),
    ]
    for src, dst_name, note in pairs:
        if copy(cfg.DASH_DIR / src, d02 / dst_name):
            manifest.append((f"02_交互大屏/{dst_name}",
                             human((d02 / dst_name).stat().st_size), note))

    # 大屏演示截图（评分标准 2.6 节可选创新加分材料）
    shot_dir = cfg.ROOT / "outputs" / "dashboard_screenshots"
    if shot_dir.is_dir():
        for p in sorted(shot_dir.iterdir()):
            if p.is_file() and copy(p, d02 / p.name):
                note = ("四标签 2×2 拼合（论文图 5-7）" if "拼图" in p.name
                        else "四标签轮播动画" if p.name.endswith(".gif")
                        else "大屏分 Tab 实拍截图（1920×1080）")
                manifest.append((f"02_交互大屏/{p.name}",
                                 human((d02 / p.name).stat().st_size), note))

    # ---------------------------------------------------------- 03 图表
    d03 = dest / "03_图表"
    reset_dir(d03)
    idx = cfg.TAB_DIR / "04_figure_index.csv"
    grp: dict[str, list[str]] = {}
    if idx.exists():
        import pandas as pd
        df = pd.read_csv(idx, encoding="utf-8-sig")
        df["大类"] = df["类别"].map(lambda c: "业务模型图" if "业务模型" in str(c) else "模板复现图")
        for _, r in df.iterrows():
            grp.setdefault(r["大类"], []).append(str(r["文件名"]))
    else:
        grp["模板复现图"] = [p.name for p in sorted(cfg.FIG_DIR.glob("*.png"))]

    fig_note = {"模板复现图": "复现教材规定的 23 种图表类型",
                "业务模型图": "RFM / 同期群 / ABC / Apriori / BCG / 预测 / 聚类 / 漏斗"}
    for g, files in sorted(grp.items()):
        sub = reset_dir(d03 / f"{g}_{len(files)}张")
        n = 0
        for f in files:
            if copy(cfg.FIG_DIR / f, sub / f):
                n += 1
        manifest.append((f"03_图表/{g}_{len(files)}张/", f"{n} 个文件 · 200dpi", fig_note.get(g, "")))

    # ---------------------------------------------------------- 04 结果表
    d04 = dest / "04_结果表"
    reset_dir(d04)
    for sub, pattern, note in [("明细表_csv", "*.csv", "模型输出明细，可直接用 Excel 打开"),
                               ("参数与指标_json", "*.json", "模型参数、阈值与核心指标")]:
        s = reset_dir(d04 / sub)
        files = sorted(cfg.TAB_DIR.glob(pattern))
        for f in files:
            copy(f, s / f.name)
        total = sum((s / f.name).stat().st_size for f in files if (s / f.name).exists())
        manifest.append((f"04_结果表/{sub}/", f"{len(files)} 个 · {human(total)}", note))

    xlsx = cfg.TAB_DIR / "00_关键结果汇总.xlsx"
    if copy(xlsx, d04 / xlsx.name):
        manifest.append(("04_结果表/00_关键结果汇总.xlsx",
                         human(xlsx.stat().st_size),
                         "16+1 个 Sheet 汇总工作簿，便于核对与二次引用"))

    # ---------------------------------------------------------- 05 数据与字典
    d05 = dest / "05_数据与字典"
    reset_dir(d05)
    arc = reset_dir(d05 / "清洗后数据_压缩")
    for f in sorted(cfg.CLEAN_DIR.glob("*.gz")):
        copy(f, arc / f.name)
    arc_total = sum(p.stat().st_size for p in arc.iterdir())
    manifest.append(("05_数据与字典/清洗后数据_压缩/",
                     f"{len(list(arc.iterdir()))} 个 · {human(arc_total)}",
                     "fact_order_items / 原始抽样 / SQLite，gzip 归档"))

    dim = reset_dir(d05 / "维表_csv")
    for f in sorted(cfg.CLEAN_DIR.glob("dim_*.csv")):
        copy(f, dim / f.name)
    manifest.append(("05_数据与字典/维表_csv/", f"{len(list(dim.iterdir()))} 个",
                     "客户 / 商品 / 订单 / 日期 四张维表（可直接查看）"))

    for f in sorted((cfg.DATA_DIR / "schema").glob("*")):
        copy(f, d05 / f.name)
    for f in sorted((cfg.RAW_DIR).glob("provenance.json")):
        copy(f, d05 / f.name)
    manifest.append(("05_数据与字典/", "数据字典 + 星型模型 + 溯源",
                     "data_dictionary.csv / star_schema.json / provenance.json"))

    # ---------------------------------------------------------- 06 源代码
    d06 = dest / "06_源代码"
    reset_dir(d06)
    sdir = reset_dir(d06 / "scripts")
    for f in sorted((root / "scripts").rglob("*.py")):
        rel = f.relative_to(root / "scripts")
        copy(f, sdir / rel)
    copy(root / "requirements.txt", d06 / "requirements.txt")
    copy(root / "run_all.py", d06 / "run_all.py")
    manifest.append(("06_源代码/scripts/", f"{len(list(sdir.rglob('*.py')))} 个脚本",
                     "01 取数 → 02 清洗 → 03 建模 → 04 绘图 → 05 大屏 → 06 论文 → 07 离线打包 → 08 归档"))
    manifest.append(("06_源代码/run_all.py", "-", "一键复现全流程入口"))

    # ---------------------------------------------------------- 07 项目文档
    d07 = reset_dir(dest / "07_项目文档")
    for name, note in [("README.md", "项目总览：数据来源、目录结构、复现步骤、结论摘要"),
                       ("图表索引.md", "35 张图的编号 / 类别 / 对应模型说明"),
                       ("数据来源合规声明.md", "许可证、抽样方法、 Privacy 合规说明"),
                       ("复现验证报告.md", "独立目录复跑 + MD5 逐文件比对的可复现性验证记录")]:
        p = root / "docs" / name
        if not p.exists():
            p = root / name
        if copy(p, d07 / name):
            manifest.append((f"07_项目文档/{name}", human((d07 / name).stat().st_size), note))

    (d07 / "在线成果页地址.txt").write_text(
        f"GitHub 仓库（源码）  ：{REPO_URL}\n"
        f"GitHub Pages 成果页 ：{PAGES_URL}\n"
        f"  ├─ 首页（成果总览）  {PAGES_URL}\n"
        f"  ├─ 交互大屏          {PAGES_URL}dashboard/dashboard_dark.html\n"
        f"  └─ 图表              {PAGES_URL}figures/\n",
        encoding="utf-8")
    manifest.append(("07_项目文档/在线成果页地址.txt", "-", "仓库与 Pages 在线地址"))

    # ---------------------------------------------------------- 提交清单
    lines = [
        "# 《商业数据分析》期末大作业 —— 提交清单",
        "",
        f"> 归档生成时间：{datetime.now():%Y-%m-%d %H:%M}　|　"
        f"由 `scripts/08_deliver.py` 自动生成",
        "",
        f"- **GitHub 仓库**：{REPO_URL}",
        f"- **在线成果页**：{PAGES_URL}",
        "",
        "## 一、文件清单",
        "",
        "| 文件 / 目录 | 大小 | 说明 |",
        "|---|---|---|",
    ]
    for path, size, note in manifest:
        lines.append(f"| `{path}` | {size} | {note} |")

    total = sum(p.stat().st_size for p in dest.rglob("*")
                if p.is_file() and "《商业数据分析》 - " not in p.name)
    lines += [
        "",
        f"**归档合计**：{human(total)}（不含两份原始作业要求文档）",
        "",
        "## 二、建议提交顺序",
        "",
        "1. `01_期末大论文/《商业数据分析》期末大论文.pdf` —— 主交付物（29 页 / 约 1.2 万字）",
        "2. `02_交互大屏/大屏_离线版(双击打开).html` —— 双击即可查看 4 页 20 组件联动大屏",
        "3. `03_图表/` —— 35 张 200dpi 图（论文中已嵌入 14 张关键图）",
        "4. `04_结果表/` —— 68 个模型输出文件，供数据核对",
        "5. `05_数据与字典/` —— 清洗后数据与数据字典",
        "6. `06_源代码/` —— 全流程可复现代码",
        "",
        "## 三、需要你补充的一项",
        "",
        "论文封面「专业班级 / 学号 / 姓名」目前为占位符。请编辑 `06_源代码/scripts/06_report.py`",
        "顶部的 `SCHOOL_INFO` 字典后重新运行：",
        "",
        "```bash",
        "python scripts/06_report.py      # 重新生成 Word",
        "python scripts/07_offline_bundle.py",
        "python scripts/08_deliver.py     # 重新归档",
        "```",
        "",
        "PDF 由本机 Word 导出，若需重新生成：",
        "```powershell",
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false",
        "$d = $w.Documents.Open(\"<绝对路径>.docx\", $false, $true)",
        "$d.SaveAs([ref]\"<绝对路径>.pdf\", [ref]17); $d.Close($false); $w.Quit()",
        "```",
        "",
    ]
    (dest / "提交清单.md").write_text("\n".join(lines), encoding="utf-8")

    iou.log(f"STEP 08 完成 ✓ 已归档至 {dest}（{human(total)}）")
    iou.log("共生成 7 个分类目录 + 提交清单.md")
    if FAILED:
        iou.log("[提示] 以下文件被占用未更新，请关闭对应程序后重新运行：")
        for p in FAILED:
            iou.log(f"       - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
