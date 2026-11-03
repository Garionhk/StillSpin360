# StillSpin360

**English** · [繁體中文](README.zh-Hant.md)

Turn a single photo into a frozen-time **360° orbit**: the camera circles the subject while everything stays still. You can then export it as a looping MP4, a GIF, or an interactive HTML viewer you can spin by hand.

It runs locally on top of a version-locked **ComfyUI Portable**, using:
- **MiniMax-H3 FL2VA** (pruned w6a8 build)
- the [360 Orbit LoRA by pablodawson](https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA)

The same photo goes in as both the first and the last keyframe, so the orbit ends exactly where it started and loops seamlessly.

## Requirements
- Windows 10/11 and an NVIDIA GPU with **12–16 GB VRAM** and a current driver.
- **32 GB RAM minimum.** With 32 GB, set a **pagefile of at least 32 GB**: the 32B text encoder and the video model take turns in system memory.
- About **45 GB free disk space**.

## Install
StillSpin360 is shared as the `release` folder:

```
release\
  StillSpin360.exe
  README.md         (this file)
  README.zh-Hant.md (繁體中文)
  installer\        install.bat, install.ps1, versions.json
  comfy_workflows\  orbit_api.json
```

Copy the whole folder somewhere with about 45 GB free (not Program Files), then:

1. Double-click `installer\install.bat`. It will:
   - check your GPU, RAM and pagefile;
   - ask you to accept the MiniMax-H3 Community License;
   - ask **which ComfyUI to use**: **1)** install a new copy for StillSpin360 (Enter), or **2)** use a ComfyUI you already have (see below);
   - for a new copy: download **ComfyUI Portable v0.42.1** (pinned, sha256-verified) and extract it next to the exe, as `ComfyUI_windows_portable\`;
   - download the models it doesn't find (up to about 36 GB) with resume and sha256 checks.

   From the source folder it also installs the GUI packages (PySide6, websocket-client) into the new copy's Python for `run.bat`. A release skips this, because the exe already includes them.
2. Re-running it is safe: verified files are skipped, and interrupted downloads resume.

The installer also creates **StillSpin360** shortcuts on the Desktop and in the Start Menu (skip with `-NoShortcuts`).

### Using a ComfyUI you already have (optional)
Choose **2** in the installer's menu, then paste the path of your ComfyUI: the portable folder that holds `run_nvidia_gpu.bat`, or the folder that holds `main.py` for a manual install with a `venv` / `.venv`. A wrong path is explained and asked again; press Enter (or B) to go back to the menu. You can also skip the menu: `install.bat -ComfyUIPath "C:\AI\ComfyUI_windows_portable"`.

```
    Which ComfyUI should StillSpin360 use?

      1) Install a new copy for StillSpin360   (about 36 GB download, ~45 GB disk)
      2) Use a ComfyUI I already have          (reuses its models; usually about 2 GB download)

    Choose 1 or 2 [Enter = 1]:
```

- It needs **ComfyUI 0.38.0 or newer**.
- **Models you already have are reused.** The installer looks through `models\diffusion_models`, `unet`, `text_encoders`, `clip`, `vae` and `loras`, including subfolders. A file counts if it has the right name and exact size. These builds are accepted:
  - **Video model:** FL2VA *pruned* w6a8, int8_convrot, fp8_scaled or bf16.
  - **Text encoder:** Qwen3-VL 32B nvfp4_awq, int8_convrot or bf16.
  - **Video VAE:** int8_convrot or fp16.
- **Only missing files are downloaded,** into your ComfyUI's `models` folder. Usually that's just the 360 Orbit LoRA (155 MB) and the optional Turbo LoRA (1.8 GB).
- **Nothing else in your ComfyUI is changed:** no Python packages, no custom nodes, no updates.
- **StillSpin360 starts your ComfyUI hidden on port 8188.** If it's already running there (for example for another program), StillSpin360 uses it and leaves it running when you close the app. Its own copy uses port 8189, so the two never clash.
- **The choice is saved in `engine.json`.** Re-running the installer shows the menu again with your current choice as the default, so Enter keeps it, and you can switch either way. Switching to StillSpin360's own copy downloads it; switching away from it leaves its `ComfyUI_windows_portable` folder for you to delete. `install.bat -NewComfyUI` picks the own copy without asking.

Options: `-SkipOptional` skips the Turbo LoRA, which the Fast preset needs. `-Rehash` re-verifies every file (with an existing ComfyUI, this also hashes the reused models).

## Run
Double-click **`StillSpin360.exe`** (or the StillSpin360 shortcut). No console window appears: the app starts the AI engine (ComfyUI) hidden in the background, and the pill at the top turns green when it's ready. Closing the window also stops the engine.

`run.bat` (source folder only) starts the same app with ComfyUI Portable's Python, showing a console. It's useful for troubleshooting a startup problem.

The window has the same dark, orange-accent style as EasyAI and walks a beginner through three steps. Every control has a short explanation under it, a tooltip, and a **(?)** button with more detail. **Help → How to use StillSpin360** (F1) shows a quick guide.

**Language:** the interface is in **English** or **Traditional Chinese (繁體中文)**. Switch any time from the **Language / 語言** menu; the choice is remembered. On first run it follows Windows (zh-TW / zh-HK opens in Chinese). Exported HTML viewers use the same language. Translations live in `app/lang/zh-Hant.json`, keyed by the English text.

1. **Choose your photos:** click the box or drag photos into it. Each photo becomes its own spin. The spin keeps each photo's aspect ratio (portrait, landscape or square). The model accepts ratios from 0.4 to 2.5; photos beyond that are center-cropped to the limit.
2. **Choose settings:** pick a preset. **Show advanced settings** reveals Steps, Turbo mode, Spin strength and Variation (seed).

   | Preset | Detail | Steps | Notes |
   |---|---|---|---|
   | Best quality | 768 | 28 | The LoRA's training setting. 16 GB cards. |
   | Balanced | 640 | 28 | |
   | Fast | 512 | 8 | Turbo mode. Best for 12 GB cards. |

   Detail is a pixel budget. At 768, a square photo renders at 768×768 and a 16:9 photo at 1024×576, so every shape costs about the same VRAM and time.

3. Press **Create 360° Spin** (Ctrl+Enter). Plain-language progress shows under the button. Results are saved to `outputs\<photo>_<time>\`, which contains `frames\*.png` and `orbit.mp4`.
4. **Watch and save your spin:**
   - **Save as GIF** → `orbit.gif`
   - **Interactive viewer** → `viewer\index.html` plus `viewer\frames\frame_000.png …` (lossless PNGs)
   - **Single-file viewer** → one `.html` with the frames embedded, easy to share (about 30–60 MB)

Technical ComfyUI output is under **AI engine → Show engine log**.

### HTML viewer controls
- **Slider** or **drag the image** to rotate. Drag right to turn clockwise, left for counter-clockwise.
- **⟲ / ⟳** step counter-clockwise or clockwise. Hold to keep turning.
- **Auto-rotate**, with a **Clockwise / Counter-clockwise** switch and a speed control.
- **Reverse direction**: use this if the orbit turns the opposite way from what you expect.
- Keys: **← / →** step, **Space** toggles auto-rotate.

## Version lock
`installer\versions.json` pins:
- the ComfyUI release, its sha256 and any custom nodes (none are needed; the workflow uses only core nodes);
- the pip packages;
- every model URL, at a fixed Hugging Face revision, with its sha256.

At startup the app compares ComfyUI's reported version with the pin and refuses to generate on a mismatch. Don't update StillSpin360's own ComfyUI from inside its portable folder. To upgrade, bump `versions.json`, test, and reinstall.

An existing ComfyUI of your own isn't pinned: any version from `min_existing_version` (0.38.0) up is accepted, and you keep updating it as usual.

## Troubleshooting
- **Out of memory / very slow first run:**
  - Use the Fast preset.
  - Close other GPU apps.
  - Make sure the pagefile is at least 32 GB.
  - Add ComfyUI flags in `prefs.json` → `"extra_comfy_args": ["--reserve-vram", "1.0"]`, or `["--lowvram"]`.
- **The subject wobbles or isn't a person:** the LoRA was trained on 28 square, human-centric clips, so other subjects and non-square shapes are untested. Try another seed, or set the orbit LoRA strength between 0.9 and 1.1.
- **The engine pill shows a version mismatch:** reinstall with the bundled installer. Someone has updated ComfyUI.
- Full ComfyUI output is under **AI engine → Show engine log**.

## Building the exe
Run `Build EXE.bat`. It uses the Python on your PATH (installing PyInstaller, PySide6, PyAV, Pillow and websocket-client if missing), builds from `StillSpin360.spec`, and fills the `release` folder with the exe, both READMEs, the installer and the workflow.
- Rebuild after changing the code, the viewer or the translations.
- Only the release's own files are replaced. Anything else in `release\`, such as an engine installed there for testing, is left alone.
- The exe needs `ComfyUI_windows_portable` next to it and keeps `prefs.json` and `outputs\` there. So in this source folder, use `run.bat`, or copy the exe out of `release\` to the project root.
- The exe is windowed (no console). A startup error is shown in a dialog instead.

## Layout
```
installer/          install.bat, install.ps1, versions.json (pins)
engine.json         written by the installer: which ComfyUI to use (own copy or yours) and its model names
comfy_workflows/    orbit_api.json (ComfyUI API-format graph)
app/                PySide6 GUI, ComfyUI server/client, exports, viewer template
app/lang/           interface translations (zh-Hant.json)
app/theme.py        EasyAI-style dark theme
app/assets/icons/   icon pack (.ico 16-256, PNGs 16-1024, favicon) built from StillSpin360.png
tools/make_icons.py rebuilds the icon pack:  python tools/make_icons.py
outputs/            generated orbits
release/            what you share: StillSpin360.exe + READMEs + installer + workflow (built by "Build EXE.bat")
StillSpin360.spec   how the exe is built
StillSpin360.py     entry point used by the exe
run.bat             start the app with a console (troubleshooting)
```
