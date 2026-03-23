"""
Parameter extraction utility
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from extractors import FileParameterExtractor, STLExtractor, STPExtractor
from models.base_models import Dimensions

logger = logging.getLogger(__name__)


class ParameterExtractor:
    """Main parameter extraction coordinator"""
    
    def __init__(self):
        self.extractors = {
            'stl': STLExtractor(),
            'stp': STPExtractor(),
            'step': STPExtractor()
        }
    
    async def extract_parameters_from_file(
        self, 
        file_data: str, 
        file_name: str, 
        file_type: str
    ) -> Dict[str, Any]:
        """
        Extract parameters from uploaded file
        
        Args:
            file_data: Base64 encoded file data
            file_name: Original filename
            file_type: File type (stl, stp, step)
            
        Returns:
            Dictionary of extracted parameters
        """
        logger.info(f"Extracting parameters from {file_type} file: {file_name}")
        
        # Get appropriate extractor
        extractor = self.extractors.get(file_type.lower())
        if not extractor:
            logger.warning(f"No extractor available for file type: {file_type}")
            return {}
        
        try:
            # Extract parameters
            parameters = await extractor.extract_parameters(file_data, file_name, file_type)
            logger.info(f"Parameter extraction completed for {file_name}")
            return parameters
        except Exception as e:
            logger.error(f"Error extracting parameters from {file_name}: {e}")
            return {}
    
    def merge_parameters(
        self,
        extracted_params: Dict[str, Any],
        request_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge extracted parameters with request parameters
        
        Args:
            extracted_params: Parameters extracted from file
            request_params: Parameters from request
            
        Returns:
            Merged parameters with request taking precedence
        """
        merged = {}
        
        # Start with extracted parameters
        if extracted_params:
            merged.update(extracted_params)
        
        # Override with request parameters (non-None values only)
        for key, value in request_params.items():
            if value is not None:
                merged[key] = value
        
        return merged
    
    def extract_dimensions_from_file_params(self, file_params: Dict[str, Any]) -> Optional[Dimensions]:
        """Extract dimensions from file parameters"""
        dimensions_data = file_params.get('dimensions')
        if dimensions_data and isinstance(dimensions_data, dict):
            try:
                return Dimensions(
                    length=dimensions_data['length'],
                    width=dimensions_data['width'],
                    height=dimensions_data['height']
                )
            except Exception as e:
                logger.warning(f"Error creating Dimensions from file params: {e}")
        return None
