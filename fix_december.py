import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 72)
print("回補隔年Q1延遲資料：將前一年 1~12 月回歸正確交易年月")
print("=" * 72)

base_dir_old = Path('110~114中古')
base_dir_new = Path('110~114預售')
output_dir = Path('data_processed/按年份整理')
backup_dir = output_dir / "_backup_before_q1_reconcile"
backup_dir.mkdir(parents=True, exist_ok=True)

output_cols = [
    "地區", "鄉鎮市區", "土地位置建物門牌", "交易標的",
    "交易年月", "交易年_西元", "交易月",
    "總價_萬", "坪數",
    "車位價格_萬", "車位面積_坪",
    "不含車位總價_萬", "不含車位坪數", "不含車位單價_萬坪",
    "建物型態", "屋齡", "移轉層次", "總樓層數",
    "戶型", "房數", "廳數", "衛數",
    "有無管理組織", "是否預售屋", "備註", "編號",
]


def process_q1_file(file_path, region_name, property_type, target_year_west):
    """讀取隔年Q1檔，篩出目標西元年的交易（1~12月），並套用與主清理一致規則。"""
    fp = Path(file_path)
    if not fp.exists():
        return None

    try:
        df = pd.read_csv(fp, skiprows=[1], encoding="utf-8")

        keep_cols = [
            "鄉鎮市區", "土地位置建物門牌", "交易標的", "交易年月日",
            "總價元", "車位總價元", "建物移轉總面積平方公尺", "車位移轉總面積平方公尺",
            "建物型態", "建築完成年月", "移轉層次", "總樓層數",
            "建物現況格局-房", "建物現況格局-廳", "建物現況格局-衛",
            "有無管理組織", "備註", "編號",
        ]
        df = df[[c for c in keep_cols if c in df.columns]].copy()
        df["地區"] = region_name

        # 日期解析與篩選（重點：抓前一年所有月份，不只12月）
        df["交易年月日_str"] = df["交易年月日"].astype(str).str.zfill(7)
        df["交易年_民國"] = pd.to_numeric(df["交易年月日_str"].str[:3], errors="coerce")
        df["交易月"] = pd.to_numeric(df["交易年月日_str"].str[3:5], errors="coerce")
        df["交易年_西元"] = df["交易年_民國"] + 1911
        df = df[(df["交易年_西元"] == target_year_west) & (df["交易月"].between(1, 12))].copy()
        if len(df) == 0:
            return None

        # 與主流程一致：標記預售屋、特殊交易濾除、房地篩選、面積/總價條件
        df["是否預售屋"] = property_type == "預售屋"

        special_keywords = ["親友", "員工", "共有人", "特殊關係"]
        df["是否特殊交易"] = df["備註"].fillna("").apply(lambda x: any(k in str(x) for k in special_keywords))

        if "交易標的" in df.columns:
            df = df[df["交易標的"].str.contains("房地", na=False)]

        df["總價元"] = pd.to_numeric(df["總價元"], errors="coerce")
        df["建物移轉總面積平方公尺"] = pd.to_numeric(df["建物移轉總面積平方公尺"], errors="coerce")
        df["車位總價元"] = pd.to_numeric(df.get("車位總價元", 0), errors="coerce").fillna(0)
        df["車位移轉總面積平方公尺"] = pd.to_numeric(df.get("車位移轉總面積平方公尺", 0), errors="coerce").fillna(0)

        df = df[(df["總價元"] > 0) & (df["建物移轉總面積平方公尺"] > 0)]
        df = df[~df["是否特殊交易"]]

        # 衍生欄位
        df["坪數"] = df["建物移轉總面積平方公尺"] / 3.30579
        df["車位面積_坪"] = df["車位移轉總面積平方公尺"] / 3.30579
        df["車位價格_萬"] = df["車位總價元"] / 10000
        df["不含車位總價_萬"] = (df["總價元"] - df["車位總價元"]) / 10000
        df["不含車位坪數"] = df["坪數"] - df["車位面積_坪"]
        df["不含車位單價_萬坪"] = np.where(
            df["不含車位坪數"] > 0,
            df["不含車位總價_萬"] / df["不含車位坪數"],
            np.nan,
        )
        df["總價_萬"] = df["總價元"] / 10000
        df["交易年月"] = df["交易年_西元"].astype(int).astype(str) + "-" + df["交易月"].astype(int).astype(str).str.zfill(2)

        # 屋齡
        df["建築完成年月_str"] = df.get("建築完成年月", "0").fillna("0").astype(str).str.zfill(7)
        df["建築完成年_民國"] = pd.to_numeric(df["建築完成年月_str"].str[:3], errors="coerce")
        df["建築完成年_西元"] = df["建築完成年_民國"] + 1911
        df["屋齡"] = (df["交易年_西元"] - df["建築完成年_西元"]).clip(0, 100)

        # 戶型
        df["房數"] = pd.to_numeric(df.get("建物現況格局-房", 0), errors="coerce").fillna(0).astype(int)
        df["廳數"] = pd.to_numeric(df.get("建物現況格局-廳", 0), errors="coerce").fillna(0).astype(int)
        df["衛數"] = pd.to_numeric(df.get("建物現況格局-衛", 0), errors="coerce").fillna(0).astype(int)
        df["戶型"] = df["房數"].astype(str) + "房" + df["廳數"].astype(str) + "廳" + df["衛數"].astype(str) + "衛"

        df = df[[c for c in output_cols if c in df.columns]]
        return df

    except Exception as e:
        print(f"  [ERROR] {fp.name}: {e}")
        return None


def reconcile_year(target_roc_year):
    """把 target 年度的延遲登錄資料（來自 next year Q1）回補進年度清理檔。"""
    target_west = target_roc_year + 1911
    next_roc = target_roc_year + 1
    q1_name = f"{next_roc}年第1季"

    year_fp = output_dir / f"{target_roc_year}年_已清理.csv"
    if not year_fp.exists():
        print(f"[SKIP] 找不到 {year_fp.name}")
        return

    print(f"\n[{target_roc_year}年] 從 {next_roc}年Q1 回補 {target_west} 年延遲登錄資料...")
    current_df = pd.read_csv(year_fp, encoding="utf-8-sig")

    files = [
        (base_dir_old / f"{next_roc}" / q1_name / "A_lvr_land_A.csv", "台北市", "中古屋"),
        (base_dir_old / f"{next_roc}" / q1_name / "F_lvr_land_A.csv", "新北市", "中古屋"),
        (base_dir_new / f"{next_roc}" / q1_name / "a_lvr_buildcase.csv", "台北市", "預售屋"),
        (base_dir_new / f"{next_roc}" / q1_name / "f_lvr_buildcase.csv", "新北市", "預售屋"),
    ]

    add_parts = []
    for fp, region, prop in files:
        part = process_q1_file(fp, region, prop, target_west)
        if part is not None and len(part) > 0:
            add_parts.append(part)
            print(f"  + {region} {prop}: {len(part):,} 筆")
        else:
            print(f"  - {region} {prop}: 0 筆（或檔案不存在）")

    if not add_parts:
        print("  [INFO] 本年無可回補資料")
        return

    add_df = pd.concat(add_parts, ignore_index=True)
    before = len(current_df)

    # 合併 + 去重
    combined = pd.concat([current_df, add_df], ignore_index=True)

    # 優先以編號去重，避免重複併入
    dedup_keys = [k for k in ["地區", "編號", "交易年_西元", "交易月", "總價_萬", "坪數"] if k in combined.columns]
    if dedup_keys:
        combined = combined.drop_duplicates(subset=dedup_keys, keep="first")
    else:
        combined = combined.drop_duplicates(keep="first")

    after = len(combined)
    added_net = after - before

    # 備份 + 覆寫
    backup_fp = backup_dir / year_fp.name
    if not backup_fp.exists():
        current_df.to_csv(backup_fp, index=False, encoding="utf-8-sig")
    combined.to_csv(year_fp, index=False, encoding="utf-8-sig")

    months = sorted(
        combined.loc[combined["交易年_西元"] == target_west, "交易月"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    print(f"  [DONE] {year_fp.name}: 原 {before:,} 筆 -> 新 {after:,} 筆 (淨增加 {added_net:,} 筆)")
    print(f"  [CHECK] {target_west} 年月份: {months}")


# 可完整回補的年度：110~113（因為需要 111~114 年Q1）
for roc in range(110, 114):
    reconcile_year(roc)

print("\n" + "=" * 72)
print("完成：110~113年已回補隔年Q1中的前一年全部月份（1~12月）")
print("注意：114年(2025)要完整，需等待115年(2026)第1季資料")
print(f"備份位置：{backup_dir}")
print("=" * 72)
