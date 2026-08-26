import json

tasks = []

# ---------------- Task 1 — Data Research (Factorio wiki) ----------------
t1_cn = """【任务开始】请记录当前时间作为 T1。
你需要帮我完成一份《Factorio 早期电力方案技术调研报告》。
1. 请直接访问以下 4 个 wiki.factorio.com 页面，抓取核心工业参数（优先从页面右侧信息框/infobox提取，其次从正文表格）：
- https://wiki.factorio.com/Boiler
- https://wiki.factorio.com/Steam_engine
- https://wiki.factorio.com/Solar_panel
- https://wiki.factorio.com/Accumulator
提取要求：
- Boiler: 建造成本（材料及数量）、燃料类型、污染排放、尺寸（格数）
- Steam engine: 建造成本、发电量(kW)、尺寸（格数）
- Solar panel: 建造成本、发电量(kW)、尺寸（格数）
- Accumulator: 建造成本、蓄电量(MJ)、最大输出(kW)、尺寸（格数）
2. 基于上述原始数据，计算并对比以下两种"基础发电单元"：
- 蒸汽单元：1×Boiler + 2×Steam engine（Factorio标准配比）
- 太阳能单元：5×Solar panel + 1×Accumulator（常见基础配比）
对比维度：
- 总建造成本（列出各设备所需材料，不要求合并同类项，但需完整）
- 稳定发电量（kW，注意太阳能夜间不发电，需配合Accumulator）
- 总占地面积（格数，Boiler和Steam engine的尺寸相加）
- 是否需要持续燃料输入（是/否）
- 是否有污染排放（是/否）
3. 生成一份 Markdown 格式的对比报告，保存到 `~\\Documents\\Agent_Test\\factorio_power_comparison.md`，要求：
- 先列出原始数据表（4 个设备各自的参数）
- 再输出一套"基础发电单元"对比总表（包含上述 5 个维度 × 2 种方案）
- 针对"游戏前期（红绿瓶/电力研发阶段）适用性"和"基地长期扩展性"两个维度，分别写出 200 字以内的分析结论
- 给出你的综合推荐方案（明确推荐哪一种，并说明理由）
4. 如果某个 wiki 页面无法访问或数据缺失，请基于你的知识库补充该设备数据，并在报告对应位置标注"[知识库补充]"，不要反复重试导致超时。
【任务结束】请记录当前时间作为 T2，并在回复最后单独输出一行："总耗时：T2 - T1 = X 分钟"。
交付物检查清单：
- [ ] 文件已成功保存到指定路径
- [ ] 包含原始数据表（4 个设备）
- [ ] 对比总表包含 2 种方案且 5 个维度无遗漏
- [ ] 有两段专项分析结论（前期适用性、长期扩展性）
- [ ] 有明确的最终推荐方案及理由
- [ ] 报告开头注明了数据来源（wiki直接抓取/知识库补充）"""

t1_en = """[TASK START] Please record the current time as T1.
I need you to complete a technical research report titled "Factorio Early-Game Power Solution Study".
1. Directly visit the following 4 wiki.factorio.com pages and scrape the core industrial parameters (prioritize the right-side infobox, then the body tables):
 - https://wiki.factorio.com/Boiler
 - https://wiki.factorio.com/Steam_engine
 - https://wiki.factorio.com/Solar_panel
 - https://wiki.factorio.com/Accumulator
 Extraction requirements:
 - Boiler: build cost (materials & quantities), fuel type, pollution emission, size (tiles)
 - Steam engine: build cost, power output (kW), size (tiles)
 - Solar panel: build cost, power output (kW), size (tiles)
 - Accumulator: build cost, energy capacity (MJ), max output (kW), size (tiles)
2. Based on the raw data above, compute and compare the following two "basic power units":
 - Steam unit: 1xBoiler + 2xSteam engine (Factorio standard ratio)
 - Solar unit: 5xSolar panel + 1xAccumulator (common basic ratio)
 Comparison dimensions:
 - Total build cost (list the materials for each device; no need to merge like items, but must be complete)
 - Stable power output (kW; note solar produces no power at night and needs an Accumulator)
 - Total footprint (tiles; sum of Boiler and Steam engine sizes)
 - Whether continuous fuel input is required (yes/no)
 - Whether there is pollution emission (yes/no)
3. Generate a Markdown comparison report and save it to `~\\Documents\\Agent_Test\\factorio_power_comparison.md`, with:
 - First, the raw data tables (parameters for each of the 4 devices)
 - Then a "basic power unit" comparison table (the 5 dimensions above x 2 solutions)
 - For "early-game suitability (red/green science / power research phase)" and "long-term base scalability", write an analysis of <=200 words each
 - Your overall recommendation (state clearly which one, and why)
4. If a wiki page is inaccessible or data is missing, supplement it from your knowledge base and mark "[knowledge base fill-in]" at that spot; do not retry repeatedly and cause timeouts.
[TASK END] Please record the current time as T2, and output one separate final line: "Total time: T2 - T1 = X minutes".
Deliverable checklist:
- [ ] File saved to the specified path
- [ ] Includes raw data tables (4 devices)
- [ ] Comparison table has 2 solutions with all 5 dimensions
- [ ] Two analysis conclusions (early-game suitability, long-term scalability)
- [ ] A clear final recommendation with reasons
- [ ] Report header notes the data source (direct wiki scrape / knowledge base fill-in)"""

tasks.append({
    "id": "cppm01",
    "title": "Data Research — Factorio early-game power (web scraping + numeric compare + report)",
    "category": "web_research",
    "source": "CPPM AI Agent Study v1.01, Task1-Prompt (p.41 CN / p.44 EN)",
    "expects_network": True,
    "prompt": t1_cn,
    "prompt_en": t1_en,
    "expected_files": ["~/Documents/Agent_Test/factorio_power_comparison.md"],
    "checkpoints": {
        "raw_data_ground_truth": {
            "boiler_size_tiles": 6, "boiler_size_dims": "2x3",
            "steam_engine_size_tiles": 15, "steam_engine_size_dims": "3x5",
            "solar_panel_size_tiles": 9, "solar_panel_size_dims": "3x3",
            "accumulator_size_tiles": 4, "accumulator_size_dims": "2x2",
            "steam_engine_power_kw": 900, "solar_panel_power_kw": 60,
            "accumulator_capacity_mj": 5.0
        },
        "computed_ground_truth": {
            "steam_unit_footprint_tiles": 36,
            "solar_unit_footprint_tiles": 49,
            "steam_unit_power_kw": 1800,
            "solar_unit_day_power_kw": 300,
            "solar_unit_avg_power_kw_approx": 210
        },
        "rubric": [
            "Scraped device sizes match wiki ground truth (boiler 6, steam engine 15, solar 9, accumulator 4 tiles)",
            "Powers correct (steam engine 900kW, solar 60kW, accumulator 5.0MJ)",
            "Steam unit footprint = 36 tiles; solar unit footprint = 49 tiles; steam unit power = 1800kW",
            "Report has raw-data tables (4 devices) + comparison table (5 dims x 2 setups)",
            "Two <=200-word analyses (early-game suitability, long-term scalability)",
            "Clear final recommendation with reasoning; data source noted (scrape vs KB fill-in)",
            "File saved to the specified path"
        ]
    }
})

# ---------------- Task 2 — Sales Data Analysis ----------------
t2_cn = """【任务开始】请记录当前时间作为 T1。
我有一份销售数据需要处理。请按以下步骤执行：
1. 创建一个模拟的 CSV 文件 `~\\Documents\\Agent_Test\\sales_data.csv`，包含 2025 年 1 月至 12 月的销售记录。要求：
- 字段：月份(month)、销售额(revenue，单位万元，范围 50-200)、成本(cost，单位万元，范围 30-120)、渠道(channel，枚举：线上/线下/分销)。
- 数据量：每月 3 条记录（共 36 行），其中故意插入 3 处缺失值（随机分布在 revenue 或 cost 列）和 2 处异常值（revenue < cost）。
2. 编写一个 Python 脚本 `~\\Documents\\Agent_Test\\sales_analysis.py`，要求该脚本实现：
- 读取上述 CSV
- 数据清洗：用当月同渠道均值填充缺失值；标记并剔除 revenue < cost 的异常行
- 计算：每月汇总销售额、毛利率((revenue-cost)/revenue)；按渠道统计全年占比
- 输出两张图表并保存到 `~\\Documents\\Agent_Test\\`：
* 月度销售额+毛利率双轴折线图（monthly_trend.png）
* 渠道占比饼图（channel_pie.png）
- 在脚本最后打印清洗前后的数据行数对比，以及全年总毛利率
3. 执行该 Python 脚本，确保两张图片成功生成且没有报错。
4. 向我汇报：脚本执行日志摘要、清洗掉的异常行详情、全年总毛利率数值。
【任务结束】请记录当前时间作为 T2，并在回复最后单独输出一行："总耗时：T2 - T1 = X 分钟"。
交付物检查清单：
- [ ] CSV 文件存在且格式正确（36 行 + 3 缺失 + 2 异常）
- [ ] Python 脚本存在且可运行
- [ ] 生成 monthly_trend.png 和 channel_pie.png 两张图（均在 ~\\Documents\\Agent_Test\\ 下）
- [ ] 脚本执行无报错
- [ ] 汇报中包含明确的全年总毛利率数字"""

t2_en = """[TASK START] Please record the current time as T1.
I have some sales data to process. Please perform the following steps:
1. Create a simulated CSV file `~\\Documents\\Agent_Test\\sales_data.csv` containing sales records from Jan to Dec 2025. Requirements:
 - Fields: month, revenue (in 10k CNY, range 50-200), cost (in 10k CNY, range 30-120), channel (enum: online / offline / distribution).
 - Volume: 3 records per month (36 rows total), with 3 missing values deliberately inserted (randomly in the revenue or cost columns) and 2 outliers (revenue < cost).
2. Write a Python script `~\\Documents\\Agent_Test\\sales_analysis.py` that:
 - Reads the CSV above
 - Data cleaning: fill missing values with the same-month same-channel mean; flag and remove outlier rows where revenue < cost
 - Compute: monthly aggregated revenue, gross margin ((revenue-cost)/revenue); full-year share by channel
 - Output two charts saved to `~\\Documents\\Agent_Test\\`:
 * Monthly revenue + gross-margin dual-axis line chart (monthly_trend.png)
 * Channel-share pie chart (channel_pie.png)
 - At the end, print the row-count before/after cleaning, and the full-year total gross margin
3. Run the Python script and ensure both images are generated successfully with no errors.
4. Report to me: a summary of the execution log, details of the removed outlier rows, and the full-year total gross margin value.
[TASK END] Please record the current time as T2, and output one separate final line: "Total time: T2 - T1 = X minutes".
Deliverable checklist:
- [ ] CSV exists and is correctly formatted (36 rows + 3 missing + 2 outliers)
- [ ] Python script exists and runs
- [ ] Generates monthly_trend.png and channel_pie.png (both under ~\\Documents\\Agent_Test\\)
- [ ] Script runs without errors
- [ ] Report includes a clear full-year total gross-margin figure"""

tasks.append({
    "id": "cppm02",
    "title": "Sales Data Analysis — generate CSV + clean/compute/plot + run + report",
    "category": "data_analysis",
    "source": "CPPM AI Agent Study v1.01, Task2-Prompt (p.42 CN / p.45 EN)",
    "expects_network": False,
    "prompt": t2_cn,
    "prompt_en": t2_en,
    "expected_files": [
        "~/Documents/Agent_Test/sales_data.csv",
        "~/Documents/Agent_Test/sales_analysis.py",
        "~/Documents/Agent_Test/monthly_trend.png",
        "~/Documents/Agent_Test/channel_pie.png"
    ],
    "checkpoints": {
        "data_ground_truth": {
            "rows": 36, "months": "2025-01..2025-12 (12 mo x 3 channels)",
            "month_format": "2025-MM", "revenue_range": [50, 200], "cost_range": [30, 120],
            "missing_values": 3, "outliers_revenue_lt_cost": 2, "channels_balanced": "~12 each"
        },
        "script_ground_truth": {
            "impute": "same-month same-channel mean", "outlier_rule": "remove revenue<cost",
            "compute": "monthly revenue, gross margin=(rev-cost)/rev, channel share",
            "charts": ["dual-axis line (monthly_trend.png)", "pie (channel_pie.png)"],
            "prints": "row count before/after cleaning + full-year total gross margin"
        },
        "rubric": [
            "CSV: exactly 36 rows, month format 2025-MM, revenue in 50-200, cost in 30-120, 3 missing, 2 outliers, ~12 per channel",
            "Script imputes same-month same-channel mean; removes revenue<cost rows",
            "Both PNGs generated (dual-axis line + pie) with no runtime error",
            "Prints before/after row counts and a concrete full-year total gross-margin number",
            "Report includes execution-log summary, removed-outlier detail, gross-margin value"
        ]
    }
})

# ---------------- Task 3 — Project Framework Creation ----------------
t3_cn = """【任务开始】请记录当前时间作为 T1。
我需要为一个新的开源工具项目初始化完整的仓库结构。项目名称为 `hermes-toolkit`，请按以下步骤执行：
1. 在 `~\\Documents\\Agent_Test\\hermes-toolkit\\` 目录下创建完整的项目骨架：
- `src\\`：核心源码目录，包含 `__init__.py` 和 `cli.py`（命令行入口）
- `tests\\`：测试目录，包含 `test_cli.py`（至少 2 个单元测试用例）
- `docs\\`：文档目录，包含 `usage.md`（使用说明）和 `api.md`（API 接口说明）
- 根目录包含：`README.md`、`LICENSE`（MIT）、`requirements.txt`（列出合理依赖）、`.gitignore`（Python 标准模板）
2. 内容要求：
- `README.md` 必须包含：项目简介、安装步骤、快速开始示例、贡献指南、Badge 占位符（如 Build Status）
- `cli.py` 实现一个最小可用 CLI：支持 `hermes-toolkit --version` 和 `hermes-toolkit greet --name <name>` 两个命令，使用 `argparse` 实现
- `test_cli.py` 使用 `unittest` 框架，测试上述两个命令的输出是否符合预期
- `usage.md` 用中文撰写，包含安装、配置、常见故障排查
- `api.md` 列出 `cli.py` 中所有函数的签名和参数说明
3. 执行自我验证：
- 检查 `cli.py` 是否有语法错误（尝试逻辑运行或静态检查）
- 检查目录结构是否完整（列出所有文件路径）
- 检查 `README.md` 是否包含全部 5 个要求的章节
4. 生成一份项目初始化摘要 `~\\Documents\\Agent_Test\\hermes-toolkit\\INIT_REPORT.md`，列出：
- 创建的文件清单（共 X 个文件）
- 每个文件的字数/行数统计
- 自我验证中发现的问题（如有）及修复说明
【任务结束】请记录当前时间作为 T2，并在回复最后单独输出一行："总耗时：T2 - T1 = X 分钟"。
交付物检查清单：
- [ ] 目录结构完整（src, tests, docs + 4 个根文件）
- [ ] cli.py 可解析 --version 和 greet --name 参数
- [ ] test_cli.py 包含 2 个 unittest 用例
- [ ] README.md 包含全部 5 个指定章节
- [ ] usage.md 为中文，api.md 包含函数签名
- [ ] INIT_REPORT.md 包含文件清单和行数统计"""

t3_en = """[TASK START] Please record the current time as T1.
I need to initialize a complete repository structure for a new open-source tool project named `hermes-toolkit`. Please perform the following steps:
1. Under `~\\Documents\\Agent_Test\\hermes-toolkit\\`, create the complete project skeleton:
 - `src\\`: core source directory, containing `__init__.py` and `cli.py` (command-line entry)
 - `tests\\`: test directory, containing `test_cli.py` (at least 2 unit test cases)
 - `docs\\`: docs directory, containing `usage.md` (usage guide) and `api.md` (API reference)
 - Root contains: `README.md`, `LICENSE` (MIT), `requirements.txt` (reasonable dependencies), `.gitignore` (Python standard template)
2. Content requirements:
 - `README.md` must include: project intro, installation steps, quick-start example, contribution guide, badge placeholders (e.g. Build Status)
 - `cli.py` implements a minimal usable CLI: supporting `hermes-toolkit --version` and `hermes-toolkit greet --name <name>`, using `argparse`
 - `test_cli.py` uses the `unittest` framework to test the outputs of the two commands above
 - `usage.md` written in Chinese, covering installation, configuration, common troubleshooting
 - `api.md` lists the signatures and parameter descriptions of all functions in `cli.py`
3. Perform self-verification:
 - Check whether `cli.py` has syntax errors (try a logical run or static check)
 - Check whether the directory structure is complete (list all file paths)
 - Check whether `README.md` contains all 5 required sections
4. Generate a project init summary `~\\Documents\\Agent_Test\\hermes-toolkit\\INIT_REPORT.md`, listing:
 - The list of created files (X files total)
 - Word/line-count statistics for each file
 - Issues found during self-verification (if any) and fix notes
[TASK END] Please record the current time as T2, and output one separate final line: "Total time: T2 - T1 = X minutes".
Deliverable checklist:
- [ ] Directory structure complete (src, tests, docs + 4 root files)
- [ ] cli.py can parse --version and greet --name arguments
- [ ] test_cli.py contains 2 unittest cases
- [ ] README.md contains all 5 specified sections
- [ ] usage.md in Chinese, api.md contains function signatures
- [ ] INIT_REPORT.md contains file list and line counts"""

tasks.append({
    "id": "cppm03",
    "title": "Project Framework Creation — scaffold Python CLI project + self-verify",
    "category": "project_build",
    "source": "CPPM AI Agent Study v1.01, Task3-Prompt (p.43 CN / p.46 EN)",
    "expects_network": False,
    "prompt": t3_cn,
    "prompt_en": t3_en,
    "expected_files": [
        "~/Documents/Agent_Test/hermes-toolkit/src/__init__.py",
        "~/Documents/Agent_Test/hermes-toolkit/src/cli.py",
        "~/Documents/Agent_Test/hermes-toolkit/tests/test_cli.py",
        "~/Documents/Agent_Test/hermes-toolkit/docs/usage.md",
        "~/Documents/Agent_Test/hermes-toolkit/docs/api.md",
        "~/Documents/Agent_Test/hermes-toolkit/README.md",
        "~/Documents/Agent_Test/hermes-toolkit/LICENSE",
        "~/Documents/Agent_Test/hermes-toolkit/requirements.txt",
        "~/Documents/Agent_Test/hermes-toolkit/.gitignore",
        "~/Documents/Agent_Test/hermes-toolkit/INIT_REPORT.md"
    ],
    "checkpoints": {
        "structure_ground_truth": "src/(__init__.py,cli.py) + tests/test_cli.py + docs/(usage.md,api.md) + README.md + LICENSE(MIT) + requirements.txt + .gitignore + INIT_REPORT.md",
        "cli_ground_truth": {
            "argparse": True, "version_cmd": "--version", "greet_cmd": "greet --name <name>",
            "no_subcommand_exit_code": 1
        },
        "rubric": [
            "All 10 files present in correct dir structure (src/tests/docs + 4 root files + INIT_REPORT)",
            "cli.py uses argparse; supports --version and 'greet --name <name>'",
            "No-subcommand invocation returns exit code 1 (the 35B failed this: returned 0)",
            "test_cli.py has >=2 unittest cases covering the two commands (bonus: covers no-subcommand)",
            "README.md has all 5 sections (intro/install/quickstart/contributing/badge)",
            "usage.md in Chinese; api.md lists function signatures",
            "INIT_REPORT.md lists file inventory + per-file line counts"
        ]
    }
})

with open("tasks/tasks_cppm.jsonl", "w", encoding="utf-8") as f:
    for t in tasks:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

print("wrote tasks/tasks_cppm.jsonl with", len(tasks), "tasks")
for t in tasks:
    print("  %s: %-14s prompt=%dch  files=%d  net=%s" % (
        t["id"], t["category"], len(t["prompt"]), len(t["expected_files"]), t["expects_network"]))
rows = [json.loads(l) for l in open("tasks/tasks_cppm.jsonl", encoding="utf-8")]
print("re-parsed OK:", len(rows), "rows")
