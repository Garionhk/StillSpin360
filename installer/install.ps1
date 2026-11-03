# StillSpin360 installer
# Sets up the AI engine (ComfyUI) and the MiniMax-H3 models. Either:
#   - installs its own pinned ComfyUI Portable next to StillSpin360.exe, or
#   - uses a ComfyUI already on this PC, reusing the models it has and adding only what is missing.
# The choice is saved in engine.json, which StillSpin360 reads at start-up.
# Safe to re-run: verified files are skipped, broken or partial downloads are resumed or replaced.

param(
    [string]$ComfyUIPath,       # use this existing ComfyUI (portable folder, or the folder with main.py)
    [switch]$NewComfyUI,        # install StillSpin360's own ComfyUI, even if another is configured
    [switch]$AcceptLicense,     # skip the interactive license prompt
    [switch]$SkipOptional,      # don't download optional models (Turbo LoRA)
    [switch]$Rehash,            # re-verify every file even if it was verified before
    [switch]$NoShortcuts        # don't create Desktop / Start Menu shortcuts
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Root       = Split-Path -Parent $PSScriptRoot
$Cfg        = Get-Content (Join-Path $PSScriptRoot 'versions.json') -Raw | ConvertFrom-Json
$StatePath  = Join-Path $Root 'installed.json'
$EnginePath = Join-Path $Root 'engine.json'
$Downloads  = Join-Path $Root 'downloads'
$Portable   = Join-Path $Root 'ComfyUI_windows_portable'

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "    ! $msg" -ForegroundColor Yellow }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }

# ---------------------------------------------------------------- state
# Files inside the project are keyed by their relative path, so the folder can be moved or renamed.
# Files in an existing ComfyUI elsewhere keep their absolute path.
function Get-StateKey($path) {
    $full = [System.IO.Path]::GetFullPath($path)
    if ($full.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) { $full = $full.Substring($Root.Length).TrimStart('\') }
    return $full.ToLower()
}
function Convert-LegacyKey($key) {
    # Older installs stored absolute paths; keep everything from the first project sub-folder on.
    if ($key -notmatch ':\\') { return $key }
    $m = [regex]::Match($key, '\\(comfyui_windows_portable|downloads)\\.*$')
    if ($m.Success) { return $m.Value.TrimStart('\') }
    return $key
}

$State = @{ verified = @{} }
if (Test-Path $StatePath) {
    $raw = Get-Content $StatePath -Raw | ConvertFrom-Json
    if ($raw.verified) { $raw.verified.PSObject.Properties | ForEach-Object { $State.verified[(Convert-LegacyKey $_.Name)] = $_.Value } }
    if ($raw.comfyui_version) { $State.comfyui_version = $raw.comfyui_version }
}
function Save-State {
    $out = [ordered]@{
        app_version     = $Cfg.app_version
        comfyui_version = $State.comfyui_version
        verified        = $State.verified
    }
    $out | ConvertTo-Json -Depth 5 | Set-Content -Path $StatePath -Encoding UTF8
}

# ---------------------------------------------------------------- downloads
function Test-Verified($path, $sha256, $size) {
    if (-not (Test-Path -LiteralPath $path)) { return $false }
    $len = (Get-Item -LiteralPath $path).Length
    if ($size -and $len -ne $size) { return $false }
    $key = Get-StateKey $path
    if (-not $Rehash -and $State.verified[$key] -eq $sha256) { return $true }
    Write-Host "    hashing $(Split-Path $path -Leaf) ..."
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLower()
    if ($actual -eq $sha256) {
        $State.verified[$key] = $sha256
        Save-State
        return $true
    }
    Write-Warn "hash mismatch for $path (got $actual)"
    return $false
}

function Get-VerifiedFile($url, $dest, $sha256, $size) {
    if (Test-Verified $dest $sha256 $size) { Write-Ok "ok  $(Split-Path $dest -Leaf)"; return }
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Force }
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    $part = "$dest.part"
    if ($size -and (Test-Path -LiteralPath $part) -and (Get-Item -LiteralPath $part).Length -gt $size) { Remove-Item -LiteralPath $part -Force }
    if (-not ($size -and (Test-Path -LiteralPath $part) -and (Get-Item -LiteralPath $part).Length -eq $size)) {
        Write-Host "    downloading $(Split-Path $dest -Leaf)$(if ($size) { ' (' + [math]::Round($size / 1GB, 2) + ' GB)' })"
        & curl.exe -L --fail --retry 10 --retry-delay 5 --retry-all-errors -C - -o $part $url
        if ($LASTEXITCODE -ne 0) { throw "download failed ($LASTEXITCODE): $url" }
    }
    Move-Item -LiteralPath $part $dest -Force
    if (-not (Test-Verified $dest $sha256 $size)) {
        Remove-Item -LiteralPath $dest -Force
        throw "verification failed for $dest - re-run the installer to try again"
    }
    Write-Ok "ok  $(Split-Path $dest -Leaf)"
}

# ---------------------------------------------------------------- existing ComfyUI
function ConvertTo-Version($text) {
    # "0.43.0", "v0.38", "0.42.1-rc1" -> [version] with three parts
    $parts = @(($text -replace '^v', '' -replace '[^0-9.].*$', '').Split('.') | Where-Object { $_ -ne '' })
    while ($parts.Count -lt 3) { $parts += '0' }
    return [version]($parts[0..2] -join '.')
}

function Resolve-ExistingComfy($path) {
    # Accepts the portable folder (with run_nvidia_gpu.bat), or the folder that holds main.py.
    $p = $path.Trim().Trim('"').TrimEnd('\')
    if (-not $p -or -not (Test-Path -LiteralPath $p -PathType Container)) { throw "That folder does not exist: $p" }
    $p = (Resolve-Path -LiteralPath $p).Path
    if ((Test-Path -LiteralPath "$p\ComfyUI\main.py") -and (Test-Path -LiteralPath "$p\python_embeded\python.exe")) {
        $comfy = "$p\ComfyUI"; $python = "$p\python_embeded\python.exe"; $portableLayout = $true
    } elseif (Test-Path -LiteralPath "$p\main.py") {
        $comfy = $p
        $parent = Split-Path $p
        if (Test-Path -LiteralPath "$parent\python_embeded\python.exe") { $python = "$parent\python_embeded\python.exe"; $portableLayout = $true }
        elseif (Test-Path -LiteralPath "$p\venv\Scripts\python.exe")    { $python = "$p\venv\Scripts\python.exe";    $portableLayout = $false }
        elseif (Test-Path -LiteralPath "$p\.venv\Scripts\python.exe")   { $python = "$p\.venv\Scripts\python.exe";   $portableLayout = $false }
        else { throw "Found ComfyUI in $p, but not its Python (no python_embeded, venv or .venv folder)." }
    } else {
        throw "No ComfyUI found in $p. Choose the folder that contains run_nvidia_gpu.bat (portable) or main.py."
    }
    $version = '0.0.0'
    $vf = "$comfy\comfyui_version.py"
    if (Test-Path -LiteralPath $vf) {
        $m = Select-String -LiteralPath $vf -Pattern '__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
        if ($m) { $version = $m.Matches[0].Groups[1].Value }
    }
    if ((ConvertTo-Version $version) -lt (ConvertTo-Version $Cfg.comfyui.min_existing_version)) {
        throw ("Your ComfyUI is v$version; StillSpin360 needs v$($Cfg.comfyui.min_existing_version) or newer. " +
               "Update it (update\update_comfyui.bat in a portable install), or press Enter at the question to install a new copy.")
    }
    return [pscustomobject]@{ ComfyDir = $comfy; Python = $python; Portable = $portableLayout; Version = $version }
}

function Find-ExistingModel($model, $modelsDir) {
    # A compatible file anywhere under the role's folders (ComfyUI users often sort models into subfolders),
    # matched by name and exact size. Returns the file and the name ComfyUI lists it under.
    $candidates = @([pscustomobject]@{ file = (Split-Path $model.dest -Leaf); sha256 = $model.sha256; size = $model.size }) + @($model.alternatives)
    foreach ($c in $candidates) {
        foreach ($folder in $Cfg.model_folders.($model.role)) {
            $base = Join-Path $modelsDir $folder
            if (-not (Test-Path -LiteralPath $base)) { continue }
            $hit = Get-ChildItem -LiteralPath $base -Recurse -File -Filter $c.file -ErrorAction SilentlyContinue |
                   Where-Object { $_.Length -eq $c.size } | Select-Object -First 1
            if (-not $hit) { continue }
            if ($Rehash -and -not (Test-Verified $hit.FullName $c.sha256 $c.size)) { continue }
            return [pscustomobject]@{ Path = $hit.FullName; Name = $hit.FullName.Substring($base.Length + 1) }
        }
    }
    return $null
}

# ---------------------------------------------------------------- 1. system checks
Write-Step "Checking system"
try {
    $gpus = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
    foreach ($g in $gpus) {
        $p = $g.Split(',') | ForEach-Object { $_.Trim() }
        Write-Host "    GPU: $($p[0])  VRAM: $([math]::Round([double]$p[1] / 1024, 1)) GB  driver: $($p[2])"
        if ([double]$p[1] -lt 11500) { Write-Warn "less than 12 GB VRAM - generation will be very slow or fail" }
    }
} catch {
    Write-Warn "nvidia-smi not found - an NVIDIA GPU with a recent driver is required"
}

$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Write-Host "    RAM: $ramGB GB"
$pageMB = (Get-CimInstance Win32_PageFileUsage | Measure-Object AllocatedBaseSize -Sum).Sum
Write-Host "    Pagefile: $([math]::Round($pageMB / 1024)) GB"
if ($ramGB -lt 48 -and $pageMB -lt 32768) {
    Write-Warn "With $ramGB GB RAM, set a pagefile of at least 32 GB (System > Advanced > Performance > Virtual memory)."
    Write-Warn "The 32B text encoder and the video model are swapped through system memory."
}

# ---------------------------------------------------------------- 2. license
Write-Step "License"
if (-not $AcceptLicense -and -not $State.verified['license']) {
    Write-Host "    The models are released under the $($Cfg.license.name)."
    Write-Host "    Read it here: $($Cfg.license.url)"
    $answer = Read-Host "    Type YES to accept and continue"
    if ($answer -ne 'YES') { throw "License not accepted - nothing was downloaded." }
}
$State.verified['license'] = $Cfg.license.name
Save-State
Write-Ok "accepted"

# ---------------------------------------------------------------- 3. which ComfyUI
Write-Step "AI engine (ComfyUI)"
$saved = $null
if (Test-Path $EnginePath) { $saved = Get-Content $EnginePath -Raw | ConvertFrom-Json }
$bundledInstalled = (Test-Path (Join-Path $Portable 'ComfyUI\main.py')) -and $State.comfyui_version

function Ask($prompt) { return Read-Host $prompt }   # one place for input, so the menu can be tested

function Select-Engine($saved, $bundledInstalled) {
    # Returns $null for StillSpin360's own copy, or the resolved existing ComfyUI.
    $savedPath = $null
    if ($saved -and $saved.kind -eq 'existing') {
        $savedPath = $(if ($saved.portable) { Split-Path $saved.comfy_dir } else { $saved.comfy_dir })
    }
    $default = $(if ($savedPath) { '2' } else { '1' })
    $own = $(if ($bundledInstalled) { "Keep StillSpin360's own copy".PadRight(38) + "(already installed)" }
             else { "Install a new copy for StillSpin360".PadRight(38) + "(about 36 GB download, ~45 GB disk)" })
    $mine = "Use a ComfyUI I already have".PadRight(38) + "(reuses its models; usually about 2 GB download)"
    while ($true) {
        Write-Host ""
        Write-Host "    Which ComfyUI should StillSpin360 use?"
        Write-Host ""
        Write-Host "      1) $own"
        Write-Host "      2) $mine"
        Write-Host ""
        if ($savedPath) { Write-Host "    Currently: your ComfyUI at $savedPath" }
        elseif ($bundledInstalled) { Write-Host "    Currently: StillSpin360's own copy" }
        $choice = (Ask "    Choose 1 or 2 [Enter = $default]").Trim()
        if (-not $choice) { $choice = $default }

        if ($choice -eq '1') {
            if ($savedPath -and -not $bundledInstalled) {
                Write-Warn "Switching to StillSpin360's own copy - this downloads ComfyUI and the models (about 36 GB)."
                Write-Warn "Your ComfyUI is left as it is."
            }
            return $null
        }
        if ($choice -ne '2') { Write-Warn "Please type 1 or 2."; continue }

        Write-Host ""
        Write-Host "    Choose the folder that contains run_nvidia_gpu.bat (portable ComfyUI),"
        Write-Host "    or the folder with main.py (manual install with a venv)."
        Write-Host "    Only missing model files are added to it - nothing else in your ComfyUI is changed."
        while ($true) {
            $hint = $(if ($savedPath) { "Enter = $savedPath, B = back" } else { "Enter = back" })
            $answer = (Ask "    Path of your ComfyUI folder [$hint]").Trim()
            if ($answer -eq 'b' -or $answer -eq 'B' -or (-not $answer -and -not $savedPath)) { break }
            if (-not $answer) { $answer = $savedPath }
            try {
                $found = Resolve-ExistingComfy $answer
                if ($bundledInstalled) {
                    Write-Host "    StillSpin360's own copy in ComfyUI_windows_portable will no longer be used."
                    Write-Host "    You can delete that folder later to free disk space."
                }
                return $found
            } catch { Write-Warn $_.Exception.Message }
        }
    }
}

$Existing = $null
if ($NewComfyUI) {
    Write-Ok "using StillSpin360's own copy (-NewComfyUI)"
} elseif ($ComfyUIPath) {
    $Existing = Resolve-ExistingComfy $ComfyUIPath
} else {
    $Existing = Select-Engine $saved $bundledInstalled
}

if ($Existing) {
    $ComfyDir  = $Existing.ComfyDir
    $ModelsDir = Join-Path $ComfyDir 'models'
    Write-Ok "using your ComfyUI v$($Existing.Version): $ComfyDir"
    if (-not $Existing.Portable) { Write-Ok "Python: $($Existing.Python)" }
} else {
    $ComfyDir  = Join-Path $Portable 'ComfyUI'
    $ModelsDir = Join-Path $ComfyDir 'models'
}

# ---------------------------------------------------------------- 4. plan the models
Write-Step "Models"
$plan = @()
foreach ($m in $Cfg.models) {
    if (-not $m.required -and $SkipOptional) { Write-Host "    skip $($m.name) (optional)"; continue }
    $found = if ($Existing) { Find-ExistingModel $m $ModelsDir } else { $null }
    if ($found) { Write-Ok "found  $($m.name): $($found.Name)" }
    $plan += [pscustomobject]@{ Model = $m; Found = $found }
}
$needBytes = ($plan | Where-Object { -not $_.Found } | ForEach-Object { $_.Model.size } | Measure-Object -Sum).Sum
if (-not $Existing -and -not $bundledInstalled) { $needBytes += 8GB }   # portable build + archive while extracting
$drive = (Get-Item -LiteralPath $(if ($Existing) { $ComfyDir } else { $Root })).PSDrive
Write-Host "    Free on $($drive.Name): $([math]::Round($drive.Free / 1GB)) GB (this install needs up to $([math]::Round($needBytes / 1GB, 1)) GB)"
if ($drive.Free -lt $needBytes) { throw "Not enough disk space on drive $($drive.Name):" }

# ---------------------------------------------------------------- 5. StillSpin360's own ComfyUI Portable (pinned)
if (-not $Existing) {
    Write-Step "ComfyUI Portable v$($Cfg.comfyui.version)"
    $Python = Join-Path $Portable 'python_embeded\python.exe'
    if ($bundledInstalled) {
        if ($State.comfyui_version -ne $Cfg.comfyui.version) {
            throw ("ComfyUI v$($State.comfyui_version) is installed but this release pins v$($Cfg.comfyui.version). " +
                   "Move your models out of $ModelsDir, delete $Portable and re-run the installer.")
        }
        Write-Ok "already installed"
    } else {
        if (Test-Path $Portable) {
            throw "$Portable exists but was not installed by this installer. Remove or rename it and re-run."
        }
        $sevenZip = Join-Path $Downloads '7zr.exe'
        Get-VerifiedFile $Cfg.sevenzip.url $sevenZip $Cfg.sevenzip.sha256 $null
        $archive = Join-Path $Downloads 'ComfyUI_windows_portable_nvidia.7z'
        Get-VerifiedFile $Cfg.comfyui.url $archive $Cfg.comfyui.sha256 $Cfg.comfyui.size
        Write-Host "    extracting ..."
        & $sevenZip x $archive "-o$Root" -y | Out-Null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $ComfyDir 'main.py'))) { throw "extraction failed" }
        $State.comfyui_version = $Cfg.comfyui.version
        $State.verified.Remove((Get-StateKey $archive))
        Save-State
        Remove-Item $archive -Force
        Write-Ok "installed"
    }

    Write-Step "Custom nodes"
    if (-not $Cfg.custom_nodes -or $Cfg.custom_nodes.Count -eq 0) {
        Write-Ok "none required (core ComfyUI nodes only)"
    }
    foreach ($node in $Cfg.custom_nodes) {
        $dir = Join-Path $ComfyDir "custom_nodes\$($node.name)"
        if (-not (Test-Path $dir)) { & git clone $node.repo $dir; if ($LASTEXITCODE -ne 0) { throw "git clone failed: $($node.repo)" } }
        & git -C $dir fetch --quiet origin
        & git -C $dir checkout --quiet $node.commit
        if ($LASTEXITCODE -ne 0) { throw "could not check out $($node.name) at $($node.commit)" }
        $req = Join-Path $dir 'requirements.txt'
        if (Test-Path $req) { & $Python -s -m pip install --no-warn-script-location -r $req }
        Write-Ok "$($node.name) @ $($node.commit.Substring(0, 8))"
    }

    # Only needed to run the source (run.bat). A release has StillSpin360.exe, which carries its own GUI libraries.
    Write-Step "GUI packages"
    if (Test-Path (Join-Path $Root 'app\main.py')) {
        & $Python -s -m pip install --disable-pip-version-check --no-warn-script-location @($Cfg.python_packages)
        if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
        Write-Ok "installed"
    } else {
        Write-Ok "not needed (StillSpin360.exe includes them)"
    }
}

# ---------------------------------------------------------------- 6. download what is missing
Write-Step "Downloading models"
$names = [ordered]@{}
foreach ($role in @($Cfg.models | ForEach-Object { $_.role })) { $names[$role] = $null }
foreach ($item in $plan) {
    $m = $item.Model
    if ($item.Found) { $names[$m.role] = $item.Found.Name; continue }
    Write-Host "  - $($m.name)"
    Get-VerifiedFile $m.url (Join-Path $ModelsDir $m.dest) $m.sha256 $m.size
    $names[$m.role] = Split-Path $m.dest -Leaf
}
if (-not ($plan | Where-Object { -not $_.Found })) { Write-Ok "nothing to download - every model was already there" }

# ---------------------------------------------------------------- 7. engine.json
$engine = [ordered]@{
    kind      = $(if ($Existing) { 'existing' } else { 'bundled' })
    comfy_dir = $ComfyDir
    python    = $(if ($Existing) { $Existing.Python } else { Join-Path $Portable 'python_embeded\python.exe' })
    portable  = $(if ($Existing) { $Existing.Portable } else { $true })
    port      = $(if ($Existing) { $Cfg.ports.existing } else { $Cfg.ports.bundled })
    models    = $names
}
$engine | ConvertTo-Json -Depth 4 | Set-Content -Path $EnginePath -Encoding UTF8
Write-Ok "saved engine.json ($($engine.kind) ComfyUI, port $($engine.port))"

# ---------------------------------------------------------------- 8. shortcuts
if (-not $NoShortcuts) {
    Write-Step "Shortcuts"
    $shell = New-Object -ComObject WScript.Shell
    $targets = @(
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'StillSpin360.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Programs')) 'StillSpin360.lnk')
    )
    # Prefer the windowed exe (no console at all); fall back to run.bat if it hasn't been built.
    $exe = Join-Path $Root 'StillSpin360.exe'
    foreach ($lnk in $targets) {
        $s = $shell.CreateShortcut($lnk)
        $s.WorkingDirectory = $Root
        $s.Description      = 'StillSpin360 - photo to frozen-time 360 orbit'
        if (Test-Path $exe) {
            $s.TargetPath   = $exe
            $s.IconLocation = "$exe,0"
            $s.WindowStyle  = 1
        } else {
            $s.TargetPath   = Join-Path $Root 'run.bat'
            $s.IconLocation = (Join-Path $Root 'app\assets\icons\stillspin360.ico') + ',0'
            $s.WindowStyle  = 7   # start the console minimized; the GUI is the real window
        }
        $s.Save()
        Write-Ok $lnk
    }
}

Save-State
Write-Step "Done. Start StillSpin360 from the desktop shortcut or StillSpin360.exe"
