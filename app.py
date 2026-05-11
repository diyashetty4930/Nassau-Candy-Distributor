
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── PAGE CONFIG ────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy Distributor",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .block-container { padding-top: 1rem; }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 { color: #2d2d2d; }
    h2 { color: #4C72B0; }
</style>
""", unsafe_allow_html=True)

# ── LOAD & PREPARE DATA ────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("Nassau Candy Distributor.csv")
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True)
    df["Ship Date"]  = pd.to_datetime(df["Ship Date"],  dayfirst=True)

    df["raw_diff"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Ship Date"] = np.where(df["raw_diff"] <= 915,
        df["Ship Date"] - pd.Timedelta(days=730),
        np.where(df["raw_diff"] <= 1280,
            df["Ship Date"] - pd.Timedelta(days=1095),
            df["Ship Date"] - pd.Timedelta(days=1461)
        )
    )
    df["Ship Date"] = pd.to_datetime(df["Ship Date"])
    df.drop(columns=["raw_diff"], inplace=True)

    df["Lead Time (Days)"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df = df[df["Lead Time (Days)"] > 0]

    product_factory_map = {
        "Wonka Bar - Nutty Crunch Surprise"  : "Lot's O' Nuts",
        "Wonka Bar - Fudge Mallows"          : "Lot's O' Nuts",
        "Wonka Bar -Scrumdiddlyumptious"     : "Lot's O' Nuts",
        "Wonka Bar - Milk Chocolate"         : "Wicked Choccy's",
        "Wonka Bar - Triple Dazzle Caramel"  : "Wicked Choccy's",
        "Laffy Taffy"                        : "Sugar Shack",
        "SweeTARTS"                          : "Sugar Shack",
        "Nerds"                              : "Sugar Shack",
        "Fun Dip"                            : "Sugar Shack",
        "Fizzy Lifting Drinks"               : "Sugar Shack",
        "Everlasting Gobstopper"             : "Secret Factory",
        "Lickable Wallpaper"                 : "Secret Factory",
        "Wonka Gum"                          : "Secret Factory",
        "Kazookles"                          : "The Other Factory",
        "Hair Toffee"                        : "The Other Factory"
    }
    df["Factory"]        = df["Product Name"].map(product_factory_map)
    df["Route (State)"]  = df["Factory"] + " → " + df["State/Province"]
    df["Route (Region)"] = df["Factory"] + " → " + df["Region"]
    df["Month-Year"]     = df["Order Date"].dt.to_period("M").astype(str)

    delay_threshold  = df["Lead Time (Days)"].quantile(0.75)
    df["Is_Delayed"] = df["Lead Time (Days)"] > delay_threshold

    return df

df = load_data()

# ── SIDEBAR ────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/emoji/96/candy-emoji.png", width=80)
st.sidebar.title("🍬 Nassau Candy")
st.sidebar.markdown("### Filters")

# Date filter
min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()
date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Region filter
all_regions  = ["All"] + sorted(df["Region"].unique().tolist())
selected_region = st.sidebar.selectbox("Region", all_regions)

# Ship Mode filter
all_modes = ["All"] + sorted(df["Ship Mode"].unique().tolist())
selected_mode = st.sidebar.selectbox("Ship Mode", all_modes)

# Lead Time slider
lt_min = int(df["Lead Time (Days)"].min())
lt_max = int(df["Lead Time (Days)"].max())
lt_range = st.sidebar.slider(
    "Lead Time Range (Days)",
    min_value=lt_min,
    max_value=lt_max,
    value=(lt_min, lt_max)
)

# Factory filter
all_factories = ["All"] + sorted(df["Factory"].dropna().unique().tolist())
selected_factory = st.sidebar.selectbox("Factory", all_factories)

# ── APPLY FILTERS ──────────────────────────────────────────
filtered = df.copy()
if len(date_range) == 2:
    filtered = filtered[
        (filtered["Order Date"].dt.date >= date_range[0]) &
        (filtered["Order Date"].dt.date <= date_range[1])
    ]
if selected_region != "All":
    filtered = filtered[filtered["Region"] == selected_region]
if selected_mode != "All":
    filtered = filtered[filtered["Ship Mode"] == selected_mode]
if selected_factory != "All":
    filtered = filtered[filtered["Factory"] == selected_factory]
filtered = filtered[
    (filtered["Lead Time (Days)"] >= lt_range[0]) &
    (filtered["Lead Time (Days)"] <= lt_range[1])
]

# ── HEADER ─────────────────────────────────────────────────
st.title("🍬 Nassau Candy Distributor")
st.markdown("### Factory-to-Customer Shipping Route Efficiency Dashboard")
st.markdown("---")

# ── KPI CARDS ──────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📦 Total Orders",    f"{len(filtered):,}")
k2.metric("⏱️ Avg Lead Time",   f"{filtered['Lead Time (Days)'].mean():.1f} days")
k3.metric("🚨 Delay Rate",      f"{filtered['Is_Delayed'].mean()*100:.1f}%")
k4.metric("💰 Total Sales",     f"${filtered['Sales'].sum():,.0f}")
k5.metric("📈 Total Profit",    f"${filtered['Gross Profit'].sum():,.0f}")

st.markdown("---")

# ── TAB LAYOUT ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Route Efficiency",
    "🗺️ Geographic Analysis",
    "🚚 Ship Mode Analysis",
    "🔍 Route Drill-Down"
])

# ════════════════════════════════════════════════════════════
# TAB 1 — ROUTE EFFICIENCY
# ════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Route Efficiency Overview")

    route_summary = filtered.groupby("Route (State)").agg(
        Total_Orders  = ("Order ID",          "count"),
        Avg_Lead_Time = ("Lead Time (Days)",   "mean"),
        Std_Lead_Time = ("Lead Time (Days)",   "std"),
        Total_Sales   = ("Sales",              "sum"),
        Total_Profit  = ("Gross Profit",       "sum"),
        Delayed_Orders= ("Is_Delayed",         "sum")
    ).reset_index()

    route_summary["Std_Lead_Time"]  = route_summary["Std_Lead_Time"].fillna(0)
    route_summary["Delay_Rate_%"]   = (
        route_summary["Delayed_Orders"] / route_summary["Total_Orders"] * 100
    ).round(2)
    route_summary = route_summary[route_summary["Total_Orders"] >= 10]

    # Efficiency Score
    lt_norm  = (route_summary["Avg_Lead_Time"] - route_summary["Avg_Lead_Time"].min()) /                (route_summary["Avg_Lead_Time"].max() - route_summary["Avg_Lead_Time"].min())
    std_norm = (route_summary["Std_Lead_Time"] - route_summary["Std_Lead_Time"].min()) /                (route_summary["Std_Lead_Time"].max() - route_summary["Std_Lead_Time"].min())
    route_summary["Efficiency_Score"] = (
        1 - (0.7 * lt_norm + 0.3 * std_norm)
    ) * 100
    route_summary["Efficiency_Score"] = route_summary["Efficiency_Score"].round(2)
    route_summary = route_summary.sort_values("Efficiency_Score", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🏆 Top 10 Most Efficient Routes")
        top10 = route_summary.head(10).sort_values("Efficiency_Score", ascending=True)
        fig = px.bar(top10, x="Efficiency_Score", y="Route (State)",
                     orientation="h", color="Efficiency_Score",
                     color_continuous_scale="Greens",
                     labels={"Efficiency_Score": "Score"})
        fig.update_layout(height=400, showlegend=False,
                         yaxis_title="", xaxis_title="Efficiency Score")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### ⚠️ Bottom 10 Least Efficient Routes")
        bot10 = route_summary.tail(10).sort_values("Efficiency_Score", ascending=False)
        fig = px.bar(bot10, x="Efficiency_Score", y="Route (State)",
                     orientation="h", color="Efficiency_Score",
                     color_continuous_scale="Reds_r",
                     labels={"Efficiency_Score": "Score"})
        fig.update_layout(height=400, showlegend=False,
                         yaxis_title="", xaxis_title="Efficiency Score")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📋 Full Route Performance Table")
    st.dataframe(
        route_summary[[
            "Route (State)", "Total_Orders", "Avg_Lead_Time",
            "Std_Lead_Time", "Delay_Rate_%", "Efficiency_Score"
        ]].round(2),
        use_container_width=True
    )

# ════════════════════════════════════════════════════════════
# TAB 2 — GEOGRAPHIC ANALYSIS
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Geographic Shipping Analysis")

    state_abbrev = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
        "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
        "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
        "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
        "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
        "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
        "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
        "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
        "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
        "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
        "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
        "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
        "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC"
    }

    state_data = filtered.groupby("State/Province").agg(
        Total_Orders  = ("Order ID",         "count"),
        Avg_Lead_Time = ("Lead Time (Days)",  "mean"),
        Delay_Rate    = ("Is_Delayed",        "mean")
    ).reset_index()
    state_data["State_Code"]  = state_data["State/Province"].map(state_abbrev)
    state_data["Delay_Rate"]  = (state_data["Delay_Rate"] * 100).round(2)
    state_data["Avg_Lead_Time"] = state_data["Avg_Lead_Time"].round(2)
    state_data = state_data.dropna(subset=["State_Code"])

    map_metric = st.radio(
        "Select Map Metric",
        ["Avg Lead Time", "Total Orders", "Delay Rate"],
        horizontal=True
    )

    metric_col = {
        "Avg Lead Time" : "Avg_Lead_Time",
        "Total Orders"  : "Total_Orders",
        "Delay Rate"    : "Delay_Rate"
    }[map_metric]

    fig_map = px.choropleth(
        state_data,
        locations="State_Code",
        locationmode="USA-states",
        color=metric_col,
        scope="usa",
        color_continuous_scale="RdYlGn_r",
        hover_name="State/Province",
        hover_data={"Total_Orders": True,
                    "Avg_Lead_Time": True,
                    "Delay_Rate": True},
        title=f"{map_metric} by US State"
    )
    fig_map.update_layout(height=500, title_x=0.5)
    st.plotly_chart(fig_map, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🐢 Top 10 Slowest States")
        slow = state_data.nlargest(10, "Avg_Lead_Time")[
            ["State/Province", "Avg_Lead_Time", "Total_Orders"]
        ]
        st.dataframe(slow, use_container_width=True)

    with col2:
        st.markdown("#### 🚀 Top 10 Fastest States")
        fast = state_data.nsmallest(10, "Avg_Lead_Time")[
            ["State/Province", "Avg_Lead_Time", "Total_Orders"]
        ]
        st.dataframe(fast, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 3 — SHIP MODE ANALYSIS
# ════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Ship Mode Performance Analysis")

    shipmode = filtered.groupby("Ship Mode").agg(
        Total_Orders  = ("Order ID",         "count"),
        Avg_Lead_Time = ("Lead Time (Days)",  "mean"),
        Delay_Rate    = ("Is_Delayed",        "mean"),
        Total_Sales   = ("Sales",             "sum")
    ).reset_index()
    shipmode["Delay_Rate"]    = (shipmode["Delay_Rate"] * 100).round(2)
    shipmode["Avg_Lead_Time"] = shipmode["Avg_Lead_Time"].round(2)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ⏱️ Avg Lead Time by Ship Mode")
        fig = px.bar(shipmode, x="Ship Mode", y="Avg_Lead_Time",
                     color="Ship Mode", text="Avg_Lead_Time",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
        fig.update_layout(height=400, showlegend=False,
                         yaxis_title="Avg Lead Time (Days)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 🚨 Delay Rate by Ship Mode")
        fig = px.bar(shipmode, x="Ship Mode", y="Delay_Rate",
                     color="Ship Mode", text="Delay_Rate",
                     color_discrete_sequence=px.colors.qualitative.Set1)
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(height=400, showlegend=False,
                         yaxis_title="Delay Rate (%)")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📦 Order Volume by Ship Mode")
    fig = px.pie(shipmode, values="Total_Orders", names="Ship Mode",
                 hole=0.5,
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📋 Ship Mode Summary Table")
    st.dataframe(shipmode, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 4 — ROUTE DRILL DOWN
# ════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Route Drill-Down Analysis")

    selected_route = st.selectbox(
        "Select a Route to Analyse",
        sorted(filtered["Route (State)"].unique().tolist())
    )

    route_df = filtered[filtered["Route (State)"] == selected_route].copy()
    route_df = route_df.sort_values("Order Date")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders",   f"{len(route_df):,}")
    col2.metric("Avg Lead Time",  f"{route_df['Lead Time (Days)'].mean():.1f} days")
    col3.metric("Delay Rate",     f"{route_df['Is_Delayed'].mean()*100:.1f}%")
    col4.metric("Total Sales",    f"${route_df['Sales'].sum():,.0f}")

    st.markdown("#### 📈 Lead Time Trend Over Time")
    monthly = route_df.groupby("Month-Year").agg(
        Avg_Lead_Time = ("Lead Time (Days)", "mean"),
        Total_Orders  = ("Order ID",         "count")
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["Month-Year"],
        y=monthly["Avg_Lead_Time"],
        mode="lines+markers",
        name="Avg Lead Time",
        line=dict(color="#4C72B0", width=2.5),
        marker=dict(size=8)
    ))
    fig.update_layout(
        height=350,
        xaxis_title="Month",
        yaxis_title="Avg Lead Time (Days)",
        xaxis_tickangle=45
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📋 Order Level Detail")
    st.dataframe(
        route_df[[
            "Order ID", "Order Date", "Ship Date",
            "Lead Time (Days)", "Ship Mode",
            "Product Name", "Sales", "Gross Profit", "Is_Delayed"
        ]].sort_values("Order Date", ascending=False),
        use_container_width=True
    )

# ── FOOTER ─────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center>Nassau Candy Distributor — Shipping Route Efficiency Dashboard | "
    "Built with Streamlit</center>",
    unsafe_allow_html=True
)
