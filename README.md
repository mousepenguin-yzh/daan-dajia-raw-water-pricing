# 大安大甲聯合運用－原水費計價情境互動樹

會議討論用的靜態互動頁面。展示資料來自 Google Sheet 的「網頁樹狀資料」分頁；分析母資料仍以原工作表為準。

## 日常更新

1. 修改 Google Sheet「網頁樹狀資料」。
2. 在本機 clone 的專案資料夾中雙擊 `更新並發布.bat`。
3. 工具會自動：
   - 讀取最新 CSV
   - 驗證 node_id / parent_id / level / sort_order / node_type / status
   - 重建 `index.html`
   - git commit + push
4. GitHub Pages 會沿用同一個網址更新。

若資料結構驗證失敗，流程會在發布前停止。

## 第一次在新電腦使用

```bash
git clone https://github.com/mousepenguin-yzh/daan-dajia-raw-water-pricing.git
```

需具備 Python 3 與 Git，並完成 GitHub 的登入／憑證設定。

## 資料發布原則

- 網頁只讀取「網頁樹狀資料」公開 CSV。
- 其他分析母表不需要公開。
- 網頁 HTML 是每次發布時的 Snapshot，不會在瀏覽時即時連回 Google Sheet。
- 網頁加入 `noindex,nofollow`，但 GitHub Pages 本身仍是公開網址；知道網址的人即可查看。
