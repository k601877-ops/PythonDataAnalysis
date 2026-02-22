import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("批次清理程式 v2 - 110~114年 全年資料（含預售屋）")
print("=" * 70)

# 基本設定
base_dir_old = Path('110~114中古')
base_dir_new = Path('110~114預售')
output_dir = Path('data_processed/按年份整理')
output_dir.mkdir(parents=True, exist_ok=True)

# 最終輸出欄位
output_cols = [
    '地區', '鄉鎮市區', '土地位置建物門牌', '交易標的',
    '交易年月', '交易年_西元', '交易月',
    '總價_萬', '坪數', 
    '車位價格_萬', '車位面積_坪',
    '不含車位總價_萬', '不含車位坪數', '不含車位單價_萬坪',
    '建物型態', '屋齡', '移轉層次', '總樓層數',
    '戶型', '房數', '廳數', '衛數',
    '有無管理組織', '是否預售屋', '備註', '編號'
]

def process_file(file_path, region_name, property_type):
    """處理單一檔案"""
    if not Path(file_path).exists():
        return None
    
    try:
        # 讀取
        df = pd.read_csv(file_path, skiprows=[1], encoding="utf-8", dtype_backend='numpy_nullable')
        initial_count = len(df)
        
        # 需要欄位
        keep_cols = ['鄉鎮市區', '土地位置建物門牌', '交易標的', '交易年月日', 
                     '總價元', '車位總價元', '建物移轉總面積平方公尺', '車位移轉總面積平方公尺',
                     '建物型態', '建築完成年月', '移轉層次', '總樓層數',
                     '建物現況格局-房', '建物現況格局-廳', '建物現況格局-衛',
                     '有無管理組織', '備註', '編號']
        
        # 只保留存在的欄位
        available_cols = [c for c in keep_cols if c in df.columns]
        df = df[available_cols].copy()
        df['地區'] = region_name
        
        # 數值轉換
        df['總價元'] = pd.to_numeric(df['總價元'], errors='coerce')
        df['建物移轉總面積平方公尺'] = pd.to_numeric(df['建物移轉總面積平方公尺'], errors='coerce')
        df['車位總價元'] = df['車位總價元'].fillna(0)
        df['車位移轉總面積平方公尺'] = df['車位移轉總面積平方公尺'].fillna(0)
        
        # 標記特殊交易
        special_keywords = ['親友', '員工', '共有人', '特殊關係']
        df['是否特殊交易'] = df['備註'].fillna('').apply(
            lambda x: any(k in str(x) for k in special_keywords)
        )
        
        # 標記預售屋
        df['是否預售屋'] = True if property_type == '預售屋' else False
        
        # 過濾條件
        if '交易標的' in df.columns:
            df = df[df['交易標的'].str.contains('房地', na=False)]
        df = df[(df['總價元'] > 0) & (df['建物移轉總面積平方公尺'] > 0)]
        
        # 過濾特殊交易
        special_count = len(df[df['是否特殊交易']])
        df = df[~df['是否特殊交易']]
        
        # 計算衍生欄位
        df['坪數'] = df['建物移轉總面積平方公尺'] / 3.30579
        df['車位面積_坪'] = df['車位移轉總面積平方公尺'] / 3.30579
        df['車位價格_萬'] = df['車位總價元'] / 10000
        
        df['不含車位總價_萬'] = (df['總價元'] - df['車位總價元']) / 10000
        df['不含車位坪數'] = df['坪數'] - df['車位面積_坪']
        df['不含車位單價_萬坪'] = np.where(
            df['不含車位坪數'] > 0,
            df['不含車位總價_萬'] / df['不含車位坪數'],
            np.nan
        )
        
        df['總價_萬'] = df['總價元'] / 10000
        
        # 交易年月
        df['交易年月日_str'] = df['交易年月日'].astype(str).str.zfill(7)
        df['交易年_民國'] = df['交易年月日_str'].str[:3].astype(int)
        df['交易月'] = df['交易年月日_str'].str[3:5].astype(int)
        df['交易年_西元'] = df['交易年_民國'] + 1911
        df['交易年月'] = df['交易年_西元'].astype(str) + '-' + df['交易月'].astype(str).str.zfill(2)
        
        # 屋齡
        df['建築完成年月_str'] = df['建築完成年月'].fillna('0').astype(str).str.zfill(7)
        df['建築完成年_民國'] = pd.to_numeric(df['建築完成年月_str'].str[:3], errors='coerce')
        df['建築完成年_西元'] = df['建築完成年_民國'] + 1911
        df['屋齡'] = (df['交易年_西元'] - df['建築完成年_西元']).clip(0, 100)
        
        # 戶型
        df['房數'] = pd.to_numeric(df.get('建物現況格局-房', 0), errors='coerce').fillna(0).astype(int)
        df['廳數'] = pd.to_numeric(df.get('建物現況格局-廳', 0), errors='coerce').fillna(0).astype(int)
        df['衛數'] = pd.to_numeric(df.get('建物現況格局-衛', 0), errors='coerce').fillna(0).astype(int)
        df['戶型'] = df['房數'].astype(str) + '房' + df['廳數'].astype(str) + '廳' + df['衛數'].astype(str) + '衛'
        
        # 選擇輸出欄位
        df = df[[c for c in output_cols if c in df.columns]]
        
        print(f"    ✓ {property_type:s} {region_name}: {initial_count} → {len(df):,} 筆 (移除 {special_count} 筆特殊交易)")
        return df
        
    except Exception as e:
        print(f"    ❌ 錯誤：{str(e)}")
        return None

# 掃描所有年份
print("\n開始處理...\n")
year_data = {}  # {年份: pd.DataFrame}

for year in range(110, 115):  # 110, 111, 112, 113, 114
    year_data[year] = []
    print(f"【{year}年】")
    
    # 四個季度
    for quarter in range(1, 5):
        quarter_name = f"{year}年第{quarter}季"
        print(f"  {quarter_name}:")
        
        # 中古屋
        old_tp = base_dir_old / f"{year}" / quarter_name / "A_lvr_land_A.csv"
        old_nt = base_dir_old / f"{year}" / quarter_name / "F_lvr_land_A.csv"
        
        df_tp = process_file(str(old_tp), '台北市', '中古屋')
        df_nt = process_file(str(old_nt), '新北市', '中古屋')
        
        # 預售屋（檔案名稱不同）
        new_tp = base_dir_new / f"{year}" / quarter_name / "a_lvr_buildcase.csv"
        new_nt = base_dir_new / f"{year}" / quarter_name / "f_lvr_buildcase.csv"
        
        df_tp_presale = process_file(str(new_tp), '台北市', '預售屋')
        df_nt_presale = process_file(str(new_nt), '新北市', '預售屋')
        
        # 合併該季度資料
        quarter_dfs = [df for df in [df_tp, df_nt, df_tp_presale, df_nt_presale] if df is not None]
        if quarter_dfs:
            quarter_df = pd.concat(quarter_dfs, ignore_index=True)
            year_data[year].append(quarter_df)
    
    # 補齊12月資料（從隔年第1季檔案中抓取）
    next_year = year + 1
    if next_year <= 114:  # 確保隔年檔案存在
        next_q1_name = f"{next_year}年第1季"
        print(f"  補齊12月（從{next_q1_name}）:")
        
        dec_count = 0
        target_year_west = year + 1911  # 目標西元年
        
        # 中古屋
        old_tp_next = base_dir_old / f"{next_year}" / next_q1_name / "A_lvr_land_A.csv"
        old_nt_next = base_dir_old / f"{next_year}" / next_q1_name / "F_lvr_land_A.csv"
        
        df_tp_next = process_file(str(old_tp_next), '台北市', '中古屋')
        df_nt_next = process_file(str(old_nt_next), '新北市', '中古屋')
        
        # 預售屋
        new_tp_next = base_dir_new / f"{next_year}" / next_q1_name / "a_lvr_buildcase.csv"
        new_nt_next = base_dir_new / f"{next_year}" / next_q1_name / "f_lvr_buildcase.csv"
        
        df_tp_presale_next = process_file(str(new_tp_next), '台北市', '預售屋')
        df_nt_presale_next = process_file(str(new_nt_next), '新北市', '預售屋')
        
        # 從隔年第1季資料中篩選出當年12月的資料
        for df_next in [df_tp_next, df_nt_next, df_tp_presale_next, df_nt_presale_next]:
            if df_next is not None and '交易年_西元' in df_next.columns and '交易月' in df_next.columns:
                df_dec = df_next[(df_next['交易年_西元'] == target_year_west) & (df_next['交易月'] == 12)].copy()
                if len(df_dec) > 0:
                    year_data[year].append(df_dec)
                    dec_count += len(df_dec)
        
        if dec_count > 0:
            print(f"    ✓ 補入 {dec_count} 筆12月資料")
        else:
            print(f"    ⚠ 未找到12月資料")
    
    # 合併該年所有季度
    if year_data[year]:
        year_df = pd.concat(year_data[year], ignore_index=True)
        year_data[year] = year_df
        print(f"  ➜ {year}年合計：{len(year_df):,} 筆\n")
    else:
        year_data[year] = None

# 儲存各年檔案
print("\n" + "=" * 70)
print("儲存結果")
print("=" * 70 + "\n")

for year, df in year_data.items():
    if df is not None and len(df) > 0:
        output_file = output_dir / f"{year}年_已清理.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        # 統計
        tp_count = len(df[df['地區'] == '台北市'])
        nt_count = len(df[df['地區'] == '新北市'])
        presale_count = len(df[df['是否預售屋']])
        
        print(f"✅ {output_file.name}")
        print(f"   總筆數：{len(df):,} | 台北：{tp_count:,} | 新北：{nt_count:,} | 預售：{presale_count:,}")
        print(f"   平均價格：{df['總價_萬'].mean():.0f}萬 | 平均單價：{df['不含車位單價_萬坪'].mean():.1f}萬/坪\n")

print("=" * 70)
print(f"✅ 全部完成！檔案位置：{output_dir}")
print("=" * 70)
