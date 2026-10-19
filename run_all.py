# -*- coding: utf-8 -*-
"""
run_all.py —— 一键复现入口
===========================
按顺序执行完整流水线，克隆仓库后只需一条命令即可复现全部图表、结果表、
交互式大屏与期末大论文：

    python run_all.py

流水线共 6 个阶段：
    STEP 01  数据获取      scripts/01_load.py       官方 ZIP 下载 + 按发票抽样
    STEP 02  数据清洗      scripts/02_clean.py      去重/缺失/异常治理 + 星型模型
    STEP 03  分析模型      scripts/03_analysis.py   8 类商业模型 + 9 组业务图数据
    STEP 04  静态图表      scripts/04_visuals.py    35 张 200dpi 图表
    STEP 05  交互大屏      scripts/05_dashboard.py  4 标签页 20 组件暗色大屏
    STEP 06  论文生成      scripts/06_report.py     期末大论文 Word 文档

可选参数：
    python run_all.py --skip 1 2      跳过 STEP 01、02（数据已存在时加速）
    python run_all.py --only 4 5      仅执行 STEP 04、05
    python run_all.py --list          查看阶段清单

设计要点：
    * 每个阶段都是幂等的 —— 重复执行不会产生重复文件或覆盖损坏；
    * 任一阶段失败立即中断并打印阶段编号，便于定位；
    * 随机种子在 scripts/utils/config.py 中固定为 2026，结果完全可复现。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

# (步骤编号, 脚本相对路径, 中文说明)
STEPS: list[tuple[int, str, str]] = [
    (1, "scripts/01_load.py", "数据获取（官方下载 + 按发票抽样）"),
    (2, "scripts/02_clean.py", "数据清洗与治理（星型模型构建）"),
    (3, "scripts/03_analysis.py", "商业分析模型（8 类模型计算）"),
    (4, "scripts/04_visuals.py", "静态图表生成（35 张 200dpi）"),
    (5, "scripts/05_dashboard.py", "交互式大屏（20 组件）"),
    (6, "scripts/06_report.py", "期末大论文生成（Word）"),
]


def run_step(step: int, script: str, desc: str) -> bool:
    """执行单个阶段，返回是否成功。"""
    line = "=" * 74
    print(f"\n{line}\n▶ STEP {step:02d}  {desc}\n  script: {script}\n{line}",
          flush=True)
    t0 = time.time()
    proc = subprocess.run([PY, str(ROOT / script)], cwd=ROOT)
    cost = time.time() - t0
    if proc.returncode == 0:
        print(f"\n✔ STEP {step:02d} 完成，用时 {cost:.1f}s", flush=True)
        return True
    print(f"\n✘ STEP {step:02d} 失败（退出码 {proc.returncode}，用时 {cost:.1f}s）",
          flush=True)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="商业数据分析项目一键复现入口")
    ap.add_argument("--skip", nargs="*", type=int, default=[],
                    help="跳过的阶段编号，如 --skip 1 2")
    ap.add_argument("--only", nargs="*", type=int, default=[],
                    help="仅执行的阶段编号，如 --only 4 5")
    ap.add_argument("--list", action="store_true", help="列出全部阶段后退出")
    args = ap.parse_args()

    if args.list:
        for s, sc, d in STEPS:
            print(f"  STEP {s:02d}  {sc:28s}  {d}")
        return 0

    # --only 优先于 --skip
    if args.only:
        todo = [s for s in STEPS if s[0] in args.only]
    else:
        todo = [s for s in STEPS if s[0] not in args.skip]

    print("=" * 74)
    print("  商业数据分析 · 期末大作业 · 一键复现")
    print(f"  数据源：UCI Machine Learning Repository - Online Retail II (#502)")
    print(f"  随机种子：2026   待执行阶段：{', '.join(str(s[0]) for s in todo)}")
    print("=" * 74)

    t_all = time.time()
    for step, script, desc in todo:
        if not run_step(step, script, desc):
            return 1

    print("\n" + "=" * 74)
    print(f"  全部阶段执行成功，总用时 {time.time() - t_all:.1f}s")
    print("  产出位置：")
    print("    图表     outputs/figures/      （35 张 PNG，200dpi）")
    print("    结果表   outputs/tables/       （CSV / JSON）")
    print("    大屏     outputs/dashboard/dashboard_dark.html")
    print("    论文     docs/《商业数据分析》期末大论文.docx")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
