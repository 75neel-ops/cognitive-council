"""Cognitive Council — four AI agents and a Chief AI."""
import streamlit as st
from config import AGENTS, PROVIDERS, DEFAULT_MODELS, get_model_settings, get_secret
from services.council_engine import run_council

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
.stApp {background: #0b1020;}
.block-container {max-width: 1180px; padding-top: 2rem;}
.hero {padding: 1.5rem 1.7rem; border: 1px solid #263653; border-radius: 18px;
background: linear-gradient(120deg,#172846,#111827); margin-bottom: 1.2rem;}
.hero h1 {font-size: 2.4rem; margin: 0; color: #f8fafc;}
.hero p {color: #b8c7dc; margin: .5rem 0 0;}
.small-muted {color:#9aabc2; font-size:.9rem;}
</style>
<div class="hero">
<h1>🧠 COGNITIVE COUNCIL</h1>
<p>Four independent AI minds. One Chief. A clearer way to think.</p>
</div>
""", unsafe_allow_html=True)

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
            provider = st.selectbox("Provider", PROVIDERS, index=PROVIDERS.index(provider) if provider in PROVIDERS else 0, key=f"{agent['id']}_provider")
            models = DEFAULT_MODELS[provider]
            model = st.selectbox("Model", models, index=models.index(model) if model in models else 0, key=f"{agent['id']}_model")
            agent_settings.append({**agent, "provider": provider, "model": model, "instructions": agent["focus"]})
    st.divider()
    st.subheader("Chief AI")
    cp, cm = get_model_settings("chief", "openai", "gpt-4o")
    cp = st.selectbox("Chief provider", PROVIDERS, index=PROVIDERS.index(cp) if cp in PROVIDERS else 0, key="chief_provider")
    cm_options = DEFAULT_MODELS[cp]
    cm = st.selectbox("Chief model", cm_options, index=cm_options.index(cm) if cm in cm_options else 0, key="chief_model")
    chief_settings = {"provider": cp, "model": cm}

st.subheader("Ask the Council")
question = st.text_area("Your question", placeholder="What would you like the four AI members to examine?", height=125)
st.caption("Tip: Ask a focused question. Advanced mode uses additional model calls and may cost more.")
run = st.button("Convene the Council", type="primary", use_container_width=True, disabled=not question.strip())

if run:
    with st.spinner("The four members are preparing their independent responses..."):
        progress = st.progress(0, text="Waiting for the panel...")
        try:
            result = run_council(question.strip(), mode, agent_settings, chief_settings,
                                 progress=lambda done, total: progress.progress(done/total, text=f"Independent responses: {done}/{total}"))
            progress.empty()
            st.success("The Council has completed its session.")
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
