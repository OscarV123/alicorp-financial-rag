import re
from typing import List, Dict

_NON_PRINTING = re.compile(r'[\ufeff\u200b\u200c\u200d]+')
_SPACE_RE = re.compile(r'[ \t]+')

def normalize_lines(text: str) -> List[str]:
    if not text:
        return []

    normalized = []
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = _NON_PRINTING.sub('', text)
    text = text.replace('\xa0', ' ')
    text = text.replace('\f', '\n')

    for line in text.split('\n'):
        cleaned = _SPACE_RE.sub(' ', line).strip()
        normalized.append(cleaned)

    return normalized

def is_numericish(value: str) -> bool:
    if not value:
        return False

    v = value.strip()
    if v in {'-', '—', '–'}:
        return True

    v = v.strip('()')

    v = re.sub(r'^[sS]/\s*', '', v)

    v = v.replace('%', '')
    v = v.replace('p.p.', '').replace('pp', '')
    v = v.replace('x', '')

    v = v.replace(' ', '').replace(',', '')

    if not v:
        return False

    if v[0] in '+-':
        v = v[1:]

    parts = v.split('.')
    if len(parts) > 2:
        return False
    return all(part.isdigit() for part in parts if part)

def remove_table_lines(page_record: dict) -> str:
    text = page_record.get("page_text", "") or ""
    if not text:
        return ""

    lines = normalize_lines(text)
    ranges = sorted(page_record.get("table_ranges", []))
    merged = []
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    mask = [False] * len(lines)
    for start, end in merged:
        for idx in range(start, min(end, len(lines))):
            mask[idx] = True

    kept = [line for idx, line in enumerate(lines) if idx < len(mask) and not mask[idx]]
    return "\n".join(kept)
