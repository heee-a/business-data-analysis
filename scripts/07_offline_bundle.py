# -*- coding: utf-8 -*-
"""
STEP 07 —— 离线自包含大屏打包

把 outputs/dashboard/dashboard_dark.html 中所有 CDN 外链脚本替换为本地内联库，
生成 outputs/dashboard/dashboard_offline.html：单文件、双击即开、无需联网。

内联策略：
  * echarts  —— 多个组件各引用一次 CDN，仅首次内联，后续直接删除（全局已可用）
  * plotly   —— 用于「全球销售分布 choropleth」，内联完整库
  * 其余外链 —— 删除并给出告警

依赖的库文件会自动从本机 Python 包中提取（plotly）或 assets/ 目录读取（echarts）。

用法：  python scripts/07_offline_bundle.py
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

SRC = cfg.DASH_DIR / "dashboard_dark.html"
DST = cfg.DASH_DIR / "dashboard_offline.html"
ASSET = cfg.ROOT / "assets"


def ensure_plotly_lib() -> Path | None:
    """从本机 plotly 包中提取与 Python 端版本严格匹配的 plotly.min.js。"""
    dst = ASSET / "plotly.min.js"
    if dst.exists() and dst.stat().st_size > 1_000_000:
        return dst
    try:
        import plotly
        src = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
        if src.exists():
            shutil.copy(src, dst)
            iou.log(f"已从 plotly {plotly.__version__} 包中提取 JS 库 → {dst}")
            return dst
    except Exception as exc:  # pragma: no cover
        iou.log(f"[WARN] 提取 plotly 库失败：{exc}")
    return None


def main() -> int:
    if not SRC.exists():
        iou.log(f"[ERROR] 未找到 {SRC}，请先运行 scripts/05_dashboard.py")
        return 1
    echarts_js = (ASSET / "echarts.min.js").read_text(encoding="utf-8")
    plotly_lib = ensure_plotly_lib()
    plotly_js = plotly_lib.read_text(encoding="utf-8") if plotly_lib else ""

    html = SRC.read_text(encoding="utf-8")
    links = re.findall(r'<script[^>]*\bsrc=["\'](https?://[^"\']+)["\'][^>]*>\s*</script>', html)
    iou.log(f"检测到 {len(links)} 个外链脚本")

    # ---- echarts：仅首次内联，后续删除
    state = {"echarts": 0}

    def _echarts(m: re.Match) -> str:
        state["echarts"] += 1
        if state["echarts"] == 1:
            return "<script>\n" + echarts_js + "\n</script>"
        return ""

    html = re.sub(
        r'<script[^>]*\bsrc=["\']https?://[^"\']*echarts[^"\']*["\'][^>]*>\s*</script>',
        _echarts, html)
    iou.log(f"echarts：内联 1 次，去重删除 {max(state['echarts'] - 1, 0)} 次")

    # ---- plotly：内联一次
    if plotly_js:
        n_p = len(re.findall(
            r'<script[^>]*\bsrc=["\']https?://[^"\']*plot\.?ly[^"\']*["\'][^>]*>\s*</script>',
            html, flags=re.I))
        html = re.sub(
            r'<script[^>]*\bsrc=["\']https?://[^"\']*plot\.?ly[^"\']*["\'][^>]*>\s*</script>',
            lambda m: "<script>\n" + plotly_js + "\n</script>", html, count=1)
        iou.log(f"plotly：内联 {min(n_p, 1)} 次（{plotly_lib.stat().st_size / 1048576:.2f} MB）")
    else:
        iou.log("[WARN] 未获取到 plotly 库，choropleth 地图在离线版中将不可用")

    # ---- 其余残留外链：删除
    left = re.findall(r'<script[^>]*\bsrc=["\'](https?://[^"\']+)["\'][^>]*>\s*</script>', html)
    if left:
        for u in left:
            iou.log(f"[WARN] 已移除无法内联的外链：{u}")
        html = re.sub(
            r'<script[^>]*\bsrc=["\']https?://[^"\']+["\'][^>]*>\s*</script>', "", html)

    html = html.replace(
        "<title>", "<!-- 离线自包含版：echarts / plotly 已内联，无需联网即可查看 -->\n<title>", 1)

    DST.write_text(html, encoding="utf-8")
    iou.log(f"STEP 07 完成 ✓ 离线大屏 → {DST} ({DST.stat().st_size / 1048576:.2f} MB，单文件自包含)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
