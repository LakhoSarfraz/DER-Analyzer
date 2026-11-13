import re
import docx

EXCLUDED_STYLE_PREFIXES = (
    "heading", "title", "subtitle", "caption", "toc", "table of contents",
    "quote", "intense quote", "bibliography", "footnote", "endnote",
)
EXCLUDED_STYLE_NAMES = {
    "list paragraph", "list", "list bullet", "list number",
    "list bullet 2", "list bullet 3", "list number 2", "list number 3",
}
_MONTH = (r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
          r"January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")
DATE_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    r"|\d{4}[./-]\d{1,2}[./-]\d{1,2}"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+" + _MONTH + r"\.?(?:\s+\d{2,4})?"
    r"|" + _MONTH + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{2,4})?"
    r")", re.IGNORECASE)
LIST_MARKER_RE = re.compile(
    r"^\s*(?:"
    r"[•\-\*\u2022\u25E6\u25AA\u25AB\u25CB\u25CF\u25A0]\s"
    r"|\(?\d{1,3}[\.\)]\s"
    r"|\(?[a-zA-Z][\.\)]\s"
    r"|\(?[ivxlcdmIVXLCDM]{1,7}[\.\)]\s"
    r")")

def _is_native_list(p):
    try:
        pPr = p._p.pPr
        return pPr is not None and pPr.numPr is not None
    except Exception: return False

def _looks_like_heading_text(text):
    words = text.split()
    if len(words) > 12: return False
    if text.isupper(): return True
    if text.endswith(":") and len(words) <= 8: return True
    if not re.search(r"[.!?]", text) and len(words) <= 10: return True
    return False

def extract_paragraphs_from_docx(file_path, min_words=10):
    try: doc = docx.Document(file_path)
    except Exception as e: raise IOError(f"Failed to read Word document '{file_path}'. Error: {e}")
    stats = {"headings": 0, "lists": 0, "short": 0, "imported": 0}
    result = []
    for p in doc.paragraphs:
        style = getattr(p, "style", None)
        style_name = (getattr(style, "name", "") or "").strip().lower()
        if style_name in EXCLUDED_STYLE_NAMES or any(style_name.startswith(pref) for pref in EXCLUDED_STYLE_PREFIXES):
            stats["headings"] += 1; continue
        try:
            if p.paragraph_format.outline_level is not None:
                stats["headings"] += 1; continue
        except Exception: pass
        if _is_native_list(p):
            stats["lists"] += 1; continue
        text = p.text.strip()
        if not text: continue
        if not DATE_PREFIX_RE.match(text) and LIST_MARKER_RE.match(text):
            stats["lists"] += 1; continue
        if _looks_like_heading_text(text):
            stats["headings"] += 1; continue
        if len(text.split()) < min_words:
            stats["short"] += 1; continue
        result.append(text); stats["imported"] += 1
    return result, stats
