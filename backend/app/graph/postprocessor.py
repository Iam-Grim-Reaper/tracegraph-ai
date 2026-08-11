import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.graph.models import (
    ExtractedGraph,
    GraphEntity,
    GraphRelationship,
)
from app.graph.normalizer import EntityNormalizer
from app.graph.validator import (
    GraphRelationshipValidator,
    RejectedRelationship,
)
from app.models.document import (
    Document,
    DocumentChunk,
)


@dataclass
class ProcessedChunkGraph:
    entities: list[GraphEntity]
    relationships: list[GraphRelationship]
    rejected_relationships: list[
        RejectedRelationship
    ]


class GraphPostProcessor:
    def __init__(self):
        self.normalizer = EntityNormalizer()
        self.validator = GraphRelationshipValidator()

    def process(
        self,
        document: Document,
        chunk: DocumentChunk,
        extracted_graph: ExtractedGraph,
    ) -> ProcessedChunkGraph:
        # Step 1: Resolve semantic aliases.
        resolved_candidates = (
            self.normalizer.resolve_alias_entities(
                extracted_graph.entities
            )
        )

        # Step 2: Produce canonical entities.
        entities = (
            self.normalizer.normalize_entities(
                resolved_candidates
            )
        )

        entity_lookup = self._build_entity_lookup(
            entities
        )

        # Step 3: Validate relationships.
        accepted, rejected = (
            self.validator.filter_relationships(
                extracted_graph.relationships
            )
        )

        relationships: list[
            GraphRelationship
        ] = []

        for relationship in accepted:
            # Step 4: Ground claimed evidence
            # against the actual source chunk.
            if not self._evidence_is_grounded(
                evidence=relationship.evidence_text,
                chunk_text=chunk.text,
            ):
                rejected.append(
                    RejectedRelationship(
                        relationship=relationship,
                        reason=(
                            "Evidence text was not "
                            "sufficiently grounded "
                            "in source chunk"
                        ),
                    )
                )
                continue

            # Step 5: Resolve endpoints.
            source_key = (
                relationship.source_type.value,
                self.normalizer.normalize_name(
                    relationship.source_name
                ),
            )

            target_key = (
                relationship.target_type.value,
                self.normalizer.normalize_name(
                    relationship.target_name
                ),
            )

            source_entity = entity_lookup.get(
                source_key
            )

            target_entity = entity_lookup.get(
                target_key
            )

            if source_entity is None:
                rejected.append(
                    RejectedRelationship(
                        relationship=relationship,
                        reason=(
                            "Could not resolve "
                            "relationship source "
                            "to a canonical entity"
                        ),
                    )
                )
                continue

            if target_entity is None:
                rejected.append(
                    RejectedRelationship(
                        relationship=relationship,
                        reason=(
                            "Could not resolve "
                            "relationship target "
                            "to a canonical entity"
                        ),
                    )
                )
                continue

            # Step 6: Attach provenance.
            relationships.append(
                GraphRelationship(
                    source_entity_id=(
                        source_entity.entity_id
                    ),
                    target_entity_id=(
                        target_entity.entity_id
                    ),
                    relationship_type=(
                        relationship.relationship_type
                    ),
                    confidence=(
                        relationship.confidence
                    ),
                    evidence_text=(
                        relationship.evidence_text.strip()
                    ),
                    source_document_id=str(
                        document.id
                    ),
                    source_chunk_id=str(
                        chunk.id
                    ),
                    page_number=(
                        chunk.metadata.page_number
                    ),
                )
            )

        return ProcessedChunkGraph(
            entities=entities,
            relationships=relationships,
            rejected_relationships=rejected,
        )

    def _build_entity_lookup(
        self,
        entities: list[GraphEntity],
    ) -> dict[
        tuple[str, str],
        GraphEntity,
    ]:
        lookup: dict[
            tuple[str, str],
            GraphEntity,
        ] = {}

        for entity in entities:
            names = [
                entity.name,
                *entity.aliases,
            ]

            for name in names:
                key = (
                    entity.entity_type.value,
                    self.normalizer.normalize_name(
                        name
                    ),
                )

                lookup[key] = entity

        return lookup

    @classmethod
    def _evidence_is_grounded(
        cls,
        evidence: str,
        chunk_text: str,
    ) -> bool:
        normalized_evidence = (
            cls._normalize_for_match(
                evidence
            )
        )

        normalized_chunk = (
            cls._normalize_for_match(
                chunk_text
            )
        )

        if not normalized_evidence:
            return False

        if not normalized_chunk:
            return False

        # Best case: direct normalized match.
        if normalized_evidence in normalized_chunk:
            return True

        evidence_tokens = (
            cls._tokenize_for_match(
                normalized_evidence
            )
        )

        chunk_tokens = (
            cls._tokenize_for_match(
                normalized_chunk
            )
        )

        # Very short evidence is too easy
        # to match accidentally.
        if len(evidence_tokens) < 4:
            return False

        evidence_token_set = set(
            evidence_tokens
        )

        chunk_token_set = set(
            chunk_tokens
        )

        token_coverage = (
            len(
                evidence_token_set
                & chunk_token_set
            )
            / len(evidence_token_set)
        )

        window_size = len(
            evidence_tokens
        )

        best_similarity = 0.0

        if len(chunk_tokens) <= window_size:
            windows = [
                chunk_tokens
            ]
        else:
            windows = [
                chunk_tokens[
                    start:start + window_size
                ]
                for start in range(
                    len(chunk_tokens)
                    - window_size
                    + 1
                )
            ]

        for window in windows:
            if not window:
                continue

            similarity = SequenceMatcher(
                None,
                " ".join(
                    evidence_tokens
                ),
                " ".join(
                    window
                ),
            ).ratio()

            best_similarity = max(
                best_similarity,
                similarity,
            )

        return (
            token_coverage >= 0.85
            and best_similarity >= 0.75
        )

    @staticmethod
    def _tokenize_for_match(
        value: str,
    ) -> list[str]:
        tokens: list[str] = []

        for token in value.split():
            cleaned = token.strip(
                ".,;:!?()[]{}\"'"
            )

            if cleaned:
                tokens.append(
                    cleaned
                )

        return tokens

    @staticmethod
    def _normalize_for_match(
        value: str,
    ) -> str:
        value = unicodedata.normalize(
            "NFKC",
            value,
        )

        value = value.casefold()

        # Normalize Unicode dash variants.
        value = re.sub(
            r"[‐-‒–—]",
            "-",
            value,
        )

        # Fix PDF spacing such as:
        # ConvNeXt -Small -> ConvNeXt-Small
        value = re.sub(
            r"\s*-\s*",
            "-",
            value,
        )

        # Collapse repeated whitespace.
        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()