from app.ingestion.loaders.pdf_loader import PDFLoader
from app.ingestion.chunker import TextChunker
from app.retrieval.contextualizer import Contextualizer


def main():
    document, pages = PDFLoader().load(
        "../data/sample.pdf"
    )

    chunks = TextChunker(
        max_chars=1000
    ).chunk_pages(
        document=document,
        pages=pages,
    )

    document_text = "\n\n".join(
        page.text
        for page in pages
    )

    chunk = chunks[3]

    contextualizer = Contextualizer()

    context = contextualizer.contextualize_chunk(
        document=document,
        chunk=chunk,
        document_text=document_text,
    )

    print("\nORIGINAL CHUNK")
    print("=" * 80)
    print(chunk.text)

    print("\nGENERATED CONTEXT")
    print("=" * 80)
    print(context)

    print("\nCONTEXTUAL RETRIEVAL REPRESENTATION")
    print("=" * 80)

    contextual_text = (
        f"{context}\n\n{chunk.text}"
    )

    print(contextual_text)


if __name__ == "__main__":
    main()