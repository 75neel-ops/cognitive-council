"""Runs the four-agent panel and Chief AI synthesis."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from providers.base import get_provider


def _ask(provider_name: str, model: str, system: str, prompt: str) -> str:
    return get_provider(provider_name).generate(model, system, prompt)


def run_council(question: str, mode: str, agents: list[dict], chief: dict,
                progress=None, research_context: str = "") -> dict:
    answers = {}
    evidence = (
        "RETRIEVED RESEARCH RECORDS (discovery leads; verify before relying on them):\n"
        + research_context + "\n\n"
        if research_context else
        "No live external research records were retrieved for this session.\n\n"
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(
                _ask, a["provider"], a["model"],
                f"You are {a['role']}. {a['instructions']} Answer independently. "
                "State assumptions and uncertainty. Do not invent sources.",
                evidence + "QUESTION: " + question,
            ): a for a in agents
        }
        for future in as_completed(futures):
            agent = futures[future]
            try:
                answers[agent["id"]] = {
                    "name": agent["name"], "answer": future.result(), "error": None
                }
            except Exception as exc:
                answers[agent["id"]] = {
                    "name": agent["name"], "answer": "", "error": str(exc)
                }
            if progress:
                progress(len(answers), 4)

    successful = [a for a in agents if answers.get(a["id"], {}).get("answer")]
    if not successful:
        details = "\n".join(
            f"- {a['name']} ({a['provider']} / {a['model']}): "
            f"{answers.get(a['id'], {}).get('error', 'No response')}"
            for a in agents
        )
        raise RuntimeError(
            "None of the four agents returned an answer. Individual errors:\n" + details
        )

    critiques = {}
    if mode == "Advanced":
        panel = "\n\n".join(
            f"{answers[a['id']]['name']}:\n{answers[a['id']]['answer']}"
            for a in successful
        )
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(
                    _ask, a["provider"], a["model"],
                    f"You are {a['role']}. {a['instructions']} "
                    "You are now in a rigorous peer-review round.",
                    evidence + f"ORIGINAL QUESTION: {question}\n\nPANEL RESPONSES:\n{panel}\n\n"
                    "Identify the strongest points, errors, unsupported claims, missing literature, "
                    "and disagreements. Then give your revised position. Be fair; do not manufacture disagreement.",
                ): a for a in successful
            }
            for future in as_completed(futures):
                agent = futures[future]
                try:
                    critiques[agent["id"]] = future.result()
                except Exception as exc:
                    critiques[agent["id"]] = f"Peer review failed: {exc}"

    material = []
    for agent in agents:
        item = answers.get(agent["id"], {})
        if item.get("answer"):
            block = f"### {item['name']}\n{item['answer']}"
            if agent["id"] in critiques:
                block += f"\n\n**Peer review and revised position**\n{critiques[agent['id']]}"
            material.append(block)
        elif item.get("error"):
            material.append(f"### {agent['name']}\nAgent error: {item['error']}")

    chief_system = (
        "You are the Chief Intelligence Officer of Cognitive Council. Synthesize the panel; "
        "do not merely average opinions. Separate well-supported points from speculation. "
        "Identify agreement, meaningful disagreement, limitations, and what evidence would "
        "change the conclusion. Never claim a fact was independently verified unless evidence "
        "was actually supplied."
    )
    chief_prompt = (
        f"MODE: {mode}\nQUESTION: {question}\n\n{evidence}"
        f"PANEL OUTPUTS:\n{chr(10).join(material)}\n\n"
        "Produce a research-grade report with: Executive summary; key findings; competing "
        "arguments and disagreements; evidence quality and limitations; research gaps; "
        "practical implications; next steps. Cite retrieved records by [R#] identifiers when "
        "relevant. Clearly distinguish journal articles, preprints, metadata-only records, and "
        "news reports. News is context, not scientific evidence. Do not invent citations, DOIs, "
        "quotations, or findings. If evidence is thin, say so."
    )
    final = _ask(chief["provider"], chief["model"], chief_system, chief_prompt)
    return {
        "question": question, "mode": mode, "answers": answers,
        "critiques": critiques, "final": final, "research_context": research_context,
    }
