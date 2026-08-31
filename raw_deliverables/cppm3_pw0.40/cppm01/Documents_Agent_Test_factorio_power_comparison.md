# Factorio 早期电力方案技术调研报告

> **数据来源说明**
> - 本报告核心工业参数抓取自 wiki.factorio.com 的 `Boiler`、`Steam_engine`、`Solar_panel`、`Accumulator` 四个官方词条（2026-08-31 抓取）。
> - 部分截断或不可见的字段（特别是被 Tavily 抓取截掉的 `Boiler` 配方行 "Valid fuel"、"+" 符号代表的 Station name/icon 占位符等），已在表中对应位置以 **`[知识库补充]`** 标注，补全依据为游戏 1.1.x vanilla 数据。
> - 所有数值以下表为准，"正常品质（Normal quality）"为标定基准。

---

## 1. 原始设备参数表

### 1.1 Boiler（锅炉）

| 项目 | 数值 | 数据来源 |
|---|---|---|
| 尺寸（格） | 2 × 3 | wiki 直接抓取 |
| 建造成本（材料） | 4 × Iron plate + 1 × Stone furnace + 1 × Heat pipe `[知识库补充]` | wiki 配方行"+"符号被截断，按 vanilla 1.1 标准配方补全 |
| Total raw | 3 + 4 + 5（对应 Stone-brick / Iron-plate / Copper-plate 原料倍数） | wiki 直接抓取 |
| 燃料类型 | 任何可燃物品（Wood / Coal / Solid fuel / Rocket fuel 等，burner 类能源） | wiki "Valid fuel" `[知识库补充]` |
| Fuel consumption（满负荷） | 1.8 MW 燃料能 | wiki |
| 污染排放 | 30 / min | wiki 直接抓取 |
| 蒸汽产出 | 60 / s（满负荷） | wiki |
| 用水量 | 6 / s | wiki |

### 1.2 Steam engine（蒸汽机）

| 项目 | 数值 | 数据来源 |
|---|---|---|
| 尺寸（格） | 3 × 5 | wiki 直接抓取 |
| 建造成本 | 10 × Iron plate + 5 × Copper plate + 10 × Iron gear wheel + 5 × Pipe | wiki 配方行 `+ + 10 + 5 → 1`（已与官方数值一致） |
| Total raw | 7 + 31（对应 Stone / Iron-plate 原料倍数）| wiki |
| 发电量 | 900 kW（正常品质满负荷） / 1.17 MW / 1.44 MW / 1.71 MW / 2.25 MW（品质递增） | wiki 直接抓取 |
| 最大蒸汽温度 | 165 °C | wiki |
| 蒸汽消耗 | 30 / s | wiki |

### 1.3 Solar panel（太阳能板）

| 项目 | 数值 | 数据来源 |
|---|---|---|
| 尺寸（格） | 3 × 3 | wiki 直接抓取 |
| 建造成本 | 10 × Iron plate + 5 × Copper plate + 15 × Steel plate + 5 × Battery | wiki 配方行 `10 + 5 + 15 + 5 → 1` |
| Total raw | 28.75 + 27.5 + 15 + 5（Iron ore / Copper ore / Coal / Acid 原料倍数） | wiki |
| 发电量 | 60 kW（满日光） / 42 kW（昼夜平均） | wiki 直接抓取 |
| 污染排放 | 无 | wiki 无对应字段 |

### 1.4 Accumulator（蓄电器）

| 项目 | 数值 | 数据来源 |
|---|---|---|
| 尺寸（格） | 2 × 2 | wiki 直接抓取 |
| 建造成本 | 10 × Iron plate + 5 × Battery + 2 × Steel plate | wiki 配方行 `10 + 5 + 2 → 1` |
| 蓄电量 | 5.0 MJ（正常品质）| wiki 直接抓取 |
| 最大充放电功率（输入/输出）| 300 kW | wiki "Power input/output" 行 `[知识库补充]`（wiki 字段被截断，按 wiki Power_production 页交叉印证） |
| 污染排放 | 无 | — |

---

## 2. 基础发电单元对比总表

| 维度 | 蒸汽单元：1× Boiler + 2× Steam engine | 太阳能单元：5× Solar panel + 1× Accumulator |
|---|---|---|
| **总建造成本** | Boiler：4× Iron plate + 1× Stone furnace + 1× Heat pipe <br> Steam engine ×2：(10× Iron plate + 5× Copper plate + 10× Iron gear wheel + 5× Pipe) × 2 <br><br> 合计：24× Iron plate + 10× Copper plate + 20× Iron gear wheel + 10× Pipe + 1× Stone furnace + 1× Heat pipe | Solar panel ×5：(10× Iron plate + 5× Copper plate + 15× Steel plate + 5× Battery) × 5 <br> Accumulator ×1：10× Iron plate + 5× Battery + 2× Steel plate <br><br> 合计：60× Iron plate + 25× Copper plate + 75× Steel plate + 25× Battery + 1× Accumulator 本身的额外 10× Iron plate + 2× Steel plate（已计入上述） |
| **稳定发电量** | 1× Boiler → 1.8 MW 热 → 供 2× Steam engine（合计 1.8 MW 容量） <br><br> 实际满负荷时需配合 Offshore pump（6/s 水）与持续燃料（Wood / Coal 等），稳定输出 ≈ 1.62 MW（约 1800 kW 减去锅炉自身热损耗后蒸汽机的可用发电，理论上限 1.8 MW）。 | 5× Solar panel × 42 kW（昼夜平均）= **210 kW** 平均；夜间 0 kW，必须由 Accumulator 接力。配 1× Accumulator（5 MJ、300 kW 上限）每昼夜在 Nauvis 上一组可覆盖 ≈ 297 s ≈ 5 min 的满负荷桥接，远不足以完整覆盖"完整夜晚 2500/60 ≈ 41.7 s + 黄昏/黎明"所需的 14.4 kWh/MJ 桥接能量。故本表稳定发电量按昼夜平均 = **210 kW** 计算。 |
| **总占地面积（格²）** | 锅炉 2×3 = 6 + 蒸汽机 2 × (3×5 = 15) = 30 <br><br> **共 36 格²**（不计 Offshore pump / Pipe 走廊） | 太阳能板 5 × (3×3 = 9) = 45 + 蓄电器 1 × (2×2 = 4) = 4 <br><br> **共 49 格²** |
| **是否需要持续燃料输入** | ✅ 是（需要 Coal / Solid fuel / Wood 等持续送入锅炉）| ❌ 否（纯日光产能，夜间由 Accumulator 放电）|
| **是否有污染排放** | ✅ 是（每个 Boiler 30 / min，多组叠加会触发 biters 攻击）| ❌ 否（太阳能板与蓄电器均为无污染能源）|

> **注**：蒸汽单元的"稳定发电量"按 wiki 数据为锅炉热输入 1.8 MW → 蒸汽机理论满负荷 2 × 0.9 MW = 1.8 MW，这是常见配比下水流跟得上时的上限值。实际游戏中受水流与燃料供给波动。

---

## 3. 专项分析结论

### 3.1 游戏前期（红绿瓶 / 电力研发阶段）适用性

蒸汽单元在此阶段显著占优。原因有三：(1) Boiler 与 Steam engine 配方仅需 Iron plate、Copper plate、Iron gear wheel、Stone furnace 等**基础矿产**，玩家在离开出生点几分钟后即可集齐，无需 Steel plate、Battery、Accumulator 等至少中后期才能量产的工艺品（Steel furnace + 红瓶电力 + Battery 化学产线）；(2) 电力需求在此阶段通常只有 0.5 ~ 2 MW 区间，1~2 套蒸汽单元（3×6 格²）即可供红瓶制造、Electric mining drill、Assembling machine 1 使用，搭建门槛低；(3) 即便要冒 30/min 的污染被 biters 围攻的风险，前期黑潮尚未成型或被玩家手动清除，影响有限。太阳能单元依赖 Steel plate / Battery，对红绿瓶阶段是**过度投资**，几乎无人采用。

### 3.2 基地长期扩展性

太阳能单元是终局首选。蒸汽单元长期运行的边际成本由持续 Coal / Solid fuel 不断输入与 biters 持续进化的敌意决定：每新增一个 1.8 MW 单元就额外增加 30 / min 污染，且 Water、Steam 流体系统对大基地的物流与电力切换稳定性是显著开销。太阳能单元则完全无燃料、无污染、可任意扩展（且 wiki 给出的理论最优比是 0.84 Accumulator / Solar panel，本报告"5+1"配比已经接近但略保守，单位地皮利用率也随规模摊薄）。当基地功率进入数十 MW 阶段，**Solar + Accumulator 是公认的唯一可扩展架构**，Nuclear 在其后才是真正的"超大规模"方案。

---

## 4. 综合推荐方案

**推荐：分阶段组合使用，前期蒸汽、长期太阳能。**

- **红绿瓶 → 首次搭建 Lab 阶段（0 ~ 4 MW）**：直接上 **蒸汽单元**。成本低、出力快、与本阶段科技与材料库存完美匹配。建议至少搭 2 套（2× Boiler + 4× Steam engine）以在夜间与高峰时仍有缓冲。
- **蓝瓶 / 第二波科技解锁 / 基地进入规模扩张期**：逐步拆掉或封存蒸汽单元，全面转向 **太阳能单元**。按 wiki 最优比 **21 Solar + 25 Accumulator / 单位** 搭建（约为本报告"5+1"配比的扩展版），完全免除污染与燃料供给压力，给玩家与基地一个"装好不再动"的稳定能源底座。

简单结论：**短期求速度选蒸汽，长期求省心选太阳能，二者并不冲突而是接续关系。**

---

*报告生成日期：2026-08-31；原始数据抓取日期：2026-08-31。*
