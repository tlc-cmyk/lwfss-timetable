# 教師時間表 · 世界龍岡學校劉皇發中學

手機友善、離線可用的教師時間表查詢網頁（繁體中文 zh-HK）。輸入教師 ShortName（例如 `TLC`）即可查看循環日課表。今日循環日會依 **2026–2027 校曆表** 自動判斷（香港時間 Asia/Hong_Kong）。

## 如何使用

1. 用瀏覽器開啟 `index.html`（建議經本機／靜態 HTTP 伺服器，見下方）。
2. 在「輸入教師代碼」欄輸入 ShortName（不區分大小寫），例如 `TLC`。
3. **頂部橫幅是唯一資訊來源**：顯示**香港時間**、**選取的校曆日期**、**循環日**（或「無上課／假期」）、**鐘聲類型**（一般／BF）、校曆**當日事項**，以及**當值老師**。各分頁唔會重複呢啲資料。**點擊橫幅**即可改期（循環日、鐘聲、當值、課表、事項一併更新）。橫幅／主色會依日期類型變色：**一般上課日**藍、**BF 日**（Day 5／10）綠、**假期／無上課**粉紅。
4. 可用的功能（分頁只顯示獨特內容）：
   - **循環日課表**：揀 Day 1–10 睇該日各節（科目、班別、課室）及鐘聲時間；空堂會標示。若揀嘅 Day 唔係今日循環日，可「跳至今日循環日」。當選取日期為**今日**且顯示今日循環日時，會標示**現正進行的一節**。
   - **即時空堂**：顯示**現正時段**同空堂老師列表（時間／循環日見頂部）；小息／午飯可預覽下一節空堂。約每分鐘自動更新。
   - **全日概覽**：一次睇晒十日時間表。
   - **代堂助手**（簡單密碼閘，預設 `123`；`sessionStorage` 本分頁解鎖，僅前端檢查）：揀缺席教師、循環日（或跟頂部），指派代堂老師同備註，可匯出 CSV／列印。
   - **搜尋課室／班別**：例如搜 `604`、`5A`、`COMPUTER`。
   - **循環日覆寫**：本機手動覆寫／管理員覆寫（日常循環日見頂部）。
   - **校曆**：月／週瀏覽；點選日子同步頂部。格內可見循環日圈號同事項摘要；詳細日期／當值見頂部。
   - **當值**：職責說明同即將當值列表（當日當值見頂部；點一列可改頂部日期）。
   - **房間預約**：即將推出。
   - **教師進修申請**：填寫老師姓名（可選 ShortName 從 `data.js` 帶出）、進修日期、時間、地點、活動名稱、進修類型；可**拍照／上載通告圖片**，以瀏覽器 **Tesseract.js（CDN）OCR** 嘗試辨識日期、時間、**活動名稱／題目／課程**、**地點／venue／地址**與類型（較長標題優先、避免把日期時間混入名稱／地點；可編輯預覽後套用）；亦可對照圖片手動填寫。完成後可預覽並以瀏覽器「另存為 PDF」匯出校長審批用表格。

不需登入、不需 Google API key；時間表內嵌於 `data.js`，校曆內嵌於 `calendar.js`，鐘聲時間內嵌於 `bells.js`。


## 鐘聲時間（上課時間表）

循環日會自動套用對應鐘聲：

| 循環日 | 時間表 |
|--------|--------|
| Day 1–4、6–9 | **一般上課時間** |
| Day 5、10 | **BF 上課時間表** |

### 日期類型顏色

| 日期類型 | 顏色主題 |
|----------|----------|
| 一般上課日（Day 1–4、6–9） | 藍（預設） |
| BF 日（Day 5、10） | 綠 |
| 假期／無上課 | 粉紅 |

頂部橫幅與主要強調色（分頁、按鈕、選中循環日等）會跟住選取日期切換，方便一眼分辨。

各節開始／結束時間會顯示於「循環日課表」、全日概覽與代堂助手課堂列表。完整時段（含早會、小息、午飯、閱讀時段）見 `bells.json`。依 `bells.js` 的一般／BF 時間表對照時鐘，判斷現正哪一節。

## 當日事項（校曆備註）

`calendar.json` / `calendar.js` 的 `events` 欄位由校曆表「備註」欄解析而來（例如「家長教師會周年大會」）。頂部橫幅會在有事項的日期顯示「當日事項」；無備註則不顯示。

## 今日循環日如何決定

優先次序（高 → 低）：

1. **`cycle-config.json` 的 `overrideDay`**（全校靜態設定，IT 改檔即全校生效）
2. 本機「管理員覆寫」（PIN 閘，只影響該瀏覽器，方便測試）
3. 本機「手動覆寫」（只限當日）
4. **`calendar.json` / `calendar.js`** 依香港日期自動對應循環日 1–10
5. 若校曆該日無圈號 → 視為無正規上課（假期／活動／考試等）

### IT 協調員：更新全校覆寫

編輯網站根目錄的 `cycle-config.json`：

```json
{
  "overrideDay": null,
  "pin": "1234",
  "updated": null
}
```

- 正常日子：保持 `"overrideDay": null`，讓校曆自動生效。
- 臨時改日：設為 `1`–`10`（數字），並把 `updated` 改成 ISO 時間（例如 `"2026-10-10T09:00:00+08:00"`）。
- `pin` 只用於網頁「管理員／IT」本機測試閘，**不是**伺服器端保安。

### 更新校曆（每年／校曆改版）

1. 取得新校曆 PDF，轉成文字（或更新 `calendar-2026-2027.txt`）。
2. 如有需要，調整 `scripts/build_calendar.py` 內各月份的行範圍 `MONTH_BLOCKS`。
3. 執行：

```bash
cd timetable-app
python3 scripts/build_calendar.py /path/to/calendar-YYYY-YYYY.txt
```

4. 會覆寫 `calendar.json` 與 `calendar.js`。重新整理網頁即可。

校曆圈號 ①–⑩ 對應循環日；無圈號日期為 `null`。

## 本機開啟（建議）

```bash
cd timetable-app
python3 -m http.server 8765
```

然後開啟：http://127.0.0.1:8765/

亦可直接雙擊 `index.html`（多數功能可離線；`cycle-config.json` 在 `file://` 下可能無法 fetch，但不影響內嵌校曆自動判斷）。

## 靜態托管（給同事用）

本應用全為相對路徑，可直接上傳整個資料夾到任何靜態網站托管，例如：

- GitHub Pages / Cloudflare Pages / Netlify / Surge
- 學校內網 IIS / Nginx / 共用磁碟經 HTTP 分享

上傳後請確認這些檔案都在網站根（或同一子目錄）且可被讀取：

| 檔案 | 說明 |
|------|------|
| `index.html` | 單頁應用 |
| `data.js` / `data.json` | 時間表 |
| `calendar.js` / `calendar.json` | 校曆循環日 |
| `bells.js` / `bells.json` | 一般／BF 鐘聲時間 |
| `duty.js` / `duty.json` | 當值表日期 → Teacher1／Teacher2 |
| `cycle-config.json` | 可選全校覆寫 |
| `README.md` | 說明 |

公開網址（GitHub Pages）：https://tlc-cmyk.github.io/lwfss-timetable/

亦可將整個資料夾或 zip 上傳至學校其他靜態托管。

## 更新時間表資料（從 Google Sheet）

Sheet 名稱：`timetablegrok`  
fileId：`14UPpVtyrCCzM_uExw7hsfKxKk-5F_kzZMy00j1RYFoM`

```bash
cd timetable-app
python3 scripts/build_data.py /path/to/export.json
# 或
python3 scripts/build_data.py /path/to/timetable.csv
```

會覆寫 `data.js` 與 `data.json`。

Sheet 格式：每行一位教師；欄位 `ShortName, EngName, ChiName`，其後為 `DxPyCl / DxPySu / DxPyTe / DxPyRm`（D1–D10、P1–P7；D5／D10 另有 P8）。

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `index.html` | 單頁應用（UI／邏輯） |
| `data.js` / `data.json` | 時間表 |
| `calendar.js` / `calendar.json` | 校曆日期 → 循環日 |
| `bells.js` / `bells.json` | 一般／BF 鐘聲時間 |
| `duty.js` / `duty.json` | 當值表日期 → Teacher1／Teacher2 |
| `cycle-config.json` | 全校循環日覆寫（可選） |
| `calendar-2026-2027.txt` | 校曆文字來源（供重建） |
| `scripts/build_data.py` | 由 Sheet 匯出重建時間表 |
| `scripts/build_calendar.py` | 由校曆文字重建 calendar 檔 |
| `scripts/build_duty.py` | 由當值表文字重建 duty 檔 |
| `README.md` | 本說明 |

## 當值老師

來源：Duty Roster（Sep 2026 – July 2027），更新於 1/9/2026。

```bash
python3 scripts/build_duty.py /path/to/duty-roster.txt
```

會覆寫 `duty.js` 與 `duty.json`。介面頂部與日期選擇會顯示「今日／當日當值」；「當值」分頁可查即將當值日子。


## 校曆檢視

「校曆」分頁提供月曆與週檢視，資料來自 `calendar.js`（循環日＋事項）與 `duty.js`（當值），顏色依 `bells.js` 日類型：

| 類型 | 顏色 |
|------|------|
| 一般上課日（Day 1–4、6–9） | 藍 |
| BF 日（Day 5、10） | 綠 |
| 假期／無上課 | 粉紅 |

點選格子會更新頂部橫幅的瀏覽日期與循環日（與其他分頁共用）。

## 注意事項

- ICT 等長科目代碼會簡化顯示；完整代碼可將滑鼠移上課堂查看。
- 班別如 `5A,5B,5C,5D` 會顯示為 `5A-D`。
- 「代堂助手」進入前會顯示密碼提示（預設 `123`），解鎖後以 `sessionStorage` 記住至關閉分頁；僅客戶端檢查，並非真正保安。以缺席教師當日課堂為主；代堂人選 = 該節時間表空缺（空堂）的其他教師；可匯出 CSV／文字。
- 資料以匯出／校曆解析當下為準；有更新請重新執行對應 build 腳本。
