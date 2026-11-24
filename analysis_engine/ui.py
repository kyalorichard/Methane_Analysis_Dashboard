import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from .io import infer_roles

NAVY = "#082B4C"
TEAL = "#18A889"
BLUE = "#2D83C7"
PURPLE = "#8061C8"
ORANGE = "#E88A45"


def apply_style():
    """Apply a consistent, responsive visual system across all Streamlit pages."""
    st.markdown(
        """<style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap');

        :root {
          --ink:#183247;
          --navy:#123B35;
          --green:#176B5B;
          --green-2:#23866F;
          --mint:#E8F4EF;
          --gold:#D7A33D;
          --muted:#647789;
          --line:#E1E9E5;
          --canvas:#F5F8F6;
          --surface:#FFFFFF;
          --shadow:0 8px 24px rgba(24,50,71,.055);
        }

        html, body, [class*='css'] {
            font-family:'DM Sans',sans-serif;
            color:var(--ink);
        }
        .stApp {background:var(--canvas);}
        .block-container {
            padding-top:1.45rem;
            padding-bottom:3rem;
            max-width:1540px;
        }
        h1,h2,h3,h4 {
            font-family:'Manrope','DM Sans',sans-serif;
            color:var(--ink);
            letter-spacing:-.025em;
        }
        h1 {font-size:1.85rem !important;font-weight:800 !important;}
        h2 {font-size:1.32rem !important;font-weight:750 !important;}
        h3 {font-size:1.05rem !important;font-weight:750 !important;}
        p, li {line-height:1.55;}

        /* Sidebar theme */
        section[data-testid='stSidebar'] {
            background:linear-gradient(180deg,#123B35 0%,#0E302C 100%);
            border-right:1px solid rgba(255,255,255,.08);
        }
        section[data-testid='stSidebar'] * {color:#F4FAF7;}
        section[data-testid='stSidebar'] .stCaption,
        section[data-testid='stSidebar'] small {color:#C5D9D1 !important;}
        section[data-testid='stSidebar'] hr {border-color:rgba(255,255,255,.17);}
        section[data-testid='stSidebar'] [data-testid='stFileUploader'] {
            background:rgba(255,255,255,.08);
            border:1px dashed rgba(255,255,255,.32);
            border-radius:12px;
            padding:10px;
        }
        section[data-testid='stSidebar'] [data-testid='stFileUploader'] section {
            background:transparent;
        }
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] label,
        section[data-testid='stSidebar'] [data-testid='stFileUploader'] label {
            font-weight:700;
            color:#F4FAF7 !important;
        }
        section[data-testid='stSidebar'] [data-testid='stButton'] button {
            background:rgba(255,255,255,.19);
            border:1px solid rgba(255,255,255,.4);
            color:white;
            border-radius:10px;
            font-weight:700;
        }
        section[data-testid='stSidebar'] [data-testid='stButton'] button:hover {
            background:rgba(255,255,255,.19);
            border-color:rgba(255,255,255,.4);
        }

        /* Selectbox labels stay white; selected values use dark text. */
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] label,
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] label p {
            color:#F4FAF7 !important;
        }
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] [data-baseweb='select'],
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] [data-baseweb='select'] > div {
            background-color:#F7FBF9 !important;
            color:#173B34 !important;
            border-radius:10px !important;
            color-scheme:light !important;
        }
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] [data-baseweb='select'] *,
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] [data-baseweb='select'] input,
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] [data-baseweb='select'] span {
            color:#173B34 !important;
            -webkit-text-fill-color:#173B34 !important;
            opacity:1 !important;
        }
        section[data-testid='stSidebar'] [data-testid='stSelectbox'] [data-baseweb='select'] svg {
            fill:#173B34 !important;
            color:#173B34 !important;
        }

        /* Streamlit/BaseWeb dropdown popovers are mounted outside the sidebar. */
        body div[data-baseweb='popover'],
        body div[data-baseweb='popover'] ul,
        body div[data-baseweb='menu'],
        body ul[data-testid='stSelectboxVirtualDropdown'] {
            background-color:#FFFFFF !important;
            color:#173B34 !important;
            color-scheme:light !important;
        }
        body div[data-baseweb='popover'] [role='listbox'],
        body div[data-baseweb='popover'] [role='option'],
        body div[data-baseweb='popover'] [role='option'] *,
        body div[data-baseweb='menu'] [role='option'],
        body div[data-baseweb='menu'] [role='option'] *,
        body ul[data-testid='stSelectboxVirtualDropdown'] li,
        body ul[data-testid='stSelectboxVirtualDropdown'] li * {
            color:#173B34 !important;
            -webkit-text-fill-color:#173B34 !important;
            opacity:1 !important;
        }
        body div[data-baseweb='popover'] [role='option']:hover,
        body div[data-baseweb='menu'] [role='option']:hover,
        body ul[data-testid='stSelectboxVirtualDropdown'] li:hover {
            background-color:#E8F4EF !important;
        }
        body div[data-baseweb='popover'] [role='option'][aria-selected='true'],
        body div[data-baseweb='menu'] [role='option'][aria-selected='true'],
        body ul[data-testid='stSelectboxVirtualDropdown'] li[aria-selected='true'] {
            background-color:#DDEFE7 !important;
            color:#123B35 !important;
        }

        /* Sidebar navigation */
        [data-testid='stSidebarNav'] {padding-top:.35rem;}
        [data-testid='stSidebarNav'] a {
            border-radius:9px;
            margin:2px 7px;
            padding:7px 10px;
            transition:background .15s ease;
        }
        [data-testid='stSidebarNav'] a:hover {background:rgba(255,255,255,.12);}
        [data-testid='stSidebarNav'] a[aria-current='page'] {
            background:rgba(255,255,255,.17);
            border-left:3px solid #D7A33D;
            font-weight:800;
        }
        [data-testid='stSidebarNav'] span {font-size:.88rem;}

        /* Metrics, tables, charts and controls */
        div[data-testid='stMetric'] {
            background:var(--surface);
            border:1px solid var(--line);
            padding:15px 17px;
            border-radius:14px;
            box-shadow:var(--shadow);
        }
        div[data-testid='stMetricLabel'] {
            color:var(--muted);
            font-size:.74rem;
            font-weight:800;
            letter-spacing:.055em;
        }
        div[data-testid='stMetricValue'] {
            color:var(--navy);
            font-family:'Manrope',sans-serif;
            font-size:1.65rem;
            font-weight:800;
        }
        div[data-testid='stMetricDelta'] {font-size:.78rem;}
        div[data-testid='stVerticalBlockBorderWrapper'] {
            border-radius:14px;
            border-color:var(--line);
            background:white;
        }
        [data-testid='stDataFrame'], [data-testid='stTable'] {
            border:1px solid var(--line);
            border-radius:12px;
            overflow:hidden;
            background:white;
        }
        [data-testid='stPlotlyChart'] {
            background:white;
            border:1px solid var(--line);
            border-radius:14px;
            padding:8px 8px 2px;
            box-shadow:0 3px 12px rgba(24,50,71,.025);
        }
        [data-testid='stExpander'] {
            background:white;
            border:1px solid var(--line);
            border-radius:12px;
        }
        [data-testid='stTabs'] button {font-weight:700;}
        [data-testid='stTabs'] button[aria-selected='true'] {
            color:var(--green);
            border-bottom-color:var(--green);
        }
        .stButton>button,
        .stDownloadButton>button,
        [data-testid='stFormSubmitButton'] button {
            border-radius:10px;
            font-weight:750;
            min-height:2.55rem;
            border:1px solid #C9D8D1;
            transition:all .15s ease;
        }
        .stButton>button[kind='primary'],
        [data-testid='stFormSubmitButton'] button[kind='primary'] {
            background:var(--green);
            border-color:var(--green);
            color:white;
        }
        .stButton>button:hover, .stDownloadButton>button:hover {
            border-color:var(--green);
            color:var(--green);
        }
        [data-testid='stTextInput'] input,
        [data-testid='stNumberInput'] input,
        [data-testid='stTextArea'] textarea,
        [data-testid='stSelectbox'] div[data-baseweb='select'] > div,
        [data-testid='stMultiSelect'] div[data-baseweb='select'] > div {
            border-radius:9px;
        }
        [data-testid='stAlert'] {border-radius:11px;}

        /* Page heading and reusable cards */
        .hero {
            background:linear-gradient(112deg,#123B35 0%,#176B5B 66%,#23866F 100%);
            color:white;
            padding:25px 28px;
            border-radius:18px;
            margin-bottom:20px;
            box-shadow:0 10px 24px rgba(18,59,53,.12);
            position:relative;
            overflow:hidden;
        }
        .hero:after {
            content:'';
            position:absolute;
            width:240px;
            height:240px;
            border:1px solid rgba(255,255,255,.12);
            border-radius:50%;
            right:-65px;
            top:-115px;
            box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 58px rgba(255,255,255,.025);
        }
        .hero h1 {
            color:white;
            margin:7px 0 0 0;
            font-size:1.9rem !important;
            position:relative;
            z-index:1;
        }
        .hero p {
            color:#E1F0EA;
            margin:.42rem 0 0 0;
            max-width:900px;
            position:relative;
            z-index:1;
        }
        .tag {
            display:inline-block;
            background:#E5F4EC;
            color:#176B5B;
            border-radius:20px;
            padding:5px 10px;
            font-size:10px;
            font-weight:800;
            letter-spacing:.07em;
        }
        .panel {
            background:white;
            border:1px solid var(--line);
            border-radius:14px;
            padding:17px 19px;
            margin:8px 0;
            box-shadow:0 3px 12px rgba(24,50,71,.025);
        }
        .muted {color:var(--muted);font-size:12px;}
        .brand-lockup {
            display:flex;
            align-items:center;
            gap:10px;
            padding:8px 2px 13px;
        }
        .brand-mark {
            width:38px;
            height:38px;
            border-radius:12px;
            background:linear-gradient(135deg,#D7A33D,#E9C36D);
            display:flex;
            align-items:center;
            justify-content:center;
            color:#173B34;
            font-weight:900;
            font-family:Manrope,sans-serif;
            font-size:18px;
        }
        .brand-name {
            font-family:Manrope,sans-serif;
            font-weight:800;
            font-size:15px;
            line-height:1.15;
            color:#fff;
        }
        .brand-sub {
            font-size:10px;
            color:#C5D9D1;
            letter-spacing:.09em;
            text-transform:uppercase;
            margin-top:4px;
        }
        .section-kicker {
            font-size:.72rem;
            font-weight:800;
            letter-spacing:.09em;
            text-transform:uppercase;
            color:var(--green);
            margin-bottom:5px;
        }
        .workflow-card {
            height:100%;
            background:white;
            border:1px solid var(--line);
            border-radius:14px;
            padding:16px 17px;
            box-shadow:0 3px 12px rgba(24,50,71,.025);
        }
        .workflow-card .step {
            font-size:.72rem;
            color:var(--green);
            font-weight:800;
            letter-spacing:.08em;
            text-transform:uppercase;
        }
        .workflow-card h3 {margin:.45rem 0 .35rem;color:var(--ink);}
        .workflow-card p {font-size:.88rem;color:var(--muted);margin:0;}

        /* Sidebar navigation groups and utility panels */
        .nav-group-label {
            font-size:.68rem;
            font-weight:850;
            letter-spacing:.11em;
            text-transform:uppercase;
            color:#B7D2C7;
            padding:13px 9px 4px;
        }
        section[data-testid='stSidebar'] [data-testid='stPageLink'] a {
            border-radius:9px;
            padding:7px 9px;
            color:#F4FAF7 !important;
        }
        section[data-testid='stSidebar'] [data-testid='stPageLink'] a:hover {
            background:rgba(255,255,255,.12);
        }
        .empty-state {
            background:#fff;
            border:1px dashed #B8CBC1;
            border-radius:15px;
            padding:24px;
            text-align:center;
            margin:10px 0;
        }
        .empty-state-icon {font-size:1.8rem;color:#176B5B;}
        .empty-state-title {
            font-weight:800;
            color:#183247;
            font-size:1rem;
            margin:5px 0;
        }
        .empty-state-copy {
            font-size:.86rem;
            color:#647789;
            max-width:600px;
            margin:auto;
        }
        .progress-step {
            display:flex;
            gap:10px;
            align-items:flex-start;
            padding:9px 0;
            border-bottom:1px solid rgba(255,255,255,.10);
        }
        .progress-step:last-child {border-bottom:0;}
        .progress-step small {
            display:block;
            font-size:.72rem;
            opacity:.76;
            margin-top:2px;
        }
        .progress-dot {
            display:inline-flex;
            align-items:center;
            justify-content:center;
            border-radius:50%;
            width:22px;
            height:22px;
            flex:0 0 22px;
            font-weight:900;
            background:rgba(255,255,255,.12);
        }
        .progress-step.done .progress-dot {background:#D7A33D;color:#173B34;}
        .progress-step.todo .progress-dot {color:#C5D9D1;}
        [data-testid='stDataFrame'] {font-size:.86rem;}
        [data-testid='stDownloadButton'] button {background:#F4F8F5;}
        .workflow-card {transition:transform .15s ease,box-shadow .15s ease;}
        .workflow-card:hover {
            transform:translateY(-2px);
            box-shadow:0 9px 24px rgba(24,50,71,.08);
        }

        @media(max-width:760px) {
            .block-container {padding:.7rem .65rem 1.6rem;}
            section[data-testid='stSidebar'] {min-width:0;}
            .workflow-card {padding:13px;}
            [data-testid='stHorizontalBlock'] {gap:.55rem;}
            div[data-testid='stMetricValue'] {font-size:1.25rem;}
            .hero {border-radius:13px;padding:17px;}
        }
        </style>""",
        unsafe_allow_html=True,
    )


def get_data():
    from platform_core.auth import require_principal

    require_principal()
    if "data" not in st.session_state:
        st.warning(
            "Load a dataset from the Project workspace in the sidebar "
            "to activate this module."
        )
        st.stop()
    return st.session_state["data"]


def get_roles(df):
    roles = st.session_state.get("roles") or infer_roles(df)
    return roles


def header(title, subtitle, badge="ACTIVE DATASET"):
    st.markdown(
        f"<div class='hero'><span class='tag'>{badge}</span>"
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value, helptext) in zip(cols, items):
        col.metric(label, value, help=helptext)


def numeric_cols(df):
    return df.select_dtypes(include="number").columns.tolist()


def choose_col(df, label, default=None, options=None, key=None):
    opts = options or list(df.columns)
    if not opts:
        st.error(f"No eligible variables for {label}.")
        st.stop()
    ix = opts.index(default) if default in opts else 0
    return st.selectbox(label, opts, index=ix, key=key)


def note(text, kind="info"):
    getattr(st, kind)(text)


def distribution(df, col, title=None):
    x = pd.to_numeric(df[col], errors="coerce").dropna()
    if x.empty:
        st.info("No numeric observations available.")
        return
    fig = px.histogram(
        x,
        x=x.name,
        nbins=35,
        marginal="box",
        title=title or f"Distribution of {col}",
        color_discrete_sequence=[BLUE],
    )
    fig.update_layout(
        template="plotly_white",
        height=350,
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def grouped_summary(df, group, outcome):
    data = df[[group, outcome]].copy()
    data[outcome] = pd.to_numeric(data[outcome], errors="coerce")
    data = data.dropna()
    return (
        data.groupby(group)[outcome]
        .agg(
            n="count",
            mean="mean",
            sd="std",
            median="median",
            minimum="min",
            maximum="max",
        )
        .reset_index()
    )


def style_plotly(fig, height=None):
    """Apply consistent research-workspace styling to Plotly figures."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="DM Sans, Arial, sans-serif", color="#183247", size=12),
        title=dict(font=dict(size=16, color="#183247"), x=0.02, xanchor="left"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=18, r=18, t=58, b=18),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        hoverlabel=dict(bgcolor="#123B35", font=dict(color="#FFFFFF")),
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#DCE7E1")
    fig.update_yaxes(gridcolor="#EDF2EF", zeroline=False)
    return fig


def section_intro(title, description=None, eyebrow=None):
    """Consistent compact section heading."""
    if eyebrow:
        st.markdown(
            f"<div class='section-kicker'>{eyebrow}</div>",
            unsafe_allow_html=True,
        )
    st.subheader(title)
    if description:
        st.caption(description)


def empty_state(title, message, action_label=None):
    """Friendly empty-state panel for modules without eligible data."""
    st.markdown(
        f"<div class='empty-state'><div class='empty-state-icon'>◎</div>"
        f"<div class='empty-state-title'>{title}</div>"
        f"<div class='empty-state-copy'>{message}</div></div>",
        unsafe_allow_html=True,
    )
    if action_label:
        st.caption(action_label)


def progress_step(label, complete, detail=""):
    """Render a compact workflow status line."""
    symbol = "✓" if complete else "○"
    css = "done" if complete else "todo"
    st.markdown(
        f"<div class='progress-step {css}'><span class='progress-dot'>{symbol}</span>"
        f"<span><b>{label}</b><small>{detail}</small></span></div>",
        unsafe_allow_html=True,
    )


def render_sidebar_navigation():
    """Apply shared styling and render navigation on every Streamlit page."""
    # Each multipage script executes independently, so apply the shared
    # stylesheet here on every page.
    apply_style()

    with st.sidebar:
        st.markdown(
            "<div class='brand-lockup'><div class='brand-mark'>M</div><div>"
            "<div class='brand-name'>Methane Phenotype<br>Analytics</div>"
            "<div class='brand-sub'>ICARDA research workspace</div></div></div>",
            unsafe_allow_html=True,
        )

        groups = [
            (
                "WORKSPACE",
                [
                    ("Overview", "app.py", "🏠"),
                    ("Guided workflow", "pages/22_Guided_Research_Workflow.py", "🧭"),
                    ("Integrated analysis centre", "pages/23_Integrated_Analysis_Centre.py", "🧪"),
                    ("Analysis run history", "pages/26_Analysis_Run_History.py", "🗂️"),
                    ("Projects & datasets", "pages/00_Project_Workspace.py", "🗂️"),
                ],
            ),
            (
                "DATA PREPARATION",
                [
                    ("Data management & QC", "pages/01_Data_Management.py", "🧹"),
                    ("Data preparation studio", "pages/24_Data_Preparation_Studio.py", "🧽"),
                    ("Species & protocol", "pages/16_Species_Protocol_Configuration.py", "🐑"),
                    ("Phenotype builder", "pages/19_Custom_Phenotype_Builder.py", "🧬"),
                ],
            ),
            (
                "EXPLORE & VALIDATE",
                [
                    ("Descriptive analysis", "pages/02_Descriptive_Analysis.py", "📊"),
                    ("Phenotype analysis", "pages/06_Phenotype_Analysis.py", "🔬"),
                    ("Repeatability", "pages/07_Repeatability_Reliability.py", "🔁"),
                    ("Group comparisons", "pages/08_Group_Comparisons.py", "⚖️"),
                    ("Phenotype validation", "pages/21_Phenotype_Validation.py", "✅"),
                    ("Low / high emitters", "pages/18_Low_High_Emitter_Reports.py", "↕️"),
                    ("Emitter tracking", "pages/20_Longitudinal_Emitter_Tracking.py", "📈"),
                ],
            ),
            (
                "MODEL & EXPLAIN",
                [
                    ("Statistical models", "pages/03_Statistical_Models.py", "📐"),
                    ("ML benchmarking", "pages/04_ML_Benchmarking.py", "🤖"),
                    ("Research model lab", "pages/25_Research_Model_Lab.py", "🧬"),
                    ("Clustering & PCA", "pages/05_Clustering_PCA.py", "🧩"),
                    ("Model explainability", "pages/09_Explainability.py", "💡"),
                    ("Longitudinal analysis", "pages/10_Longitudinal_Analysis.py", "🗓️"),
                    ("Advanced analysis", "pages/11_Advanced_Analysis.py", "🧪"),
                    ("Sensitivity & robustness", "pages/12_Sensitivity_Robustness.py", "🛡️"),
                    ("Equivalence analysis", "pages/13_Equivalence_Analysis.py", "↔️"),
                    ("Phenotype scorecard", "pages/14_Phenotype_Scorecard.py", "🏅"),
                    ("Scientific workbench", "pages/17_Scientific_Analysis_Workbench.py", "🧰"),
                ],
            ),
            (
                "OUTPUTS",
                [("Reports & exports", "pages/15_Reports_Exports.py", "📄")],
            ),
        ]

        for group, links in groups:
            st.markdown(
                f"<div class='nav-group-label'>{group}</div>",
                unsafe_allow_html=True,
            )
            for label, target, icon in links:
                st.page_link(target, label=label, icon=icon)

        st.divider()
        st.markdown(
            "<div class='section-kicker'>Active project</div>",
            unsafe_allow_html=True,
        )

        try:
            from platform_core.database import configured
            from platform_core.workspace import list_projects
            from platform_core.auth import require_principal

            principal = require_principal()
            if configured():
                projects = list_projects(principal.tenant_id, principal.subject)
                if projects:
                    project_opts = {
                        f"{project['name']} · {project['species'].title()}": project
                        for project in projects
                    }
                    project_labels = list(project_opts)
                    active = st.session_state.get("active_project_id")
                    default = next(
                        (
                            label
                            for label, project in project_opts.items()
                            if project["id"] == active
                        ),
                        project_labels[0],
                    )
                    chosen = st.selectbox(
                        "Project",
                        project_labels,
                        index=project_labels.index(default),
                        key="shared_project_switch",
                    )
                    st.session_state["active_project_id"] = project_opts[chosen]["id"]
                    st.session_state["active_project_species"] = project_opts[chosen]["species"]
                else:
                    st.caption("No projects available")
            else:
                st.caption("Local research session")
        except Exception:
            st.caption("Project context unavailable")

        st.markdown(
            "<div class='section-kicker'>Active dataset</div>",
            unsafe_allow_html=True,
        )

        if "data" in st.session_state:
            st.success(f"{len(st.session_state['data']):,} records loaded")
            st.caption(st.session_state.get("data_name", "Dataset"))

            catalogue = st.session_state.get("dataset_catalogue", {})
            if catalogue:
                labels = {
                    f"{item['name']} · {item['species'].title()}": key
                    for key, item in catalogue.items()
                }
                current = st.session_state.get("active_dataset_key")
                label_list = list(labels)
                default = next(
                    (label for label, key in labels.items() if key == current),
                    label_list[0],
                )
                choice = st.selectbox(
                    "Switch dataset",
                    label_list,
                    index=label_list.index(default),
                    key="shared_dataset_switch",
                )
                selected_key = labels[choice]

                if selected_key != current:
                    item = catalogue[selected_key]
                    st.session_state["data"] = item["data"]
                    st.session_state["raw_data_snapshot"] = item["data"].copy(deep=True)
                    st.session_state["cleaning_log"] = []
                    st.session_state["data_name"] = item["name"]
                    st.session_state["species"] = item["species"]

                    from .io import infer_roles

                    st.session_state["roles"] = infer_roles(item["data"])
                    st.session_state["active_dataset_key"] = selected_key
                    st.rerun()
        else:
            st.info("No active dataset. Open Overview to import data.")
