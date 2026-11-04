import math
import re
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime

from jobs_map import is_csv_recent, read_jobs_data


# --- classification helpers (work on the job title text) ---

POSITION_RULES = [
    ("Professor / Tenure", r"professor|tenure|w2|w3|chair"),
    ("Postdoc", r"post.?doc|postdoctoral"),
    ("PhD / Doktorand", r"phd|doktorand|doctoral|Promotion"),
    ("Psychologist / Therapist", r"psycholog|psychotherapeut|therapeut|neuropsycholog"),
    ("Research Staff", r"mitarbeiter|associate|assistant|researcher|scientist|wissenschaft"),
    ("IT / Data / Admin", r"data|software|it.|admin|dev|engineer|informatik"),
]

CONTRACT_RULES = [
    ("Permanent (unbefristet)", r"unbefristet|permanent|tenure|unlimited"),
]

WORKTIME_RULES = [
    ("Part-time", r"\d{1,3}\s*%|teilzeit|part.?time|\d{1,2}\s*wostd|half.?time"),
]


def classify(title: str, rules) -> str | None:
    for label, pattern in rules:
        if re.search(pattern, title, re.IGNORECASE):
            return label
    return None


def position_type(title: str) -> str:
    return classify(title, POSITION_RULES) or "Other"


def contract_type(title: str) -> str:
    return classify(title, CONTRACT_RULES) or "Not specified"


def worktime_type(title: str) -> str:
    return classify(title, WORKTIME_RULES) or "Full-time / not specified"


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_english(title: str) -> bool:
    """A rough split: titles without German umlauts / typical German words count as English."""
    return not re.search(r"mitarbeiter|wissenschaft|psycholog|therapeut|bekleidung", title, re.IGNORECASE)


def main():
    st.set_page_config(page_title="Job on Map — Leibniz Psychology", layout="wide")

    st.title("🗺️ Job on Map — Leibniz Psychology Jobs")
    st.caption("All Leibniz psychology job postings on one interactive map.")

    # brand purple for selected filter chips (instead of default red)
    st.markdown("""
        <style>
        .stMultiSelect [data-baseweb="tag"] {
            background-color: #e8e5ff !important;
            color: #4C4CFF !important;
        }
        .stMultiSelect [data-baseweb="tag"] svg {
            color: #4C4CFF !important;
        }
        .stDateInput input {
            border-color: #4C4CFF !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if not is_csv_recent():
        st.caption("⚠️ Data last updated: see published dates. Job listings may be outdated.")

    jobs = read_jobs_data("latest_job.csv")
    if not jobs:
        st.error("No job data available")
        return

    # enrich each job with filterable fields
    for job in jobs:
        job["position_type"] = position_type(job["title"])
        job["contract"] = contract_type(job["title"])
        job["worktime"] = worktime_type(job["title"])
        job["lang"] = "English" if is_english(job["title"]) else "German"

    df = pd.DataFrame(jobs)

    # --- sidebar filters ---
    st.sidebar.header("🔎 Filters")

    # free-text search
    search = st.sidebar.text_input(
        "Search title",
        placeholder="e.g. klinisch, Postdoc, E13 …",
    ).strip().lower()

    # position type (multi-select)
    type_options = sorted(df["position_type"].unique())
    selected_types = st.sidebar.multiselect(
        "Position type",
        type_options,
        default=type_options,
    )

    # contract / permanency
    contract_options = sorted(df["contract"].unique())
    selected_contracts = st.sidebar.multiselect(
        "Contract",
        contract_options,
        default=contract_options,
        help=(
            "'Permanent' is only flagged when the posting title explicitly says "
            "unbefristet / permanent / tenure. Most listings do not mention "
            "contract type in the title — check the detail page."
        ),
    )

    # work time
    worktime_options = sorted(df["worktime"].unique())
    selected_worktime = st.sidebar.multiselect(
        "Work time",
        worktime_options,
        default=worktime_options,
    )

    # language of the posting
    lang_options = sorted(df["lang"].unique())
    selected_langs = st.sidebar.multiselect(
        "Posting language",
        lang_options,
        default=lang_options,
    )

    # city (multi-select, sorted by count)
    city_counts = df["city"].value_counts()
    city_options = list(city_counts.index)
    selected_cities = st.sidebar.multiselect(
        "City / location",
        city_options,
        default=[],
        help="Leave empty to see all locations",
    )

    # distance filter (only active when a city is selected)
    radius_km = st.sidebar.selectbox(
        "Distance from selected city",
        ["All", 25, 50, 100],
        index=0,
        help="Pick a city above, then show only jobs within this radius.",
    )

    # date range
    df["published_date"] = pd.to_datetime(df["published_date"])
    min_date = df["published_date"].min().date()
    max_date = df["published_date"].max().date()
    date_range = st.sidebar.date_input(
        "Published between",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if len(date_range) == 1:
        date_range = (date_range[0], max_date)

    # --- apply filters ---
    mask = (
        df["position_type"].isin(selected_types)
        & df["contract"].isin(selected_contracts)
        & df["worktime"].isin(selected_worktime)
        & df["lang"].isin(selected_langs)
        & df["published_date"].dt.date.between(date_range[0], date_range[1])
    )
    if selected_cities:
        mask &= df["city"].isin(selected_cities)
        if radius_km != "All":
            center_city = selected_cities[0]
            center_row = df[df["city"] == center_city].iloc[0]
            c_lat = center_row["position"]["lat"]
            c_lon = center_row["position"]["lng"]
            mask &= df["position"].apply(
                lambda p: haversine_km(c_lat, c_lon, p["lat"], p["lng"]) <= radius_km
            )
    if search:
        mask &= df["title"].str.lower().str.contains(search)

    filtered = df[mask].reset_index(drop=True)
    total = len(df)

    st.sidebar.markdown("---")
    st.sidebar.metric("Showing", f"{len(filtered)} / {total}")

    if filtered.empty:
        st.warning("No jobs match the selected filters")
        return

    # --- map + list ---
    col1, col2 = st.columns([2, 1])

    with col1:
        m = folium.Map(
            location=[filtered["position"].apply(lambda p: p["lat"]).mean(),
                      filtered["position"].apply(lambda p: p["lng"]).mean()],
            zoom_start=5,
        )

        for idx, row in filtered.iterrows():
            pos = row["position"]
            contract_badge = " 🔒" if row["contract"].startswith("Permanent") else ""
            html = f"""
                <div style="min-width: 220px; font-family: sans-serif;">
                    <b>{row['title']}</b><br>
                    📍 {row['city']} &nbsp;·&nbsp; 📅 {row['published_date'].strftime('%Y-%m-%d')}<br>
                    💼 {row['position_type']} &nbsp;·&nbsp; ⏱ {row['worktime']}{contract_badge}<br>
                    <a href="{row['url']}" target="_blank" style="color: #4C4CFF; font-weight: bold;">→ View posting</a>
                </div>
            """
            folium.Marker(
                location=[pos["lat"], pos["lng"]],
                popup=folium.Popup(html, max_width=300),
                tooltip=f"{row['title'][:50]} — {row['city']}",
            ).add_to(m)

        st_folium(m, width=800, height=600)

    with col2:
        st.subheader(f"📋 {len(filtered)} positions")
        for idx, row in filtered.iterrows():
            contract_emoji = "🔒" if row["contract"].startswith("Permanent") else ""
            label = f"{row['title'][:55]} — {row['city']}"
            with st.expander(label):
                st.write(f"**Type:** {row['position_type']}")
                st.write(f"**Work time:** {row['worktime']}")
                st.write(f"**Contract:** {row['contract']} {contract_emoji}")
                st.write(f"**Published:** {row['published_date'].strftime('%Y-%m-%d')}")
                st.markdown(f"[→ View posting]({row['url']})")


if __name__ == "__main__":
    main()
