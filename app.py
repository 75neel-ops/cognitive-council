"""Cognitive Council — four AI agents and a Chief AI."""
import streamlit as st
from config import AGENTS, PROVIDERS, DEFAULT_MODELS, get_model_settings, get_secret
from services.council_engine import run_council
from research.sources import search_research

st.set_page_config(page_title="Cognitive Council", page_icon="🧠", layout="wide")

# Public hosting is fine, but keep paid API access behind a shared password.
try:
    APP_PASSWORD = str(st.secrets.get("APP_PASSWORD", "")).strip()
except Exception:
    APP_PASSWORD = ""

if not APP_PASSWORD:
    st.error("The app owner must configure APP_PASSWORD in Streamlit Secrets before the Council can be used.")
    st.stop()

if not st.session_state.get("authenticated", False):
    st.title("🔐 Cognitive Council")
    st.caption("This AI workspace is access-protected.")
    with st.form("login_form"):
        entered = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Unlock Cognitive Council", type="primary")
    if submitted:
        if entered == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()
st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#f7f9fc !important; color:#172033 !important;}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {background:#eef2f7 !important;}
.block-container {max-width:1220px; padding-top:2rem; color:#172033 !important;}
.stMarkdown, .stMarkdown p, .stMarkdown li, label, [data-testid="stCaptionContainer"] {color:#172033 !important;}
.hero {padding:1.5rem 1.7rem; border:1px solid #d7dfeb; border-radius:18px; background:linear-gradient(120deg,#ffffff,#eaf1fb); margin-bottom:1.2rem; box-shadow:0 3px 14px rgba(25,45,75,.06);}
.hero h1 {font-size:2.4rem; margin:0; color:#14213d !important;}
.hero p {color:#42526b !important; margin:.5rem 0 0;}
.agent-card {background:#fff; border:1px solid #d8e0eb; border-radius:13px; padding:14px 12px; min-height:105px; box-shadow:0 2px 8px rgba(25,45,75,.04);}
.agent-card strong {color:#172033; display:block; margin-bottom:5px;}
.agent-card span {color:#52627a; font-size:.88rem;}
.small-muted {color:#52627a !important; font-size:.9rem;}
div.stButton > button[kind="primary"] {background:#2457a6; color:white; border:0;}
</style>
<div class="hero"><h1>🧠 COGNITIVE COUNCIL</h1><p>Four independent AI minds. One Chief. A clearer way to think.</p></div>
""", unsafe_allow_html=True)

st.markdown("### Meet your four AI members")
cols = st.columns(4)
for col, agent in zip(cols, AGENTS):
    with col:
        st.markdown(f'<div class="agent-card"><strong>{agent["name"]}</strong><span>{agent["role"]}</span></div>', unsafe_allow_html=True)
st.caption("All four members work on every question. Configure each member's provider and model in the left-hand Model Control Centre.")

with st.sidebar:
    st.header("Council settings")
    mode = st.radio("Thinking mode", ["Basic", "Advanced"], help="Basic runs independent answers and a synthesis. Advanced adds peer review and revised positions.")
    st.divider()
    st.subheader("Model Control Centre")
    st.caption("Assign a provider and model to each agent. API keys are read from deployment secrets.")
    agent_settings = []
    for i, agent in enumerate(AGENTS, 1):
        with st.expander(f"{i}. {agent['name']}", expanded=(i == 1)):
            provider, model = get_model_settings(agent["id"])
            provider = st.selectbox("Provider", PROVIDERS, index=PROVIDERS.index(provider) if provider in PROVIDERS else 0, key=f"{agent['id']}_provider_v2")
            models = DEFAULT_MODELS[provider]
            model = st.selectbox("Model", models, index=models.index(model) if model in models else 0, key=f"{agent['id']}_model_v2")
            agent_settings.append({**agent, "provider": provider, "model": model, "instructions": agent["focus"]})
    st.divider()
    st.subheader("Chief AI")
    cp, cm = get_model_settings("chief", "openai", "gpt-4o")
    cp = st.selectbox("Chief provider", PROVIDERS, index=PROVIDERS.index(cp) if cp in PROVIDERS else 0, key="chief_provider_v2")
    cm_options = DEFAULT_MODELS[cp]
    cm = st.selectbox("Chief model", cm_options, index=cm_options.index(cm) if cm in cm_options else 0, key="chief_model_v2")
    chief_settings = {"provider": cp, "model": cm}

st.subheader("Ask the Council")
question = st.text_area("Your question", placeholder="What would you like the four AI members to examine?", height=125)
research_query = st.text_input("Research topic / keywords", placeholder="e.g. adolescent anxiety, gut microbiome and depression, AI alignment")
research_enabled = st.checkbox("Search recent research papers and news before analysis", value=True,
    help="Retrieves discovery records from OpenAlex, Crossref, arXiv and GDELT News. News is context, not scientific evidence.")
years_back = st.selectbox("Publication window", [1, 3, 5, 10], index=1, disabled=not research_enabled,
    help="Scholarly search window. News search focuses on the latest 30 days.")
st.caption("Tip: Ask a focused question. Advanced mode uses additional model calls and may cost more. Live source retrieval may be subject to public API rate limits.")
run = st.button("Convene the Council", type="primary", use_container_width=True, disabled=not question.strip())

if run:
    with st.spinner("The four members are preparing their independent responses..."):
        progress = st.progress(0, text="Waiting for the panel...")
        try:
            research_data = {"results": [], "errors": []}
            research_context = ""
            if research_enabled:
                progress.progress(0.05, text="Searching scholarly indexes and recent news...")
                research_data = search_research((research_query.strip() or question.strip()), years_back=years_back, per_source=5)
                source_lines = []
                for idx, item in enumerate(research_data["results"], 1):
                    item["ref"] = f"R{idx}"
                    source_lines.append(
                        f"[R{idx}] {item.get('title')} | {item.get('source')} | {item.get('date')} | "
                        f"{item.get('venue')} | URL: {item.get('url')} | Abstract/summary: {item.get('abstract')}"
                    )
                research_context = "\n".join(source_lines)
            result = run_council(question.strip(), mode, agent_settings, chief_settings,
                                 progress=lambda done, total: progress.progress(0.1 + 0.75*done/total, text=f"Council responses: {done}/{total}"),
                                 research_context=research_context)
            progress.empty()
            st.success("The Council has completed its session.")
            if research_enabled:
                st.markdown("## Live research desk")
                st.caption(f"Search window: from {research_data.get('from_date', 'recent')}. Records are discovery leads; verify publication status and methods before citing.")
                if research_data.get("errors"):
                    with st.expander("Some sources could not be reached"):
                        for err in research_data["errors"]:
                            st.warning(err)
                if research_data.get("results"):
                    for item in research_data["results"]:
                        label = f"[{item['ref']}] {item.get('title', 'Untitled')}"
                        url = item.get("url") or ""
                        st.markdown(f"**{label}**" + (f" — [{item.get('source')}]({url})" if url else f" — {item.get('source')}"))
                        meta = " · ".join(str(x) for x in [item.get("date"), item.get("venue"), item.get("kind")] if x)
                        st.caption(meta + (f" · Citations indexed: {item['citations']}" if item.get("citations") is not None else ""))
                        if item.get("authors"):
                            st.caption("Authors / publisher: " + item["authors"])
                        if item.get("retracted"):
                            st.error("Marked as retracted in OpenAlex — do not treat as current supporting evidence.")
                        if item.get("abstract"):
                            with st.expander(f"Abstract / summary — {item['ref']}"):
                                st.write(item["abstract"])
                else:
                    st.warning("No source records were retrieved. The Council answer is based on model knowledge only; check source errors above.")
            st.markdown("## Chief AI — Final Synthesis")
            st.markdown(result["final"])
            st.divider()
            st.markdown("## Individual perspectives")
            for agent in AGENTS:
                item = result["answers"].get(agent["id"], {})
                with st.expander(item.get("name", agent["name"]), expanded=False):
                    if item.get("error"):
                        st.error(item["error"])
                    else:
                        st.markdown(item.get("answer", "No response."))
                    if agent["id"] in result["critiques"]:
                        st.markdown("#### Peer review and revised position")
                        st.markdown(result["critiques"][agent["id"]])
            st.download_button("Download session as Markdown",
                data=f"# Cognitive Council\n\nQuestion: {question}\nMode: {mode}\n\n## Chief AI\n\n{result['final']}\n\n## Agent responses\n\n" + "\n\n".join(f"### {v['name']}\n{v['answer']}" for v in result["answers"].values()),
                file_name="cognitive_council_session.md", mime="text/markdown")
        except Exception as exc:
            progress.empty()
            st.error(f"Council session could not be completed: {exc}")

st.divider()
st.markdown('<p class="small-muted">Cognitive Council is an AI-assisted analysis tool. Model agreement is not proof of correctness; verify important claims independently.</p>', unsafe_allow_html=True)
