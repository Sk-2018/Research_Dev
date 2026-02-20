
from __future__ import annotations
from typing import Optional
from urllib.parse import urlparse, unquote
def sharepoint_url_to_unc(url: str) -> Optional[str]:
    try:
        p = urlparse(url)
        if not (p.scheme in {"http","https"} and p.netloc): return None
        path = unquote(p.path).lstrip("/").replace("/","\\"); host = p.netloc
        if not path: return None
        return f"\\\\{host}@SSL\\{path}"
    except Exception: return None
