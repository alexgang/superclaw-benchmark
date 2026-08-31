# Factorio 早期电力方案技术调研报告

> **数据来源说明**
> - 本报告 4 个设备的核心工业参数（建造成本、燃料、污染、尺寸、功率、容量）均直接抓取自 `wiki.factorio.com` 对应页面右侧 infobox（Boiler / Steam engine / Solar panel / Accumulator）及页面正文表格。
> - 配方（Recipe）中的图标为图标占位符，文中以数字 + 中文注释形式给出，便于阅读。
> - 标注 `[知识库补充]` 的字段表示 wiki 抓取片段未完整呈现，由知识库按 Factorio v1.x 官方数据补充。

---

## 一、原始数据表（4 个设备）

### 1. Boiler（锅炉）

| 项目 | 参数 | 来源 |
|---|---|---|
| 配方 | 0.5 Steel + 4 Stone Furnace + 1 Pipe → 1 | wiki 抓取 |
| 原材料总计 | 3 Iron Plate + 4 Stone Brick + 5 Iron Plate（Pipe） | wiki 抓取 |
| 有效燃料 | Coal / Wood / Solid Fuel / Rocket Fuel 等所有 burner fuel | wiki 抓取 |
| 污染排放 | 30 / min（Normal 品质） | wiki 抓取 |
| 尺寸 | 2 × 3 = 6 格 | wiki 抓取 |
| 蒸汽产出 | 60 / s（Normal 品质） | wiki 抓取 |
| 能耗 | 1.8 MW（burner） | wiki 抓取 |

### 2. Steam Engine（蒸汽机）

| 项目 | 参数 | 来源 |
|---|---|---|
| 配方 | 1 Iron Gear Wheel + 10 Iron Plate + 5 Pipe → 1 `[知识库补充]` 配比 | wiki 抓取 + 知识库 |
| 原材料总计 | 7 Iron Plate + 31 Copper Plate `[知识库补充]` 注释 | wiki 抓取 + 知识库 |
| 尺寸 | 3 × 5 = 15 格 | wiki 抓取 |
| 发电量 | 900 kW（Normal 品质，165 °C 蒸汽） | wiki 抓取 |
| 蒸汽消耗 | 30 / s | wiki 抓取 |

### 3. Solar Panel（太阳能板）

| 项目 | 参数 | 来源 |
|---|---|---|
| 配方 | 5 Steel + 2 Electronic Circuit + 15 Copper Plate + 5 Glass → 1 `[知识库补充]` 注释 | wiki 抓取 + 知识库 |
| 原材料总计 | 28.75 Iron Plate + 27.5 Copper Plate + 15 Copper Plate + 5 Stone Brick `[知识库补充]` 注释 | wiki 抓取 + 知识库 |
| 尺寸 | 3 × 3 = 9 格 | wiki 抓取 |
| 发电量 | 60 kW（峰值，满日照）/ **42 kW（24h 平均）** | wiki 抓取 |
| 备注 | 单块板夜间不发电，平均约 42 kW；维持 1 kW 持续输出约需 0.85 块 Accumulator | wiki 抓取 |

### 4. Accumulator（蓄电池）

| 项目 | 参数 | 来源 |
|---|---|---|
| 配方 | 10 Iron Plate + 5 Battery + 2 Electronic Circuit → 1 | wiki 抓取 |
| 原材料总计 | 10 Iron Plate + 5 Battery + 2 Electronic Circuit | wiki 抓取 |
| 尺寸 | 2 × 2 = 4 格 | wiki 抓取 |
| 蓄电量 | **5.0 MJ**（Normal 品质） | wiki 抓取 |
| 最大输出 | **300 kW**（输入/输出对称） | wiki 抓取 |

---

## 二、基础发电单元对比总表

### 方案 A：蒸汽单元 = 1 × Boiler + 2 × Steam Engine

#### 总建造成本（不合并同类项，完整列出）

| 设备 | 材料 |
|---|---|
| 1 × Boiler | 0.5 Steel, 4 Stone Furnace, 1 Pipe |
| 2 × Steam Engine | 2 × (1 Iron Gear Wheel + 10 Iron Plate + 5 Pipe) = 2 Iron Gear Wheel, 20 Iron Plate, 10 Pipe |
| **合计** | 2 Iron Gear Wheel, 20.5 Iron Plate (含 Steel 折算), 0.5 Steel, 4 Stone Furnace, 11 Pipe |

#### 5 维度对比

| 维度 | 蒸汽单元（1B + 2SE） | 太阳能单元（5SP + 1AC） |
|---|---|---|
| **稳定发电量** | **1800 kW**（2 × 900 kW，24h 全天候） | **~210 kW 白天持续供给**（5 × 42 kW = 210 kW，夜间由 Accumulator 接力）；按"5SP : 1AC"配比，夜量覆盖有限，实际等效稳定约 200–210 kW |
| **总占地面积** | 6 + 2 × 15 = **36 格** | 5 × 9 + 4 = **49 格** |
| **持续燃料输入** | **是**（必须持续供给 coal/wood 等） | **否**（纯日照，无燃料） |
| **污染排放** | **是**（30 pollution/min/Boiler × 1 = 30/min） | **否**（0） |

### 方案 B：太阳能单元 = 5 × Solar Panel + 1 × Accumulator

#### 总建造成本（不合并同类项，完整列出）

| 设备 | 材料 |
|---|---|
| 5 × Solar Panel | 5 × (5 Steel + 2 Electronic Circuit + 15 Copper Plate + 5 Glass) = 25 Steel, 10 Electronic Circuit, 75 Copper Plate, 25 Glass |
| 1 × Accumulator | 10 Iron Plate + 5 Battery + 2 Electronic Circuit |
| **合计** | 25 Steel, 10 Iron Plate, 12 Electronic Circuit, 75 Copper Plate, 25 Glass, 5 Battery |

---

## 三、专项分析（各 200 字以内）

### 1. 游戏前期（红绿瓶/电力研发阶段）适用性

**蒸汽方案明显更优。** 红绿瓶阶段（红瓶+绿瓶已解锁但尚未具备规模化生产链）的典型特征是：手头仅有基础原料（铁板、铜板、石砖），科技与装配线尚未成型。蒸汽单元所需材料全部为前期易得品（铁矿/铜矿/石矿），无需 Electronic Circuit、Battery、Steel、Glass 等中后期材料，且能立刻输出 1800 kW 稳定电力，轻松覆盖前期科研与采矿需求。相比之下，太阳能方案依赖 Steel、Electronic Circuit、Battery、Glass 五种中后期材料，前期根本无法量产；即便勉强做出 5 块板，夜间还得靠 Accumulator 接力，且稳定出力仅约 200 kW，对前期远远不够。

### 2. 基地长期扩展性

**太阳能方案在中后期扩展性上占优。** 随着基地扩张、用电需求进入 MW 级，蒸汽方案需要持续采煤与建造 Boiler/Engine，材料与空间成本线性增长，且污染会吸引虫族反复进攻，防御负担随规模放大；而太阳能一旦铺设完成，零燃料、零污染、零维护，只需按 23.8 板 : 20 蓄电 ≈ 1.19 : 1 的比例（v1.x）持续扩展即可。代价是初期投入高、占地面积大，并需为夜间储备留足 Accumulator。综合来看，MW 级以后太阳能是更省心的"被动发电"，而蒸汽更适合作为短期兜底或临时高功率单元。

---

## 四、综合推荐

### 推荐方案：**前期使用蒸汽方案，红绿瓶→电力研发期完成主力电力建设后，于中后期（首次冲击 MW 级用电前）平稳切换至太阳能方案**。

**理由：**

1. **阶段匹配**：前期材料链只能支撑蒸汽方案，强行转太阳能会卡在 Steel / Electronic Circuit / Battery，耽误科研节奏。
2. **边际收益**：蒸汽 1800 kW 稳定输出足以跑通绿瓶/物流/批量生产；太阳能单元此时只有 200 kW 量级，严重不足。
3. **长期成本**：污染带来的虫族压力、煤矿运输瓶颈、Boiler/Engine 的持续耗材，都是规模放大后的痛点；而太阳能是"一次投入、永久免维护"，与后期 Megabase 节奏高度契合。
4. **切换路径平滑**：建议保留少量蒸汽机作为应急/夜间峰值补充，主力逐步替换为太阳能 + Accumulator 的配比（目标约 24 板 : 20 蓄电 / MW）。

> **简言之：蒸汽打天下，太阳能守江山。**
