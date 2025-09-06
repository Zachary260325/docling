"""Simple test for original markdown preservation without pytest fixtures."""

from pathlib import Path

from docling.backend.md_backend import MarkdownDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument


def test_original_markdown_basic_preservation():
    """Test basic original markdown preservation functionality."""
    # Use the sample markdown file
    test_file = Path("tests/data/md/Ideal holiday itinerary.md")
    
    # Create backend
    in_doc = InputDocument(
        path_or_stream=test_file,
        format=InputFormat.MD,
        backend=MarkdownDocumentBackend,
        filename=test_file.name
    )
    backend = MarkdownDocumentBackend(in_doc=in_doc, path_or_stream=test_file)
    
    # Test original markdown storage
    original = backend.get_original_markdown()
    assert original is not None
    assert len(original) > 0
    assert isinstance(original, str)
    
    # Test chunking with preservation
    chunks = backend.chunk_with_original_preservation()
    assert len(chunks) > 0
    
    # Test that all chunks preserve original markdown
    for chunk in chunks:
        assert hasattr(chunk.meta, 'original_markdown')
        assert chunk.meta.original_markdown == original
        assert hasattr(chunk, 'text')
        assert chunk.text is not None


def test_exact_pattern_matching_basic():
    """Test that exact patterns are preserved for matching."""
    test_file = Path("tests/data/md/Ideal holiday itinerary.md")
    
    in_doc = InputDocument(
        path_or_stream=test_file,
        format=InputFormat.MD,
        backend=MarkdownDocumentBackend,
        filename=test_file.name
    )
    backend = MarkdownDocumentBackend(in_doc=in_doc, path_or_stream=test_file)
    
    chunks = backend.chunk_with_original_preservation()
    
    # Test that exact patterns are preserved
    test_pattern = "**天数**：7天"
    
    # Should be in original
    original = backend.get_original_markdown()
    assert test_pattern in original
    
    # Should be in all chunks
    for chunk in chunks:
        assert test_pattern in chunk.meta.original_markdown


def test_original_preserving_chunker_import():
    """Test that OriginalPreservingChunker can be imported and used."""
    # Test import
    from docling_core.transforms.chunker.hierarchical_chunker import OriginalPreservingChunker
    
    test_file = Path("tests/data/md/Ideal holiday itinerary.md")
    
    in_doc = InputDocument(
        path_or_stream=test_file,
        format=InputFormat.MD,
        backend=MarkdownDocumentBackend,
        filename=test_file.name
    )
    backend = MarkdownDocumentBackend(in_doc=in_doc, path_or_stream=test_file)
    
    # Get document and original text
    doc = backend.convert()
    original_text = backend.get_original_markdown()
    
    # Use chunker directly
    chunker = OriginalPreservingChunker(original_markdown_text=original_text)
    chunks = list(chunker.chunk(doc))
    
    # Should work
    assert len(chunks) > 0
    
    # Should preserve original in all chunks
    for chunk in chunks:
        assert hasattr(chunk.meta, 'original_markdown')
        assert chunk.meta.original_markdown == original_text


def test_backend_vs_direct_chunker_consistency():
    """Test that backend method and direct chunker produce consistent results."""
    test_file = Path("tests/data/md/Ideal holiday itinerary.md")
    
    in_doc = InputDocument(
        path_or_stream=test_file,
        format=InputFormat.MD,
        backend=MarkdownDocumentBackend,
        filename=test_file.name
    )
    backend = MarkdownDocumentBackend(in_doc=in_doc, path_or_stream=test_file)
    
    # Method 1: Backend convenience
    chunks1 = backend.chunk_with_original_preservation()
    
    # Method 2: Direct chunker
    from docling_core.transforms.chunker.hierarchical_chunker import OriginalPreservingChunker
    
    doc = backend.convert()
    original_text = backend.get_original_markdown()
    chunker = OriginalPreservingChunker(original_markdown_text=original_text)
    chunks2 = list(chunker.chunk(doc))
    
    # Should produce same results
    assert len(chunks1) == len(chunks2)
    
    for chunk1, chunk2 in zip(chunks1, chunks2):
        assert chunk1.text == chunk2.text
        assert chunk1.meta.original_markdown == chunk2.meta.original_markdown
