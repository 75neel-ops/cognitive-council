"""Configuration helpers for Cognitive Council."""
from __future__ import annotations
import os
import streamlit as st

PROVIDERS = ["openai", "gemini", "anthropic"]

DEFAULT_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "gemini": ["gemini-2.0-flash", "gemini-2.5-flash"],
    "anthropic": ["claude-3-5-haiku-latest", "claude-3-7-sonnet-latest"],
}

AGENTS = [
    {"id": "agent_1", "name": "The Researcher", "role": "Researcher", "focus": "Explain the question carefully, distinguish established facts from uncertainty, and identify what evidence would matter."},
    {"id": "agent_2", "name": "The Specialist", "role": "Subject Specialist", "focus": "Analyze the question from the most relevant specialist discipline. Be precise and technically grounded."},
    {"id": "agent_3", "name": "The Critic", "role": "Critical Analyst", "focus": "Challenge assumptions, find weaknesses, counterexamples, missing variables, and alternative explanations."},
    {"id": "agent_4", "name": "The Independent Thinker", "role": "Independent Thinker", "focus": "Offer a fresh perspective, connect ideas across fields, and avoid simply repeating conventional answers."},
]

def get_secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, "")).strip()

def get_model_settings(agent_id: str, provider_default: str = "openai", model_default: str = "gpt-4o-mini"):
    try:
        section = st.secrets.get("models", {})
        provider = str(section.get(f"{agent_id}_provider", provider_default))
        model = str(section.get(f"{agent_id}_model", model_default))
    except Exception:
        provider, model = provider_default, model_default
    return provider, model
