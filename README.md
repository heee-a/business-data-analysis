<div align="center">

# 基于 UCI Online Retail II 的零售商业数据分析

**合规取数 · 数据治理 · 9 类商业模型 · 35 张 Python 图表 · 20 组件交互大屏**

《商业数据分析》期末大作业 · 嘉兴大学 数据科学学院 · 2026 年秋季学期

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: CC BY 4.0](https://img.shields.io/badge/Data_License-CC_BY_4.0-green.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Reproducible](https://img.shields.io/badge/Reproducible-seed_2026-orange)](#-一键复现)
[![Dashboard](https://img.shields.io/badge/Dashboard-Pyecharts_20_components-red)](#-交互式大屏)

</div>

---

## 项目简介

本项目以 [UCI Machine Learning Repository **Online Retail II**](https://archive.ics.uci.edu/dataset/502/online+retail+ii)（数据集 #502，CC BY 4.0）跨国零售交易数据为对象，完成从 **真实数据获取 → 清洗治理 → 模型分析 → 图表复现与大屏呈现 → 商业洞察提炼** 的端到端商业数据分析流程。

- **零爬虫**：数据通过官方一次性 ZIP 下载文件获取（白名单方式），全程无任何网页抓取；
- **可复现**：随机种子固定为 `2026`，克隆后执行一条命令即可重现全部 35 张图表、70 张结果表与交互大屏；
- **全 Python**：所有图表与大屏均由 Python 生成，未使用 Power BI / Tableau / Fine BI 等任何 BI 软件；
- **模型驱动**：9 类商业分析模型，每个参数与阈值均给出业务依据，预测含 95% 置信区间与 30 天留出回测。

### 核心分析结论速览

| 维度 | 关键发现 |
| --- | --- |
| 市场结构 | 英国单一市场贡献 **84.96%** 销售额，集中度过高 |
| 商品结构 | **22.42%** 的 SKU 贡献 **80%** 营收（A 类 1,135 个）；51.22% 的 C 类 SKU 仅贡献 5% |
| 客户价值 | 「重要价值客户」以 28.69% 人数贡献 **69.99%** 营收，人均 £3,244 |
| 留存曲线 | 次月留存 **10.65%**（断崖），此后长期稳定在 **9%~12%** 平台期 |
| 季节性 | 圣诞季品类同比增速 **+40.61%**、派对品类 **+50.52%** |
| 关联规则 | 3,866 条规则，最强提升度 **16.11**（茶具系列强关联） |
| 销售预测 | Holt-Winters 优于 SARIMA，回测 MAPE **34.70%** / RMSE **£11,169** |

---

## 目录结构

```text
business-data-analysis/
├── data/
│   ├── raw/            # 原始数据层：抽样后明细(.gz)、溯源信息、抽样清单
│   ├── clean/          # 清洗后数据层：星型模型 5 表 + SQLite 库（含 .gz 归档）
│   └── schema/         # 数据字典、星型模型说明
├── scripts/
│   ├── 01_load.py      # 数据获取（官方下载 + 按发票整单抽样，种子 2026）
│   ├── 02_clean.py     # 清洗治理 + 星型模型 + CSV/JSON/SQLite 三格式导出
│   ├── 03_analysis.py  # 9 类商业分析模型计算
│   ├── 04_visuals.py   # 35 张静态图表（200dpi）
│   ├── 05_dashboard.py # Pyecharts 交互大屏（4 页 20 组件，暗色主题）
│   ├── 06_report.py    # 期末大论文 Word + 图表索引生成
│   ├── 07_offline_bundle.py # 离线自包含大屏（内联 echarts/plotly，免联网）
│   ├── 08_deliver.py   # 交付物按提交类别归档到作业目录
│   ├── 09_excel_summary.py # 关键结果 Excel 汇总（20 个 Sheet）
│   ├── 10_dashboard_screenshots.py # 大屏演示截图（无头浏览器实拍 + 拼图 + GIF）
│   └── utils/          # config / io_utils / style / chart_helpers
├── outputs/
│   ├── figures/        # fig01 ~ fig35（35 张 PNG）
│   ├── tables/         # 70 个结果表（CSV + JSON）+ 00_关键结果汇总.xlsx
│   ├── dashboard/      # dashboard_dark.html（CDN 版）+ dashboard_offline.html（离线版）
│   ├── dashboard_screenshots/ # 大屏分 Tab 截图 + 拼图 + 轮播 GIF
│   └── html/           # 20 个独立组件 HTML
├── docs/               # 期末大论文、图表索引、数据来源合规声明
├── pages/              # GitHub Pages 入口（大屏离线版 + 图表图廊）
├── requirements.txt
├── run_all.py          # 一键复现入口
└── README.md
```

---

## 数据来源与合规声明

| 项目 | 内容 |
| --- | --- |
| 数据源 | **Online Retail II**，UCI ML Repository 数据集编号 #502 |
| 官方页面 | <https://archive.ics.uci.edu/dataset/502/online+retail+ii> |
| 获取方式 | **官方一次性下载文件（ZIP）** —— 课程附件 A 白名单方式，**非爬虫** |
| 获取日期 | 2026-10-19 |
| 原始规模 | 1,067,371 行明细 / 53,628 张发票 / 45.62 MB / 2009-12-01 ~ 2011-12-09 |
| 授权协议 | **CC BY 4.0**（署名即可自由使用、转换与再分发） |
| 抽样方法 | **按发票整单随机抽样 30%**，随机种子 **2026**，抽中 16,088 张发票 / 315,722 行 |

> **合规声明**：本项目数据获取全程未使用任何爬虫技术（无 Scrapy / Selenium /
> requests+网页解析 / 模拟登录），仅通过 `urllib.request` 对官方静态 URL 发起
> 1 次 GET 请求下载二进制文件。SHA256 校验值、抽样清单与溯源信息见
> [`data/raw/provenance.json`](data/raw/provenance.json) 与
> [`docs/数据来源合规声明.md`](docs/数据来源合规声明.md)。
> 完整数据字典见 [`data/schema/data_dictionary.csv`](data/schema/data_dictionary.csv)。

**为什么按发票而非按行抽样？** Apriori 购物篮分析依赖同一订单内商品的共现关系；
按行抽样会把同一发票的明细随机拆散，撕裂购物篮、系统性低估共现频次。
以「订单」为抽样单元可保证被选中的每张发票保留全部明细行。

> **仓库体积策略**：仓库只追踪 `.gz` 归档版（明细表 54MB→6.7MB、SQLite 63MB→11MB、
> 原始抽样 31MB→4.7MB），未压缩大文件已列入 `.gitignore`。
> 执行流水线即可在本地重新生成全部未压缩文件；或直接 `gunzip -k data/**/*.gz`。

---

## 一键复现

```bash
# 1. 克隆仓库
git clone https://github.com/heee-a/business-data-analysis.git
cd business-data-analysis

# 2. 安装依赖（建议 Python 3.11+ 虚拟环境）
pip install -r requirements.txt

# 3. 一键复现全部结果
python run_all.py
```

`run_all.py` 依次执行 10 个阶段：

| STEP | 脚本 | 说明 | 耗时参考 |
| :--: | --- | --- | :-: |
| 01 | `01_load.py` | 官方 ZIP 下载 + 按发票抽样（已存在则跳过下载） | ~2 min |
| 02 | `02_clean.py` | 去重/缺失/异常治理 + 星型模型 + 多格式导出 | ~40 s |
| 03 | `03_analysis.py` | 9 类商业模型计算 | ~3 min |
| 04 | `04_visuals.py` | 35 张静态图表 | ~1 min |
| 05 | `05_dashboard.py` | 交互大屏 | ~30 s |
| 06 | `06_report.py` | 期末大论文 + 图表索引 | ~10 s |
| 07 | `07_offline_bundle.py` | 离线自包含大屏打包（可选，需 `assets/echarts.min.js`） | ~2 s |
| 08 | `08_deliver.py` | 交付物归档到作业目录（可选） | ~5 s |
| 09 | `09_excel_summary.py` | 关键结果 Excel 汇总（20 个 Sheet） | ~1 s |
| 10 | `10_dashboard_screenshots.py` | 大屏演示截图：分 Tab 实拍 + 拼图 + GIF（可选，需本机 Chrome/Edge） | ~20 s |

```bash
# 常用参数
python run_all.py --list          # 查看阶段清单
python run_all.py --only 4 5      # 仅重新生成图表与大屏
python run_all.py --skip 1 2      # 数据已就绪时跳过前两步
```

> 交互大屏也可直接用浏览器打开 `outputs/dashboard/dashboard_dark.html`（无需运行代码），
> 或访问在线版：<https://heee-a.github.io/business-data-analysis/>

---

## 商业分析模型（9 类）

每个模型的参数与阈值均有业务依据，详见论文第 4.2 节。

| # | 模型 | 关键参数与业务依据 | 核心图 |
| :-: | --- | --- | :-: |
| M1 | 环比/同比 + 移动平均 | MA7/30/90 多周期平滑；剔除不完整末月 | fig01/25 |
| M2 | RFM 八分类 | **中位数切分**（分布右偏，抗极值）：R=203 天，F=2 次，M=£488.69 | fig26/27 |
| M3 | 同期群留存 | **月度粒度**（周太碎、季太粗）；对角线=100% 验证 | fig28 |
| M4 | 帕累托/ABC | A:累计 80%，B:累计 95%；销售额口径 | fig29 |
| M5 | Apriori 关联规则 | support≥**0.01**（铺货价值）/ lift>**1.0**（正向）/ conf≥**0.15**（推荐命中） | fig30/31 |
| M6 | 波士顿矩阵 | 相对份额阈值 1.0；增速阈值取大盘同比 **7.62%** | fig32 |
| M7 | SARIMA / Holt-Winters | 周周期 7 天；**30 天留出回测**，输出点预测+**95% CI** | fig33 |
| M8 | K-Means 分群 | log1p + 标准化；K 由**轮廓系数**定（K=2，0.4271）；seed=2026 | fig34 |
| M9 | 复购漏斗 | 五级转化，定位「第 2 次购买」瓶颈 | fig35 |

### 稳健性检验（RFM 切分方式敏感性）

阈值选择不应只给理由，还应检验结论是否依赖它。对 RFM 同时用三种切分计算核心高价值客群
（`03_rfm_threshold_sensitivity.csv`）：

| 切分方式 | 阈值 R / F / M | 核心客群人数 | 人数占比 | 营收占比 |
| --- | --- | --- | :--: | :--: |
| **中位数（采用）** | 203 天 / 2.00 次 / £488.69 | 1,069 | 28.69% | **69.99%** |
| 均值 | 249 天 / 2.89 次 / £1,329.56 | 572 | 15.35% | 61.43% |
| 60 分位 | 126 天 / 2.00 次 / £671.73 | 784 | 21.04% | 62.84% |

三种方案下「不足三成客户贡献六成以上营收」的结构均成立，结论稳健；
同时可见均值切分因 Monetary 均值被拉高到中位数的 2.7 倍，
会少识别约 500 名可运营的高潜客户 —— 这反向印证了采用中位数的理由。

### 预测回测结果（测试集 30 天）

| 模型 | 阶数 | MAPE | RMSE | AIC | 选用 |
| --- | --- | :-: | :-: | :-: | :-: |
| **Holt-Winters** | 加法趋势(阻尼)+加法季节(7) | **34.70%** | £11,169 | — | ✔ |
| SARIMA | (1,1,1)(1,0,1,7) | 36.33% | £11,023 | 13,879.5 | |

---

## 可视化作品索引

### 模板复现类（25 种，fig01–fig25）

对照《Excel 数据可视化——从图表到数据大屏》模板，用 Matplotlib/Seaborn 复现。
瀑布图、子弹图、坡度图、矩形树图、玫瑰图、仪表盘、日历热力图等图型 **Matplotlib 无原生支持**，
已在 `scripts/utils/chart_helpers.py` 中自行实现（矩形树图采用 squarify 算法）。

| 类别 | 图型 | 编号 |
| --- | --- | --- |
| 比较类 | 柱形图 / 条形图 / 堆积柱形图 / 百分比堆积 | fig04, 05, 07, 08 |
| 构成类 | 环形图 / 矩形树图 / 玫瑰图 / 词云 | fig06, 23, 20, 24 |
| 趋势类 | 折线图 / 面积图 / 多重移动平均 | fig02, 03, 25 |
| 分布类 | 直方图 / 箱线图 / 小提琴图 / 散点图 / 气泡图 | fig11, 12, 22, 09, 10 |
| 关系类 | 雷达图 / 日历热力图 / 热力图 | fig14, 17, 13 |
| 进度类 | 仪表盘 / 子弹图 / 瀑布图 | fig16, 21, 15 |
| 变化类 | 双轴组合 / 三轴组合 / 坡度图 | fig19, 01, 18 |

### 业务模型类（10 张，fig26–fig35）

与 9 类模型一一对应：RFM 气泡矩阵、RFM 分群对比、同期群留存热力图、
帕累托 ABC、关联规则散点、共现网络、波士顿矩阵、预测置信带、K-Means 分群、复购漏斗。

### 交互式大屏（Pyecharts，4 页 20 组件）

| 标签页 | 组件 | 交互能力 |
| --- | --- | --- |
| ① 销售总览 | 趋势 / 双轴 / 国家柱形 / 月度排名时间轴 / 星期时段热力 | 时间轴轮播、缩放 |
| ② 客户洞察 | RFM 玫瑰 / 分群柱形 / 留存曲线 / 复购漏斗 / 分群画像 | 图例筛选 |
| ③ 商品结构 | TOP10 / 品类环形 / 词云 / ABC / 关联规则榜 / 明细表 | 词云、表格排序 |
| ④ 预测复盘 | 置信带 / 回测对比 / 同比复盘 / 波士顿矩阵 | 区间下钻 |

> 全部图表 200dpi、统一命名 `figNN_<主题>.png`、统一 12 色商业配色板；
> 完整索引见 [`docs/图表索引.md`](docs/图表索引.md)。

**大屏演示材料**（评分标准 2.6 节的可选创新加分项）：`scripts/10_dashboard_screenshots.py`
调用本机无头浏览器对离线大屏逐标签页实拍 1920×1080 截图，并合成四标签拼图与轮播 GIF，
存放于 `outputs/dashboard_screenshots/`：

| 文件 | 内容 |
| --- | --- |
| `大屏_销售总览.png` | Tab ① KPI 卡 + 销售趋势 + 月度排名时间轴 |
| `大屏_客户价值.png` | Tab ② RFM 玫瑰图 + 分群对比 + 留存曲线 + 复购漏斗 |
| `大屏_商品洞察.png` | Tab ③ TOP10 + 品类环形 + 词云 + ABC + 关联规则榜 |
| `大屏_预测与复盘.png` | Tab ④ 预测置信带 + 回测对比 + 波士顿矩阵 |
| `大屏演示_四标签拼图.png` | 四标签 2×2 拼合（论文图 5-7） |
| `大屏演示_轮播.gif` | 四标签轮播动画 |

---

## 提交物清单

| 提交物 | 位置 |
| --- | --- |
| 期末大论文（Word，约 1.34 万字，34 页，16 张嵌入图） | `docs/《商业数据分析》期末大论文.docx` |
| 期末大论文（PDF 版） | `docs/《商业数据分析》期末大论文.pdf` |
| 数据来源合规声明 | `docs/数据来源合规声明.md` |
| 图表索引（35 图 + 20 组件） | `docs/图表索引.md` |
| 可复现性验证报告（独立目录复跑 + MD5 比对） | `docs/复现验证报告.md` |
| 数据字典与星型模型说明 | `data/schema/` |
| 关键结果 Excel 汇总（20 个 Sheet） | `outputs/tables/00_关键结果汇总.xlsx` |
| 交互大屏（在线，JS 已内联、打开即用） | [GitHub Pages](https://heee-a.github.io/business-data-analysis/) |
| 交互大屏（离线单文件） | `outputs/dashboard/dashboard_offline.html` |
| 大屏演示截图 + 拼图 + 轮播 GIF（创新加分材料） | `outputs/dashboard_screenshots/` |

## 作者

秦子睿 · 数据科学与大数据技术 大数据241班 · 学号 2024459985127 · 数据科学学院

## 评分标准对照

对照《要求及评分标准》逐项自查的落实情况：

| 评分维度 | 分值 | 落实情况 | 证据位置 |
| --- | :-: | --- | --- |
| 1. 数据获取合规性与清洗质量 | 15 | 白名单官方 ZIP 下载、**零爬虫**；合规声明含数据源/URL/获取方式/日期/License；抽样方法与种子已说明；缺失/异常/重复三类治理 + 主外键对齐；CSV/JSON/SQLite 三格式导出 | `data/raw/provenance.json`、`docs/数据来源合规声明.md`、论文 §2–§3 |
| 2. 商业分析模型应用深度 | 20 | **9 类**模型（要求 ≥3）：环比同比 + 移动平均、RFM 八分类、同期群留存、帕累托 ABC、Apriori、波士顿矩阵、SARIMA + Holt-Winters、K-Means、复购漏斗；每个阈值均给业务依据；预测含 95% 置信区间 + 30 天留出回测（MAPE 34.70%）；**另做 RFM 阈值稳健性检验**（中位数/均值/60 分位三方案结论一致） | `scripts/03_analysis.py`、`outputs/tables/03_*`、论文 §4 |
| 3. 可视化复现与大屏质量 | 25 | **35 张**图（模板复现 25 + 业务模型 10）；Matplotlib 无原生支持的图型（瀑布/子弹/坡度/矩形树图）已自行实现；大屏 **4 页 20 组件**，带筛选联动、缩放、下钻、暗色主题；全 Python 生成，无 BI 软件、无 Excel 截图 | `outputs/figures/`、`outputs/dashboard/dashboard_offline.html`、`docs/图表索引.md` |
| 4. 代码规范性与文档完整性 | 10 | 10 阶段流水线 + `run_all.py` 一键复现（支持 `--skip` / `--only`）；`requirements.txt` 固定版本；README 含来源/步骤/索引/分工；图表统一命名 `figNN_主题.png` 并有索引表；**已实测独立目录复跑后 35 图 + 70 表 MD5 全部一致**，并修复词云随机布局与 Apriori 排序两处非确定性 | `run_all.py`、`requirements.txt`、`docs/图表索引.md`、`docs/复现验证报告.md` |
| 5. 期末大论文质量 | 25 | 题目 18 字；摘要 265 字符（200–300 区间内）；关键词 5 个；正文 1.34 万字含 16 张嵌入图与逐图解读、Python 与 Excel 实现对比（§5.2.1 专节 + 对照表）；6 条带数据支撑的商业建议 | `docs/《商业数据分析》期末大论文.docx` / `.pdf` |
| 6. 创新性与商业洞察深度 | 5 | 自研图表算法（squarify 矩形树图、子弹图）；自动化复现流水线（含离线大屏打包、交付归档、大屏演示截图三个自建步骤）；大屏演示截图 + 轮播 GIF（无头浏览器自动实拍）；AI 使用规范披露（论文第 8 章） | `scripts/utils/chart_helpers.py`、`outputs/dashboard_screenshots/`、论文 §8 |

> 优秀级自检项均已覆盖：预测含置信区间与误差回测 ✓；大屏组件 ≥6 且有筛选联动/下钻 ✓；
> 图表 10 行 3 列缩排附录（论文附录 D）✓；≥3 条可落地商业建议（6 条）✓；
> 大屏演示截图/录屏（可选创新材料）✓；仓库公开且非空 ✓。

## 分工说明

独立完成，全流程（数据获取、清洗治理、模型建模、可视化、大屏搭建、论文撰写）均由本人承担。

## AI 使用披露

开发过程中使用了 AI 编程助手辅助代码框架编写、图型算法实现与文字润色；
数据获取、清洗规则设计、模型选型、参数设定、结果解读与商业结论均由本人独立完成并承担责任。
详细披露见表 8-1（论文第 8 章）。

---

## License

- 代码：仅供课程作业与教学参考；
- 数据：[Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) 遵循
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，引用格式：

```bibtex
@dataset{chen_d_2012_online_retail_ii,
  author    = {Chen, D.},
  title     = {Online Retail II},
  year      = {2012},
  publisher = {UCI Machine Learning Repository},
  doi       = {10.24432/C60H6D}
}
```

<div align="center">
<sub>用 Python 把 30 万行交易明细，变成 8 个模型、35 张图与 5 条可落地的商业建议。</sub>
</div>
