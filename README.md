# 雙北購屋決策分析系統（PythonDataAnalysis）

本專案用於分析雙北（台北市、新北市）不動產交易資料，提供：

- 原始資料清理與欄位標準化
- 隔年 Q1 延遲揭露資料回補（修正交易年月）
- Streamlit 互動式視覺化儀表板

---

## 1. 專案結構

```text
Python專題/
├─ 110~114中古/                    # 原始中古屋資料
├─ 110~114預售/                    # 原始預售屋資料
├─ data_processed/
│  └─ 按年份整理/                  # 清理後輸出資料
├─ batch_clean_all_years_v2.py      # 主清理程式
├─ fix_december.py                  # 回補隔年Q1延遲揭露資料
├─ app.py                           # Streamlit 視覺化介面
├─ 雙北購屋決策分析系統.bat          # 啟動介面（若已配置）
└─ 打包程式.bat                      # 打包 EXE（若已配置）
```

---

## 2. 環境需求

- Windows 10/11
- Python 3.9 以上

建議套件：

- pandas
- numpy
- streamlit
- plotly
- pyinstaller（需要打包 EXE 時）

---

## 3. 執行流程（建議順序）

1. 執行資料清理
2. 執行延遲資料回補
3. 啟動視覺化介面

### 3.1 資料清理

```bash
python batch_clean_all_years_v2.py
```

### 3.2 回補隔年 Q1 延遲揭露

```bash
python fix_december.py
```

### 3.3 啟動視覺化

```bash
streamlit run app.py
```

啟動後通常可於瀏覽器開啟：

`http://localhost:8501`

---

## 4. 關於 EXE 與跨電腦使用

### 4.1 可以在其他電腦使用嗎？

可以。只要把「程式與資料夾」完整帶走，維持相對位置即可。

### 4.2 Streamlit 一定會開瀏覽器嗎？

會。Streamlit 本質是 Web 介面，EXE 只是啟動器，畫面仍由瀏覽器顯示。

---

## 5. 打包 EXE（可選）

若要將清理程式打包：

```bash
python -m PyInstaller --onefile --console batch_clean_all_years_v2.py
python -m PyInstaller --onefile --console fix_december.py
```

打包後 EXE 會在 `dist/` 目錄。

> 注意：`app.py` 為 Streamlit 應用，通常建議以 `streamlit run app.py` 啟動。

---

## 6. 常見問題

### Q1：改了最外層資料夾名稱會壞掉嗎？

若程式採用相對路徑且專案內部資料夾結構不變，通常可以正常運行。

### Q2：為什麼顯示「無法載入資料」？

請確認：

1. 已先跑過 `batch_clean_all_years_v2.py`
2. 必要時再跑 `fix_december.py`
3. `data_processed/按年份整理/` 底下有 `*年_已清理.csv`

### Q3：搬到其他電腦後打不開？

請確認：

- 資料夾是否完整複製
- 防毒軟體是否阻擋 EXE
- 權限是否允許執行

---

## 7. 專案說明

本專案為課程/專題用途，重點在：

- 雙北房市資料整理
- 政策事件與市場變化視覺化
- 提供購屋決策參考

