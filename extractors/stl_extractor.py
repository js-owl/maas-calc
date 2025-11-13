"""
STL file parameter extractor
"""

import logging
import math
from typing import Dict, Any, Optional
from pathlib import Path

from .file_extractor import FileParameterExtractor
from models.base_models import Dimensions

logger = logging.getLogger(__name__)


class STLExtractor(FileParameterExtractor):
    """STL file parameter extractor"""
    
    def __init__(self):
        super().__init__()
        self.supported_types = ['stl']
    
    async def extract_parameters(self, file_data: str, file_name: str, file_type: str) -> Dict[str, Any]:
        """Extract parameters from STL file"""
        logger.info(f"Extracting parameters from STL file: {file_name}")
        
        temp_file = None
        try:
            # Save file temporarily
            temp_file = self._save_temp_file(file_data, file_name)
            
            # Analyze STL file
            analysis_result = await self._analyze_stl_file(temp_file)
            
            # Extract parameters
            parameters = {
                'dimensions': analysis_result.get('dimensions'),
                'volume': analysis_result.get('volume'),
                'surface_area': analysis_result.get('surface_area'),
                'features': analysis_result.get('features', {}),
                'file_info': {
                    'filename': file_name,
                    'file_type': file_type,
                    'file_size': len(file_data)
                },
                # ML-compatible features
                'obb_x': analysis_result.get('obb_x'),
                'obb_y': analysis_result.get('obb_y'),
                'obb_z': analysis_result.get('obb_z'),
                'min_size': analysis_result.get('min_size'),
                'mid_size': analysis_result.get('mid_size'),
                'max_size': analysis_result.get('max_size'),
                'aspect_ratio_xy': analysis_result.get('aspect_ratio_xy'),
                'aspect_ratio_yz': analysis_result.get('aspect_ratio_yz'),
                'aspect_ratio_xz': analysis_result.get('aspect_ratio_xz'),
                'bbox_volume': analysis_result.get('bbox_volume'),
                'check_sizes_for_lathe': analysis_result.get('check_sizes_for_lathe')
            }
            
            logger.info(f"STL analysis completed for file: {file_name}")
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting parameters from STL file {file_name}: {e}")
            raise
        finally:
            if temp_file:
                self._cleanup_temp_file(temp_file)
    
    async def _analyze_stl_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze STL file and extract comprehensive geometric information"""
        try:
            # Import trimesh for STL analysis
            import trimesh
            import numpy as np
            import math
            
            # Load the STL file
            mesh = trimesh.load(str(file_path))
            
            # Extract basic geometric information
            bounds = mesh.bounds
            volume = mesh.volume
            surface_area = mesh.area  # trimesh uses 'area' not 'surface_area'
            
            # Calculate OBB dimensions
            oriented_bounding_box = mesh.bounding_box_oriented
            dimensions = oriented_bounding_box.extents
            sorted = np.sort(dimensions)
            obb_x = sorted[2]
            obb_y = sorted[1]
            obb_z = sorted[0]
            
            # Extract dimensions for compatibility
            dimensions = {
                'length': obb_x,
                'width': obb_y,
                'thickness': obb_z
            }
            
            # Calculate derived features
            obb_dims = [obb_x, obb_y, obb_z]
            min_size = obb_z
            mid_size = obb_y
            max_size = obb_x
            
            # Calculate aspect ratios
            aspect_ratio_xy = obb_x / obb_y if obb_y > 0 else 0.0
            aspect_ratio_yz = obb_y / obb_z if obb_z > 0 else 0.0
            aspect_ratio_xz = obb_x / obb_z if obb_z > 0 else 0.0
            
            # Bounding box volume
            bbox_volume = obb_x * obb_y * obb_z
            
            # Lathe suitability check
            check_sizes_for_lathe = 1 if any(
                abs(obb_dims[i] - obb_dims[j]) < 0.1 
                for i in range(3) for j in range(i+1, 3)
            ) else 0
            
            # Extract surface features
            features = self._extract_stl_surface_features(mesh)
            
            return {
                'dimensions': dimensions,
                'volume': volume,
                'surface_area': surface_area,
                'features': features,
                # ML-compatible features
                'obb_x': obb_x,
                'obb_y': obb_y,
                'obb_z': obb_z,
                'min_size': min_size,
                'mid_size': mid_size,
                'max_size': max_size,
                'aspect_ratio_xy': aspect_ratio_xy,
                'aspect_ratio_yz': aspect_ratio_yz,
                'aspect_ratio_xz': aspect_ratio_xz,
                'bbox_volume': bbox_volume,
                'check_sizes_for_lathe': check_sizes_for_lathe
            }
            
        except Exception as e:
            logger.error(f"Error analyzing STL file {file_path}: {e}")
            # Return default values if analysis fails
            return {
                'dimensions': None,
                'volume': None,
                'surface_area': None,
                'features': {},
                'obb_x': 0.0,
                'obb_y': 0.0,
                'obb_z': 0.0,
                'min_size': 0.0,
                'mid_size': 0.0,
                'max_size': 0.0,
                'aspect_ratio_xy': 1.0,
                'aspect_ratio_yz': 1.0,
                'aspect_ratio_xz': 1.0,
                'bbox_volume': 0.0,
                'check_sizes_for_lathe': 0
            }
    
    def _extract_stl_surface_features(self, mesh) -> Dict[str, Any]:
        """Extract surface features from STL mesh"""
        try:
            features = {
                'file_type': 'stl',
                'face_count': len(mesh.faces),
                'vertex_count': len(mesh.vertices),
                'edge_count': len(mesh.edges) if hasattr(mesh, 'edges') else 0
            }
            
            return features
            
        except Exception as e:
            logger.warning(f"Error extracting STL surface features: {e}")
            return {
                'file_type': 'stl',
                'face_count': 0,
                'vertex_count': 0,
                'edge_count': 0
            }
