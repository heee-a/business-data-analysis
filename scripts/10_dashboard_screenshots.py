# -*- coding: utf-8 -*-
"""
STEP 10 —— 大屏演示截图与演示动图生成（创新加分材料）

评分标准 2.6 节将「大屏演示截图或录屏」列为可选创新加分材料。本阶段用本机
Chrome / Edge 无头浏览器对离线自包含大屏（dashboard_offline.html）逐标签页
截图，并合成四标签拼图与轮播 GIF，全部产物写入：

    outputs/dashboard_screenshots/
        大屏_销售总览.png         Tab 1  1920x1080
        大屏_客户价值.png         Tab 2  1920x1080
        大屏_商品洞察.png         Tab 3  1920x1080
        大屏_预测与复盘.png       Tab 4  1920x1080
        大屏演示_四标签拼图.png   2x2 拼合（1920x1080）
        大屏演示_轮播.gif        四标签轮播动画（960x540）

实现要点：
  * 截图方式为「临时变体 + 脚本注入」：把一段激活指定 Tab 的 JS 注入到
    HTML 最后一个 </body> 之前（离线包内联 JS 源码中含有大量 </body>
    字面量，只能替换最后一处，否则会破坏脚本解析），再用无头浏览器
    --screenshot 截取视口；
  * 浏览器按 Chrome → Edge 顺序自动探测，均缺失时本阶段跳过（可选阶段）；
  * 轮播 GIF 与拼图由 Pillow 合成，无需 ffmpeg。

用法：  python scripts/10_dashboard_screenshots.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from utils import config as cfg  # noqa: E402
from utils import io_utils as iou  # noqa: E402

SRC = cfg.DASH_DIR / "dashboard_offline.html"
DST_DIR = cfg.ROOT / "outputs" / "dashboard_screenshots"

# 标签页 ID → 展示名（与 05_dashboard.py 中的 Tab 定义一致）
TABS: list[tuple[str, str]] = [
    ("tab1", "销售总览"),
    ("tab2", "客户价值"),
    ("tab3", "商品洞察"),
    ("tab4", "预测与复盘"),
]

# 组件较多的标签页需要更高的截图视口，否则首屏放不下全部组件
# （Tab2 共 7 个组件：RFM 玫瑰/分群柱形/留存曲线/漏斗/K-Means 画像/
#  流失预警十分位/预警名单，1080 高只能展示前 4 个）
TAB_VIEW_H: dict[str, int] = {"tab2": 2520}

VIEW_W, VIEW_H = 1920, 1080
GIF_W, GIF_H = 960, 540


def find_browser() -> Path | None:
    """按优先级探测本机可用的无头浏览器（Chrome → Edge）。"""
    candidates = [
        Path(r"C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path(r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path(r"C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    ]
    for exe in candidates:
        if exe.exists():
            return exe
    found = shutil.which("chrome") or shutil.which("msedge") or shutil.which("chromium")
    return Path(found) if found else None


def make_variant(html: str, tab_id: str) -> str:
    """注入「同步激活指定 Tab 并回到顶部」的脚本，返回变体 HTML 文本。

    只能在最后一个 </body> 前注入：离线包内联的 echarts/plotly 源码中
    含有大量 </body> 字符串字面量，全局替换会破坏 JS 解析。
    激活逻辑同步执行（不依赖定时器）：headless 截图发生在 load 事件之后，
    定时器可能尚未触发；ECharts 初始化与 resize 均为同步渲染，
    DOMContentLoaded 时点击 Tab 即可让目标面板完成绘制。
    """
    idx = html.rfind("</body>")
    if idx < 0:
        raise ValueError("HTML 中未找到 </body>，无法注入截图脚本")
    js = (
        "<script>(function(){function activate(){"
        "var b=document.querySelector('.tab[data-tab=\"" + tab_id + "\"]');"
        "if(b){b.click();} window.scrollTo(0,0);}"
        "if(document.readyState!=='loading'){activate();}"
        "else{document.addEventListener('DOMContentLoaded',activate);}})();</script>"
    )
    return html[:idx] + js + html[idx:]


def shoot(browser: Path, variant_html: str, out_png: Path,
          view_h: int = VIEW_H) -> bool:
    """无头浏览器截取视口（1920×view_h）。

    注意：不使用 --virtual-time-budget。大屏内联动画由 rAF/setInterval
    驱动，虚拟时间预算会使其陷入饥饿导致 Chrome 永不退出；去掉后约 4s
    即可完成截图。另使用隔离的 --user-data-dir，规避默认配置文件的
    锁竞争与后台 Web 应用安装逻辑。

    view_h 高于 VIEW_H 用于组件较多的标签页（如 Tab2 共 7 个组件，
    1080 高的首屏只能展示前 4 个）：加高视口即可一次性完整截取，
    拼合时再由 Pillow 统一缩放，不影响其他标签页。
    """
    with tempfile.TemporaryDirectory(prefix="dash_shot_") as td:
        tmp_html = Path(td) / "variant.html"
        tmp_html.write_text(variant_html, encoding="utf-8")
        profile = Path(td) / "profile"
        file_url = tmp_html.as_uri()
        cmd = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={VIEW_W},{view_h}",
            f"--user-data-dir={profile}",
            f"--screenshot={out_png}",
            file_url,
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=240,
        )
    return proc.returncode == 0 and out_png.exists() and out_png.stat().st_size > 20_000


def build_composites(shots: list[Path]) -> None:
    """用 Pillow 合成四标签拼图与轮播 GIF。"""
    try:
        from PIL import Image
    except ImportError:
        iou.log("[WARN] 未安装 Pillow，跳过拼图与 GIF 合成")
        return

    ims = []
    for p in shots:
        im = Image.open(p).convert("RGB")
        # 超高截图（如 Tab2 的 2520 高完整版）在拼图/GIF 中取首屏裁剪，
        # 避免强制缩放导致内容压扁；完整内容保留在单张截图文件里
        if im.height > VIEW_H:
            im = im.crop((0, 0, im.width, VIEW_H))
        ims.append(im)

    sheet = Image.new("RGB", (GIF_W * 2, GIF_H * 2), (10, 15, 26))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((GIF_W, GIF_H), Image.LANCZOS),
                    ((i % 2) * GIF_W, (i // 2) * GIF_H))
    sheet.save(DST_DIR / "大屏演示_四标签拼图.png")

    frames = [im.resize((GIF_W, GIF_H), Image.LANCZOS) for im in ims]
    frames[0].save(DST_DIR / "大屏演示_轮播.gif", save_all=True,
                   append_images=frames[1:], duration=1400, loop=0, optimize=True)
    iou.log("已合成四标签拼图与轮播 GIF")


def main() -> int:
    if not SRC.exists():
        iou.log(f"[WARN] 未找到 {SRC}，请先运行 STEP 07（离线打包），本阶段跳过")
        return 0
    browser = find_browser()
    if browser is None:
        iou.log("[WARN] 未探测到 Chrome / Edge 无头浏览器，大屏截图阶段跳过")
        return 0

    DST_DIR.mkdir(parents=True, exist_ok=True)
    html = SRC.read_text(encoding="utf-8")
    iou.log(f"使用浏览器 {browser.name} 对 {SRC.name} 逐标签页截图")

    shots: list[Path] = []
    for tab_id, tab_name in TABS:
        out_png = DST_DIR / f"大屏_{tab_name}.png"
        ok = shoot(browser, make_variant(html, tab_id), out_png,
                   view_h=TAB_VIEW_H.get(tab_id, VIEW_H))
        iou.log(f"  Tab {tab_id}（{tab_name}）→ {out_png.name}"
                + ("  ✓" if ok else "  ✗ 失败"))
        if ok:
            shots.append(out_png)

    if len(shots) == len(TABS):
        build_composites(shots)
    iou.log(f"STEP 10 完成 ✓  产物目录：{DST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
