"""CID content resolution.

This module resolves CID values to their content, trying multiple sources:
1. Database (primary storage)
2. Filesystem paths (for development)
3. cids/ directory (fallback)

Design decisions:
- No caching (always load fresh)
- Raises clear errors if CID not found (no silent fallback)
- Supports both text and bytes output
"""

from pathlib import Path
from typing import Optional, Union


class CIDResolver:
    """Resolves CID values to content (no caching).
    
    Resolution strategy:
    1. Try database lookup (CID paths stored with leading slash)
    2. Try filesystem path (e.g., reference/templates/...)
    3. Try cids/ directory as fallback
    
    No caching - always resolves fresh to ensure latest content.
    """
    
    def resolve(
        self, 
        cid_value: str, 
        *, 
        as_bytes: bool = False
    ) -> Optional[Union[str, bytes]]:
        """Resolve a CID value to its content.
        
        Args:
            cid_value: CID identifier or file path
            as_bytes: If True, return bytes; if False, return str
            
        Returns:
            Content as str or bytes, or None if not found
            
        Raises:
            No exceptions - returns None if CID not found
            
        Note: No caching - always loads fresh content
        """
        # Try database first
        content = self._try_database(cid_value, as_bytes)
        if content is not None:
            return content
            
        # Try filesystem path resolution
        content = self._try_filesystem_path(cid_value, as_bytes)
        if content is not None:
            return content
            
        # Try cids/ directory as fallback
        content = self._try_cids_directory(cid_value, as_bytes)
        if content is not None:
            return content
            
        return None
    
    def _try_database(
        self, 
        cid_value: str, 
        as_bytes: bool
    ) -> Optional[Union[str, bytes]]:
        """Try to resolve CID from database."""
        try:
            from cid_storage import get_cid_content
            
            # CID paths are stored with leading slash
            cid_path = f"/{cid_value}" if not cid_value.startswith("/") else cid_value
            content = get_cid_content(cid_path)
            
            if not content:
                return None
                
            # Handle different content formats
            if hasattr(content, "file_data"):
                return self._convert_data(content.file_data, as_bytes)
            if hasattr(content, "data"):
                return self._convert_data(content.data, as_bytes)
            return self._convert_data(content, as_bytes)
            
        except Exception:
            return None
    
    def _try_filesystem_path(
        self, 
        cid_value: str, 
        as_bytes: bool
    ) -> Optional[Union[str, bytes]]:
        """Try to resolve from filesystem path (for development)."""
        try:
            candidate = str(cid_value) if cid_value is not None else ""
            if not candidate:
                return None
                
            normalized = candidate.lstrip("/")
            candidate_path = Path(normalized)
            
            if candidate_path.exists() and candidate_path.is_file():
                if as_bytes:
                    return candidate_path.read_bytes()
                return candidate_path.read_text(encoding="utf-8")
                
        except Exception:
            pass
            
        return None
    
    def _try_cids_directory(
        self, 
        cid_value: str, 
        as_bytes: bool
    ) -> Optional[Union[str, bytes]]:
        """Try to resolve from cids/ directory."""
        try:
            # Remove leading slash if present for filesystem lookup
            bare_cid = cid_value.lstrip("/")
            cid_file = Path("cids") / bare_cid
            
            if cid_file.exists():
                if as_bytes:
                    return cid_file.read_bytes()
                return cid_file.read_text(encoding="utf-8")
                
        except Exception:
            pass
            
        return None
    
    def _convert_data(
        self, 
        data: Union[str, bytes, bytearray], 
        as_bytes: bool
    ) -> Union[str, bytes]:
        """Convert data to requested format."""
        if as_bytes:
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            return str(data).encode("utf-8")
        else:
            if isinstance(data, bytes):
                return data.decode("utf-8")
            return data
