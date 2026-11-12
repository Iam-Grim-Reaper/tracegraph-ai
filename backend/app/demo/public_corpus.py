"""Fixed, content-addressed public demo dataset.

Document IDs are generated from the *actual* GitHub file bytes using
create_stable_document_id; never use filenames alone for access control.
Updating demo files requires intentionally updating this manifest.
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from app.models.document import FileType, create_stable_document_id


@dataclass(frozen=True)
class DemoDocument:
    filename: str
    file_type: FileType
    sha256_hex: str
    document_id: str


PUBLIC_DEMO_DOCUMENTS = (
    DemoDocument(
        "SHREY DOC FINAL.pdf",
        FileType.PDF,
        "df0d7658b4a3425fd822fdc9dc601a72e1dc80e9d110d8169b2b00f7598a1230",
        "05d5c184-d8cf-5e93-9117-f86a47a0da38",
    ),
    DemoDocument(
        "Team 16 12 (1).docx",
        FileType.DOCX,
        "d544ba927a6e06f09cc6e55b49d526f573c59f0346d3e5b7aff8bc053cb644ac",
        "c3b3b47a-cfbb-52be-9b7a-58f7d342fc95",
    ),
    DemoDocument(
        "Team 33 Final PPT.pptx",
        FileType.PPTX,
        "515d813de16480aae3d224b1935c323abaf692889fdd64e55f999a087bd1da25",
        "f9c77928-151c-5170-8c8a-d7e2315140eb",
    ),
)

PUBLIC_DEMO_IDS = frozenset(doc.document_id for doc in PUBLIC_DEMO_DOCUMENTS)


def is_public_demo_mode(settings) -> bool:
    return settings.app_env == "production" and settings.public_demo_only


def validate_demo_file(doc: DemoDocument, root: Path) -> Path:
    """Fail closed when GitHub content changes without manifest approval."""
    if Path(doc.filename).name != doc.filename:
        raise ValueError("Invalid public demo filename")
    path = root / doc.filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing public demo file: {doc.filename}")
    content = path.read_bytes()
    if sha256(content).hexdigest() != doc.sha256_hex:
        raise ValueError(f"Public demo checksum mismatch: {doc.filename}")
    computed = create_stable_document_id(content, doc.file_type)
    if computed != UUID(doc.document_id):
        raise ValueError(f"Public demo document ID mismatch: {doc.filename}")
    return path
