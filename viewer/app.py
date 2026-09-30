import sys
from pathlib import Path

# Add project root (/Users/laxmishetty/Desktop/ux-studio) to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import os
import time
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv(override=True)

from db.database import init_db, create_campaign, get_campaign_tasks, DEFAULT_DB_PATH
from orchestrator import run_orchestrator  

# Page Configuration
st.set_page_config(
    page_title="UX Studio — Landing Page Engine",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Cozy Neutral Theme CSS
st.markdown(
    """
    <style>
        :root {
            --bg-base: #f7f6f2;
            --surface: #ffffff;
            --text-main: #2d312e;
            --text-muted: #6b7280;
            --border-soft: #e5e4de;
            --accent-warm: #d97706;
            --success-soft: #059669;
        }
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1300px;
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .status-completed { background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
        .status-claimed { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
        .status-pending { background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
        .status-failed { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
        
        .card-panel {
            background-color: #ffffff;
            border: 1px solid #e5e4de;
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Ensure Blackboard DB Schema
init_db(DEFAULT_DB_PATH)

# Preset Dictionary for The Big Promise (Set B)
PROMISE_PRESETS = {
    "⚡ Save time": "Save busy people hours each week by doing the heavy lifting for them.",
    "💰 Save money": "Cut down high expenses without sacrificing craftsmanship or quality.",
    "🛋️ Convenience": "Make getting what they need effortless, fast, and delivered directly to them.",
    "✨ Treat yourself": "Offer handcrafted quality and an experience that feels special and elevated.",
}

# Session State Tracking
if "active_campaign_id" not in st.session_state:
    st.session_state.active_campaign_id = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
if "big_promise_text" not in st.session_state:
    st.session_state.big_promise_text = PROMISE_PRESETS["⚡ Save time"]


def set_promise(text: str):
    st.session_state.big_promise_text = text


# Sidebar: Campaign Orchestration
with st.sidebar:
    st.title("UX Studio")
    st.caption("Distributed Multi-Agent Landing Page Synthesizer")
    st.divider()

    st.subheader("Launch New Campaign")
    product_name = st.text_input(
        "Product or Business Name",
        placeholder="e.g., Hearth & Crumb Bakery",
    )
    target_audience = st.text_input(
        "Who is this for?",
        placeholder="e.g., Neighborhood families and food lovers who value fresh, organic sourdough",
    )

    st.markdown("**The Big Promise**")
    st.caption("What problem do you solve, or why should they care? Pick an idea or edit below:")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⚡ Save time", use_container_width=True):
            set_promise(PROMISE_PRESETS["⚡ Save time"])
            st.rerun()
        if st.button("🛋️ Convenience", use_container_width=True):
            set_promise(PROMISE_PRESETS["🛋️ Convenience"])
            st.rerun()
    with col_btn2:
        if st.button("💰 Save money", use_container_width=True):
            set_promise(PROMISE_PRESETS["💰 Save money"])
            st.rerun()
        if st.button("✨ Treat yourself", use_container_width=True):
            set_promise(PROMISE_PRESETS["✨ Treat yourself"])
            st.rerun()

    big_promise = st.text_area(
        "Your core customer promise",
        key="big_promise_text",
        height=85,
        label_visibility="collapsed",
    )

    brand_notes = st.text_area(
        "Brand Vibe & Personality (Optional)",
        placeholder="e.g., Warm earthy tones, cozy neighborhood feel, inviting and approachable tone.",
        height=85,
    )

    if st.button("Synthesize Variations", use_container_width=True, type="primary"):
        if not product_name or not target_audience:
            st.error("Please supply both a Business Name and Target Audience.")
        else:
            with st.spinner("Decomposing brief & dispatching framework tasks..."):
                campaign_id = run_orchestrator(
                    product_name=product_name,
                    target_audience=target_audience,
                    primary_goal=big_promise,
                    brand_notes=brand_notes or "",
                    db_path=DEFAULT_DB_PATH,
                )
            st.session_state.active_campaign_id = campaign_id
            st.session_state.auto_refresh = True
            st.success(f"Dispatched campaign: `{campaign_id}`")
            st.rerun()

    st.divider()
    active_input = st.text_input("Inspect Existing Campaign ID", value=st.session_state.active_campaign_id or "")
    if st.button("Load Campaign", use_container_width=True):
        st.session_state.active_campaign_id = active_input
        st.rerun()

# Main Workspace
if not st.session_state.active_campaign_id:
    st.info("👈 Fill out the brief in the sidebar to generate landing page variants across the agent suite.")
    st.stop()

campaign_id = st.session_state.active_campaign_id
tasks = get_campaign_tasks(campaign_id=campaign_id, db_path=DEFAULT_DB_PATH)

col_title, col_ctrl = st.columns([3, 1])
with col_title:
    st.header(f"Campaign: {campaign_id}")
with col_ctrl:
    auto_poll = st.checkbox("Live Poll Blackboard", value=st.session_state.auto_refresh)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

if not tasks:
    st.warning("No tasks found for this campaign on the blackboard.")
    st.stop()

# 1. Blackboard Status Grid
st.subheader("Blackboard Execution Status")
status_cols = st.columns(len(tasks))

all_done = True
for idx, task in enumerate(tasks):
    status = task["status"]
    if status in ("pending", "claimed"):
        all_done = False

    with status_cols[idx]:
        st.markdown(
            f"""
            <div class="card-panel">
                <div style="font-size: 0.85rem; color: #6b7280; font-weight: 500;">{task['framework'].upper()}</div>
                <div style="font-size: 1.05rem; font-weight: 700; margin: 0.25rem 0;">{task['archetype']}</div>
                <span class="status-badge status-{status}">{status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# 2. Interactive Page Previews
st.divider()
st.subheader("Generated Variant Previews")

completed_tasks = [t for t in tasks if t["status"] == "completed" and t.get("output_html_path")]

if not completed_tasks:
    st.info("Workers are claiming and generating landing pages. The view will update once results land.")
else:
    tab_labels = [f"{t['archetype']} ({t['framework']})" for t in completed_tasks]
    tabs = st.tabs(tab_labels)

    for tab, task in zip(tabs, completed_tasks):
        with tab:
            file_path = task["output_html_path"]

            col_meta, col_actions = st.columns([3, 1])
            with col_meta:
                st.caption(f"Worker: **{task['framework']}** | Archetype: **{task['archetype']}** | File: `{file_path}`")

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                with col_actions:
                    st.download_button(
                        label="⬇️ Download HTML",
                        data=html_content,
                        file_name=f"{campaign_id}_{task['framework']}.html",
                        mime="text/html",
                        use_container_width=True,
                    )

                # Render HTML preview in responsive iframe
                components.html(html_content, height=720, scrolling=True)

                with st.expander("Inspect Source Code"):
                    st.code(html_content, language="html")
            else:
                st.error(f"Target HTML file `{file_path}` not found on disk.")

# Polling Handler
if auto_poll and not all_done:
    time.sleep(2.0)
    st.rerun()
elif auto_poll and all_done:
    st.session_state.auto_refresh = False