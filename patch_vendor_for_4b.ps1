# patch_vendor_for_4b.ps1
# ONE-SHOT admin patch: relax qwen3.5-4b requirements in SuperClaw vendor file.
# Run from an elevated PowerShell:
#   PS> Start-Process pwsh -Verb RunAs -ArgumentList '-NoProfile','-File','C:\Users\Trekker-PTL\superclaw_benchmark\patch_vendor_for_4b.ps1'
# Or right-click pwsh → Run as administrator → run this file.

$ErrorActionPreference = 'Stop'

$path = 'C:\Program Files\Intel\SuperClaw\servicehub\llmrouter_manager\_internal\llmrouter_manager\data\models.builtin.json'

if (-not (Test-Path $path)) { throw "vendor file not found: $path" }

# 1) Backup (no-op if already exists)
$bak = "$path.v3.4.bak"
if (-not (Test-Path $bak)) {
  Copy-Item $path $bak -Force
  Write-Host "[OK] backup -> $bak"
} else {
  Write-Host "[skip] backup already exists: $bak"
}

# 2) Read current
$raw = [System.IO.File]::ReadAllText($path)
$json = $raw | ConvertFrom-Json

# 3) Patch qwen3.5-4b requirements
$changed = $false
foreach ($m in $json.models) {
  if ($m.id -eq 'qwen3.5-4b') {
    $cur = $m.requirements
    Write-Host "[before] mem_speed=$($cur.min_mem_speed_mts), igpu=$($cur.igpu_keywords -join ',')"
    if ($cur.min_mem_speed_mts -ne 4800) { $cur.min_mem_speed_mts = 4800; $changed = $true }
    if ($cur.igpu_keywords.Count -ne 0)  { $cur.igpu_keywords = @();  $changed = $true }
    Write-Host "[after]  mem_speed=$($cur.min_mem_speed_mts), igpu=$($cur.igpu_keywords -join ',')"
  }
}
if (-not $changed) { Write-Host "[skip] requirements already relaxed" }

# 4) Write back WITHOUT BOM (BOM breaks JSON parser on next boot)
if ($changed) {
  $newContent = $json | ConvertTo-Json -Depth 100
  [System.IO.File]::WriteAllText($path, $newContent, [System.Text.UTF8Encoding]::new($false))
  Write-Host "[OK] written (no BOM)"
}

# 5) Verify
$bytes = [System.IO.File]::ReadAllBytes($path)
$bom = ($bytes.Length -ge 3) -and ($bytes[0] -eq 0xEF) -and ($bytes[1] -eq 0xBB) -and ($bytes[2] -eq 0xBF)
Write-Host "[verify] BOM: $bom  (must be False)"

$recheck = [System.IO.File]::ReadAllText($path) | ConvertFrom-Json
foreach ($m in $recheck.models) {
  if ($m.id -eq 'qwen3.5-4b') {
    Write-Host "[verify] 4B requirements = $($m.requirements | ConvertTo-Json -Compress)"
  }
}
Write-Host "DONE"
