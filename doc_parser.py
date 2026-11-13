import re
import os
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

EXCLUDED_STYLE_PREFIXES = (
    "heading", "title", "subtitle", "caption", "toc", "table of contents",
    "quote", "intense quote", "bibliography", "footnote", "endnote",
)
EXCLUDED_STYLE_NAMES = {
    "list paragraph", "list", "list bullet", "list number",
    "list bullet 2", "list bullet 3", "list number 2", "list number 3",
}

# Validation for "On [date]" and "It is learnt"
VALIDATION_RE = re.compile(
    r"^(?:"
    r"On\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+[a-zA-Z]+|\s*[/\-]\s*\d{1,2})"  # On 16 Aug, On 16/8, On 16-8
    r"|It\s+is\s+learnt"                                                # It is learnt
    r")", re.IGNORECASE
)

def _iter_block_items(parent):
    """Yields paragraphs and tables in the exact order they appear in the document."""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def _clean_text(text):
    text = text.replace('\t', ' ')
    # Strip manual numbering like "1. " or "1) "
    text = re.sub(r'^\s*\d+[\.\)]\s*', '', text)
    return text.strip()

def _process_asterisks(text):
    # If text starts with *...* and is immediately followed by On/It is learnt
    match = re.match(r'^\s*\*([^\*]+)\*\s*(.*)', text)
    if match:
        inside = match.group(1)
        outside = match.group(2)
        if len(inside.split()) <= 10 and VALIDATION_RE.match(outside):
            return outside
    return text

def extract_paragraphs_from_docx(file_path, min_words=10):
    # Handle legacy .doc files by converting to .docx using MS Word (if installed)
    if file_path.lower().endswith('.doc'):
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(file_path)
            new_path = file_path + "x"
            doc.SaveAs2(new_path, FileFormat=16) # 16 = wdFormatXMLDocument
            doc.Close()
            word.Quit()
            file_path = new_path
        except ImportError:
            raise IOError("Reading .doc files requires 'pywin32' and Microsoft Word installed on this PC.\nPlease save the file as .docx.")
        except Exception as e:
            raise IOError(f"Failed to convert .doc file. Is Microsoft Word installed?\nError: {e}")

    try:
        doc = docx.Document(file_path)
    except Exception as e:
        raise IOError(f"Failed to read Word document '{file_path}'. Error: {e}")

    stats = {"headings": 0, "lists": 0, "short": 0, "imported": 0}
    result = []

    for block in _iter_block_items(doc):
        if isinstance(block, Table):
            # Extract full text for model training
            cells_text = []
            for row in block.rows:
                for cell in row.cells:
                    cells_text.append(cell.text.strip())
            full_text = " ".join(cells_text)
            
            # Extract first row for UI preview
            preview_text = ""
            if len(block.rows) > 0:
                preview_text = " | ".join(c.text.strip() for c in block.rows[0].cells)
                
            if len(full_text.split()) >= min_words:
                result.append({
                    "type": "table",
                    "text": full_text,
                    "display_text": preview_text,
                    "is_valid": True, # Tables bypass the On[date] validation
                    "obj": block
                })
                stats["imported"] += 1
            else:
                stats["short"] += 1
                
        elif isinstance(block, Paragraph):
            style = getattr(block, "style", None)
            style_name = (getattr(style, "name", "") or "").strip().lower()
            
            if style_name in EXCLUDED_STYLE_NAMES or any(style_name.startswith(pref) for pref in EXCLUDED_STYLE_PREFIXES):
                stats["headings"] += 1; continue
                
            try:
                if block.paragraph_format.outline_level is not None:
                    stats["headings"] += 1; continue
            except Exception: pass
            
            raw_text = block.text.strip()
            if not raw_text: continue
            
            # 1. Process Asterisks
            text = _process_asterisks(raw_text)
            
            # 2. Clean Tabs & Numbering
            text = _clean_text(text)
            
            if len(text.split()) < min_words:
                stats["short"] += 1; continue
                
            # 3. Validate (On [date] or It is learnt)
            is_valid = bool(VALIDATION_RE.match(text))
            
            result.append({
                "type": "paragraph",
                "text": text,
                "display_text": text,
                "is_valid": is_valid,
                "obj": block
            })
            stats["imported"] += 1

    return result, stats
