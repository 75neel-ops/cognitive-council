"""Live literature and news retrieval for research-grounded Council sessions.

Uses public metadata/search APIs. Records are discovery leads, not peer-review guarantees.
"""
from __future__ import annotations

from datetime import date, timedelta
from html import unescape
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def _get_json(url: str, timeout: int = 18) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CognitiveCouncil/1.0 (research discovery)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _get_text(url: str, timeout: int = 18) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "CognitiveCouncil/1.0 (research discovery)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _clean(text: str | None, limit: int = 900) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", unescape(str(text)))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _openalex_abstract(index: dict | None) -> str:
    if not index:
        return ""
    words = {}
    for word, positions in index.items():
        for position in positions:
            words[int(position)] = word
    return _clean(" ".join(words[k] for k in sorted(words)), 1000)


def search_openalex(query: str, from_date: str, limit: int = 6) -> list[dict]:
    params = urllib.parse.urlencode({
        "search": query, "filter": f"from_publication_date:{from_date}",
        "sort": "publication_date:desc", "per-page": limit,
        "select": "id,doi,title,publication_year,publication_date,cited_by_count,authorships,primary_location,abstract_inverted_index,best_oa_location,type,is_retracted"
    })
    data = _get_json("https://api.openalex.org/works?" + params)
    out = []
    for item in data.get("results", []):
        authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])[:4]]
        loc = item.get("primary_location") or {}
        source = loc.get("source") or {}
        oa = item.get("best_oa_location") or {}
        out.append({
            "source": "OpenAlex", "title": item.get("title") or "Untitled",
            "authors": ", ".join(x for x in authors if x) or "Authors not listed",
            "date": item.get("publication_date") or str(item.get("publication_year") or ""),
            "venue": source.get("display_name") or "Venue not listed",
            "citations": item.get("cited_by_count", 0),
            "doi": item.get("doi") or "",
            "url": item.get("doi") or item.get("id") or "",
            "open_access_url": oa.get("landing_page_url") or oa.get("pdf_url") or "",
            "abstract": _openalex_abstract(item.get("abstract_inverted_index")),
            "retracted": bool(item.get("is_retracted")),
            "kind": item.get("type") or "scholarly work",
        })
    return out


def search_crossref(query: str, from_date: str, limit: int = 5) -> list[dict]:
    params = urllib.parse.urlencode({
        "query.bibliographic": query, "filter": f"from-pub-date:{from_date}",
        "sort": "published", "order": "desc", "rows": limit,
        "select": "DOI,title,author,published,published-print,published-online,container-title,URL,type,abstract"
    })
    data = _get_json("https://api.crossref.org/works?" + params)
    out = []
    for item in data.get("message", {}).get("items", []):
        date_parts = (item.get("published") or item.get("published-online") or item.get("published-print") or {}).get("date-parts", [[]])[0]
        authors = [(" ".join(filter(None, [a.get("given"), a.get("family")]))).strip() for a in item.get("author", [])[:4]]
        doi = item.get("DOI", "")
        out.append({
            "source": "Crossref", "title": (item.get("title") or ["Untitled"])[0],
            "authors": ", ".join(a for a in authors if a) or "Authors not listed",
            "date": "-".join(str(x) for x in date_parts),
            "venue": (item.get("container-title") or [""])[0],
            "citations": None, "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else item.get("URL", ""),
            "open_access_url": "", "abstract": _clean(item.get("abstract"), 850),
            "retracted": False, "kind": item.get("type") or "scholarly work",
        })
    return out


def search_arxiv(query: str, limit: int = 5) -> list[dict]:
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}", "start": 0, "max_results": limit,
        "sortBy": "submittedDate", "sortOrder": "descending"
    })
    xml = _get_text("https://export.arxiv.org/api/query?" + params)
    root = ET.fromstring(xml)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", ns):
        authors = [a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)[:4]]
        link = next((x.attrib.get("href", "") for x in entry.findall("a:link", ns) if x.attrib.get("rel") == "alternate"), "")
        out.append({
            "source": "arXiv", "title": _clean(entry.findtext("a:title", default="", namespaces=ns), 300),
            "authors": ", ".join(x for x in authors if x) or "Authors not listed",
            "date": entry.findtext("a:published", default="", namespaces=ns)[:10],
            "venue": "arXiv preprint", "citations": None, "doi": "",
            "url": link, "open_access_url": link,
            "abstract": _clean(entry.findtext("a:summary", default="", namespaces=ns), 900),
            "retracted": False, "kind": "preprint",
        })
    return out


def search_pubmed(query: str, limit: int = 5) -> list[dict]:
    """Search PubMed for biomedical literature; abstracts are fetched when available."""
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmax": limit,
        "sort": "date", "retmode": "json",
    })
    search_data = _get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + params)
    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    fetch_params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
    root = ET.fromstring(_get_text("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + fetch_params))
    out = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", default="")
        title_node = article.find(".//ArticleTitle")
        title = "".join(title_node.itertext()) if title_node is not None else "Untitled"
        abstract = " ".join("".join(node.itertext()) for node in article.findall(".//Abstract/AbstractText"))
        author_names = []
        for author in article.findall(".//Author")[:4]:
            name = " ".join(filter(None, [author.findtext("ForeName"), author.findtext("LastName")]))
            if name:
                author_names.append(name)
        journal = article.findtext(".//Journal/Title", default="PubMed indexed journal")
        year = article.findtext(".//PubDate/Year", default="")
        doi = ""
        for article_id in article.findall(".//ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = article_id.text or ""
                break
        out.append({
            "source": "PubMed", "title": _clean(title, 350),
            "authors": ", ".join(author_names) or "Authors not listed",
            "date": year, "venue": journal, "citations": None, "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            "open_access_url": "", "abstract": _clean(abstract, 1000),
            "retracted": False, "kind": "biomedical journal record",
        })
    return out


def search_news(query: str, limit: int = 6) -> list[dict]:
    params = urllib.parse.urlencode({
        "query": f'"{query}"', "mode": "ArtList", "format": "json",
        "maxrecords": limit, "sort": "DateDesc", "timespan": "30d",
    })
    data = _get_json("https://api.gdeltproject.org/api/v2/doc/doc?" + params)
    out = []
    for item in data.get("articles", []):
        out.append({
            "source": "GDELT News", "title": item.get("title") or "Untitled article",
            "authors": item.get("domain") or "Publisher not listed",
            "date": item.get("seendate", "")[:8], "venue": item.get("domain", ""),
            "citations": None, "doi": "", "url": item.get("url", ""),
            "open_access_url": "", "abstract": _clean(item.get("title", ""), 400),
            "retracted": False, "kind": "news article",
        })
    return out


def search_research(query: str, years_back: int = 3, per_source: int = 5) -> dict:
    """Search several public indexes independently; partial failures do not stop the search."""
    from_date = (date.today() - timedelta(days=365 * years_back)).isoformat()
    providers = [
        ("OpenAlex", lambda: search_openalex(query, from_date, per_source)),
        ("Crossref", lambda: search_crossref(query, from_date, per_source)),
        ("arXiv", lambda: search_arxiv(query, per_source)),
        ("PubMed", lambda: search_pubmed(query, per_source)),
        ("GDELT News", lambda: search_news(query, per_source)),
    ]
    results, errors = [], []
    for name, fn in providers:
        try:
            results.extend(fn())
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    # Prefer one record per DOI/URL/title while retaining provenance.
    seen, unique = set(), []
    for item in results:
        key = (item.get("doi") or item.get("url") or item.get("title", "").lower()).lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    unique.sort(key=lambda x: (x.get("date", ""), x.get("source") == "GDELT News"), reverse=True)
    return {"query": query, "from_date": from_date, "results": unique, "errors": errors}
