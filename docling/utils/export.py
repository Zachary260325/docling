import logging
from collections.abc import Iterable
from typing import Any, Dict, List, Tuple, Union

from docling_core.types.doc import BoundingBox, CoordOrigin
from docling_core.types.legacy_doc.base import BaseCell, BaseText, Ref, Table

from docling.datamodel.document import ConversionResult, Page

_log = logging.getLogger(__name__)


def generate_multimodal_pages(
    doc_result: ConversionResult,
) -> Iterable[Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]], Page]]:
    label_to_doclaynet = {
        "title": "title",
        "table-of-contents": "document_index",
        "subtitle-level-1": "section_header",
        "checkbox-selected": "checkbox_selected",
        "checkbox-unselected": "checkbox_unselected",
        "caption": "caption",
        "page-header": "page_header",
        "page-footer": "page_footer",
        "footnote": "footnote",
        "table": "table",
        "formula": "formula",
        "list-item": "list_item",
        "code": "code",
        "figure": "picture",
        "picture": "picture",
        "reference": "text",
        "paragraph": "text",
        "text": "text",
    }

    content_text = ""
    page_no = 0
    start_ix = 0
    end_ix = 0
    doc_items: List[Tuple[int, Union[BaseCell, BaseText]]] = []

    doc = doc_result.legacy_document

    def _process_page_segments(doc_items: list[Tuple[int, BaseCell]], page: Page):
        segments = []

        for ix, item in doc_items:
            item_type = item.obj_type
            label = label_to_doclaynet.get(item_type, None)

            if label is None or item.prov is None or page.size is None:
                continue

            bbox = BoundingBox.from_tuple(
                tuple(item.prov[0].bbox), origin=CoordOrigin.BOTTOMLEFT
            )
            new_bbox = bbox.to_top_left_origin(page_height=page.size.height).normalized(
                page_size=page.size
            )

            new_segment = {
                "index_in_doc": ix,
                "label": label,
                "text": item.text if item.text is not None else "",
                "bbox": new_bbox.as_tuple(),
                "data": [],
            }

            if isinstance(item, Table):
                table_html = item.export_to_html()
                new_segment["data"].append(
                    {
                        "html_seq": table_html,
                        "otsl_seq": "",
                    }
                )

            segments.append(new_segment)

        return segments

    def _process_page_cells(page: Page):
        cells: List[dict] = []
        if page.size is None:
            return cells
        for cell in page.cells:
            new_bbox = (
                cell.rect.to_bounding_box()
                .to_top_left_origin(page_height=page.size.height)
                .normalized(page_size=page.size)
            )
            is_ocr = cell.from_ocr
            ocr_confidence = cell.confidence
            cells.append(
                {
                    "text": cell.text,
                    "bbox": new_bbox.as_tuple(),
                    "ocr": is_ocr,
                    "ocr_confidence": ocr_confidence,
                }
            )
        return cells

    def _process_page():
        page_ix = page_no - 1
        page = doc_result.pages[page_ix]

        page_cells = _process_page_cells(page=page)
        page_segments = _process_page_segments(doc_items=doc_items, page=page)
        
        # For markdown files, try to use original content when processing entire document
        original_md = doc_result.get_original_markdown()
        if (original_md is not None and 
            start_ix == 0 and 
            doc.main_text is not None and 
            end_ix == len(doc.main_text) - 1):
            # Use original markdown when processing the entire document
            content_md = original_md
        else:
            # Use regular export for partial ranges or non-markdown documents
            content_md = doc.export_to_markdown(
                main_text_start=start_ix, main_text_stop=end_ix
            )
        
        # No page-tagging since we only do 1 page at the time
        content_dt = doc.export_to_document_tokens(
            main_text_start=start_ix, main_text_stop=end_ix, add_page_index=False
        )

        return content_text, content_md, content_dt, page_cells, page_segments, page

    if doc.main_text is None:
        return
    
    # Special handling for markdown documents and other non-paginated formats
    # If we have items but they don't have page information, treat as single page
    has_items_with_pages = False
    for ix, orig_item in enumerate(doc.main_text):
        item = doc._resolve_ref(orig_item) if isinstance(orig_item, Ref) else orig_item
        if item is not None and item.prov is not None and len(item.prov) > 0:
            has_items_with_pages = True
            break
    
    if not has_items_with_pages:
        # Handle as single page document (e.g., markdown)
        page_no = 1
        start_ix = 0
        end_ix = len(doc.main_text) - 1
        doc_items = [(ix, item) for ix, item in enumerate(doc.main_text)]
        
        # Create a dummy page if no pages exist
        if not doc_result.pages:
            # For markdown, we still need to yield the content
            content_text = ""
            for item in doc.main_text:
                resolved_item = doc._resolve_ref(item) if isinstance(item, Ref) else item
                if resolved_item and resolved_item.text:
                    content_text += resolved_item.text + " "
            
            # Get original markdown if available
            original_md = doc_result.get_original_markdown()
            if original_md is not None:
                content_md = original_md
            else:
                content_md = doc.export_to_markdown(
                    main_text_start=start_ix, main_text_stop=end_ix
                )
            
            content_dt = doc.export_to_document_tokens(
                main_text_start=start_ix, main_text_stop=end_ix, add_page_index=False
            )
            
            # Create empty page data for consistency
            page_cells = []
            page_segments = []
            
            # Create a dummy page object if needed
            from docling.datamodel.document import Page as PageClass
            from docling_core.types.doc import Size
            dummy_page = PageClass(
                page_no=1,
                size=Size(width=210, height=297),  # A4 size in mm
                cells=[],
            )
            
            yield content_text, content_md, content_dt, page_cells, page_segments, dummy_page
        else:
            # Use the first page if available
            yield _process_page()
        return
    
    # Normal processing for paginated documents
    for ix, orig_item in enumerate(doc.main_text):
        item = doc._resolve_ref(orig_item) if isinstance(orig_item, Ref) else orig_item
        if item is None or item.prov is None or len(item.prov) == 0:
            _log.debug(f"Skipping item {orig_item}")
            continue

        item_page = item.prov[0].page

        # Page is complete
        if page_no > 0 and item_page > page_no:
            yield _process_page()

            start_ix = ix
            doc_items = []
            content_text = ""

        page_no = item_page
        end_ix = ix
        doc_items.append((ix, item))
        if item.text is not None and item.text != "":
            content_text += item.text + " "

    if len(doc_items) > 0:
        yield _process_page()
