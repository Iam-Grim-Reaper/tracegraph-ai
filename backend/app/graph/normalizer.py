import hashlib
import re
import unicodedata

from app.graph.models import (
    EntityCandidate,
    GraphEntity,
)


class EntityNormalizer:
    @staticmethod
    def normalize_name(
        name: str,
    ) -> str:
        if not name.strip():
            raise ValueError(
                "Entity name cannot be empty"
            )

        # Normalize Unicode representation.
        value = unicodedata.normalize(
            "NFKC",
            name,
        )

        # Case-insensitive canonical form.
        value = value.casefold()

        # Treat punctuation variants such as
        # Grad-CAM, Grad_CAM and Grad CAM alike.
        value = re.sub(
            r"[-_/]+",
            " ",
            value,
        )

        # Remove remaining punctuation while
        # preserving letters and numbers.
        value = re.sub(
            r"[^\w\s]",
            "",
            value,
        )

        # Collapse repeated whitespace.
        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    def normalize_entity(
        self,
        candidate: EntityCandidate,
    ) -> GraphEntity:
        normalized_name = self.normalize_name(
            candidate.name
        )

        entity_id = self._build_entity_id(
            normalized_name=normalized_name,
            entity_type=candidate.entity_type.value,
        )

        aliases = self._normalize_aliases(
            candidate.aliases,
            canonical_name=candidate.name,
        )

        return GraphEntity(
            entity_id=entity_id,
            name=candidate.name.strip(),
            normalized_name=normalized_name,
            entity_type=candidate.entity_type,
            aliases=aliases,
        )

    def normalize_entities(
        self,
        candidates: list[EntityCandidate],
    ) -> list[GraphEntity]:
        entities_by_id: dict[
            str,
            GraphEntity,
        ] = {}

        for candidate in candidates:
            entity = self.normalize_entity(
                candidate
            )

            existing = entities_by_id.get(
                entity.entity_id
            )

            if existing is None:
                entities_by_id[
                    entity.entity_id
                ] = entity
                continue

            merged_aliases = set(
                existing.aliases
            )

            merged_aliases.update(
                entity.aliases
            )

            if (
                entity.name
                != existing.name
            ):
                merged_aliases.add(
                    entity.name
                )

            existing.aliases = sorted(
                merged_aliases
            )

        return list(
            entities_by_id.values()
        )

    @staticmethod
    def _build_entity_id(
        normalized_name: str,
        entity_type: str,
    ) -> str:
        value = (
            f"{entity_type}|"
            f"{normalized_name}"
        )

        digest = hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()

        return digest

    def _normalize_aliases(
        self,
        aliases: list[str],
        canonical_name: str,
    ) -> list[str]:
        canonical_normalized = (
            self.normalize_name(
                canonical_name
            )
        )

        unique: dict[str, str] = {}

        for alias in aliases:
            if not alias.strip():
                continue

            normalized_alias = (
                self.normalize_name(
                    alias
                )
            )

            if (
                normalized_alias
                == canonical_normalized
            ):
                continue

            unique[
                normalized_alias
            ] = alias.strip()

        return sorted(
            unique.values()
        )