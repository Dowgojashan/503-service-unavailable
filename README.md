# Project Overview

本專案包含兩個主要部分：
1. **E-commerce Support Agent 實驗**：位於根目錄的 Python 筆記本（`phase1_easy.ipynb`, `phase2_medium.ipynb`, `phase3_hard.ipynb`），主要測試 LLM（如 Gemma-3）在不同難度下的對話表現。
2. **資料缺失補全研究 (Data Imputation)**：位於 `A1/` 目錄，包含一篇關於 `Deep Learning vs. Conventional Methods for Tabular Data Imputation` 的論文及其相關圖表。

---

## 環境設定 (Environment Setup)

### 1. 安裝 Python 依賴項
建議使用 Python 3.9+ 環境。請執行以下指令安裝所需套件：

```bash
pip install -r requirements.txt
```

主要依賴套件說明：
- `pandas`, `numpy`: 資料處理與數值運算。
- `google-generativeai`: 用於呼叫 Google Gemini / Gemma 系列模型 API。
- `python-dotenv`: 管理環境變數（如 API Key）。
- `tqdm`: 顯示進度條。
- `ipykernel`: 支援 Jupyter Notebook 執行。

### 2. 環境變數設定 (.env)
在專案根目錄下建立一個 `.env` 檔案（如果尚未存在），並填入您的 Gemini API Key：

```env
GEMINI_API_KEY=您的_API_KEY_在這邊
```

### 3. 資料準備
確保根目錄包含以下資料檔案：
- `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`
- `bitext_with_difficulty.csv` (由 phase1 產生)

---

## 專案結構說明

- `/`: 存放主實驗筆記本與原始資料。
- `/A1/`: 存放學術論文原始碼 (`main.tex`)、PDF 報告與實驗結果圖表。
- `/experiment_logs/`: 存放 LLM 實驗的執行紀錄 (JSON 格式)。
- `fact_sheet_*.json`: 存放實驗中使用的事實清單。

## 如何執行
1. 依照「環境設定」步驟完成安裝。
2. 開啟 Jupyter Notebook 或 VS Code Jupyter Extension。
3. 依序執行 `phase1_easy.ipynb` -> `phase2_medium.ipynb` -> `phase3_hard.ipynb`。
