# payload_viewer/sharepoint.py
from __future__ import annotations

import os
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional


def sharepoint_url_to_unc(url: str) -> Optional[str]:
    """
    Convert SharePoint / OneDrive folder URLs into a Windows UNC/WebDAV path.

    Supported forms:
      - https://<tenant>-my.sharepoint.com/personal/.../Documents/...
      - https://<tenant>.sharepoint.com/sites/<SiteName>/Shared%20Documents/...
      - https://<tenant>-my.sharepoint.com/my?id=/personal/.../Documents/...

    Returns:
      A UNC string like: \\\\<host>@SSL\\<path with backslashes>
      or None if the URL is not recognized.
    """
    try:
        if not url:
            return None

        u = urlparse(url.strip())
        if u.scheme not in ("http", "https"):
            return None
        if "sharepoint.com" not in u.netloc:
            return None

        # Start with the path portion
        path = u.path or ""

        # Handle "my?id=<encoded absolute path>" links
        # Example: https://tenant-my.sharepoint.com/my?id=/personal/user_domain_tld/Documents/Folder
        if path.rstrip("/").endswith("/my"):
            q = parse_qs(u.query or "")
            raw_id = (q.get("id") or [None])[0]
            if raw_id:
                path = raw_id  # already an absolute server path like /personal/...

        # Clean up odd copy-link pattern '/:f:/r/' -> '/'
        path = path.replace("/:f:/r/", "/").strip("/")
        # Decode %20 etc.
        path = unquote(path)

        # Sanity check: require library roots we know
        # personal/... or sites/... is typical for SharePoint/OneDrive
        if not (path.startswith("personal/") or path.startswith("sites/")):
            return None

        host = u.netloc
        unc = r"\\{host}@SSL\{path}".format(host=host, path=path.replace("/", "\\"))
        return unc
    except Exception:
        return None


def path_is_accessible(p: str) -> bool:
    """
    Quick check if a UNC/WebDAV path exists and is accessible.
    """
    try:
        return bool(p) and os.path.isdir(p)
    except Exception:
        return False


__all__ = ["sharepoint_url_to_unc", "path_is_accessible"]