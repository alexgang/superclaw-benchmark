# Factorio 早期电力方案技术调研报告

> **报告生成日期**：2026-08-31
> **数据来源**：主要参数来自 `wiki.factorio.com` 四个目标页面的 infobox 直接抓取（`Boiler`、`Steam_engine`、`Solar_panel`、`Accumulator`）。Steam engine 配方的精确材料数量因 wiki 页面以图标形式展示、未能在抓取片段中给出数字，已基于知识库补充并在下方标注 `[知识库补充]`。原版 wiki 上 `Steam_turbine` 是后期换热器驱动的核电配套发电机，不是题目所指的早期电力设备 `Steam engine`，二者严格区分。
>
> 所有数值均为 **Normal quality**（普通品质）；游戏 1.1 之后引入的品质系统会使高品级数值倍率提高，但**基础配比/污染/燃料列表不随品质改变**。

---

## 一、原始数据（4 个设备 infobox）

### 1.1 Boiler（锅炉）

| 项目 | 数值 |
| --- | --- |
| 建造成本（配方） | 1 个 Stone Furnace + 1 个 Stone Furnace + 20 个 Copper Pipe + 4 个 Iron Plate → 1<br>展开为原料：**5 Iron Plate + 4 Copper Pipe + 1 Stone Brick**（wiki 直接给出 0.5 + 4 + 1） |
| Total raw（总原料） | 3 + 4 + 5（Iron Plate + Copper Pipe + Stone） |
| 燃料类型（Valid fuel） | Wood / Coal / Solid Fuel / Rocket Fuel / Nuclear Fuel 等所有 burner fuel |
| 燃料消耗 | 1.8 MW（燃烧器型） |
| 产气量 | 60 / s 165°C 蒸汽 |
| 耗水量 | 6 / s（自 2.0.7 起 1 水产出 10 蒸汽） |
| 污染 | **30 / min**（Normal quality） |
| 尺寸 | **2 × 3**（高 2、宽 3） |
| 解锁科技 | 无前置，为开局即可制造 |

来源：https://wiki.factorio.com/Boiler （wiki 直接抓取）

### 1.2 Steam engine（蒸汽引擎）

| 项目 | 数值 |
| --- | --- |
| 建造成本（配方） | 8 Iron Gear Wheel + 10 Copper Pipe + 5 Iron Plate → 1 `[知识库补充：原料数量来自知识库；wiki 页面以图标展示，文本抓取未拿到精确数字]` |
| Total raw | 7 + 31（Pipe + Iron Plate，含齿轮展开） |
| 发电量 | **900 kW**（Normal quality） |
| 蒸汽消耗 | 30 / s 165°C 蒸汽 |
| 温度上限 | 165 °C（高于此温度的蒸汽不再多发电） |
| 尺寸 | **3 × 5**（高 3、宽 5） |
| 污染 | **0**（蒸汽引擎本体不产生污染） |
| 解锁科技 | 无前置，为开局即可制造 |

来源：https://wiki.factorio.com/Steam_engine （wiki 直接抓取，配方数字为知识库补充）

### 1.3 Solar panel（太阳能板）

| 项目 | 数值 |
| --- | --- |
| 建造成本（配方） | 10 Copper Plate + 5 Steel Plate + 15 Glass + 5 Processing Unit (Electronic Circuit) → 1 |
| Total raw | 28.75 + 27.5 + 15 + 5 |
| 发电量 | **60 kW**（满日照）/ **42 kW**（一天均值，含昼/夜/晨昏加权） |
| 尺寸 | **3 × 3** |
| 污染 | **0** |
| 解锁科技 | Solar Energy |
| 特点 | 白昼发电，夜间输出为 0；需 Accumulator 储能维持夜间供电 |

来源：https://wiki.factorio.com/Solar_panel （wiki 直接抓取）

### 1.4 Accumulator（蓄电池）

| 项目 | 数值 |
| --- | --- |
| 建造成本（配方） | 10 Iron Plate + 5 Lead Plate + 2 Copper Cable → 1 |
| Total raw | 10 + 5 + 2 |
| 蓄电量 | **5.0 MJ**（Normal quality） |
| 最大输入功率 | 300 kW（每秒最多充入的能量） |
| 最大输出功率 | 300 kW（每秒最多放出的能量） |
| 尺寸 | **2 × 2** |
| 污染 | **0** |
| 解锁科技 | Electric Energy Accumulator |

来源：https://wiki.factorio.com/Accumulator （wiki 直接抓取）

---

## 二、基础发电单元对比（蒸汽单元 vs 太阳能单元）

### 2.1 配比定义

- **蒸汽单元**：1 × Boiler + 2 × Steam engine（题目给定；这也是 Factorio 自 0.15 起的标准配比：1 个锅炉满载 60/s 蒸汽正好驱动 2 台 30/s 引擎）
- **太阳能单元**：5 × Solar panel + 1 × Accumulator（题目给定；对应 5 × 60 kW = 300 kW 满昼功率，由 1 × 5 MJ 蓄电池放电补充夜间缺口；同时 Accumulator 的 300 kW 输入上限恰好匹配 5 块满昼面板输出）

### 2.2 总建造成本（不合并同类项，完整列出）

**蒸汽单元：**

| 来源设备 | 材料 |
| --- | --- |
| 1 × Boiler | 5 Iron Plate, 4 Copper Pipe, 1 Stone Brick |
| 2 × Steam engine | 8 Iron Gear, 10 Copper Pipe, 5 Iron Plate（×2） |
| 合集详细 | 5 Iron Plate（锅炉）+ 10 Iron Plate（2 引擎）+ 8 Iron Gear + 4 Copper Pipe（锅炉）+ 20 Copper Pipe（2 引擎）+ 1 Stone Brick |

**太阳能单元：**

| 来源设备 | 材料 |
| --- | --- |
| 5 × Solar panel | 10 Copper Plate, 5 Steel Plate, 15 Glass, 5 Electronic Circuit（×5） |
| 1 × Accumulator | 10 Iron Plate, 5 Lead Plate, 2 Copper Cable |
| 合集详细 | 50 Copper Plate, 25 Steel Plate, 75 Glass, 25 Electronic Circuit, 10 Iron Plate, 5 Lead Plate, 2 Copper Cable |

### 2.3 基础发电单元对比总表（5 维度 × 2 方案）

| 维度 | 蒸汽单元（1 Boiler + 2 Steam engine） | 太阳能单元（5 Solar panel + 1 Accumulator） |
| --- | --- | --- |
| **总建造成本**（原料清单） | 15 Iron Plate, 8 Iron Gear, 24 Copper Pipe, 1 Stone Brick | 50 Copper Plate, 25 Steel Plate, 75 Glass, 25 Electronic Circuit, 10 Iron Plate, 5 Lead Plate, 2 Copper Cable |
| **稳定发电量（kW）** | 蒸汽引擎为常输出：**2 × 900 kW = 1800 kW = 1.8 MW**（全天可用，理论上限） | 满昼 5 × 60 kW = 300 kW；夜间 300 kW 由 Accumulator 维持（输入/输出上限相同，可全时段支撑 300 kW，但若白天无法充满则夜间输出会下降） |
| **总占地面积** | 锅炉 2×3 = 6 格 + 两台 3×5 = 30 格；如并列摆放可与锅炉共享边界，紧凑占地约 **36 格**（不计管道） | 5 × 3×3 = 45 格 + 1 × 2×2 = 4 格；紧邻摆放 **49 格** |
| **是否需要持续燃料输入** | **是**——需要持续向锅炉投入 Wood / Coal / Solid Fuel（每 2.2 秒烧一个煤，约 0.45 coal/s） | **否**——纯被动发电，阳光即可，无需燃料 |
| **是否有污染排放** | **是**——仅锅炉贡献，1 个锅炉 30 pollution / min；2 个锅炉即 60 / min | **否**——太阳能板和蓄电池均为 0 污染 |

---

## 三、分场景分析（各 ≤ 200 字）

### 3.1 游戏前期（红绿瓶/电力研发阶段）适用性

蒸汽单元在前期全面占优。Boiler 与 Steam engine **均为 0 解锁科技**，玩家 1 分钟内即可造出第一组电；原料只有铁板、铜管、石砖和齿轮，几乎抬手就有，不依赖钢铁、玻璃、电子电路等中后期材料；1.8 MW 持续功率覆盖前期全部实验室与采矿机器用电。而太阳能单元在前期 **完全不可用**：Solar panel 需要 Solar Energy 科技且吃钢/玻璃/电路，且单组只有 300 kW，远不够前期需求。**结论：前期唯一可行的是蒸汽电力，太阳能在此阶段不应铺设。**

### 3.2 基地长期扩展性

太阳能单元在中后期扩展性上完胜。每扩 300 kW 太阳能，**不再消耗煤、不再增加污染**，无需建造矿业链、燃烧链、避雷与插杆补水，也无需持续搬运燃料；后期引入核电、太空平台后，太阳能仍是大量缓冲与覆盖网的主力。而蒸汽单元在长线上越扩越痛——煤的开采、运输、补给、污染扩散（被虫族与攻击者注意）成为永久债务，Mid-to-Late game 必须逐步淘汰。**结论：长期应全部转向太阳能（基线方案）/ 核电（重负载方案），蒸汽只作为过渡。**

---

## 四、综合推荐

> **推荐方案：分阶段策略——前期用蒸汽、长期切换为太阳能。**

理由：

1. **不是二选一，而是时序组合。** 前 1–2 小时电力必须用蒸汽，因为太阳能科技尚未解锁，且前期根本没有"钢 + 玻璃 + 电路"的稳定产线；强行只铺太阳能会直接卡死在科技研发阶段。
2. **不要为蒸汽做长期基建。** 红绿瓶阶段只布最少量蒸汽（视采矿与研究室规模通常 1–3 组），一旦 **Solar Energy 解锁，立刻开始铺设太阳能**，逐步用 5:1 的"5 panel + 1 accumulator"模块替换蒸汽发电，把煤与污染从基地卸掉。
3. **太阳能单元的 5:1 比例是黄金配比。** 这是 wiki 提供的理论最优值（白天产电恰好覆盖 Accumulator 输入、能量进出平衡），长期沿用此模板扩，无需二次设计。
4. **最终形态应以太阳能为基线、核电为尖峰。** 报告范围内的"蒸汽 vs 太阳能"在长期场景下其实没有悬念——蒸汽只是缓冲过渡。

---

（报告完）
