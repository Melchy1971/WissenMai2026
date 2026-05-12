"""
Golden Query Set for Retrieval Regression Detection.

Design:
- 10 active benchmark documents, each with a unique keyword (bqkw001..010)
  and a shared keyword (benchcorpus).
- 1 archived document with its own unique keyword (bencharchived).
- 12 golden queries covering single-hit precision, multi-hit recall,
  and lifecycle exclusion.
"""
from __future__ import annotations

from dataclasses import dataclass, field


SHARED_KEYWORD = "benchcorpus"
ARCHIVED_KEYWORD = "bencharchived"


@dataclass(frozen=True)
class BenchmarkDocument:
    label: str
    unique_kw: str
    title: str
    content: str


@dataclass(frozen=True)
class GoldenQuery:
    id: str
    description: str
    query: str
    expected_labels: list[str]
    k: int = 5
    expect_empty: bool = False


BENCHMARK_CORPUS: list[BenchmarkDocument] = [
    BenchmarkDocument(
        label="quantum",
        unique_kw="bqkw001kv",
        title="Quantencomputing Grundlagen",
        content=(
            f"{SHARED_KEYWORD} bqkw001kv "
            "Quantencomputing nutzt Superposition und Verschraenkung. "
            "Qubits existieren gleichzeitig in mehreren Zustaenden. "
            "Quantenalgorithmen loesen bestimmte Probleme exponentiell schneller."
        ),
    ),
    BenchmarkDocument(
        label="ml",
        unique_kw="bqkw002ml",
        title="Maschinelles Lernen Klassifikation",
        content=(
            f"{SHARED_KEYWORD} bqkw002ml "
            "Klassifikationsalgorithmen unterscheiden Datenpunkte nach Klassen. "
            "Random Forest kombiniert viele Entscheidungsbaeume. "
            "Kreuzvalidierung schuetzt vor Overfitting bei kleinen Datensaetzen."
        ),
    ),
    BenchmarkDocument(
        label="privacy",
        unique_kw="bqkw003dp",
        title="Datenschutz und DSGVO",
        content=(
            f"{SHARED_KEYWORD} bqkw003dp "
            "Die DSGVO regelt den Umgang mit personenbezogenen Daten in der EU. "
            "Verantwortliche muessen Verarbeitungsverzeichnisse fuehren. "
            "Betroffenenrechte umfassen Auskunft, Berichtigung und Loeschung."
        ),
    ),
    BenchmarkDocument(
        label="security",
        unique_kw="bqkw004ns",
        title="Netzwerksicherheit und Zugangskontrolle",
        content=(
            f"{SHARED_KEYWORD} bqkw004ns "
            "Firewalls kontrollieren eingehenden und ausgehenden Netzwerkverkehr. "
            "Zugangskontrolle basiert auf Rollen und Berechtigungen. "
            "Intrusion Detection Systeme erkennen unerwuenschte Zugriffe."
        ),
    ),
    BenchmarkDocument(
        label="deeplearning",
        unique_kw="bqkw005nn",
        title="Neuronale Netze und Backpropagation",
        content=(
            f"{SHARED_KEYWORD} bqkw005nn "
            "Backpropagation berechnet Gradienten rueckwaerts durch das Netz. "
            "Aktivierungsfunktionen wie ReLU einfuehren Nicht-Linearitaet. "
            "Dropout verhindert Overfitting durch zufaelliges Deaktivieren von Neuronen."
        ),
    ),
    BenchmarkDocument(
        label="database",
        unique_kw="bqkw006db",
        title="Datenbankoptimierung und Indexierung",
        content=(
            f"{SHARED_KEYWORD} bqkw006db "
            "Datenbankindizes beschleunigen Abfragen auf grossen Tabellen erheblich. "
            "Der Abfrageplaner waehlt den optimalen Ausfuehrungsplan automatisch. "
            "Partitionierung verteilt Daten auf mehrere physische Speichereinheiten."
        ),
    ),
    BenchmarkDocument(
        label="kubernetes",
        unique_kw="bqkw007k8",
        title="Container und Kubernetes Orchestrierung",
        content=(
            f"{SHARED_KEYWORD} bqkw007k8 "
            "Kubernetes orchestriert containerisierte Anwendungen automatisch. "
            "Pods sind die kleinste deploybare Einheit in Kubernetes-Clustern. "
            "Services ermoeglichen stabilen Netzwerkzugang zu laufenden Pods."
        ),
    ),
    BenchmarkDocument(
        label="api",
        unique_kw="bqkw008ra",
        title="REST API und OAuth Authentifizierung",
        content=(
            f"{SHARED_KEYWORD} bqkw008ra "
            "REST APIs verwenden HTTP-Methoden fuer CRUD-Operationen auf Ressourcen. "
            "OAuth 2.0 delegiert Authentifizierung an den Authorisierungsserver. "
            "JWT-Tokens enthalten signierte Claims fuer zustandslose Sitzungen."
        ),
    ),
    BenchmarkDocument(
        label="backup",
        unique_kw="bqkw009bk",
        title="Backup Replikation und Hochverfuegbarkeit",
        content=(
            f"{SHARED_KEYWORD} bqkw009bk "
            "Replikation kopiert Daten auf mehrere Knoten fuer Ausfallsicherheit. "
            "Hochverfuegbarkeit erfordert redundante Systeme mit automatischem Failover. "
            "Recovery Point Objective definiert den maximal tolerierten Datenverlust."
        ),
    ),
    BenchmarkDocument(
        label="crypto",
        unique_kw="bqkw010cr",
        title="Kryptographie und Verschluesselung",
        content=(
            f"{SHARED_KEYWORD} bqkw010cr "
            "Symmetrische Verschluesselung verwendet denselben Schluessel. "
            "Asymmetrische Kryptographie nutzt ein Schluesselpaar aus Public und Private Key. "
            "Hashfunktionen erzeugen aus beliebigen Eingaben Fingerabdruecke fester Laenge."
        ),
    ),
]

ARCHIVED_DOCUMENT = BenchmarkDocument(
    label="archived",
    unique_kw=ARCHIVED_KEYWORD,
    title="Archiviertes Benchmark-Dokument",
    content=(
        f"{SHARED_KEYWORD} {ARCHIVED_KEYWORD} "
        "Dieses Dokument ist archiviert und soll in Suchergebnissen nicht erscheinen. "
        "Es validiert die Lifecycle-Isolation des PostgreSQL-Suchindexes."
    ),
)

ACTIVE_LABELS: list[str] = [doc.label for doc in BENCHMARK_CORPUS]

GOLDEN_QUERIES: list[GoldenQuery] = [
    # Q01-Q10: Single-hit precision — each unique keyword matches exactly one document
    GoldenQuery(
        id="gq-001", description="Einzeltreffer: Quantencomputing (bqkw001kv)",
        query="bqkw001kv", expected_labels=["quantum"], k=5,
    ),
    GoldenQuery(
        id="gq-002", description="Einzeltreffer: Maschinelles Lernen (bqkw002ml)",
        query="bqkw002ml", expected_labels=["ml"], k=5,
    ),
    GoldenQuery(
        id="gq-003", description="Einzeltreffer: Datenschutz (bqkw003dp)",
        query="bqkw003dp", expected_labels=["privacy"], k=5,
    ),
    GoldenQuery(
        id="gq-004", description="Einzeltreffer: Netzwerksicherheit (bqkw004ns)",
        query="bqkw004ns", expected_labels=["security"], k=5,
    ),
    GoldenQuery(
        id="gq-005", description="Einzeltreffer: Neuronale Netze (bqkw005nn)",
        query="bqkw005nn", expected_labels=["deeplearning"], k=5,
    ),
    GoldenQuery(
        id="gq-006", description="Einzeltreffer: Datenbankoptimierung (bqkw006db)",
        query="bqkw006db", expected_labels=["database"], k=5,
    ),
    GoldenQuery(
        id="gq-007", description="Einzeltreffer: Kubernetes (bqkw007k8)",
        query="bqkw007k8", expected_labels=["kubernetes"], k=5,
    ),
    GoldenQuery(
        id="gq-008", description="Einzeltreffer: REST API (bqkw008ra)",
        query="bqkw008ra", expected_labels=["api"], k=5,
    ),
    GoldenQuery(
        id="gq-009", description="Einzeltreffer: Backup und HA (bqkw009bk)",
        query="bqkw009bk", expected_labels=["backup"], k=5,
    ),
    GoldenQuery(
        id="gq-010", description="Einzeltreffer: Kryptographie (bqkw010cr)",
        query="bqkw010cr", expected_labels=["crypto"], k=5,
    ),
    # Q11: Recall test — shared keyword in all 10 active documents
    GoldenQuery(
        id="gq-011",
        description="Mehrtreffer: Shared keyword benchcorpus (Recall@10)",
        query=SHARED_KEYWORD,
        expected_labels=ACTIVE_LABELS,
        k=10,
    ),
    # Q12: Lifecycle exclusion — archived document must not appear
    GoldenQuery(
        id="gq-012",
        description="Lifecycle-Isolation: archiviertes Dokument muss fehlen",
        query=ARCHIVED_KEYWORD,
        expected_labels=[],
        k=5,
        expect_empty=True,
    ),
]

# Regression thresholds — violation = gate failure
REGRESSION_THRESHOLDS: dict[str, float] = {
    "precision_at_k": 0.80,
    "recall_at_k": 0.70,
    "citation_completeness": 0.85,
    "missing_context_rate_max": 0.15,
}

# Maximum allowed drop vs. stored baseline before declaring regression
REGRESSION_DELTA = 0.05
