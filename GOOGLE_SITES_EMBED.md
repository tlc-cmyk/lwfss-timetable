# 將時間表嵌入 Google 網站（Sites）

公開網址（GitHub Pages）：

`https://tlc-cmyk.github.io/lwfss-timetable/`

## iframe 嵌入程式碼

將以下 HTML 貼到 Google Sites 的「嵌入」元件：

```html
<iframe
  src="https://tlc-cmyk.github.io/lwfss-timetable/"
  width="100%"
  height="900"
  style="border:0; min-height:80vh;"
  title="劉皇發中學教師時間表"
  loading="lazy"
  referrerpolicy="no-referrer-when-downgrade"
  allowfullscreen>
</iframe>
```

如需較矮或較高顯示，可改 `height`（例如 `700` 或 `1100`）。

## 在 Google Sites 插入步驟

1. 開啟要編輯的 Google 網站，按右上角「編輯」。
2. 在工具列選「插入」→「嵌入」。
3. 揀「嵌入程式碼」，貼上上方 iframe HTML，按「下一步」→「插入」。
4. 拖曳調整嵌入框大小；建議寬度設為整欄（100%）。
5. 按「發布」／「更新」，用無痕視窗開啟網站確認能載入時間表。

## 注意事項

- 必須用 **HTTPS** 公開網址；Google Sites 不會嵌入 `file://` 或本機路徑。
- 若首次發布後顯示空白，請等約 1–2 分鐘讓 GitHub Pages 建置完成，再重新整理。
- 手機版建議 height 至少 `800`，方便捲動課表。
