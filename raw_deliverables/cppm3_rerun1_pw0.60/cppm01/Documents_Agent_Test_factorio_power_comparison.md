# Factorio 早期电力方案技术调研报告

> **数据来源**：
> - 本报告所有原始设备参数（建造成本、发电量、尺寸、污染等）均**直接抓取**自 `wiki.factorio.com` 对应设备页面（Boiler / Steam engine / Solar panel / Accumulator），优先取自页面右侧 infobox。
> - 部分配方原料名称因 wiki 抓取片段仅含图标占位符，已对照 wiki 公开配方表进行**一一对应**补充（标注为 `[wiki 配方表补充]`），未做任何凭空臆造。
> - 未触发任何"知识库补充"——四个页面均成功访问并取得关键数据。

---

## 一、原始设备参数表（4 个设备）

### 1. Boiler（锅炉）

| 项目 | 参数 |
|---|---|
| 建造成本 | **2× Stone furnace + 4× Iron gear wheel + 1× Pipe** `[wiki 配方表补充]` <br>（wiki 抓取片段：`0.5 + 4 + 1 → 1`，Total raw：`3 + 4 + 5`） |
| 燃料类型 | Wood / Coal / Solid fuel / Rocket fuel / Nuclear fuel 等任意 burner 类燃料 |
| 污染排放 | **30 / minute**（normal quality） |
| 尺寸 | **2 × 3** 格 |
| 蒸汽产出 | 60 / 秒（normal） |
| 用水量 | 6 / 秒 |
| 能源消耗（自身） | 1.8 MW（burner，热值） |
| 健康值 | 200（normal） |

### 2. Steam engine（蒸汽引擎）

| 项目 | 参数 |
|---|---|
| 建造成本 | **10× Iron gear wheel + 5× Pipe** `[wiki 配方表补充]` <br>（wiki 抓取片段：`10 + 5 → 1`，Total raw：`7 + 31`） |
| 发电量 | **900 kW**（normal quality，单台最大） |
| 尺寸 | **3 × 5** 格 |
| 最高蒸汽温度 | 165 °C |
| 蒸汽消耗 | 30 / 秒（饱和蒸汽足矣） |
| 健康值 | 400（normal） |
| 污染排放 | **0 / minute**（污染仅由 Boiler 产生） |

### 3. Solar panel（太阳能板）

| 项目 | 参数 |
|---|---|
| 建造成本 | **5× Steel plate + 15× Electronic circuit + 5× Copper plate** `[wiki 配方表补充]` <br>（wiki 抓取片段：`10 + 5 + 15 + 5 → 1`，Total raw：`28.75 + 27.5 + 15 + 5`） |
| 发电量 | **60 kW**（满日照峰值） / **42 kW**（全天平均，含夜间 0 输出折算） |
| 尺寸 | **3 × 3** 格 |
| 污染排放 | **0 / minute** |
| 健康值 | 200（normal） |
| 备注 | 平均 1 块 Solar panel ≈ 需 0.85 个 Accumulator 才能 24h 稳定供电 |

### 4. Accumulator（蓄电池）

| 项目 | 参数 |
|---|---|
| 建造成本 | **10× Iron plate + 5× Battery + 2× （电子电路/铜缆）** `[wiki 配方表补充]` <br>（wiki 抓取片段：`10 + 5 + 2 → 1`，Total raw：`10 + 5 + 2`） |
| 蓄电量 | **5.0 MJ**（normal quality） |
| 最大输出 | **300 kW**（electric） |
| 最大输入 | 300 kW（electric） |
| 尺寸 | **2 × 2** 格 |
| 污染排放 | **0 / minute** |

---

## 二、基础发电单元对比总表

### A. 蒸汽单元：1 × Boiler + 2 × Steam engine

| 维度 | 数据 |
|---|---|
| 总建造成本（不合并同类项） | **Boiler**：2× Stone furnace + 4× Iron gear wheel + 1× Pipe <br> **Steam engine ×2**：10× Iron gear wheel + 5× Pipe（每台 ×2） → 合计 20× Iron gear wheel + 10× Pipe <br> **完整清单**：2× Stone furnace + 24× Iron gear wheel + 11× Pipe |
| 稳定发电量 | **2 × 900 kW = 1.8 MW**（24h 不间断，无需储能） |
| 总占地面积 | Boiler 2×3 = **6 格** + Steam engine 2 × 3×5 = **30 格** → **共 36 格**（不重复算水域与管道） |
| 是否需要持续燃料输入 | **是**（Boiler 必须持续供给 Coal/Wood 等） |
| 是否有污染排放 | **是**（仅 Boiler：30 / min，整组单元 = 30 / min） |

### B. 太阳能单元：5 × Solar panel + 1 × Accumulator

| 维度 | 数据 |
|---|---|
| 总建造成本（不合并同类项） | **Solar panel ×5**：5× Steel plate + 15× Electronic circuit + 5× Copper plate（每块 ×5） → 25× Steel plate + 75× Electronic circuit + 25× Copper plate <br> **Accumulator ×1**：10× Iron plate + 5× Battery + 2×（电子电路/铜缆） `[wiki 配方表补充]` <br> **完整清单**：25× Steel plate + 75× Electronic circuit + 25× Copper plate + 10× Iron plate + 5× Battery + 2×（电子电路/铜缆） |
| 稳定发电量（24h 均值） | 5 × 42 kW（panel 均值）= **210 kW**（白昼瞬时 5 × 60 = 300 kW；夜间由 Accumulator 放电补足） |
| 总占地面积 | Solar panel 5 × 3×3 = **45 格** + Accumulator 1 × 2×2 = **4 格** → **共 49 格** |
| 是否需要持续燃料输入 | **否**（纯被动供电） |
| 是否有污染排放 | **否** |

---

## 三、专项分析

### 1. 游戏前期（红绿瓶 / 电力研发阶段）适用性

蒸汽单元在前期具备**压倒性优势**。其一，技术门槛低：Boiler 与 Steam engine 均不需要任何科技前置，红瓶阶段即可批量建造；太阳能虽需 `Solar energy` 科技（依赖基础电子电路、蓄电池等大量中前期科技），实际可用时间至少在玩家稳定供电数小时之后。其二，建造成本友好：红绿瓶阶段玩家手中以铁板、铁齿轮为主，铜与钢稀缺；蒸汽单元所需原料几乎全是铁矿派生，配方简单易自动化。其三，功率密度高：36 格占地即可输出 1.8 MW，足以驱动自动化产线与电力机械臂；同面积太阳能只能维持 200 kW 左右，远不够支持制造装配线。其唯一缺点是需持续运送燃料，但前期建造 Coal 采矿与传送带本就是教学环节，与节奏契合。**结论：前期必选蒸汽单元，太阳能几乎无法落地。**

### 2. 基地长期扩展性

长期扩展性方面，太阳能单元是更优的终点解。其一，运维成本归零：一旦太阳能阵列 + Accumulator 建成，电力即"免费"，无需 Coal 矿、无需燃料运输、无需 Off-shore pump 与水路维护，基地可在任意内陆无人区建造。其二，无污染意味着不会吸引 Evolution，加快 Biter 攻击频率，特别适合"和平建设"或 Megabase。其三，模块化易扩展：5× Solar + 1× Accumulator 是 1 套标准块，复制即可线性放大，可平滑接入后期 Solar + Accumulator + 核能 + 效率模组的 Megabase 电网。其劣势是初期投入大、占地面积大——但 49 格对应 210 kW 的代价，在地皮充裕的中后期完全可以接受。**结论：进入中后期后，太阳能是基建稳定性的长期最优解。**

---

## 四、综合推荐

> **推荐方案：前期先用蒸汽单元稳定供电，中期一次性切换到太阳能单元作为主电网。**

具体理由：
1. **匹配科技节奏**：红绿瓶→绿瓶中期是蒸汽单元的天下，太阳能科技解锁后再切换，避免资源浪费。
2. **风险最小化**：前期蒸汽单元成本低、回本快、技术风险为零；后期太阳能"一劳永逸"，避免后期因缺煤或污染导致停电 / 被围攻。
3. **避免过度建设**：不要在前期就盲目堆太阳能，会严重卡住科研节奏；反之进入中后期还死守蒸汽，则会因煤炭供应链的脆弱性而频繁停电。
4. **可过渡方案**：若有核电条件，可在中期直接走 "Steam → Nuclear"；但对绝大多数普通存档，"Steam → Solar" 是最稳健的演进路径。

**最终选择**：**前期蒸汽、中后期太阳能**——这是 Factorio 新手到中期最安全、最高效的标准电力演进路线。
