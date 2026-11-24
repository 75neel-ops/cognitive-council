# Cognitive Council

## Ownership

Created and owned by **NilanjanC**. The app uses an original four-node Cognitive Council icon for its page favicon and branded header.

A browser-based multi-agent AI research and debate workspace.

## Research workspace

The AI Research Query Builder turns an ordinary-language question into 4–6 focused academic search queries. Researchers can review, edit, add, or remove the suggested queries before searching. If the query box is left blank, the app generates a plan automatically when the Council is convened. Query generation uses the selected Chief AI provider/model and therefore consumes an additional model API call.
When enabled, each Council session searches public discovery services for recent material:
- OpenAlex: scholarly works, authors, venues, abstracts when indexed, citation counts and open-access locations.
- Crossref: DOI and publication metadata deposited by publishers and registrants.
- PubMed: biomedical literature records and abstracts where available.
- arXiv: recent preprints, especially in physics, mathematics, computer science and related fields.
- GDELT: news-article discovery for the latest 30 days.

The app displays source links, dates, authors/publishers, venues, abstracts/summaries, indexed citation counts where available, and retraction flags when supplied by OpenAlex. The four agents receive a numbered evidence pack ([R1], [R2], …), and the Chief is instructed to cite those identifiers, distinguish news from research, and identify limitations.

Important: this is a discovery and synthesis aid, not a systematic-review platform. Index coverage varies; Crossref metadata does not itself establish peer review; arXiv items are preprints; citation counts are not quality scores; and news reports are context, not scientific evidence. Researchers should open the original records, verify publication status, methods, corrections/retractions, and references before citing. Full text is linked only when a source supplies an open-access location; the app does not bypass paywalls.

## Council architecture
- Four configurable AI agents with distinct roles.
- One Chief AI that synthesizes the panel's work.
- Basic mode: independent responses followed by a synthesis.
- Advanced mode: independent responses, peer critique, revised positions, and a final synthesis.
- AI Research Query Builder with editable, multi-query search plans.
- Optional live research retrieval before analysis.
- Downloadable Markdown session report.

## Data sources and documentation
- OpenAlex API: https://help.openalex.org/api/
- Crossref REST API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- arXiv API: https://info.arxiv.org/help/api/
- GDELT DOC API: https://blog.gdeltproject.org/gdelt-2-0-api-debuts/

## Run locally
1. Use Python 3.10 or newer.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add the API keys you want to use.
5. Run: `streamlit run app.py`

Never commit real API keys. The app also supports environment variables.

## Deployment
Deploy the repository to a Python-capable host such as Streamlit Community Cloud. Add API keys in the host's Secrets settings; do not upload `secrets.toml`.

## Status
Research discovery is integrated with the four-agent workflow. Public APIs may rate-limit or occasionally be unavailable; partial source failures are shown in the interface and do not prevent the Council from answering.
