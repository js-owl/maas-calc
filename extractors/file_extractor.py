"""
Base file parameter extractor
"""

import base64
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

from models.base_models import Dimensions

logger = logging.getLogger(__name__)


class FileParameterExtractor:
    """Base class for file parameter extraction"""
    
    def __init__(self):
        self.supported_types = []
    
    async def extract_parameters(self, file_data: str, file_name: str, file_type: str) -> Dict[str, Any]:
        """
        Extract parameters from file data
        
        Args:
            file_data: Base64 encoded file data
            file_name: Original filename
            file_type: File type (stl, stp)
            
        Returns:
            Dictionary of extracted parameters
        """
        raise NotImplementedError("Subclasses must implement extract_parameters")
    
    def _save_temp_file(self, file_data: str, file_name: str) -> Path:
        """Save base64 data to temporary file"""
        try:
            # Decode base64 data
            file_bytes = base64.b64decode(file_data)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=Path(file_name).suffix,
                prefix="stl311_"
            )
            temp_file.write(file_bytes)
            temp_file.close()
            
            return Path(temp_file.name)
        except Exception as e:
            logger.error(f"Error saving temporary file: {e}")
            raise
    
    def _cleanup_temp_file(self, file_path: Path) -> None:
        """Clean up temporary file"""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Error cleaning up temporary file {file_path}: {e}")
    
    def _extract_dimensions_from_bounds(self, bounds: Dict[str, Any]) -> Optional[Dimensions]:
        """Extract dimensions from bounding box data"""
        try:
            if not bounds or 'min' not in bounds or 'max' not in bounds:
                return None
                
            min_coords = bounds['min']
            max_coords = bounds['max']
            
            if len(min_coords) < 3 or len(max_coords) < 3:
                return None
            
            length = max_coords[0] - min_coords[0]
            width = max_coords[1] - min_coords[1] 
            height = max_coords[2] - min_coords[2]
            
            if length > 0 and width > 0 and height > 0:
                return Dimensions(
                    length=length,
                    width=width,
                    height=height
                )
        except Exception as e:
            logger.warning(f"Error extracting dimensions from bounds: {e}")
        
        return None
