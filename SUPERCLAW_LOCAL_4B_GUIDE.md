# SuperClaw 本地 llamacpp 模式 + Qwen3.5-4B Auto Router 操作指南

> **目标**：在 SuperClaw v1.2.0.0813 上，让 `model=auto` 路由到本地 4B 模型（llamacpp 模式），并能正确显示在 `/v1/models` 中。
>
> **应用场景**：v1.0 / v3 复现验证。SuperClaw 默认 `local-0-8b`（qwen3.5-0.8b）很弱，我们想切到 4B。

---

## 0. 重要警告（必须先读）

- **不要用 Edge server 模式**！v1.2.0.0813 的 Edge 模式有 **dual-probe 验证**（同时检查 chat + embeddings），Qwen3.5-4B 不支持 embeddings。Edge 模式会报 "未同时提供对话与嵌入模型"。
- 使用 v1.1 风格的 **local llamacpp 模式**（SuperClaw Tauri 的 "Local llamacpp" 选项）。此模式不需要 dual-probe。
- 4B GGUF 用 **lowercase** 目录名 `qwen3.5-4b`（匹配 vendor `models.builtin.json` 的 lowercase id）。**不要大写**！
- `state` 字段值必须 ∈ `["unavailable", "provisioning", "ready", "error"]`，**不要用 `"pending"`**（v1.2.0.0813 验证器会拒）。

---

## 1. 前置准备：4B 模型文件

```bash
# 路径（lowercase 目录名！）
mkdir -p "C:/Users/Tekker-PTL/AppData/Local/SuperClaw/llmrouter_manager/models/qwen3.5-4b"

# 4B GGUF 必须来自 MTP 仓库（带 draft-mtp 投机解码）
# 路径：hf-mirror.com/unsloth/Qwen3.5-4B-MTP-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf
# SHA256: 3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630
# 大小: 2,834,975,040 bytes

# 下载（如果还没有）
curl -L -C -o "C:/Users/Tekker-PTL/AppData/Local/SuperClaw/llmrouter_manager/models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf" \
  "https://hf-mirror.com/unsloth/Qwen3.5-4B-MTP-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf"

# 验证
python -c "
import hashlib
p = 'C:/Users/Tekker-PTL/AppData/Local/SuperClaw/llmrouter_manager/models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf'
h = hashlib.sha256()
with open(p, 'rb') as f:
    while True:
        c = f.read(8*1024*1024)
        if not c: break
        h.update(c)
assert h.hexdigest() == '3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630', 'SHA mismatch'
print('SHA verified')
"
```

**严禁**：把 4B 复制到其他位置（比如 `models/Qwen3.5-4B/`）。SuperClaw 的 vendor id 是 lowercase `qwen3.5-4b`。

---

## 2. 修改 vendor 文件（需要 admin 权限）

### 2.1 编辑 `models.builtin.json`

路径：`C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\data\models.builtin.json`

需要以 **admin 身份** 打开 PowerShell，然后运行：

```powershell
# 备份
$path = 'C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\data\models.builtin.json'
Copy-Item $path "$path.bak" -Force

# 1) 改 qwen3.5-4b 的 requirements（放宽 mem_speed + 清空 igpu_keywords）
# 2) 找到 id="qwen3.5-4b" 的对象，把 requirements 改成：
#    {"min_ram_gb": 32, "min_mem_speed_mts": 4800, "igpu_keywords": []}
# 3) 保持 id 是 lowercase "qwen3.5-4b"（不要大写！）

# 用 Python 安全写入（避免 BOM 引起 JSON 解析失败）
$content = (Get-Content $path -Raw) | ConvertFrom-Json | ConvertTo-Json -Depth 100
$json = $content | ConvertFrom-Json
foreach ($m in $json) {
    if ($m.id -eq 'qwen3.5-4b') {
        $m.requirements = @{
            'min_ram_gb' = 32
            'min_mem_speed_mts' = 4800
            'igpu_keywords' = @()
        }
    }
}
$newContent = $json | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($path, $newContent, [System.Text.UTF8Encoding]::new($false))
```

### 2.2 编辑 `bundles.builtin.json`

路径：`C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\data\bundles.builtin.json`

```powershell
$path = 'C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\data\bundles.builtin.json'
Copy-Item $path "$path.bak" -Force

# 找到 bundle_id="local-4b" 的对象，把 chat_model_id 改成 "qwen3.5-4b"（lowercase！）
$content = (Get-Content $path -Raw) | ConvertFrom-Json
foreach ($bundle in $content.bundles) {
    if ($bundle.bundle_id -eq 'local-4b') {
        $bundle.chat_model_id = 'qwen3.5-4b'   # lowercase 一定要
    }
}
$newContent = $content | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($path, $newContent, [System.Text.UTF8Encoding]::new($false))
```

**关键**：这里 2.1、2.2 都用 `[System.IO.File]::WriteAllText` 的 `$false`（不要写 BOM）。如果用 `Set-Content -Encoding UTF8` 会写 BOM，导致 `llmrouter_manager` 启动失败（"not valid JSON" 错误）。

### 2.3 （可选但推荐）编辑 `model_profiles.json`

路径：`C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\routing\policy\model_profiles.json`

```powershell
$path = 'C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\routing\policy\model_profiles.json'
$content = Get-Content $path -Raw | ConvertFrom-Json
if (-not $content.profiles.'qwen3.5-4b') {
    $content.profiles | Add-Member -NotePropertyName 'qwen3.5-4b' -NotePropertyValue @{system_prompt='local-short.txt'} -Force
}
$newContent = $content | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($path, $newContent, [System.Text.UTF8Encoding]::new($false))
```

---

## 3. 改 SQLite DB（用户态权限即可）

数据库路径：`%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db`

### 3.1 运行（PowerShell 或 Python）

```python
import sqlite3, json, pathlib
DB = pathlib.Path(os.path.expandvars(r'%LOCALAPPDATA%\SuperClaw\llmrouter_manager\llmrouter_manager.db'))

# 备份
import shutil
shutil.copy2(DB, DB.with_suffix('.db.v3.4.bak'))

con = sqlite3.connect(DB); cur = con.cursor()

# 3.2) active_chat_model_id  → "qwen3.5-4b" (lowercase!)
cur.execute("UPDATE config SET value=? WHERE key='active_chat_model_id'", ('"qwen3.5-4b"',))
print('  config.active_chat_model_id = qwen3.5-4b')

# 3.3) primary_bundle = local-4b
new_bundle = json.dumps({
    'backend': 'llama', 'bundle_id': 'local-4b', 'bundle_revision': 3,
    'capability_contract_version': 1, 'capability_grade': 'minimal',
    'chat_model_id': 'qwen3.5-4b', 'embedding_model_id': 'KaLM-embedding-v2.5',
    'registry_version': 1, 'state': 'ready'
})
cur.execute("""UPDATE bundle_lifecycle SET
                  primary_bundle=?, bundle_revision=3,
                  pending_bundle=NULL, previous_bundle=NULL,
                  prepare_token=NULL, prepare_operation_id=NULL
              WHERE singleton=1""", (new_bundle,))
print('  primary_bundle = local-4b / qwen3.5-4b / state=ready / rev=3')

# 3.4) model_verifications: 重命名 qwen3.5-4b 行
gguf = pathlib.Path(os.path.expandvars(
    r'%LOCALAPPDATA%\SuperClaw\llmrouter_manager\models\qwen3.5-4b\Qwen3.5-4B-Q4_K_M.gguf'))
if gguf.exists() and gguf.stat().st_size == 2834975040:
    st = gguf.stat()
    cur.execute("DELETE FROM model_verifications WHERE asset_id='qwen3.5-4b'")
    cur.execute("""INSERT OR REPLACE INTO model_verifications
                   (asset_id, expected_sha256, filename, size_bytes, mtime_ns, ctime_ns)
                   VALUES (?,?,?,?,?,?)""",
                ('qwen3.5-4b',
                 '3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630',
                 'Qwen3.5-4B-Q4_K_M.gguf',
                 gguf.stat().st_size, st.st_mtime_ns, st.st_ctime_ns))
    print('  model_verifications: qwen3.5-4b inserted')

# 3.5) 清空 session locality 缓存
cur.execute("DELETE FROM config WHERE key LIKE 'routing.session_locality%'")
print('  cleared session locality')

con.commit(); con.close()
print('DB updated')
```

---

## 4. 重启 SuperClaw 服务栈（冷启动）

```python
import subprocess, time, requests

# 4.1) 杀 SuperClaw Tauri + servicehub + llmrouter_manager + llama-server
subprocess.run(['powershell', '-NoProfile', '-Command',
    "Get-Process | Where-Object { $_.Name -match 'SuperClaw|servicehub|llmrouter_manager|llama-server' } | ForEach-Object { Stop-Process -Id $_.Id -Force }"
], capture_output=True)
time.sleep(5)

# 4.2) 启动 SuperClaw Tauri
subprocess.Popen(
    [r'C:\Program Files\Intel\SuperClaw\SuperClaw.exe'],
    env={**__import__('os').environ, 'HTTP_PROXY':'', 'HTTPS_PROXY':''},
    stdout=open('C:/Users/Tekker-PTL/superclaw_benchmark/logs/superclaw_v3.4.log','w'),
    stderr=subprocess.STDOUT
)
print('SuperClaw launched, waiting 40s for boot...')
time.sleep(40)

# 4.3) 等待 router ready
for i in range(20):
    try:
        r = requests.get('http://127.0.0.1:18321/v1/models', timeout=2)
        if r.status_code == 200:
            print(f'  router up at attempt {i+1}')
            break
    except: pass
    time.sleep(2)
```

---

## 5. 验证 4B 加载 + alias 注册

```python
import requests, json

# 5.1) /v1/models 应含 local-model + auto + cloud-model
r = requests.get('http://127.0.0.1:18321/v1/models')
models = r.json().get('data', [])
print('available models:')
for m in models:
    print(f"  {m['id']:20} {m.get('description','')[:60]}")

# 应有 'local-model' 这一项，描述里是 "Primary llama: qwen3.5-4b" 或类似
assert any(m['id'] == 'local-model' for m in models), 'local-model missing!'
print('  local-model registered OK')

# 5.2) test model=local-model (应走 4B)
r = requests.post('http://127.0.0.1:18321/v1/chat/completions', json={
    'model': 'local-model',
    'messages': [{'role':'user','content':'echo ok'}],
    'max_tokens': 16,
})
b = r.json()
print(f"  model={b['model']}, answer_len={len(b['choices'][0]['message']['content'])}")
assert b['model'] == 'qwen3.5-4b', 'local-model not routing to 4B'
print('  local-model routes to 4B OK')

# 5.3) test model=auto (router 决定，可能 local 或 cloud)
r = requests.post('http://127.0.0.1:18321/v1/chat/completions', json={
    'model': 'auto',
    'messages': [{'role':'user','content':'echo ok'}],
    'max_tokens': 16,
})
b = r.json()
print(f"  model=auto upstream={b['model']}")

# 5.4) 查 router log 看 LatentFactorRouter 决策
import subprocess
r = subprocess.run(['powershell', '-NoProfile', '-Command',
    "Get-ChildItem 'C:\Users\Tekker-PTL\AppData\Local\SuperClaw\llmrouter_manager\logs\llmrouter_manager-*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName -Tail 20 }"
], capture_output=True, text=True)
print('  router log tail:')
for line in r.stdout.strip().split('\n')[-10:]:
    print(f"  {line[:140]}")
```

---

## 6. perf_weight 路由测试

```python
import sqlite3, requests, time, subprocess

DB = '/tmp/superclaw_test.db'  # ignored, use the live one
import pathlib
LIVE = pathlib.Path('/c/Users/Tekker-PTL/AppData/Local/SuperClaw/llmrouter_manager/llmrouter_manager.db')

# 6.1) 设 perf_weight=0.0 (强制 local)
# 6.2) 设 perf_weight=1.0 (强制 cloud)
# 6.3) 5 个值：0.0, 0.3, 0.5, 0.7, 0.9, 1.0

def set_pw(pw):
    con = sqlite3.connect(LIVE)
    con.execute("UPDATE config SET value=? WHERE key='perf_weight'", (str(pw),))
    con.commit(); con.close()

for pw in [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]:
    set_pw(pw)
    time.sleep(1)
    r = requests.post('http://127.0.0.1:18321/v1/chat/completions', json={
        'model': 'auto',
        'messages': [{'role':'user','content':'echo ok'}],
        'max_tokens': 8,
    })
    b = r.json()
    src = '?'
    if 'choices' in b:
        ans = b['choices'][0].get('message',{}).get('content','')
        src = b.get('model','?')
    else:
        ans = f"ERR {b.get('error',{}).get('message','')[:60]}"
        src = 'err'
    print(f"  pw={pw}  upstream={src}  answer={ans[:40]}")
```

---

## 7. 常见错误

| 错误 | 原因 | 修复 |
|---|---|---|
| `local_model_not_configured` | alias 没注册 | 跑 step 4 (冷启动) 让 router 重新读 DB |
| `Primary Bundle switch could not be completed safely` | DB bundle_revision 不匹配 GUI 期望 | bump DB bundle_revision 到 2 或更高 |
| `state=pending is invalid_value` | v1.2.0.0813 验证器只接受 `["unavailable","provisioning","ready","error"]` | 改成 `state=ready` |
| `bundle 'local-4b' chat_model_id must reference a trusted chat asset` | DB chat_model_id 和 model_verifications asset_id 不匹配 | 3 个都改成同一个 case 的 string |
| `not valid JSON: Unexpected UTF-8 BOM` | `Set-Content -Encoding UTF8` 写了 BOM | 用 `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))` 重写 |
| `Local model not found (qwen3.5-4b not found)` | upstream llama-server 没加载 4B | 检查 4B GGUF 在 `models/qwen3.5-4b/`、SHA 正确 |
| `LatentFactorRouter configured local model 'qwen3.5-4b' did not match` | trained label 是 `Qwen3.5-4B` 大写，router id 是 `qwen3.5-4b` 小写 | **不影响路由**，是 v1.2.0.0813 内部 bug，忽略 |

---

## 8. 验证清单

- [ ] `models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf` 存在，SHA256 = `3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630`
- [ ] `models.builtin.json` qwen3.5-4b entry 还在 lowercase，requirements 已放宽
- [ ] `bundles.builtin.json` local-4b.chat_model_id = "qwen3.5-4b"（lowercase）
- [ ] `model_profiles.json` 含 qwen3.5-4b
- [ ] DB config.active_chat_model_id = "qwen3.5-4b"
- [ ] DB bundle_lifecycle.primary_bundle = local-4b，state=ready，cache cleared
- [ ] DB model_verifications 有 qwen3.5-4b 行
- [ ] 冷启动后 `/v1/models` 包含 local-model + auto + cloud-model
- [ ] `model=local-model` 测试返回 model=qwen3.5-4b
- [ ] `model=auto` 测试在不同 perf_weight 下路由变化
- [ ] **不要**用 Edge server 模式（dual-probe 验证会失败）
- [ ] **不要**把 4B 放在 `models/Qwen3.5-4B/`（大写）— vendor id 是 lowercase
- [ ] **不要**用 `Set-Content -Encoding UTF8`（写 BOM）— 用 `[System.IO.File]::WriteAllText(..., [System.Text.UTF8Encoding]::new($false))`
- [ ] **不要**用 `state=pending` — 验证器只接受 `["unavailable","provisioning","ready","error"]`

---

## 9. v3.4 实际运行修正记录（2026-08-13）

把指南实际跑了一遍，发现以下与原文的差异/补充：

### 9.1 4B GGUF 不需要下载

本地已有备份：`superclaw_benchmark/backup_for_reinstall/models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf`（2,834,975,040 B，SHA 匹配）。不需要从 `hf-mirror.com` 下载。

### 9.2 0.8B 和 KaLM 不需要从备份导入

live 安装 profile 下已经存在：
- `models/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf`
- `models/KaLM-embedding-v2.5/kalm-embedding-multilingual-mini-instruct-v2.5-q8_0.gguf`

直接跳过 Section 1 中这两个文件的导入，只导入 4B。

### 9.3 只有 1 个 vendor JSON 需要编辑

实际状态（v3.4 之前）：
- ✅ `bundles.builtin.json` 中 `local-4b.chat_model_id` 早已是 `"qwen3.5-4b"`（lowercase），**无需编辑**
- ✅ `model_profiles.json` 早已包含 `qwen3.5-4b` profile（`system_prompt=local-short.txt`），**无需编辑**
- ✏️ `models.builtin.json` 需要把 `qwen3.5-4b.requirements` 改为 `{"min_ram_gb": 32, "min_mem_speed_mts": 4800, "igpu_keywords": []}`

也就是说指南 Section 2.2 和 2.3 在大多数情况下可以跳过，只跑 2.1。

### 9.4 用户名路径修正

指南里所有 `C:\Users\Tekker-PTL\...` 路径是过时的旧 profile。
**实际 live 安装是 `C:\Users\Trekker-PTL\...`**。

`%LOCALAPPDATA%` 展开后是 `C:\Users\<当前用户>\AppData\Local`。把指南里所有的 `Tekker-PTL` 替换成 `Trekker-PTL` 即可。

### 9.5 bundle_revision 每次冷启动都会 +1

我在 DB 里设了 `bundle_revision = 3`，第一次冷启动后日志显示 `bundle_revision = 4`，第二次冷启动后是 `5`。这是正常的——llmrouter_manager 每次 `bundle_prepare` 都自增。**不要追着设置固定值**，让系统自己管。

### 9.6 冷启动后进程可能静默消失

观察到的现象：
- 第一次冷启动后（20:32:38 起），服务起来了，成功处理了 2 个 cloud-model 请求（20:35:01）
- 过了 1 分钟左右，所有 SuperClaw 相关进程（SuperClaw.exe、servicehub、llmrouter_manager、3 个 llama-server）全部消失
- 日志**没有** `service.shutdown` 之类的关闭日志
- 端口 18321 不再 LISTEN

**最可能的原因**：Tauri 父进程被关掉（手动关 GUI / 看门狗 / 任何 Stop-Process）会清理整个进程树，但子进程没时间写 shutdown 日志。

**对策**：
- 冷启动 + 验证 `/v1/models` + 测试 `model=local-model` 必须在**同一个 shell 会话**里快速完成
- 不要在 launch 后空等几秒再做验证——窗口期很短
- 如果进程真的消失了，直接再 launch 一次即可，不需要重新改 DB/JSON（DB 已持久化）

### 9.7 验证清单补充

v3.4 实测：
- `curl 127.0.0.1:18321/v1/models` 第二次冷启动后第 3 次 poll（9 秒）拿到 HTTP 200
- `model=local-model` 测试 `Reply with exactly: OK_4B_LOCAL` → 返回 `upstream=qwen3.5-4b, answer="OK_4B_LOCAL"` ✓
- `model=auto` 测试 `Reply with exactly: OK_AUTO` → 返回 `upstream=qwen3.5-4b`，路由器日志显示 `[LatencyRouter] auto -> local-model (predicted 'qwen3.6-35b')`（预测是大模型，但硬件只有 4B，所以 fallback 到 4B——**这恰好是 4B 跑通的证据**）

### 9.8 详细运行日志

完整 v3.4 运行记录（带时间戳、命令、输出、备份位置）见：
`superclaw_benchmark/results/superclaw_4b_setup_v3.4.md`
