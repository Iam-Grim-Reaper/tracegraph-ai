import re

from app.models.document import (
    ChunkMetadata,
    Document,
    DocumentChunk,
    ParsedPage,
    create_stable_chunk_id,
)


class TextChunker:
    def __init__(
        self,
        max_chars: int = 1000,
    ):
        if max_chars < 100:
            raise ValueError(
                "max_chars must be at least 100"
            )

        self.max_chars = max_chars

    def chunk(
        self,
        document: Document,
        text: str,
    ) -> list[DocumentChunk]:
        chunk_texts = self._chunk_text(
            text
        )

        chunk_specs = [
            (
                None,
                chunk_text,
            )
            for chunk_text in chunk_texts
        ]

        return self._build_chunks(
            document=document,
            chunk_specs=chunk_specs,
        )

    def chunk_pages(
        self,
        document: Document,
        pages: list[ParsedPage],
    ) -> list[DocumentChunk]:
        if not pages:
            raise ValueError(
                "Cannot chunk an empty "
                "page list"
            )

        chunk_specs: list[
            tuple[int | None, str]
        ] = []

        for page in pages:
            if not page.text.strip():
                continue

            page_chunks = self._chunk_text(
                page.text
            )

            for chunk_text in page_chunks:
                chunk_specs.append(
                    (
                        page.page_number,
                        chunk_text,
                    )
                )

        if not chunk_specs:
            raise ValueError(
                "Pages contain no "
                "chunkable text"
            )

        return self._build_chunks(
            document=document,
            chunk_specs=chunk_specs,
        )

    def _chunk_text(
        self,
        text: str,
    ) -> list[str]:
        cleaned_text = text.strip()

        if not cleaned_text:
            raise ValueError(
                "Cannot chunk empty text"
            )

        paragraphs = (
            self._extract_paragraphs(
                cleaned_text
            )
        )

        chunk_texts: list[str] = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph_parts = (
                self._split_long_paragraph(
                    paragraph
                )
            )

            for part in paragraph_parts:
                if not current_chunk:
                    current_chunk = part
                    continue

                candidate = (
                    f"{current_chunk}"
                    f"\n\n{part}"
                )

                if (
                    len(candidate)
                    <= self.max_chars
                ):
                    current_chunk = candidate

                else:
                    chunk_texts.append(
                        current_chunk
                    )

                    current_chunk = part

        if current_chunk:
            chunk_texts.append(
                current_chunk
            )

        return chunk_texts

    def _build_chunks(
        self,
        document: Document,
        chunk_specs: list[
            tuple[int | None, str]
        ],
    ) -> list[DocumentChunk]:
        # IDs are now deterministic.
        #
        # Same:
        # document ID
        # + index
        # + page
        # + text
        #
        # = same chunk UUID.
        chunk_ids = [
            create_stable_chunk_id(
                document_id=document.id,
                chunk_index=index,
                text=chunk_text,
                page_number=page_number,
            )
            for index, (
                page_number,
                chunk_text,
            ) in enumerate(
                chunk_specs
            )
        ]

        chunks: list[
            DocumentChunk
        ] = []

        for index, (
            page_number,
            chunk_text,
        ) in enumerate(
            chunk_specs
        ):
            previous_chunk_id = (
                chunk_ids[index - 1]
                if index > 0
                else None
            )

            next_chunk_id = (
                chunk_ids[index + 1]
                if (
                    index
                    < len(chunk_ids) - 1
                )
                else None
            )

            chunk = DocumentChunk(
                id=chunk_ids[index],
                document_id=document.id,
                chunk_index=index,
                text=chunk_text,
                metadata=ChunkMetadata(
                    page_number=(
                        page_number
                    ),
                ),
                previous_chunk_id=(
                    previous_chunk_id
                ),
                next_chunk_id=(
                    next_chunk_id
                ),
            )

            chunks.append(
                chunk
            )

        return chunks

    def _extract_paragraphs(
        self,
        text: str,
    ) -> list[str]:
        raw_paragraphs = re.split(
            r"\n\s*\n",
            text,
        )

        paragraphs = []

        for paragraph in raw_paragraphs:
            cleaned = re.sub(
                r"\s+",
                " ",
                paragraph,
            ).strip()

            if cleaned:
                paragraphs.append(
                    cleaned
                )

        return paragraphs

    def _split_long_paragraph(
        self,
        paragraph: str,
    ) -> list[str]:
        if (
            len(paragraph)
            <= self.max_chars
        ):
            return [
                paragraph
            ]

        words = paragraph.split()

        parts: list[str] = []
        current_part = ""

        for word in words:
            if len(word) > self.max_chars:
                if current_part:
                    parts.append(
                        current_part
                    )

                    current_part = ""

                while (
                    len(word)
                    > self.max_chars
                ):
                    parts.append(
                        word[
                            :self.max_chars
                        ]
                    )

                    word = word[
                        self.max_chars:
                    ]

                if word:
                    current_part = word

                continue

            candidate = (
                f"{current_part} {word}"
                if current_part
                else word
            )

            if (
                len(candidate)
                <= self.max_chars
            ):
                current_part = candidate

            else:
                parts.append(
                    current_part
                )

                current_part = word

        if current_part:
            parts.append(
                current_part
            )

        return parts