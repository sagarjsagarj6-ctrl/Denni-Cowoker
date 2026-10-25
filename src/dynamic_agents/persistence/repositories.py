"""Repositories that serialize typed models and keep secrets out of storage."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import TypeVar

from dynamic_agents.models.domain import (
    EvaluationRecord,
    ResumeTokenRecord,
    RunRecord,
    Team,
    TeamSnapshot,
)
from dynamic_agents.persistence.db import Database

T = TypeVar("T")

#: Words that carry no retrieval signal and would otherwise dominate ranking.
_STOP_WORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "any",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "day",
        "get",
        "has",
        "him",
        "his",
        "how",
        "its",
        "new",
        "now",
        "old",
        "see",
        "two",
        "who",
        "boy",
        "did",
        "she",
        "use",
        "with",
        "this",
        "that",
        "from",
        "they",
        "what",
        "when",
        "where",
        "which",
        "their",
        "would",
        "there",
        "been",
        "have",
        "more",
        "than",
        "then",
        "into",
        "about",
        "please",
        "tell",
        "give",
        "does",
        "your",
        "will",
        "should",
        "could",
        "case",
    }
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _query_terms(query: str, limit: int = 24) -> list[str]:
    """Extract meaningful lowercase terms from a free-text query."""
    tokens = _TOKEN_PATTERN.findall(query.lower())
    terms: list[str] = []
    for token in tokens:
        if len(token) < 3 or token in _STOP_WORDS or token in terms:
            continue
        terms.append(token)
    return terms[:limit]


def _query_phrases(query: str, limit: int = 6) -> list[str]:
    """Extract adjacent meaningful term pairs as exact-phrase probes."""
    tokens = [token for token in _TOKEN_PATTERN.findall(query.lower()) if len(token) >= 3]
    phrases: list[str] = []
    for first, second in zip(tokens, tokens[1:], strict=False):
        if first in _STOP_WORDS or second in _STOP_WORDS:
            continue
        phrase = f"{first} {second}"
        if phrase not in phrases:
            phrases.append(phrase)
    return phrases[:limit]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    """Persistence facade with atomic upserts for application records."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.database.upgrade()

    def save_run(self, record: RunRecord) -> None:
        payload = record.model_dump_json()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO runs(run_id,request_id,status,payload,created_at,updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(run_id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at",
                (
                    record.run_id,
                    record.request_id,
                    record.status.value,
                    payload,
                    record.started_at.isoformat(),
                    now_iso(),
                ),
            )

    def get_run(self, run_id: str) -> RunRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM runs WHERE run_id=?", (run_id,)
            ).fetchone()
        return RunRecord.model_validate_json(row["payload"]) if row else None

    def save_team(self, team: Team) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO teams(team_id,payload,created_at) VALUES(?,?,?)",
                (team.team_id, team.model_dump_json(), team.created_at.isoformat()),
            )

    def get_team(self, team_id: str) -> Team | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM teams WHERE team_id=?", (team_id,)
            ).fetchone()
        return Team.model_validate_json(row["payload"]) if row else None

    def save_snapshot(self, snapshot: TeamSnapshot) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO snapshots(snapshot_id,team_id,run_id,payload,created_at) VALUES(?,?,?,?,?)",
                (
                    snapshot.snapshot_id,
                    snapshot.team_id,
                    snapshot.run_id,
                    snapshot.model_dump_json(),
                    snapshot.created_at.isoformat(),
                ),
            )

    def get_snapshot(self, snapshot_id: str) -> TeamSnapshot | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
        return TeamSnapshot.model_validate_json(row["payload"]) if row else None

    def save_token(self, token: ResumeTokenRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO resume_tokens(token_id,token_hash,snapshot_id,payload,created_at) VALUES(?,?,?,?,?)",
                (
                    token.token_id,
                    token.token_hash,
                    token.snapshot_id,
                    token.model_dump_json(),
                    token.created_at.isoformat(),
                ),
            )

    def get_token_by_hash(self, token_hash: str) -> ResumeTokenRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload FROM resume_tokens WHERE token_hash=?", (token_hash,)
            ).fetchone()
        return ResumeTokenRecord.model_validate_json(row["payload"]) if row else None

    def save_evaluation(self, evaluation: EvaluationRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO evaluations(evaluation_id,case_id,payload,created_at) VALUES(?,?,?,?)",
                (
                    evaluation.evaluation_id,
                    evaluation.case_id,
                    evaluation.model_dump_json(),
                    evaluation.created_at.isoformat(),
                ),
            )

    def add_knowledge_chunk(
        self, chunk_id: str, company_id: str | None, payload: dict[str, object]
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO knowledge_chunks(chunk_id,company_id,payload,created_at) VALUES(?,?,?,?)",
                (chunk_id, company_id, json.dumps(payload), now_iso()),
            )

    def search_knowledge(
        self, query: str, company_id: str | None, top_k: int = 8
    ) -> list[dict[str, object]]:
        """Rank knowledge chunks by weighted term relevance.

        A raw substring count treats every match as equally important, so a
        chunk that repeats a common word outranks a chunk that answers the
        actual question. Scoring here therefore:
          * drops stop words and very short terms,
          * weights rarer terms higher (inverse document frequency),
          * gives title matches more weight than body matches,
          * rewards multi-word phrase matches (title phrase above body phrase),
          * favours company-specific chunks over shared ones.
        """
        terms = _query_terms(query)
        phrases = _query_phrases(query)
        if not terms:
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM knowledge_chunks WHERE company_id IS NULL OR company_id=?",
                (company_id,),
            ).fetchall()

        documents: list[tuple[dict[str, object], str, str]] = []
        for row in rows:
            payload = json.loads(row["payload"])
            body = str(payload.get("text", "")).lower()
            title = str(payload.get("title") or payload.get("source_name") or "").lower()
            documents.append((payload, title, body))

        document_frequency: dict[str, int] = {}
        for _, _, body in documents:
            for term in terms:
                if term in body:
                    document_frequency[term] = document_frequency.get(term, 0) + 1

        total = max(1, len(documents))
        scored: list[tuple[float, dict[str, object]]] = []
        for payload, title, body in documents:
            score = 0.0
            matched = 0
            for term in terms:
                occurrences = body.count(term)
                if not occurrences and term not in title:
                    continue
                matched += 1
                idf = math.log((total + 1) / (document_frequency.get(term, 0) + 1)) + 1.0
                # Saturating term frequency keeps one repetitive chunk on top.
                contribution = idf * (occurrences / (occurrences + 1.5))
                if term in title:
                    contribution += idf * 1.0
                score += contribution
            if not matched:
                continue
            # Reward chunks that match more of the distinct query terms.
            score *= 1.0 + (matched / len(terms) - 1.0) * 0.35
            # An exact phrase hit is a much stronger signal than loose terms.
            # A phrase in the title outranks a phrase buried in the body: the
            # title states the chunk's own topic, the body merely mentions it.
            for phrase in phrases:
                if phrase in title:
                    score += 3.0
                elif phrase in body:
                    score += 2.0
            if company_id and payload.get("company_id") == company_id:
                score *= 1.2
            scored.append((score, payload))
        return [
            payload
            for _, payload in sorted(scored, key=lambda item: (-item[0], str(item[1].get("chunk_id"))))[
                :top_k
            ]
        ]

    def get_all_knowledge_chunks(self, company_id: str | None = None) -> list[dict[str, object]]:
        with self.database.connect() as connection:
            if company_id:
                rows = connection.execute(
                    "SELECT chunk_id, company_id, payload, created_at FROM knowledge_chunks WHERE company_id=?",
                    (company_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT chunk_id, company_id, payload, created_at FROM knowledge_chunks ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
        results = []
        for row in rows:
            data = json.loads(row["payload"])
            data["company_id"] = row["company_id"]
            data["created_at"] = row["created_at"]
            results.append(data)
        return results

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RunRecord.model_validate_json(row["payload"]) for row in rows]

