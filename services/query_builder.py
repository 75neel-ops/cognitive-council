"""AI-assisted conversion of plain-language research questions into database queries."""
from __future__ import annotations
import json
import re
from providers.base import get_provider


def build_research_queries(question: str, provider_name: str, model: str) -> dict:
    system = (
        "You are an expert academic search strategist. Convert a researcher's plain-language "
        "question into a compact search plan for scholarly discovery services. Do not answer "
        "the research question. Generate 4 to 6 distinct, focused search queries using natural "
        "academic terminology, synonyms and relevant technical concepts. Keep queries useful "
        "for broad indexes such as OpenAlex, Crossref, PubMed and arXiv. Avoid overly long "
        "Boolean syntax. Include a short list of key concepts. Return ONLY valid JSON with "
        'keys "concepts" (array of short strings), "queries" (array of 4-6 strings), '
        'and "search_note" (one concise sentence explaining the strategy).'
    )
    prompt = f"Research question:\n{question.strip()}\n\nCreate the search plan."
    raw = get_provider(provider_name).generate(model, system, prompt).strip()
    # Tolerate providers that wrap JSON in Markdown fences.
    raw = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw, flags=re.I)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            raise RuntimeError("The AI did not return a usable search plan. Please try again.")
        data = json.loads(match.group(0))
    queries = []
    for item in data.get("queries", []):
        value = re.sub(r"\s+", " ", str(item)).strip()
        if value and value.lower() not in {q.lower() for q in queries}:
            queries.append(value)
    if not queries:
        raise RuntimeError("The AI search plan contained no usable queries.")
    return {
        "concepts": [str(x).strip() for x in data.get("concepts", []) if str(x).strip()][:8],
        "queries": queries[:6],
        "search_note": str(data.get("search_note", "")).strip(),
    }
