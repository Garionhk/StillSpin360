# StillSpin360

[English](README.md) · **繁體中文**

把一張照片變成「時間凍結」的 **360° 環繞影片**：鏡頭繞著主體轉一整圈，畫面中的一切都靜止不動。完成後可以匯出成循環 MP4、GIF，或是可以用滑鼠轉動的互動 HTML 檢視器。

所有運算都在你自己的電腦上進行，使用版本鎖定的 **ComfyUI Portable**，搭配：
- **MiniMax-H3 FL2VA**（pruned w6a8 版本）
- [pablodawson 的 360 Orbit LoRA](https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA)

同一張照片會同時當作第一格和最後一格，所以環繞影片的結尾會剛好回到起點，可以無縫循環播放。

## 系統需求
- Windows 10/11，以及 **12–16 GB 顯示記憶體** 的 NVIDIA 顯示卡，並安裝最新驅動程式。
- **至少 32 GB 記憶體。** 如果只有 32 GB，請把 **虛擬記憶體（分頁檔）設為至少 32 GB**：32B 的文字編碼器和影片模型會輪流使用系統記憶體。
- 約 **45 GB 可用磁碟空間**。

## 安裝
StillSpin360 以 `release` 資料夾的形式提供：

```
release\
  StillSpin360.exe
  README.md         （英文說明）
  README.zh-Hant.md （本檔案）
  installer\        install.bat、install.ps1、versions.json
  comfy_workflows\  orbit_api.json
```

把整個資料夾複製到有約 45 GB 可用空間的位置（不要放在 Program Files），然後：

1. 按兩下 `installer\install.bat`。它會：
   - 檢查顯示卡、記憶體和分頁檔；
   - 請你同意 MiniMax-H3 社群授權條款（MiniMax-H3 Community License）；
   - 詢問 **要使用哪一個 ComfyUI**：**1)** 為 StillSpin360 安裝一份新的（直接按 Enter），或 **2)** 使用你已經安裝的 ComfyUI（見下方說明）；
   - 安裝新的一份時：下載 **ComfyUI Portable v0.42.1**（固定版本，並以 sha256 驗證），解壓縮到 exe 旁邊的 `ComfyUI_windows_portable\`；
   - 下載找不到的模型（最多約 36 GB），支援續傳，並以 sha256 驗證。

   從原始碼資料夾執行時，它還會把介面套件（PySide6、websocket-client）安裝到新安裝的 Python 裡，供 `run.bat` 使用。從 release 安裝時會略過這一步，因為 exe 已經內建這些套件。
2. 可以放心重新執行：已驗證的檔案會略過，中斷的下載會接續。

安裝程式也會在桌面和開始功能表建立 **StillSpin360** 捷徑（加上 `-NoShortcuts` 可略過）。

### 使用你已經安裝的 ComfyUI（選用）
在安裝程式的選單中選 **2**，然後貼上你的 ComfyUI 路徑：Portable 版請選含有 `run_nvidia_gpu.bat` 的資料夾；手動安裝（使用 `venv` / `.venv`）請選含有 `main.py` 的資料夾。路徑錯誤時會說明原因並請你重新輸入；按 Enter（或 B）可以回到選單。也可以略過選單直接指定：`install.bat -ComfyUIPath "C:\AI\ComfyUI_windows_portable"`。

安裝程式的選單是英文的，畫面如下：

```
    Which ComfyUI should StillSpin360 use?

      1) Install a new copy for StillSpin360   (about 36 GB download, ~45 GB disk)
      2) Use a ComfyUI I already have          (reuses its models; usually about 2 GB download)

    Choose 1 or 2 [Enter = 1]:
```

- **1)** 為 StillSpin360 安裝一份新的（約下載 36 GB，需要約 45 GB 磁碟空間）
- **2)** 使用我已經安裝的 ComfyUI（沿用它的模型，通常只需下載約 2 GB）

- 需要 **ComfyUI 0.38.0 或更新版本**。
- **你已經有的模型會直接沿用。** 安裝程式會搜尋 `models\diffusion_models`、`unet`、`text_encoders`、`clip`、`vae` 和 `loras`（包含子資料夾），檔名和大小完全相符才算數。可以使用的版本：
  - **影片模型：** FL2VA *pruned* 的 w6a8、int8_convrot、fp8_scaled 或 bf16。
  - **文字編碼器：** Qwen3-VL 32B 的 nvfp4_awq、int8_convrot 或 bf16。
  - **影片 VAE：** int8_convrot 或 fp16。
- **只會下載缺少的檔案**，放進你 ComfyUI 的 `models` 資料夾。通常只需要 360 Orbit LoRA（155 MB）和選用的加速 LoRA（1.8 GB）。
- **不會更動你 ComfyUI 的其他任何東西：** 不安裝 Python 套件、不安裝自訂節點、不做任何更新。
- **StillSpin360 會在背景隱藏啟動你的 ComfyUI，使用連接埠 8188。** 如果它已經在那裡執行（例如為了其他程式開著），StillSpin360 會直接使用它，關閉 StillSpin360 時也不會把它關掉。StillSpin360 自己安裝的那一份使用連接埠 8189，所以兩者不會衝突。
- **你的選擇會存在 `engine.json`。** 重新執行安裝程式時會再次顯示選單，並以你目前的選擇作為預設值，所以直接按 Enter 就會維持不變，也可以隨時改成另一個選項。改用 StillSpin360 自己的一份時會下載它；不再使用它時，它的 `ComfyUI_windows_portable` 資料夾會留著，你可以自行刪除。`install.bat -NewComfyUI` 會不經詢問直接使用 StillSpin360 自己的一份。

選項：`-SkipOptional` 會略過加速 LoRA（「快速」預設需要它）。`-Rehash` 會重新驗證每個檔案（使用現有 ComfyUI 時，也會驗證沿用的模型）。

## 執行
按兩下 **`StillSpin360.exe`**（或 StillSpin360 捷徑）。不會出現任何命令列視窗：程式會在背景隱藏啟動 AI 引擎（ComfyUI），頂端的狀態標籤變成綠色就表示就緒。關閉視窗時，AI 引擎也會一起停止。

`run.bat`（僅限原始碼資料夾）會用 ComfyUI Portable 的 Python 啟動同一個程式，並顯示命令列視窗。程式無法啟動時，可以用它來查看原因。

視窗採用和 EasyAI 相同的深色、橘色強調風格，以三個步驟帶領新手操作。每個項目下方都有簡短說明，滑鼠移上去會顯示提示，按 **(?)** 按鈕可以看到更詳細的解釋。**說明 → 如何使用 StillSpin360**（F1）會顯示快速指南。

**語言：** 介面提供 **English** 和 **繁體中文**。隨時可以從 **Language / 語言** 選單切換，程式會記住你的選擇。第一次啟動時會依照 Windows 的語言設定（zh-TW / zh-HK 會以中文開啟）。匯出的 HTML 檢視器也會使用相同語言。翻譯檔在 `app/lang/zh-Hant.json`，以英文原文作為對照。

1. **選擇照片：** 按一下方框，或把照片拖進去。每張照片都會各自變成一個環繞影片。影片會保留每張照片的長寬比（直式、橫式或正方形）。模型接受的長寬比為 0.4 到 2.5，超出範圍的照片會從中央裁切到上限。
2. **選擇設定：** 選一個預設。按 **顯示進階設定** 可以調整步數、加速模式、環繞強度和變化（種子）。

   | 預設 | 細緻度 | 步數 | 說明 |
   |---|---|---|---|
   | 最佳品質 | 768 | 28 | LoRA 訓練時的設定。適合 16 GB 顯示卡。 |
   | 平衡 | 640 | 28 | |
   | 快速 | 512 | 8 | 加速模式。最適合 12 GB 顯示卡。 |

   細緻度代表像素總量。設為 768 時，正方形照片會以 768×768 製作，16:9 照片則是 1024×576，所以不論形狀，使用的顯示記憶體和時間都差不多。

3. 按 **製作 360° 環繞影片**（Ctrl+Enter）。按鈕下方會用淺顯的文字顯示進度。成果會存到 `outputs\<照片名稱>_<時間>\`，裡面有 `frames\*.png` 和 `orbit.mp4`。
4. **觀看並儲存影片：**
   - **存成 GIF** → `orbit.gif`
   - **互動檢視器** → `viewer\index.html`，加上 `viewer\frames\frame_000.png …`（無損 PNG）
   - **單一檔案檢視器** → 一個內含所有畫面的 `.html` 檔，方便分享（約 30–60 MB）

ComfyUI 的技術訊息在 **AI 引擎 → 顯示引擎記錄**。

### HTML 檢視器操作
- 拖曳 **滑桿** 或 **直接拖曳畫面** 即可旋轉。往右拖是順時針，往左拖是逆時針。
- **⟲ / ⟳** 逐格逆時針或順時針轉動。按住不放可以持續轉動。
- **自動旋轉**，可切換 **順時針 / 逆時針**，並調整速度。
- **反轉方向**：如果旋轉方向和你預期的相反，就勾選這個選項。
- 鍵盤：**← / →** 逐格轉動，**空白鍵** 切換自動旋轉。

## 版本鎖定
`installer\versions.json` 固定了：
- ComfyUI 的版本、它的 sha256，以及自訂節點（目前不需要任何自訂節點，工作流程只用到內建節點）；
- pip 套件的版本；
- 每個模型的下載網址（固定在某個 Hugging Face 版本）及其 sha256。

程式啟動時會比對 ComfyUI 回報的版本和固定版本，如果不符就不會製作影片。請不要在 StillSpin360 自己的 Portable 資料夾裡更新 ComfyUI。要升級時，請修改 `versions.json`、測試，然後重新安裝。

你自己原本的 ComfyUI 不受版本鎖定：只要是 `min_existing_version`（0.38.0）以上的版本都可以使用，你也可以照常更新它。

## 疑難排解
- **記憶體不足／第一次執行非常慢：**
  - 改用「快速」預設。
  - 關閉其他使用顯示卡的程式。
  - 確認分頁檔至少有 32 GB。
  - 在 `prefs.json` 加入 ComfyUI 參數：`"extra_comfy_args": ["--reserve-vram", "1.0"]`，或 `["--lowvram"]`。
- **主體晃動，或主體不是人物：** 這個 LoRA 是用 28 段正方形、以人物為主的影片訓練的，其他主體和非正方形的照片沒有經過測試。可以換一個種子，或把環繞強度設在 0.9 到 1.1 之間。
- **引擎狀態顯示版本不符：** 有人更新了 ComfyUI。請用附帶的安裝程式重新安裝。
- ComfyUI 的完整輸出在 **AI 引擎 → 顯示引擎記錄**。

## 建置 exe
執行 `Build EXE.bat`。它會使用 PATH 中的 Python（缺少 PyInstaller、PySide6、PyAV、Pillow 或 websocket-client 時會自動安裝），依照 `StillSpin360.spec` 建置，然後把 exe、兩份說明檔、安裝程式和工作流程放進 `release` 資料夾。
- 修改程式碼、檢視器或翻譯之後，請重新建置。
- 只會取代 release 本身的檔案。`release\` 裡的其他東西（例如為了測試而安裝在裡面的引擎）都不會被動到。
- exe 需要旁邊有 `ComfyUI_windows_portable`，並把 `prefs.json` 和 `outputs\` 存在同一個資料夾。所以在原始碼資料夾裡，請使用 `run.bat`，或把 `release\` 裡的 exe 複製到專案根目錄。
- exe 是視窗程式（沒有命令列視窗）。啟動錯誤會以對話框顯示。

## 檔案結構
```
installer/          install.bat、install.ps1、versions.json（版本鎖定）
engine.json         由安裝程式產生：要使用哪一個 ComfyUI（自己的一份或你原本的）及其模型名稱
comfy_workflows/    orbit_api.json（ComfyUI API 格式的工作流程）
app/                PySide6 介面、ComfyUI 伺服器／用戶端、匯出功能、檢視器範本
app/lang/           介面翻譯（zh-Hant.json）
app/theme.py        EasyAI 風格的深色主題
app/assets/icons/   圖示包（.ico 16–256、PNG 16–1024、favicon），由 StillSpin360.png 產生
tools/make_icons.py 重新產生圖示包：python tools/make_icons.py
outputs/            製作完成的環繞影片
release/            要分享的檔案：StillSpin360.exe + 說明檔 + 安裝程式 + 工作流程（由 "Build EXE.bat" 產生）
StillSpin360.spec   exe 的建置設定
StillSpin360.py     exe 使用的程式進入點
run.bat             以命令列視窗啟動程式（疑難排解用）
```
