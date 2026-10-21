# -*- coding: utf-8 -*-
"""
复现验证工具 —— 将本仓库产物与另一目录（如干净目录重跑结果）做字节级比对。

背景：`docs/复现验证报告.md` 记录的可复现性主张需要工具来自动核对，
而非仅凭随机种子字段自证。本脚本即该报告 §2「逐文件比对」步骤的实现。

用法：
    # 1) 导出干净目录（等同全新克隆，排除本地未提交文件干扰）
    git archive HEAD | tar -x -C <干净目录>

    # 2) 在干净目录完整重跑
    cd <干净目录> && python run_all.py

    # 3) 回到主仓库执行比对
    python scripts/verify_reproduction.py <干净目录>

比对口径：
    * 图片 / CSV / 组件 HTML / docx / xlsx：原始字节 MD5；
    * JSON：先剔除 started_at / finished_at 等运行时间戳字段再比对
      （时间戳属运行元数据，非分析内容）；
    * 任一文件缺失或 MD5 不同即计入差异，最终输出分类汇总。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # 仓库根目录

# (相对目录, glob 模式, 标签)
COMPARE_TARGETS: list[tuple[str, str, str]] = [
    ("outputs/figures", "*.png", "静态图表"),
    ("outputs/tables", "*.csv", "结果表 CSV"),
    ("outputs/tables", "*.json", "结果表 JSON"),
    ("outputs/html", "*.html", "大屏组件 HTML"),
]

# 单文件比对目标（相对仓库根目录）
COMPARE_FILES: list[tuple[str, str]] = [
    ("docs/《商业数据分析》期末大论文.docx", "期末大论文 docx"),
    ("outputs/tables/00_关键结果汇总.xlsx", "关键结果汇总 xlsx"),
    ("outputs/report_stats.json", "论文元数据 stats.json"),
]

# JSON 中需要剔除的运行元数据字段名后缀 / 集合
_META_KEYS = {"started", "finished"}


def _md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _content_md5(p: Path) -> str:
    """JSON 剔除时间戳字段后哈希；其余格式原样字节哈希。"""
    if p.suffix != ".json":
        return _md5(p)
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:                                     # noqa: BLE001
        return _md5(p)

    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items()
                    if not (k.endswith("_at") or k in _META_KEYS)}
        if isinstance(obj, list):
            return [strip(v) for v in obj]
        return obj

    return hashlib.md5(
        json.dumps(strip(data), ensure_ascii=False, sort_keys=True)
        .encode("utf-8")).hexdigest()


def compare_dir(main: Path, other: Path, pattern: str) -> tuple[int, int, list[str]]:
    fa = {p.name: p for p in main.glob(pattern)}
    fb = {p.name: p for p in other.glob(pattern)}
    same, diff = 0, []
    for n in sorted(set(fa) | set(fb)):
        pa, pb = fa.get(n), fb.get(n)
        if pa is None:
            diff.append(f"{n}（比对目录缺失）")
        elif pb is None:
            diff.append(f"{n}（主目录缺失）")
        elif _content_md5(pa) == _content_md5(pb):
            same += 1
        else:
            diff.append(n)
    return len(set(fa) | set(fb)), same, diff


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    other_root = Path(sys.argv[1]).expanduser().resolve()
    if not other_root.is_dir():
        print(f"[ERROR] 比对目录不存在：{other_root}")
        return 2

    total_n = total_same = 0
    print("=" * 66)
    print(f"复现验证：{HERE}  ↔  {other_root}")
    print("=" * 66)

    for rel, pattern, label in COMPARE_TARGETS:
        n, same, diff = compare_dir(HERE / rel, other_root / rel, pattern)
        total_n += n
        total_same += same
        mark = "✔" if not diff else "✘"
        print(f"  {mark}  {label:<14} {same}/{n} 一致"
              + (f"  差异：{diff[:5]}" if diff else ""))

    for rel, label in COMPARE_FILES:
        pa, pb = HERE / rel, other_root / rel
        total_n += 1
        ok = pa.exists() and pb.exists() and _content_md5(pa) == _content_md5(pb)
        total_same += 1 if ok else 0
        print(f"  {'✔' if ok else '✘'}  {label:<14} {'一致' if ok else '不一致'}")

    print("=" * 66)
    ok_all = total_n == total_same
    print(f"  合计 {total_same}/{total_n} 项字节级一致"
          f" → {'复现成立 ✔' if ok_all else '存在差异 ✘'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
