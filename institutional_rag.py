"""Permitted-source RAG workflow for institutional financial outreach.

The helpers in this module intentionally model organization-level and role-based
contacts only. They are designed for public, official sources such as company
websites, SEC EDGAR filings, FINRA/BrokerCheck firm records, Federal Reserve/NIC
institution records, official press releases, annual reports, and proxy
statements. They do not support scraping social networks or collecting personal
contact data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable
from urllib.parse import urlparse


class PermittedSourceType(str, Enum):
    """Official public source categories allowed in the outreach RAG index."""

    COMPANY_WEBSITE = "company_website"
    SEC_EDGAR = "sec_edgar"
    FINRA_BROKERCHECK = "finra_brokercheck"
    FEDERAL_RESERVE_NIC = "federal_reserve_nic"
    OFFICIAL_PRESS_RELEASE = "official_press_release"
    ANNUAL_REPORT = "annual_report"
    PROXY_STATEMENT = "proxy_statement"


class OutreachRole(str, Enum):
    """Role-level contacts suitable for institutional outreach lists."""

    INVESTOR_RELATIONS = "Investor Relations"
    MEDIA_RELATIONS = "Media Relations"
    CORPORATE_SECRETARY = "Corporate Secretary"
    ALTERNATIVE_INVESTMENTS = "Alternative Investments Contact"
    INSTITUTIONAL_SALES = "Institutional Sales"
    GENERAL_CORPORATE = "General Corporate Contact"


@dataclass(frozen=True)
class PermittedSource:
    """Metadata for a public source document that may be indexed."""

    source_type: PermittedSourceType
    url: str
    organization: str
    title: str
    retrieved_at: str | None = None


@dataclass(frozen=True)
class SourceDocument:
    """A normalized document ready for chunking and embedding."""

    source: PermittedSource
    text: str


@dataclass(frozen=True)
class OutreachContact:
    """Organization or role-based contact generated from cited public sources."""

    organization: str
    role: OutreachRole
    contact_label: str
    source_urls: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class RagWorkflowStep:
    """A single workflow step with compliance controls."""

    name: str
    action: str
    compliance_gate: str


@dataclass(frozen=True)
class RetrievalResult:
    """Minimal retrieval result used to produce cited outreach entries."""

    document: SourceDocument
    score: float


@dataclass
class InstitutionalRagWorkflow:
    """Build role-based outreach lists from permitted institutional sources.

    The class is deliberately storage-agnostic: callers can plug the generated
    chunks into their preferred embedding model and vector database, then pass
    retrieval results back into ``generate_outreach_contacts``.
    """

    allowed_company_domains: set[str] = field(default_factory=set)

    def workflow_steps(self) -> list[RagWorkflowStep]:
        """Return an auditable RAG workflow with explicit compliance gates."""
        return [
            RagWorkflowStep(
                name="discover_sources",
                action="Collect official URLs from company sites, SEC EDGAR, FINRA/BrokerCheck, Federal Reserve/NIC, press releases, annual reports, and proxy statements.",
                compliance_gate="Reject social networks, scraped profile pages, personal contact brokers, and non-public data.",
            ),
            RagWorkflowStep(
                name="normalize_documents",
                action="Extract document text, source type, organization, title, URL, and retrieval timestamp.",
                compliance_gate="Keep only source-level provenance and do not infer private personal attributes.",
            ),
            RagWorkflowStep(
                name="chunk_and_embed",
                action="Chunk text by document section, embed chunks, and store vectors with source metadata.",
                compliance_gate="Index content only when the source category is permitted and the URL passes domain validation.",
            ),
            RagWorkflowStep(
                name="retrieve_with_citations",
                action="Retrieve high-scoring chunks for role-level outreach queries such as investor relations or corporate secretary.",
                compliance_gate="Require citations to public source URLs for every generated contact entry.",
            ),
            RagWorkflowStep(
                name="generate_outreach_list",
                action="Generate organization-level or role-based contacts, never individual personal dossiers.",
                compliance_gate="Suppress personal phone numbers, personal emails, household data, wealth labels, and LinkedIn-derived content.",
            ),
        ]

    def is_source_allowed(self, source: PermittedSource) -> bool:
        """Validate source category and URL domain before indexing."""
        parsed = urlparse(source.url)
        host = parsed.netloc.lower().removeprefix("www.")
        if parsed.scheme not in {"http", "https"} or not host:
            return False

        official_domains = {
            "sec.gov",
            "brokercheck.finra.org",
            "finra.org",
            "ffiec.gov",
            "federalreserve.gov",
            "nic.ffiec.gov",
        }
        if host in official_domains or any(host.endswith(f".{domain}") for domain in official_domains):
            return source.source_type in {
                PermittedSourceType.SEC_EDGAR,
                PermittedSourceType.FINRA_BROKERCHECK,
                PermittedSourceType.FEDERAL_RESERVE_NIC,
            }

        return source.source_type in {
            PermittedSourceType.COMPANY_WEBSITE,
            PermittedSourceType.OFFICIAL_PRESS_RELEASE,
            PermittedSourceType.ANNUAL_REPORT,
            PermittedSourceType.PROXY_STATEMENT,
        } and (not self.allowed_company_domains or host in self.allowed_company_domains)

    def chunk_documents(self, documents: Iterable[SourceDocument], max_chars: int = 1200) -> list[SourceDocument]:
        """Split allowed documents into simple character-bounded chunks."""
        chunks: list[SourceDocument] = []
        for document in documents:
            if not self.is_source_allowed(document.source):
                continue
            clean_text = " ".join(document.text.split())
            for start in range(0, len(clean_text), max_chars):
                chunk_text = clean_text[start : start + max_chars]
                if chunk_text:
                    chunks.append(SourceDocument(source=document.source, text=chunk_text))
        return chunks

    def generate_outreach_contacts(self, results: Iterable[RetrievalResult]) -> list[OutreachContact]:
        """Create cited role-level contacts from retrieved public documents."""
        contacts: dict[tuple[str, OutreachRole], set[str]] = {}
        for result in results:
            source = result.document.source
            text = result.document.text.lower()
            for marker, role in ROLE_MARKERS.items():
                if marker in text:
                    key = (source.organization, role)
                    contacts.setdefault(key, set()).add(source.url)

        return [
            OutreachContact(
                organization=organization,
                role=role,
                contact_label=f"{role.value} — {organization}",
                source_urls=tuple(sorted(urls)),
                notes="Generated from permitted public institutional sources.",
            )
            for (organization, role), urls in sorted(contacts.items(), key=lambda item: (item[0][0], item[0][1].value))
        ]


ROLE_MARKERS: dict[str, OutreachRole] = {
    "investor relations": OutreachRole.INVESTOR_RELATIONS,
    "media relations": OutreachRole.MEDIA_RELATIONS,
    "press contact": OutreachRole.MEDIA_RELATIONS,
    "corporate secretary": OutreachRole.CORPORATE_SECRETARY,
    "alternative investments": OutreachRole.ALTERNATIVE_INVESTMENTS,
    "institutional sales": OutreachRole.INSTITUTIONAL_SALES,
    "contact us": OutreachRole.GENERAL_CORPORATE,
}


def default_outreach_queries(organizations: Iterable[str]) -> list[str]:
    """Build safe role-level retrieval queries for each organization."""
    roles = [
        OutreachRole.INVESTOR_RELATIONS,
        OutreachRole.MEDIA_RELATIONS,
        OutreachRole.CORPORATE_SECRETARY,
        OutreachRole.ALTERNATIVE_INVESTMENTS,
    ]
    return [f"{role.value} — {organization}" for organization in organizations for role in roles]
