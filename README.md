# Cognitive Council

A browser-based multi-agent AI research and debate workspace.

## Current architecture
- Four configurable AI agents with distinct roles.
- One Chief AI that synthesizes the panel's work.
- Basic mode: independent responses followed by a synthesis.
- Advanced mode: independent responses, peer critique, revised positions, and a final synthesis.
- Provider adapters are replaceable; model IDs are configuration, not hard-coded agent identities.

## Run locally
1. Use Python 3.10 or newer.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add the API keys you want to use.
5. Run: `streamlit run app.py`

Never commit real API keys. The app also supports environment variables.

## Provider configuration
The initial version supports OpenAI, Google Gemini, and Anthropic adapters. Each agent and the Chief can be assigned a provider and model independently. You only need credentials for providers you choose.

## Deployment
Deploy the repository to a Python-capable host such as Streamlit Community Cloud. Add API keys in the host's Secrets settings; do not upload `secrets.toml`.

## Status
Initial project scaffold. The first milestone is a working Basic/Advanced panel with configurable providers. Later milestones can add source-backed web research, exportable reports, saved sessions, and usage controls.
