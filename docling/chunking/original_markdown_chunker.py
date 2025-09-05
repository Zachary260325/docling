"""Enhanced chunking support for preserving original markdown content."""

from typing import Optional, Union, Any, List, Iterator
from docling_core.transforms.chunker.hierarchical_chunker import ChunkingSerializerProvider, ChunkingDocSerializer, BaseChunker, DocChunk
from docling_core.types.doc import DoclingDocument, NodeItem
from docling_core.transforms.serializer.base import SerializationResult


class OriginalMarkdownChunkingSerializerProvider(ChunkingSerializerProvider):
    """
    Custom serializer provider that uses original markdown content when available.
    
    This provider checks if the document has original markdown content and uses it
    when chunking the entire document, while falling back to regular serialization
    for individual document items.
    """
    
    def __init__(self):
        super().__init__()
    
    def get_serializer(self, doc: DoclingDocument):
        """Get a custom serializer that can use original markdown."""
        return OriginalMarkdownChunkingDocSerializer(doc=doc)


class OriginalMarkdownChunkingDocSerializer(ChunkingDocSerializer):
    """
    Enhanced ChunkingDocSerializer that uses original markdown when appropriate.
    
    This serializer checks if the document has original markdown content and uses it
    for the complete document serialization, while using regular item-by-item 
    serialization for partial content.
    """
    
    def __init__(self, doc: DoclingDocument, **kwargs):
        super().__init__(doc=doc, **kwargs)
        # Store original content as a private attribute
        self._original_content = None
        
        # Try to get original markdown content if available
        try:
            self._original_content = doc.get_original_markdown()
        except AttributeError:
            # Method might not be available, fall back to regular serialization
            self._original_content = None
    
    def serialize_doc(self, *, parts: List[SerializationResult], **kwargs) -> SerializationResult:
        """
        Serialize a document out of its parts.
        
        This is called when the chunker wants to serialize the entire document or
        a large portion of it. We check if we have original markdown and use it.
        """
        # If we have original markdown content and we're serializing a substantial 
        # portion (heuristic: more than 1 part), use original content
        if self._original_content is not None and len(parts) > 1:
            return SerializationResult(text=self._original_content)
        
        # Fall back to regular document serialization
        return super().serialize_doc(parts=parts, **kwargs)
    
    def serialize(self, *, item: Optional[NodeItem] = None, list_level: int = 0, 
                  is_inline_scope: bool = False, visited: Optional[set] = None, **kwargs) -> SerializationResult:
        """
        Serialize a given node.
        
        For individual item serialization, we always use the regular method since
        we can't easily map back to original markdown portions.
        """
        return super().serialize(item=item, list_level=list_level, 
                               is_inline_scope=is_inline_scope, visited=visited, **kwargs)


class SingleChunkMarkdownChunker(BaseChunker):
    """
    A simple chunker that returns the entire document as a single chunk
    with original markdown content preserved when available.
    """
    
    def __init__(self):
        super().__init__()
    
    def chunk(self, doc: DoclingDocument) -> Iterator[DocChunk]:
        """
        Chunk the document into a single chunk with original markdown content.
        
        Args:
            doc: The document to chunk
            
        Yields:
            A single DocChunk containing the original markdown content if available,
            otherwise the regular markdown export.
        """
        from docling_core.transforms.chunker.hierarchical_chunker import DocMeta
        
        # Try to get original markdown content
        original_content = None
        try:
            original_content = doc.get_original_markdown()
        except AttributeError:
            pass
        
        # If no original content, use regular export
        if original_content is None:
            original_content = doc.export_to_markdown()
        
        # Create a simple meta object with minimal requirements
        # Get all document items for the meta
        doc_items = []
        for item_tuple in doc.iterate_items():
            if isinstance(item_tuple, tuple):
                item = item_tuple[0]  # Extract the actual item from the tuple
            else:
                item = item_tuple
            doc_items.append(item)
        
        meta = DocMeta(
            doc_items=doc_items if doc_items else [doc.body],  # Ensure at least one item
            origin=doc.origin
        )
        
        yield DocChunk(
            text=original_content,
            meta=meta
        )
