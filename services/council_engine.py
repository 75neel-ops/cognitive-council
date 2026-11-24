"""Runs the four-agent panel and Chief AI synthesis."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from providers.base import get_provider

def _ask(provider_name: str, model: str, system: str, prompt: str) -> str:
    return get_provider(provider_name).generate(model, system, prompt)

def run_council(question: str, mode: str, agents: list[dict], chief: dict, progress=None) -> dict:
    answers = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_ask, a["provider"], a["model"],
                        f"You are {a['role']}. {a['instructions']} Answer independently. State assumptions and uncertainty. Do not invent sources.",
                        question): a
            for a in agents
        }
        for future in as_completed(futures):
            agent = futures[future]
            try:
                answers[agent["id"]] = {"name": agent["name"], "answer": future.result(), "error": None}
            except Exception as exc:
                answers[agent["id"]] = {"name": agent["name"], "answer": "", "error": str(exc)}
            if progress:
                progress(len(answers), 4)

    successful = [a for a in agents if answers.get(a["id"], {}).get("answer")]
    if not successful:
        raise RuntimeError("None of the four agents returned an answer. Check provider keys, model names, and API access.")

    critiques = {}
    revised = {}
    if mode == "Advanced":
        panel = "\n\n".join(f"{answers[a['id']]['name']}:\n{answers[a['id']]['answer']}" for a in successful)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(_ask, a["provider"], a["model"],
                    f"You are {a['role']}. {a['instructions']} You are now in a rigorous peer-review round.",
                    f"Original question: {question}\n\nPanel responses:\n{panel}\n\nIdentify the strongest points, errors, unsupported claims, and disagreements. Then give your revised position. Be fair; do not manufacture disagreement.")
                : a for a in successful
            }
            for future in as_completed(futures):
                a = futures[future]
                try:
                    critiques[a["id"]] = future.result()
                except Exception as exc:
                    critiques[a["id"]] = f"Peer review failed: {exc}"
        revised = critiques

    material = []
    for a in agents:
        item = answers.get(a["id"], {})
        if item.get("answer"):
            block = f"### {item['name']}\n{item['answer']}"
            if a["id"] in revised:
                block += f"\n\n**Peer review and revised position**\n{revised[a['id']]}"
            material.append(block)
        elif item.get("error"):
            material.append(f"### {item['name']}\nAgent error: {item['error']}")

    chief_system = """You are the Chief Intelligence Officer of Cognitive Council. Synthesize the panel; do not merely average opinions. Separate well-supported points from speculation. Explicitly identify agreement, meaningful disagreement, limitations, and what would change the conclusion. Never claim that a fact was independently verified unless evidence was actually supplied."""
    chief_prompt = f"""MODE: {mode}\nUSER QUESTION: {question}\n\nPANEL OUTPUTS:\n{chr(10).join(material)}\n\nProduce a clear report with: Executive conclusion; strongest shared findings; disagreements and competing explanations; evidence quality and uncertainty; practical conclusion / next steps. If the panel lacks sources, say so."""
    final = _ask(chief["provider"], chief["model"], chief_system, chief_prompt)
    return {"question": question, "mode": mode, "answers": answers, "critiques": critiques, "final": final}
