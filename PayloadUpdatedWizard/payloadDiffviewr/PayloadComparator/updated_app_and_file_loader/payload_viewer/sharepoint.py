import os
from typing import Optional
from urllib.parse import urlparse, unquote

def sharepoint_url_to_unc(url: str) -> Optional[str]:
    """
    Converts a SharePoint/OneDrive URL to a Windows UNC/WebDAV path.

    Example:
    https://<tenant>.sharepoint.com/sites/MySite/Shared%20Documents
    becomes:
    \\\\<tenant>.sharepoint.com@SSL\\sites\\MySite\\Shared Documents

    Args:
        url: The SharePoint URL.

    Returns:
        A UNC path string if conversion is successful and the path is
        a valid directory, otherwise None.
    """
    if not (url.startswith("http://") or url.startswith("https://")):
        return None

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None

        # Build the UNC path
        # 1. Hostname, replacing ':' with '.' if port is present
        host = parsed.netloc.replace(":", ".")
        
        # 2. Add @SSL if it's an https URL
        if parsed.scheme == "https":
            # Check if webdav client is configured (common for business env)
            # This is the most common format
            host = f"{host}@SSL"

        # 3. Path, unquoted and with Windows slashes
        path = unquote(parsed.path).replace('/', '\\')

        # 4. Combine
        # Note: We need 2 backslashes at the start.
        unc_path = f"\\\\{host}{path}"
        
        # 5. Validate
        # This is the crucial check. If the path isn't mapped or
        # accessible, os.path.isdir will fail.
        if os.path.isdir(unc_path):
            return unc_path
        else:
            # Try common alternative (e.g., removing 'www' if present)
            if host.startswith("www."):
                alt_host = host[4:]
                alt_unc_path = f"\\\\{alt_host}{path}"
                if os.path.isdir(alt_unc_path):
                    return alt_unc_path
            
            print(f"SharePoint URL {url} resolved to {unc_path} but path is not reachable.")
            return None

    except Exception as e:
        print(f"Error converting SharePoint URL '{url}': {e}")
        return None

# --- Example Usage (manual test) ---
if __name__ == "__main__":
    test_url = "https://your-tenant.sharepoint.com/sites/YourSite/Shared%20Documents"
    unc = sharepoint_url_to_unc(test_url)
    if unc:
        print(f"Success: {unc}")
        print(f"Contents: {os.listdir(unc)[:5]}") # List first 5 items
    else:
        print(f"Failed to resolve or access: {test_url}")
        print("Note: This test will only pass if the URL is valid and")
        print("you have network access to it as a WebDAV/UNC path.")