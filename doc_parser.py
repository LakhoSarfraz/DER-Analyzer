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

VALIDATION_RE = re.compile(
    r"^(?:"
    r"On\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+[a-zA-Z]+|\s*[/\-]\s*\d{1,2})"
    r"|It\s+is\s+learnt"
    r")", re.IGNORECASE
)

def _iter_block_items(parent):
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def _get_clean_text(paragraph):
    text = paragraph.text
    if not text.strip(): return ""

    # Find the target start (On [date] or It is learnt)
    match = re.search(r'(On\s+\d{1,2}|It\s+is\s+learnt)', text, re.IGNORECASE)
    
    if match:
        prefix = text[:match.start()]
        # Check if prefix is short enough to be junk (<= 10 words)
        if len(prefix.split()) <= 10:
            # Check underline
            is_underlined = True
            if prefix.strip():
                char_idx = 0
                for run in paragraph.runs:
                    if char_idx >= match.start(): break
                    if run.text.strip():
                        if not run.underline:
                            is_underlined = False
                            break
                    char_idx += len(run.text)

            # Check asterisks
            is_asterisk = bool(re.match(r'^\s*\*([^\*]+)\*\s*$', prefix))
            
            # Check if it has no letters (pure numbering/punctuation)
            no_letters = not re.search(r'[a-zA-Z]', prefix)

            # If it's underlined, asterisked, or pure numbering, strip it
            if is_underlined or is_asterisk or no_letters:
                text = text[match.start():]

    # Aggressively remove any leading non-letters (dots, numbers, spaces)
    text = re.sub(r'^[^a-zA-Z]+', '', text)

    # Global Whitespace Normalization (replace tabs, newlines, double spaces with single space)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def extract_paragraphs_from_docx(file_path, min_words=10):
    # Handle legacy .doc files by converting to .docx using MS Word
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
            
            # Strict single-space normalization for table
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            # Extract first TWO rows for UI preview
            preview_lines = []
            for row_idx, row in enumerate(block.rows):
                if row_idx >= 2: break
                row_text = " | ".join(c.text.strip() for c in row.cells)
                preview_lines.append(re.sub(r'\s+', ' ', row_text).strip())
            preview_text = " // ".join(preview_lines)
                
            if len(full_text.split()) >= min_words:
                result.append({
                    "type": "table",
                    "text": full_text,
                    "display_text": preview_text,
                    "is_valid": True, 
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
            
            # Use the new combined cleaning logic
            text = _get_clean_text(block)
            if not text: continue
            
            if len(text.split()) < min_words:
                stats["short"] += 1; continue
                
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
