from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingestion.loaders.office_common import enforce_text_limit, validate_office_package
from app.models.document import Document, DocumentMetadata, FileType, ParsedUnit, SourceLocator, create_stable_document_id


class DOCXLoader:
    def load(self, file_path: str | Path) -> tuple[Document, list[ParsedUnit]]:
        path = Path(file_path)
        if path.suffix.lower() != ".docx":
            raise ValueError(f"Unsupported file type: {path.suffix}. Expected .docx")
        content = validate_office_package(path, "word/document.xml")
        try:
            source = DocxDocument(path)
        except Exception as exc:
            raise ValueError(f"Unable to read DOCX: {path.name}") from exc

        units = []
        heading = None
        paragraph_index = 0
        table_index = 0
        extracted = 0
        for block in source.iter_inner_content():
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if not text:
                    continue
                paragraph_index += 1
                if block.style and block.style.name.startswith("Heading"):
                    heading = text
                prefix = "List item: " if block.style and "List" in block.style.name else ""
                rendered = prefix + text
                extracted = enforce_text_limit(extracted, rendered)
                units.append(ParsedUnit(
                    text=rendered,
                    section=heading,
                    heading=heading if rendered == heading else None,
                    source_locator=SourceLocator(
                        type="section" if heading else "paragraph",
                        label=f"Section: {heading}" if heading else f"Paragraph {paragraph_index}",
                    ),
                ))
            elif isinstance(block, Table):
                table_index += 1
                rows = [[cell.text.strip() for cell in row.cells] for row in block.rows]
                rows = [row for row in rows if any(row)]
                if not rows:
                    continue
                headers = [value or f"Column {index + 1}" for index, value in enumerate(rows[0])]
                lines = [f"Table {table_index}", "Columns: " + " | ".join(headers)]
                for row in rows[1:]:
                    lines.append("Row:\n" + "\n".join(
                        f"{header}: {value}" for header, value in zip(headers, row) if value
                    ))
                rendered = "\n\n".join(lines)
                extracted = enforce_text_limit(extracted, rendered)
                units.append(ParsedUnit(
                    text=rendered,
                    section=heading,
                    source_locator=SourceLocator(type="table", label=f"Table {table_index}"),
                ))
        if not units:
            raise ValueError("DOCX contains no extractable text")
        properties = source.core_properties
        return Document(
            id=create_stable_document_id(content, FileType.DOCX),
            filename=path.name,
            file_type=FileType.DOCX,
            metadata=DocumentMetadata(title=properties.title or None, author=properties.author or None),
        ), units
