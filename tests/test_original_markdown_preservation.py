"""Test original markdown preservation functionality."""

from pathlib import Path

import pytest

from docling.backend.md_backend import MarkdownDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument


class TestOriginalMarkdownPreservation:
    """Test suite for original markdown preservation in chunks."""

    @pytest.fixture
    def sample_markdown_path(self):
        """Provide path to sample markdown file for testing."""
        return Path("tests/data/md/Ideal holiday itinerary.md")

    @pytest.fixture
    def backend_with_content(self, sample_markdown_path):
        """Create backend with markdown content loaded."""
        in_doc = InputDocument(
            path_or_stream=sample_markdown_path,
            format=InputFormat.MD,
            backend=MarkdownDocumentBackend,
            filename=sample_markdown_path.name
        )
        backend = MarkdownDocumentBackend(
            in_doc=in_doc,
            path_or_stream=sample_markdown_path
        )
        return backend

    def test_original_markdown_stored(self, backend_with_content):
        """Test that original markdown is stored correctly."""
        # Get original markdown
        original = backend_with_content.get_original_markdown()
        
        # Should not be empty
        assert original is not None
        assert len(original) > 0
        
        # Should be a string
        assert isinstance(original, str)

    def test_original_markdown_accessible_from_document(self, backend_with_content):
        """Test that original markdown can be accessed from the converted document."""
        # Convert the document
        doc = backend_with_content.convert()
        
        # Should be able to get original markdown from document
        assert hasattr(doc, 'get_original_markdown'), "Document should have get_original_markdown method"
        
        original_from_doc = doc.get_original_markdown()
        original_from_backend = backend_with_content.get_original_markdown()
        
        # Should be the same content
        assert original_from_doc is not None
        assert original_from_doc == original_from_backend
        
        # Should be a string
        assert isinstance(original_from_doc, str)
        assert len(original_from_doc) > 0

    def test_document_without_original_markdown(self):
        """Test accessing original markdown from a document that doesn't have it."""
        from docling_core.types.doc import DoclingDocument, DocumentOrigin
        
        # Create a document without original markdown
        doc = DoclingDocument(
            name="test",
            origin=DocumentOrigin(
                filename="test.md",
                mimetype="text/markdown", 
                binary_hash=12345
            )
        )
        
        # Should not have the get_original_markdown method
        assert not hasattr(doc, 'get_original_markdown'), "Document should not have get_original_markdown method"
        
        # Direct attribute access should return None
        assert getattr(doc, '_original_markdown', None) is None

    def test_original_markdown_preservation_in_chunks(self, backend_with_content):
        """Test that chunks preserve original markdown in metadata."""
        # Create chunks with original preservation
        chunks = backend_with_content.chunk_with_original_preservation()
        
        # Should have chunks
        assert len(chunks) > 0
        
        # Get original markdown for comparison
        original_markdown = backend_with_content.get_original_markdown()
        
        # Each chunk should have original markdown preserved
        for i, chunk in enumerate(chunks):
            # Check that chunk has metadata
            assert hasattr(chunk, 'meta'), f"Chunk {i} missing metadata"
            
            # Check that metadata has original_markdown field
            assert hasattr(chunk.meta, 'original_markdown'), f"Chunk {i} missing original_markdown in metadata"
            
            # Check that original markdown is preserved exactly
            assert chunk.meta.original_markdown == original_markdown, f"Chunk {i} original markdown differs"
            
            # Check that chunk also has processed text
            assert hasattr(chunk, 'text'), f"Chunk {i} missing processed text"
            assert chunk.text is not None, f"Chunk {i} processed text is None"

    def test_exact_pattern_matching(self, backend_with_content):
        """Test that exact pattern matching works on preserved text."""
        chunks = backend_with_content.chunk_with_original_preservation()
        
        # Test specific patterns that should be preserved exactly
        test_patterns = [
            "**天数**：7天",
            "**主题**：冷门自然景观",
            "**预算估计**：",
            "## 日程概述"
        ]
        
        for pattern in test_patterns:
            # Check that pattern exists in original markdown
            original = backend_with_content.get_original_markdown()
            assert pattern in original, f"Pattern '{pattern}' not in original markdown"
            
            # Check that pattern is preserved in all chunks
            for chunk in chunks:
                assert pattern in chunk.meta.original_markdown, \
                    f"Pattern '{pattern}' not preserved in chunk"

    def test_unicode_character_preservation(self, backend_with_content):
        """Test that Unicode characters are preserved correctly."""
        chunks = backend_with_content.chunk_with_original_preservation()
        original = backend_with_content.get_original_markdown()
        
        # Test specific Unicode characters that appear in the content
        unicode_chars = ['：', '，', '。', '、']
        
        for char in unicode_chars:
            original_count = original.count(char)
            if original_count > 0:  # Only test if character exists in original
                for chunk in chunks:
                    chunk_count = chunk.meta.original_markdown.count(char)
                    assert chunk_count == original_count, \
                        f"Unicode character '{char}' count differs: original={original_count}, chunk={chunk_count}"

    def test_original_preserving_chunker_direct(self, backend_with_content):
        """Test using OriginalPreservingChunker directly."""
        # Import the chunker class
        from docling_core.transforms.chunker.hierarchical_chunker import OriginalPreservingChunker
        
        # Convert document and get original text
        doc = backend_with_content.convert()
        original_text = backend_with_content.get_original_markdown()
        
        # Create chunker and process
        chunker = OriginalPreservingChunker(original_markdown_text=original_text)
        chunks = list(chunker.chunk(doc))
        
        # Should have chunks
        assert len(chunks) > 0
        
        # Each chunk should preserve original
        for chunk in chunks:
            assert hasattr(chunk.meta, 'original_markdown')
            assert chunk.meta.original_markdown == original_text

    def test_backend_convenience_vs_direct_chunker(self, backend_with_content):
        """Test that backend convenience method and direct chunker produce same results."""
        # Method 1: Backend convenience method
        chunks1 = backend_with_content.chunk_with_original_preservation()
        
        # Method 2: Direct chunker
        from docling_core.transforms.chunker.hierarchical_chunker import OriginalPreservingChunker
        
        doc = backend_with_content.convert()
        original_text = backend_with_content.get_original_markdown()
        chunker = OriginalPreservingChunker(original_markdown_text=original_text)
        chunks2 = list(chunker.chunk(doc))
        
        # Should produce same number of chunks
        assert len(chunks1) == len(chunks2)
        
        # Compare chunk content
        for chunk1, chunk2 in zip(chunks1, chunks2):
            # Same processed text
            assert chunk1.text == chunk2.text
            
            # Same original markdown
            assert chunk1.meta.original_markdown == chunk2.meta.original_markdown
            
            # Same headings if present
            if hasattr(chunk1.meta, 'headings') and hasattr(chunk2.meta, 'headings'):
                assert chunk1.meta.headings == chunk2.meta.headings

    def test_content_preservation_vs_processing(self, backend_with_content):
        """Test that original differs from processed text (showing preservation value)."""
        chunks = backend_with_content.chunk_with_original_preservation()
        
        # Should have at least one chunk
        assert len(chunks) > 0
        
        first_chunk = chunks[0]
        original = first_chunk.meta.original_markdown
        processed = first_chunk.text
        
        # Original should be longer (contains full document)
        assert len(original) >= len(processed)
        
        # They should be different (processed is chunk-specific)
        assert original != processed

    def test_multiple_markdown_files(self):
        """Test preservation works with different markdown files."""
        md_dir = Path("tests/data/md")
        
        if md_dir.exists():
            md_files = list(md_dir.glob("*.md"))
            
            for md_file in md_files[:3]:  # Test first 3 files to avoid long test times
                in_doc = InputDocument(
                    path_or_stream=md_file,
                    format=InputFormat.MD,
                    backend=MarkdownDocumentBackend,
                    filename=md_file.name
                )
                backend = MarkdownDocumentBackend(in_doc=in_doc, path_or_stream=md_file)
                
                # Should be able to get original markdown
                original = backend.get_original_markdown()
                assert original is not None
                assert len(original) > 0
                
                # Should be able to create chunks with preservation
                chunks = backend.chunk_with_original_preservation()
                assert len(chunks) > 0
                
                # All chunks should preserve the same original
                for chunk in chunks:
                    assert chunk.meta.original_markdown == original
