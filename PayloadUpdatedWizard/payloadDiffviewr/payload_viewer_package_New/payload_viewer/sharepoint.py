from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote

def sharepoint_url_to_unc(url: str) -> Optional[str]:
    """Convert SharePoint/OneDrive folder URLs to a UNC/WebDAV path (Windows)."""
    try:
        u = urlparse(url.strip())
        if u.scheme not in ("http", "https") or "sharepoint.com" not in u.netloc:
            return None

        path = u.path
        if path.rstrip("/").endswith("/my"):
            q = parse_qs(u.query or "")
            raw_id = (q.get("id") or [None])[0]
            if raw_id:
                path = raw_id

        path = str(path).replace('/:f:/r/', '/').strip('/')
        path = unquote(path)

        if not (path.startswith("personal/") or path.startswith("sites/")):
            return None

        host = u.netloc
        return r"\\{host}@SSL\{path}".format(host=host, path=path.replace('/', '\\'))
    except Exception:
        return None

def path_is_accessible(p: str) -> bool:
    try:
        return os.path.isdir(p)
    except Exception:
        return False
