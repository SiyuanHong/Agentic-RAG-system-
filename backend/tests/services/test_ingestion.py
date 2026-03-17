from app.services.ingestion import (
    _assign_page_numbers,
    _token_length,
    chunk_document,
)


def test_token_length():
    count = _token_length("hello world")
    assert isinstance(count, int)
    assert count >= 2


def test_chunk_document_simple():
    markdown = "This is a short paragraph about revenue."
    chunks = chunk_document(markdown)
    assert len(chunks) >= 1
    assert chunks[0]["content"].strip() != ""
    assert "chunk_index" in chunks[0]["metadata"]


def test_chunk_document_with_headers():
    markdown = "# Section A\n\nContent of section A.\n\n## Subsection B\n\nContent of subsection B."
    chunks = chunk_document(markdown)
    assert len(chunks) >= 2


def test_chunk_document_large_section():
    # Create a section that exceeds MAX_CHUNK_TOKENS (512)
    long_text = "This is a word. " * 300  # ~600 tokens
    markdown = f"# Big Section\n\n{long_text}"
    chunks = chunk_document(markdown)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert _token_length(chunk["content"]) <= 600  # reasonable upper bound after prefixing


def test_chunk_document_bpe_guard():
    # Very long section without headers to trigger BPE guard
    long_text = "word " * 1500
    chunks = chunk_document(long_text)
    assert len(chunks) >= 1


def test_assign_page_numbers_match():
    chunk_text = "Revenue was $1M in fiscal year 2024"
    page_map = [
        {"page": 1, "md": "Introduction to the company"},
        {"page": 2, "md": "Revenue was $1M in fiscal year 2024 according to reports"},
    ]
    pages = _assign_page_numbers(chunk_text, page_map)
    assert 2 in pages


def test_assign_page_numbers_no_match():
    chunk_text = "Completely unrelated content xyz123"
    page_map = [
        {"page": 1, "md": "This page is about something else entirely"},
    ]
    pages = _assign_page_numbers(chunk_text, page_map)
    assert pages == []


def test_assign_page_numbers_no_page_map():
    pages = _assign_page_numbers("Some text", None)
    assert pages == []


def test_assign_page_numbers_empty_chunk():
    pages = _assign_page_numbers("", [{"page": 1, "md": "content"}])
    assert pages == []
