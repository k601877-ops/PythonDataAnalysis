import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime

# ========== 頁面配置 ==========
st.set_page_config(
	page_title="雙北購屋決策分析系統",
	page_icon="🏠",
	layout="wide",
	initial_sidebar_state="expanded"
)

# ========== 樣式 ==========
st.markdown("""
<style>
	body {
		font-size: 20px !important;
	}
	.main-title {
		font-size: 4.2em;
		font-weight: bold;
		color: #1f77b4;
		margin-bottom: 0.5em;
	}
	.subtitle {
		font-size: 2.2em;
		color: #666;
		margin-bottom: 2em;
	}
	h1 {
		font-size: 2.9em !important;
	}
	h2 {
		font-size: 2.4em !important;
	}
	h3 {
		font-size: 2.1em !important;
	}
	label, [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] {
		font-size: 1.15rem !important;
	}
	[data-testid="stMetricValue"] {
		font-size: 34px !important;
	}
	[data-testid="stMetricLabel"] {
		font-size: 18px !important;
	}
	[role="row"] {
		font-size: 18px !important;
	}
</style>
""", unsafe_allow_html=True)

# ========== 政策事件（依時間排序） ==========
POLICY_EVENTS = [
	{
		"date": "2020 H2–2021 H1",
		"plot_date": "2021-02",
		"icon": "🚀",
		"name": "疫情控管成功＋資金寬鬆，交易量與房價走強（市場現象）",
		"impact": "positive",
	},
	{
		"date": "2022-03～2022-06",
		"plot_date": "2022-03",
		"icon": "📊",
		"name": "央行啟動升息循環，房貸成本上升（貨幣政策轉向）",
		"impact": "negative",
	},
	{
		"date": "2023-08",
		"plot_date": "2023-08",
		"icon": "🏛️",
		"name": "新青安貸款方案上路，首購需求被明顯拉抬（政策刺激）",
		"impact": "positive",
	},
	{
		"date": "2024 Q3–Q4",
		"plot_date": "2024-07",
		"icon": "📉",
		"name": "選擇性信用管制再收緊，市場預期降溫（管制升級）",
		"impact": "negative",
	},
]


def wrap_event_label(text, width=18):
	if len(text) <= width:
		return text
	parts = [text[i:i + width] for i in range(0, len(text), width)]
	return "<br>".join(parts[:3])


def parse_event_month(date_str):
	if not date_str:
		return None
	if "-Q" in date_str:
		year_str, quarter = date_str.split("-Q")
		month_map = {"1": "02", "2": "05", "3": "08", "4": "11"}
		return pd.to_datetime(
			f"{year_str}-{month_map.get(quarter, '02')}-01",
			format="%Y-%m-%d",
			errors="coerce",
		)
	if " H" in date_str:
		year_str, half = date_str.split(" H")
		half_map = {"1": "03", "2": "09"}
		return pd.to_datetime(
			f"{year_str}-{half_map.get(half, '03')}-01",
			format="%Y-%m-%d",
			errors="coerce",
		)
	return pd.to_datetime(date_str + "-01", format="%Y-%m-%d", errors="coerce")

# ========== 資料載入 ==========
@st.cache_data
def load_all_data():
	data_dir = Path('data_processed/按年份整理')
	dfs = []
	for file_path in sorted(data_dir.glob("*年_已清理.csv")):
		df = pd.read_csv(file_path)
		dfs.append(df)

	if dfs:
		df_all = pd.concat(dfs, ignore_index=True)
		df_all["交易年月"] = pd.to_datetime(df_all["交易年月"], format="%Y-%m", errors="coerce")
		df_all["交易年_西元"] = df_all["交易年_西元"].astype(int)
		df_all["交易月"] = df_all["交易月"].astype(int)
		return df_all
	return None


df_data = load_all_data()

if df_data is None:
	st.error("❌ 無法載入資料")
	st.stop()

# ========== 側邊欄篩選 ==========
st.sidebar.markdown("### 🎛️ 篩選條件")

cities = sorted(df_data["地區"].unique())
selected_cities = st.sidebar.multiselect("🏙️ 選擇城市", cities, default=cities)

years = sorted(df_data["交易年_西元"].unique())
selected_year = st.sidebar.multiselect("📅 選擇年份", years, default=years)

selected_quarter = st.sidebar.multiselect(
	"📊 選擇季度",
	[1, 2, 3, 4],
	default=[1, 2, 3, 4],
	format_func=lambda x: f"Q{x}",
)

selected_month = st.sidebar.multiselect(
	"🗓️ 選擇月份",
	range(1, 13),
	default=range(1, 13),
	format_func=lambda x: f"{x:02d}月",
)

df_city = df_data[df_data["地區"].isin(selected_cities)]
districts = sorted(df_city["鄉鎮市區"].unique())
selected_districts = st.sidebar.multiselect("📍 選擇行政區", districts, default=districts)

# 建物型態篩選
building_types = sorted(df_data["建物型態"].dropna().unique())
selected_building_types = st.sidebar.multiselect(
	"🏢 選擇建物型態",
	building_types,
	default=building_types,
	help="包含住宅、店面、廠房等各類建物，未選會納入所有類型"
)

# ========== 資料篩選 ==========
df_filtered = df_data[
	(df_data["地區"].isin(selected_cities))
	& (df_data["交易年_西元"].isin(selected_year))
	& (df_data["交易月"].isin(selected_month))
	& (df_data["鄉鎮市區"].isin(selected_districts))
	& (df_data["建物型態"].isin(selected_building_types))
].copy()

df_filtered["季度"] = df_filtered["交易月"].apply(lambda x: (x - 1) // 3 + 1)
df_filtered = df_filtered[df_filtered["季度"].isin(selected_quarter)]

# ========== 主標題 ==========
st.markdown(
	"<div style=\"font-size: 2.5em; font-weight: bold; color: #1f77b4;\">🏠 雙北購屋決策分析系統</div>",
	unsafe_allow_html=True,
)
st.markdown(
	"<div style=\"font-size: 1.2em; color: #666;\">聚焦房市成交熱度 • 揭露市場真相</div>",
	unsafe_allow_html=True,
)

# ========== 頁面導航 ==========
page = st.sidebar.radio(
	"📑 選擇分析頁面",
	["📊 首頁 - 成交熱度分析", "🗺️ 行政區成交對比", "📐 行政區單價趨勢", "🔮 價格預測"],
)

# ========== PAGE 1 ==========
if page == "📊 首頁 - 成交熱度分析":
	st.subheader("📊 房市成交熱度分析")

	col1, col2, col3 = st.columns(3)
	with col1:
		st.metric("📊 總成交筆數", f"{len(df_filtered):,}")
	with col2:
		monthly_avg = len(df_filtered) / max(df_filtered["交易年月"].dt.to_period("M").nunique(), 1)
		st.metric("📈 月均成交", f"{monthly_avg:.0f}")
	with col3:
		st.metric("📐 平均坪數", f"{df_filtered['坪數'].mean():.1f}坪")

	st.divider()

	st.subheader("📌 重大政策/市場事件時間線")
	for event in POLICY_EVENTS:
		impact = event.get("impact", "neutral")
		if impact == "positive":
			color = "green"
		elif impact == "negative":
			color = "red"
		else:
			color = "#999"
		st.markdown(
			f"<div style=\"border-left: 4px solid {color}; padding: 0.5em;\"><b>{event['date']} {event['icon']}</b> {event['name']}</div>",
			unsafe_allow_html=True,
		)

	st.divider()

	st.subheader("📊 月度成交件數趨勢 (含政策事件標記)")
	st.caption("💡 資料完整性說明：實價登錄12月交易資料因登記延遲特性，大部分集中在隔年1月公開。本資料已補齊110-113年的隔年Q1延遲資料，但仍存在逐步整合空間。")

	monthly_count = df_filtered.groupby("交易年月").size().reset_index(name="成交件數")
	monthly_count = monthly_count.sort_values("交易年月")
	if not monthly_count.empty:
		full_months = pd.date_range(
			start=monthly_count["交易年月"].min(),
			end=monthly_count["交易年月"].max(),
			freq="MS",
		)
		monthly_count = (
			monthly_count.set_index("交易年月")
			.reindex(full_months, fill_value=0)
			.rename_axis("交易年月")
			.reset_index()
		)

	fig = go.Figure()
	fig.add_trace(
		go.Bar(
			x=monthly_count["交易年月"],
			y=monthly_count["成交件數"],
			name="成交件數",
			marker=dict(color="rgba(31, 119, 180, 0.7)"),
		)
	)

	# 添加政策事件標記線（滑鼠移上去才顯示）
	shapes = []
	annotations = []
	hover_x = []
	hover_y = []
	hover_text = []
	colors = {"positive": "green", "negative": "red", "neutral": "#999"}
	if not monthly_count.empty:
		min_month = monthly_count["交易年月"].min()
		max_month = monthly_count["交易年月"].max()
		max_count = monthly_count["成交件數"].max() if len(monthly_count) else 0

		# 事件分段背景色
		event_points = []
		for event in POLICY_EVENTS:
			event_month = parse_event_month(event.get("plot_date"))
			if pd.notna(event_month):
				event_points.append((event_month, event))
		event_points = sorted(event_points, key=lambda x: x[0])
		segment_colors = [
			"rgba(0, 123, 255, 0.06)",
			"rgba(40, 167, 69, 0.06)",
			"rgba(255, 193, 7, 0.06)",
			"rgba(220, 53, 69, 0.06)",
		]
		for idx, (start_month, _) in enumerate(event_points):
			end_month = event_points[idx + 1][0] if idx + 1 < len(event_points) else max_month
			if end_month < min_month or start_month > max_month:
				continue
			shapes.append(
				dict(
					type="rect",
					x0=max(start_month, min_month),
					x1=min(end_month, max_month),
					y0=0,
					y1=1,
					yref="paper",
					line=dict(width=0),
					fillcolor=segment_colors[idx % len(segment_colors)],
					layer="below",
				)
			)

		for event in POLICY_EVENTS:
			event_month = parse_event_month(event.get("plot_date"))
			if pd.notna(event_month) and min_month <= event_month <= max_month:
				line_color = colors.get(event.get("impact", "neutral"), "#999")
				label_text = f"{event['date']} {event['icon']} {event['name']}"
				label_text = wrap_event_label(label_text, width=18)
				shapes.append(
					dict(
						type="line",
						x0=event_month,
						x1=event_month,
						y0=0,
						y1=1,
						yref="paper",
						line=dict(color=line_color, width=2, dash="dash"),
					)
				)
				hover_x.append(event_month)
				hover_y.append(max_count * 1.05)
				hover_text.append(label_text)

		if hover_x:
			fig.add_trace(
				go.Scatter(
					x=hover_x,
					y=hover_y,
					mode="markers",
					marker=dict(size=12, color="rgba(0,0,0,0.15)"),
					hovertext=hover_text,
					hoverinfo="text",
					showlegend=False,
				)
			)

	fig.update_layout(
		title="月度成交件數趨勢 (虛線標記政策事件: 綠=正面 紅=負面)",
		xaxis_title="交易時間",
		yaxis_title="成交件數",
		font=dict(size=19),
		title_font=dict(size=28),
		xaxis=dict(
			tickformat="%Y-%m",  # 顯示 年-月 格式
			dtick="M1",  # 每個月都顯示刻度
			tickangle=-45,  # 標籤傾斜45度，避免重疊
			tickfont=dict(size=17),
		),
		yaxis=dict(tickfont=dict(size=17)),
		hovermode="x unified",
		height=550,
		shapes=shapes,
		showlegend=True,
	)
	st.plotly_chart(fig, use_container_width=True)

	st.subheader("📈 年度成交件數對比")
	yearly_count = (
		df_filtered.groupby("交易年_西元")
		.size()
		.reset_index(name="成交件數")
		.sort_values("交易年_西元")
	)
	fig_year = go.Figure(
		data=[
			go.Bar(
				x=yearly_count["交易年_西元"],
				y=yearly_count["成交件數"],
				marker=dict(
					color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"][
						: len(yearly_count)
					]
				),
				text=yearly_count["成交件數"],
				textposition="outside",
			)
		]
	)
	fig_year.update_layout(
		title="各年度成交件數比較",
		xaxis_title="年份",
		yaxis_title="成交件數",
		font=dict(size=19),
		title_font=dict(size=28),
		yaxis=dict(range=[0, 70000]),
		height=420,
		margin=dict(t=60),
		showlegend=False,
	)
	st.plotly_chart(fig_year, use_container_width=True)

	# ===== 新增：月度量價雙軸圖 =====
	st.subheader("📊 月度成交量 vs 平均單價 (雙軸分析)")
	st.caption("展現交易量與房價的聯動關係、分離現象與政策效應")
	
	monthly_price = df_filtered.copy()
	monthly_price = monthly_price[pd.notna(monthly_price["不含車位單價_萬坪"])]
	monthly_stats = monthly_price.groupby("交易年月").agg({
		"不含車位單價_萬坪": "mean",
		"總價_萬": "count"
	}).reset_index()
	monthly_stats.columns = ["交易年月", "平均單價_萬坪", "成交件數"]
	monthly_stats = monthly_stats.sort_values("交易年月")
	
	if not monthly_stats.empty:
		fig_dual = go.Figure()
		
		# 左軸：成交件數 (柱狀)
		fig_dual.add_trace(go.Bar(
			x=monthly_stats["交易年月"],
			y=monthly_stats["成交件數"],
			name="成交件數",
			marker=dict(color="rgba(31, 119, 180, 0.6)"),
			yaxis="y"
		))
		
		# 右軸：平均單價 (折線)
		fig_dual.add_trace(go.Scatter(
			x=monthly_stats["交易年月"],
			y=monthly_stats["平均單價_萬坪"],
			name="平均單價 (萬/坪)",
			mode="lines+markers",
			line=dict(color="red", width=3),
			marker=dict(size=6),
			yaxis="y2"
		))
		
		fig_dual.update_layout(
			title="月度成交件數 vs 平均單價 (雙軸對比)",
			xaxis_title="交易時間",
			yaxis=dict(
				title=dict(text="成交件數", font=dict(color="rgba(31, 119, 180, 0.8)", size=16)),
				tickfont=dict(color="rgba(31, 119, 180, 0.8)", size=14),
			),
			yaxis2=dict(
				title=dict(text="平均單價 (萬元/坪)", font=dict(color="red", size=16)),
				tickfont=dict(color="red", size=14),
				overlaying="y",
				side="right"
			),
			font=dict(size=17),
			title_font=dict(size=24),
			hovermode="x unified",
			height=450,
			xaxis=dict(tickangle=-45),
		)
		st.plotly_chart(fig_dual, use_container_width=True)
	
	st.divider()
	
	# ===== 新增：政策事件前後對比表 =====
	st.subheader("📌 政策事件前後對比 - 量價效應分析")
	st.caption("比較各政策事件前3個月 vs 後3個月的交易量與單價變化")
	
	policy_comparison = []
	for event in POLICY_EVENTS:
		event_date = parse_event_month(event.get("plot_date"))
		if pd.isna(event_date):
			continue
		
		# 前3月數據
		before_start = event_date - pd.DateOffset(months=3)
		before_data = df_filtered[
			(df_filtered["交易年月"] >= before_start) & 
			(df_filtered["交易年月"] < event_date)
		]
		
		# 後3月數據
		after_end = event_date + pd.DateOffset(months=3)
		after_data = df_filtered[
			(df_filtered["交易年月"] >= event_date) & 
			(df_filtered["交易年月"] < after_end)
		]
		
		if len(before_data) > 0 and len(after_data) > 0:
			before_vol = len(before_data)
			after_vol = len(after_data)
			vol_change = ((after_vol - before_vol) / before_vol * 100) if before_vol > 0 else 0
			
			before_price = before_data["不含車位單價_萬坪"].dropna().mean()
			after_price = after_data["不含車位單價_萬坪"].dropna().mean()
			price_change = ((after_price - before_price) / before_price * 100) if before_price > 0 else 0
			
			policy_comparison.append({
				"🎯 政策事件": event['date'],
				"📝 說明": event['name'],
				"📊 前3月交易": before_vol,
				"📈 後3月交易": after_vol,
				"📉 交易量變化 %": f"{vol_change:+.1f}%",
				"💰 前3月單價": f"{before_price:.2f}",
				"💵 後3月單價": f"{after_price:.2f}",
				"📊 單價變化 %": f"{price_change:+.1f}%"
			})
	
	if policy_comparison:
		policy_df = pd.DataFrame(policy_comparison)
		st.dataframe(policy_df, use_container_width=True, hide_index=True)
	
	st.divider()
	
	# ===== 新增：交易量Top10行政區排行 =====
	st.subheader("🏆 交易量 Top 10 行政區排行榜")
	st.caption("驗證區域分化假設：蛋白區交易量遠超蛋黃區")
	
	top10_districts = (
		df_filtered.groupby("鄉鎮市區")
		.agg({
			"交易年月": "count",
			"不含車位單價_萬坪": "mean",
			"坪數": "mean"
		})
		.rename(columns={
			"交易年月": "交易件數",
			"不含車位單價_萬坪": "平均單價_萬坪",
			"坪數": "平均坪數"
		})
		.reset_index()
		.sort_values("交易件數", ascending=False)
		.head(10)
		.round(2)
	)
	
	fig_top10 = px.bar(
		top10_districts,
		x="鄉鎮市區",
		y="交易件數",
		color="平均單價_萬坪",
		color_continuous_scale="Viridis",
		text="交易件數",
		title="Top 10行政區交易量（顏色深度=單價高度）"
	)
	fig_top10.update_traces(textposition="auto")
	fig_top10.update_layout(
		height=450,
		font=dict(size=16),
		title_font=dict(size=22),
		xaxis_tickangle=-45,
	)
	st.plotly_chart(fig_top10, use_container_width=True)

elif page == "🗺️ 行政區成交對比":
	st.subheader("🗺️ 行政區房市成交熱度")
	district_stats = (
		df_filtered.groupby("鄉鎮市區")
		.agg({"總價_萬": "median", "交易年月": "count", "坪數": "mean"})
		.round(2)
	)
	district_stats.columns = ["中位數價格_萬", "成交件數", "平均坪數"]
	district_stats = district_stats.reset_index().sort_values("成交件數", ascending=False)

	col1, col2 = st.columns(2)
	with col1:
		st.subheader("🔥 TOP 10 成交熱度")
		fig = px.bar(
			district_stats.head(10),
			x="鄉鎮市區",
			y="成交件數",
			color="中位數價格_萬",
			color_continuous_scale="YlOrRd",
		)
		fig.update_layout(
			height=400,
			xaxis_tickangle=-45,
			font=dict(size=17),
			title_font=dict(size=24),
		)
		st.plotly_chart(fig, use_container_width=True)

	with col2:
		st.subheader("💰 TOP 10 最高中位價格")
		fig = px.bar(
			district_stats.nlargest(10, "中位數價格_萬"),
			x="鄉鎮市區",
			y="中位數價格_萬",
			color="成交件數",
			color_continuous_scale="Blues",
		)
		fig.update_layout(
			height=400,
			xaxis_tickangle=-45,
			font=dict(size=17),
			title_font=dict(size=24),
		)
		st.plotly_chart(fig, use_container_width=True)

	st.subheader("📋 全部行政區統計")
	st.dataframe(district_stats, use_container_width=True, hide_index=True)

elif page == "📐 行政區單價趨勢":
	st.subheader("📐 行政區單價趨勢")
	st.caption("以『不含車位單價_萬坪』計算平均單價，支援年/季/月區間")

	metric_col = "不含車位單價_萬坪"
	period = st.selectbox("選擇期間", ["年", "季", "月"], index=0)

	price_df = df_filtered.copy()
	price_df = price_df[pd.notna(price_df[metric_col])]

	if period == "年":
		price_df["期間"] = price_df["交易年_西元"].astype(str)
		price_df["期間排序"] = price_df["交易年_西元"]
	elif period == "季":
		price_df["期間"] = price_df["交易年_西元"].astype(str) + " Q" + price_df["季度"].astype(str)
		price_df["期間排序"] = price_df["交易年_西元"] * 10 + price_df["季度"]
	else:
		price_df["期間"] = price_df["交易年月"].dt.strftime("%Y-%m")
		price_df["期間排序"] = price_df["交易年_西元"] * 100 + price_df["交易月"]

	grouped = (
		price_df.groupby(["期間", "期間排序", "鄉鎮市區"])[metric_col]
		.mean()
		.reset_index()
		.sort_values("期間排序")
	)

	district_options = sorted(grouped["鄉鎮市區"].unique())
	selected_trend_districts = st.multiselect(
		"選擇要比較的行政區",
		district_options,
		default=district_options,
	)

	if selected_trend_districts:
		trend_df = grouped[grouped["鄉鎮市區"].isin(selected_trend_districts)]
		period_order = trend_df["期間"].drop_duplicates().tolist()
		fig_trend = px.line(
			trend_df,
			x="期間",
			y=metric_col,
			color="鄉鎮市區",
			markers=True,
			category_orders={"期間": period_order},
		)
		fig_trend.update_layout(
			title="行政區平均單價趨勢",
			xaxis_title="期間",
			yaxis_title="平均單價（萬元/坪）",
			font=dict(size=19),
			title_font=dict(size=28),
			height=450,
		)
		st.plotly_chart(fig_trend, use_container_width=True)
	else:
		st.info("請至少選擇一個行政區。")

	st.subheader("📋 行政區平均單價明細")
	pivot = grouped.pivot(index="期間", columns="鄉鎮市區", values=metric_col).round(2)
	# Filter by selected districts
	pivot_filtered = pivot[[col for col in pivot.columns if col in selected_trend_districts]]
	if not pivot_filtered.empty:
		styled_html = (
			pivot_filtered.style
			.format("{:.2f}", na_rep="—")
			.set_table_styles([
				{"selector": "th", "props": [("font-size", "24px"), ("font-weight", "700"), ("text-align", "center")]},
				{"selector": "td", "props": [("font-size", "22px"), ("text-align", "center")]},
			])
			.to_html()
		)
		st.markdown(
			f"<div style='overflow-x:auto; border:1px solid #e6e6e6; border-radius:8px; padding:8px;'>{styled_html}</div>",
			unsafe_allow_html=True,
		)
	else:
		st.info("請先在上方選擇行政區查看明細")

elif page == "🔮 價格預測":
	st.subheader("🔮 價格預測分析")
	st.info("⏳ 此功能正在開發中，敬請期待...")

st.divider()
st.markdown(
	"<div style=\"text-align: center; color: #999; font-size: 0.9em;\">雙北購屋決策分析系統 v2.0 | 以成交件數為核心分析指標</div>",
	unsafe_allow_html=True,
)
