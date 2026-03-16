import asyncio
import logging
import uuid

import httpx
import tiktoken
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.services.embedding import embed_texts

logger = logging.getLogger(__name__)

_tokenizer = tiktoken.get_encoding(settings.TIKTOKEN_ENCODING)

HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]

MAX_CHUNK_TOKENS = 512
TARGET_CHUNK_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 50

LLAMA_PARSE_BASE = settings.LLAMA_CLOUD_BASE_URL or "https://api.cloud.llamaindex.ai/api/v1"


def _token_length(text: str) -> int:
    return len(_tokenizer.encode(text))


async def parse_document(file_path: str) -> tuple[str, list[dict] | None]:
    """Parse a document via LlamaParse REST API.

    Returns (markdown, page_map) where page_map is a list of
    {"page": int, "md": str} dicts, or None if JSON fetch fails.
    """
    headers = {
        "Authorization": f"Bearer {settings.LLAMA_CLOUD_API_KEY}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=300) as client:
        # 1. Upload file to start a parsing job
        with open(file_path, "rb") as f:
            resp = await client.post(
                f"{LLAMA_PARSE_BASE}/parsing/upload",
                headers=headers,
                files={"file": (file_path.split("/")[-1], f)},
                data={"result_type": "markdown"},
            )
        resp.raise_for_status()
        job_id = resp.json()["id"]
        logger.info(f"LlamaParse job started: {job_id}")

        # 2. Poll until job completes
        for _ in range(120):  # up to ~10 minutes
            status_resp = await client.get(
                f"{LLAMA_PARSE_BASE}/parsing/job/{job_id}",
                headers=headers,
            )
            status_resp.raise_for_status()
            status = status_resp.json()["status"]

            if status == "SUCCESS":
                break
            if status in ("ERROR", "FAILED"):
                raise RuntimeError(f"LlamaParse job failed: {status_resp.json()}")

            await asyncio.sleep(5)
        else:
            raise TimeoutError(f"LlamaParse job {job_id} timed out")

        # 3. Fetch markdown result
        result_resp = await client.get(
            f"{LLAMA_PARSE_BASE}/parsing/job/{job_id}/result/markdown",
            headers=headers,
        )
        result_resp.raise_for_status()
        markdown = result_resp.json()["markdown"]

        # 4. Fetch JSON result for page-level mapping
        page_map: list[dict] | None = None
        try:
            json_resp = await client.get(
                f"{LLAMA_PARSE_BASE}/parsing/job/{job_id}/result/json",
                headers=headers,
            )
            json_resp.raise_for_status()
            pages_data = json_resp.json().get("pages", [])
            page_map = [
                {"page": p.get("page", i + 1), "md": p.get("md", "")}
                for i, p in enumerate(pages_data)
            ]
            logger.info(f"LlamaParse page map: {len(page_map)} pages")
        except Exception:
            logger.warning(f"Failed to fetch JSON page map for job {job_id}, continuing without page numbers")

        return markdown, page_map


def _assign_page_numbers(chunk_text: str, page_map: list[dict] | None) -> list[int]:
    """Match a chunk's text to its source page(s) via substring overlap."""
    if not page_map:
        return []

    # Normalize chunk text for matching
    chunk_norm = chunk_text.strip()
    if not chunk_norm:
        return []

    pages: list[int] = []
    # Use a sliding window of words from the chunk to find which page contains it
    chunk_words = chunk_norm[:200]  # first ~200 chars for matching

    for entry in page_map:
        page_md = entry.get("md", "")
        if not page_md:
            continue
        # Check if a meaningful portion of the chunk appears in this page
        if chunk_words in page_md or (len(chunk_norm) > 50 and chunk_norm[:100] in page_md):
            pages.append(entry["page"])

    # Fallback: try matching with longer overlaps
    if not pages:
        for entry in page_map:
            page_md = entry.get("md", "")
            if not page_md:
                continue
            # Check word-level overlap
            chunk_word_set = set(chunk_norm.split()[:20])
            page_word_set = set(page_md.split())
            overlap = len(chunk_word_set & page_word_set)
            if overlap >= min(10, len(chunk_word_set) * 0.6):
                pages.append(entry["page"])

    return sorted(set(pages))


def chunk_document(markdown: str, page_map: list[dict] | None = None) -> list[dict]:
    # Stage 1: split by markdown headers
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    sections = md_splitter.split_text(markdown)

    # Stage 2: recursive character split for large sections
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=TARGET_CHUNK_TOKENS,
        chunk_overlap=CHUNK_OVERLAP_TOKENS,
        length_function=_token_length,
        separators=["\n\n", "\n", ". ", " "],
    )

    chunks: list[dict] = []
    chunk_index = 0

    for section in sections:
        text = section.page_content
        metadata = dict(section.metadata)

        # Build header hierarchy prefix for sub-chunks (e.g. "Context: Budget > 2024 > Q3")
        header_parts = [metadata[k] for k in ("h1", "h2", "h3") if k in metadata]
        header_prefix = ("Context: " + " > ".join(header_parts) + "\n\n") if header_parts else ""

        if _token_length(text) <= MAX_CHUNK_TOKENS:
            page_numbers = _assign_page_numbers(text, page_map)
            chunks.append({
                "content": text,
                "metadata": {**metadata, "chunk_index": chunk_index, "page_numbers": page_numbers},
            })
            chunk_index += 1
        else:
            sub_chunks = recursive_splitter.split_text(text)
            for sub in sub_chunks:
                prefixed = header_prefix + sub
                page_numbers = _assign_page_numbers(sub, page_map)
                # BPE guard
                if _token_length(prefixed) > MAX_CHUNK_TOKENS:
                    tokens = _tokenizer.encode(prefixed)
                    for j in range(0, len(tokens), MAX_CHUNK_TOKENS):
                        part = _tokenizer.decode(tokens[j : j + MAX_CHUNK_TOKENS])
                        chunks.append({
                            "content": part,
                            "metadata": {**metadata, "chunk_index": chunk_index, "page_numbers": page_numbers},
                        })
                        chunk_index += 1
                else:
                    chunks.append({
                        "content": prefixed,
                        "metadata": {**metadata, "chunk_index": chunk_index, "page_numbers": page_numbers},
                    })
                    chunk_index += 1

    return chunks


async def process_document(document_id: str, session: AsyncSession) -> None:
    doc_uuid = uuid.UUID(document_id)
    result = await session.execute(select(Document).where(Document.id == doc_uuid))
    doc = result.scalar_one_or_none()
    if not doc:
        logger.error(f"Document {document_id} not found")
        return

    try:
        # Update status
        doc.status = DocumentStatus.PROCESSING.value
        session.add(doc)
        await session.commit()

        # Parse
        logger.info(f"Parsing document {doc.filename}")
        markdown, page_map = await parse_document(doc.file_path)

        # Chunk
        logger.info(f"Chunking document {doc.filename}")
        chunks = chunk_document(markdown, page_map)
        if not chunks:
            doc.status = DocumentStatus.COMPLETED.value
            session.add(doc)
            await session.commit()
            return

        # Inject document metadata into each chunk
        for c in chunks:
            c["metadata"]["document_id"] = str(doc.id)
            c["metadata"]["filename"] = doc.filename

        # Embed in batches
        logger.info(f"Embedding {len(chunks)} chunks for {doc.filename}")
        texts = [c["content"] for c in chunks]
        embeddings = await embed_texts(texts)

        # Store chunks
        chunk_rows = [
            Chunk(
                content=c["content"],
                chunk_metadata=c["metadata"],
                embedding=emb,
                document_id=doc.id,
                kb_id=doc.kb_id,
                user_id=doc.user_id,
            )
            for c, emb in zip(chunks, embeddings)
        ]
        session.add_all(chunk_rows)

        doc.status = DocumentStatus.COMPLETED.value
        session.add(doc)
        await session.commit()
        logger.info(f"Document {doc.filename} processed: {len(chunk_rows)} chunks")

    except Exception as e:
        logger.exception(f"Failed to process document {doc.filename}")
        await session.rollback()
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = str(e)[:500]
        session.add(doc)
        await session.commit()
