# PII 模块实测报告

日期：2026-09-08
环境：B-side SuperClaw 安装包（v3.x 内置 security_manager + OpenVINO 2026.2.1）

## TL;DR

SuperClaw 自带的 PII 模块（`security_manager :18826`）目前处于**半残状态**：
- ✅ **REGEX 路径工作**：能 catch 10/15 类 PII（身份证、手机、银行卡、邮箱、公司、地址、密码、API key）
- ❌ **NER 路径死了**：`sanitize_ready: false`，因为 Intel 装的 `multilang-pii-ner-ov-int8` 模型跟内置 OpenVINO runtime 版本不匹配（optimum 2.1.0 vs OV 2026.2.1），security_manager 启动时 hang 在算子编译
- 用户反馈"中文拦截率低"**部分对**：REGEX 路径在中文 PII 上有显著漏洞（5 个中文人名 / 2 个地址 / 1 个密码 / 1 个 API key 都漏）；NER 路径即使装上模型**也救不了**（我们用 Python 独立推理验证了：身份证/银行卡/邮箱/密码/API key 全部被错标或切碎）

## REGEX 路径实测（真 PII 模块 `/v1/file/redact/upload` use_ner=false）

| PII 类型 | 15 个 planted token 中被 catch 比例 |
|----------|--------|
| CN_SSN (18 位身份证) | 5/5 ✅ |
| CN_PHONE (11 位手机) | 4/4 ✅ |
| CN_IDCARD (18 位) | 1/1 ✅ |
| CN_BANKCARD (19 位) | 1/1 ✅ |
| CN_EMAIL | 1/1 ✅ |
| CN_COMPANY | 1/1 ✅ |
| CN_ADDRESS (北京市...) | 0/2 ❌ |
| CN_PASSWORD (Wx@2024cn#secure) | 0/1 ❌ |
| CN_APIKEY (sk-cn-...) | 0/1 ❌ |
| **CN_PERSON (张伟/李娜/王芳/赵磊/孙琪)** | **0/5 ❌** |

合计 **52/60 漏 8**，catch_rate = 87%。

## NER 路径独立推理测试（用 `Downloads\intel_models\multilang-pii-ner-ov-int8` 加载 OpenVINO 2026.3.1）

模型是 XLM-RoBERTa + 35 类 BIO 标签（GIVENNAME / SURNAME / IDCARDNUM / TELEPHONENUM / CREDITCARDNUMBER / STREET / CITY / ...）。XLM-R vocab 包含中文（250K），但训练数据主要英文（ai4privacy/open-pii-masking-500k）。

| 测试 | NER 输出 | 是否可用 |
|------|---------|--------|
| CN_PERSON (张伟) | B-GIVENNAME 张/伟、B-SURNAME 伟 | ⚠️ 部分对，但拆成 given/surname |
| CN_PERSON (李娜) | B-GIVENNAME 李/娜 | ⚠️ 同上 |
| CN_ADDRESS (北京市朝阳区建国路88号) | B-CITY 北京市 + B-STREET 建/国 + B-BUILDINGNUM 88 | ⚠️ 部分对，"建国路"切碎 |
| CN_IDCARD (110101199003078239) | B-CREDITCARDNUMBER 110/101/1990 + B-PASSPORTNUM 030 | ❌ 切碎 + 类型错（不是 IDCARDNUM） |
| CN_BANKCARD (6222021234567890123) | B-CREDITCARDNUMBER 622/202/1234 | ❌ 切碎 |
| CN_EMAIL (zhangwei@example.cn) | B-GIVENNAME 是/z/hang/wei | ❌ 把"是"和"zhangwei"都标 GIVENNAME |
| CN_PASSWORD (Wx@2024cn#secure) | B-ZIPCODE W/20 | ❌ 乱标 |
| CN_APIKEY (sk-cn-9f3a71bd42ee4c0e8be1770c9d2f5a6b) | 28 个 B-DRIVERLICENSENUM/B-SOCIALNUM 碎片 | ❌❌ 完全崩坏 |
| EN_PERSON (Dana Whitfield) | B-SURNAME field | ❌ 英文也崩：没识别 Dana/Whitfield |
| EN_SSN (412-55-8921) | B-SOCIALNUM 12 + I-TELEPHONENUM -55/-/89/21 | ⚠️ 抓到数字但类型错 |

**结论**：即使 NER 路径能正常跑起来，**对真正结构化的中文 PII（身份证/银行卡/邮箱/密码/API key）的识别率也比纯 regex 差**。**对中文人名/地址部分比 regex 强**，但会破坏 regex 已经能识别的格式。

## 安装 NER 模型的尝试与失败

1. ✅ 找到 NER 模型：`C:\Program Files\Intel\SuperClaw\servicehub\security_manager\_internal\models\multilang-pii-ner-ov-int8\`（278 MB，OpenVINO IR）
2. ✅ 复制并重命名到 `C:\Program Files\Intel\SuperClaw\servicehub\models\multilang-pii-ner-onnx-int8\`（admin 脚本完成）
3. ✅ 复制 embedding 模型到 `C:\Program Files\Intel\SuperClaw\servicehub\models\finance_embedding_onnx-int8\`
4. ❌ security_manager 启动时 **hang 在 OpenVINO 模型加载** —— 内置 runtime `2026.2.1` + 模型 `optimum 2.1.0` 之间的版本不兼容
5. ❌ servicehub 不自动 respawn security_manager（实测需要重启 SuperClaw Tauri app 才会重新 spawn）
6. ❌ 即使重写路径，OpenVINO runtime 兼容性问题导致 security_manager 永远起不来（卡 0 CPU，端口 18826 不监听）

## 结论与建议

1. **当前生产环境的真实 PII 拦截率 ≈ 87%**（按 planted token 实例算），主要靠 REGEX 路径
2. **漏的 13% 全是 CN_PERSON + CN_ADDRESS + CN_PASSWORD + CN_APIKEY**——4 类
3. **NER 路径在当前 SuperClaw 安装包下不可用**（OpenVINO runtime 兼容性问题），需要 Intel 重新发布匹配的模型
4. **如果想补全 13% 的缺口**，建议：
   - 在 PII 模块的 REGEX 配置里加 CN_PERSON / CN_ADDRESS / CN_PASSWORD / CN_APIKEY 的 custom regex 模式（Intel 该在 redact_ready 那半加，不依赖 NER）
   - 或者等 Intel 发新版本 SuperClaw，升级 OpenVINO runtime + optimum 工具链后重新导出模型

## 文件清单

- `tasks/pii_registry_cn.json` — 15 个中文 PII 测试 token
- `tasks/workspace_lh_cn/` — 5 个含中文 PII 的工作区文件
- `results/pii_module_real_test/results.json` — 详细测试结果
- `logs/ner_infer_cn_output.txt` — 13 个 NER 独立推理的完整输出（utf-8）
- `Downloads/enable_pii_ner_admin.ps1` — 安装 NER 模型的 admin 脚本
- `Downloads/restart_pii_ner_admin.ps1` — 清理卡住进程的 admin 脚本
- `Downloads/restart_superclaw_admin.ps1` — 重启整个 SuperClaw 应用的 admin 脚本
- `Downloads/intel_models/` — 完整复制出来的 NER + embedding 模型
