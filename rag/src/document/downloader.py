import requests
import os
import uuid
import urllib3
from urllib.parse import urlparse, unquote
from typing import Optional, Tuple

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_pdf(url: str, output_dir: str) -> Optional[Tuple[str, str]]:
    """
    Download PDF from URL
    Returns: (file_path, original_filename) or None if failed
    """
    try:
        print(f"Downloading PDF from {url}")
        response = requests.get(url, timeout=60, stream=True, verify=False)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
            print(f"Invalid content type: {content_type}")
            return None
        
        # Extract filename from URL or generate one
        parsed_url = urlparse(url)
        filename = unquote(os.path.basename(parsed_url.path))
        
        if not filename or not filename.endswith('.pdf'):
            filename = f"download_{uuid.uuid4().hex[:8]}.pdf"
        
        # Save to temp directory
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
        return file_path, filename
    
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return None
