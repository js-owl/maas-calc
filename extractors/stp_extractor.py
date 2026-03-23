"""
STP file parameter extractor
"""

import logging
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

from .file_extractor import FileParameterExtractor
from models.base_models import Dimensions

logger = logging.getLogger(__name__)


class STPExtractor(FileParameterExtractor):
    """STP file parameter extractor"""
    
    def __init__(self):
        super().__init__()
        self.supported_types = ['stp', 'step']
    
    async def extract_parameters(self, file_data: str, file_name: str, file_type: str) -> Dict[str, Any]:
        """Extract parameters from STP file"""
        logger.info(f"Extracting parameters from STP file: {file_name}")
        
        temp_file = None
        try:
            # Save file temporarily
            temp_file = self._save_temp_file(file_data, file_name)
            
            # Analyze STP file
            analysis_result = await self._analyze_stp_file(temp_file)
            
            # Extract parameters
            parameters = {
                'dimensions': analysis_result.get('dimensions'),
                'volume': analysis_result.get('volume'),
                'surface_area': analysis_result.get('surface_area'),
                'obb_x': analysis_result.get('obb_x'),
                'obb_y': analysis_result.get('obb_y'),
                'obb_z': analysis_result.get('obb_z'),
                'aspect_ratio_xy': analysis_result.get('aspect_ratio_xy'),
                'aspect_ratio_yz': analysis_result.get('aspect_ratio_yz'),
                'aspect_ratio_xz': analysis_result.get('aspect_ratio_xz'),
                'bbox_volume': analysis_result.get('bbox_volume'),
                'num_faces': analysis_result.get('num_faces'),
                'num_edges': analysis_result.get('num_edges'),
                'num_vertices': analysis_result.get('num_vertices'),
                'num_wires': analysis_result.get('num_wires'),
                'euler_char': analysis_result.get('euler_char'),
                'num_planar': analysis_result.get('num_planar'),
                'num_cylindrical': analysis_result.get('num_cylindrical'),
                'num_conical': analysis_result.get('num_conical'),
                'num_toroidal': analysis_result.get('num_toroidal'),
                'num_spherical': analysis_result.get('num_spherical'),
                'num_bspline': analysis_result.get('num_bspline'),
                'surface_entropy': analysis_result.get('surface_entropy'),
                'ratio_planar': analysis_result.get('ratio_planar'),
                'ratio_cylindrical': analysis_result.get('ratio_cylindrical'),
                'ratio_conical': analysis_result.get('ratio_conical'),
                'ratio_toroidal': analysis_result.get('ratio_toroidal'),
                'ratio_spherical': analysis_result.get('ratio_spherical'),
                'ratio_bspline': analysis_result.get('ratio_bspline'),
                'planar_area': analysis_result.get('planar_area'),
                'cylindrical_area': analysis_result.get('cylindrical_area'),
                'conical_area': analysis_result.get('conical_area'),
                'toroidal_area': analysis_result.get('toroidal_area'),
                'spherical_area': analysis_result.get('spherical_area'),
                'bspline_area': analysis_result.get('bspline_area'),
                'other_area': analysis_result.get('other_area'),
                'ratio_planar_area': analysis_result.get('ratio_planar_area'),
                'ratio_cylindrical_area': analysis_result.get('ratio_cylindrical_area'),
                'ratio_conical_area': analysis_result.get('ratio_conical_area'),
                'ratio_toroidal_area': analysis_result.get('ratio_toroidal_area'),
                'ratio_spherical_area': analysis_result.get('ratio_spherical_area'),
                'ratio_bspline_area': analysis_result.get('ratio_bspline_area'),
                'ratio_other_area': analysis_result.get('ratio_other_area'),
                'ratio_planar_cylindrical': analysis_result.get('ratio_planar_cylindrical'),
                'num_unique_planar_normals': analysis_result.get('num_unique_planar_normals'),
                'num_straight_edges': analysis_result.get('num_straight_edges'),
                'num_curved_edges': analysis_result.get('num_curved_edges'),
                'num_circles': analysis_result.get('num_circles'),
                'num_bspline_edges': analysis_result.get('num_bspline_edges'),
                'edge_entropy': analysis_result.get('edge_entropy'),
                'ratio_straight_edges': analysis_result.get('ratio_straight_edges'),
                'ratio_curved_edges': analysis_result.get('ratio_curved_edges'),
                'ratio_circles_edges': analysis_result.get('ratio_circles_edges'),
                'ratio_bspline_edges': analysis_result.get('ratio_bspline_edges'),
                'length_all_edges': analysis_result.get('length_all_edges'),
                'straight_length': analysis_result.get('straight_length'),
                'curved_length': analysis_result.get('curved_length'),
                'circle_length': analysis_result.get('circle_length'),
                'bspline_edge_length': analysis_result.get('bspline_edge_length'),
                'ratio_straight_edges_length': analysis_result.get('ratio_straight_edges_length'),
                'ratio_curved_edges_length': analysis_result.get('ratio_curved_edges_length'),
                'ratio_circles_edges_length': analysis_result.get('ratio_circles_edges_length'),
                'ratio_bspline_edges_length': analysis_result.get('ratio_bspline_edges_length'),
                'avg_face_area': analysis_result.get('avg_face_area'),
                'avg_edge_length': analysis_result.get('avg_edge_length'),
                'surface_to_volume_ratio': analysis_result.get('surface_to_volume_ratio'),
                'obb_compactness': analysis_result.get('obb_compactness'),
                'sphericity': analysis_result.get('sphericity'),
                'topology_complexity_score': analysis_result.get('topology_complexity_score'),
                'removable_score': analysis_result.get('removable_score'),
                'min_size': analysis_result.get('min_size'),
                'mid_size': analysis_result.get('mid_size'),
                'max_size': analysis_result.get('max_size'),
                'volume_bar': analysis_result.get('volume_bar'),
                'removable_score_better': analysis_result.get('removable_score_better'),
                'check_sizes_for_lathe': analysis_result.get('check_sizes_for_lathe'),
                'surface_area_obb': analysis_result.get('surface_area_obb'),
                'removable_volume': analysis_result.get('removable_volume'),
                'features': analysis_result.get('features', {}),
                'file_info': {
                    'filename': file_name,
                    'file_type': file_type,
                    'file_size': len(file_data)
                }
            }
            
            logger.info(f"Extract parameters completed for file: {file_name}, extracted {len(parameters)} features")
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting parameters from STP file {file_name}: {e}")
            raise
        finally:
            if temp_file:
                self._cleanup_temp_file(temp_file)
    
    async def _analyze_stp_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze STP file and extract comprehensive geometric information"""
        try:
            # Import CADQuery for STP analysis
            import cadquery as cq
            from OCP.Bnd import Bnd_OBB
            from OCP.BRepBndLib import BRepBndLib
            import math
            from collections import Counter

            # Load the STP file
            try:
                shape = cq.importers.importStep(str(file_path))
                logger.info(f"Successfully loaded STP file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to load STP file with CADQuery: {e}")
                # Fallback to basic analysis
                return self._basic_stp_analysis(file_path)
            
            # Extract geometric information
            analysis_result = {}
            
            # Get bounding box
            try:
                obb = Bnd_OBB()
                BRepBndLib.AddOBB_s(
                    shape.val().wrapped,
                    obb,
                    theIsTriangulationUsed=True,
                    theIsOptimal=True,
                    theIsShapeToleranceUsed=True
                )
                obb_dimensions = {
                    'x': 2 * obb.XHSize(),
                    'y': 2 * obb.YHSize(),
                    'z': 2 * obb.ZHSize()
                }
                
                analysis_result['obb_x'] = obb_dimensions['x']
                analysis_result['obb_y'] = obb_dimensions['y']
                analysis_result['obb_z'] = obb_dimensions['z']

                analysis_result['aspect_ratio_xy'] = obb_dimensions['x'] / obb_dimensions['y']
                analysis_result['aspect_ratio_yz'] = obb_dimensions['y'] / obb_dimensions['z']
                analysis_result['aspect_ratio_xz'] = obb_dimensions['x'] / obb_dimensions['z']
                analysis_result['bbox_volume'] = obb_dimensions['x'] * obb_dimensions['y'] * obb_dimensions['z']

                dimensions = sorted(obb_dimensions.values())
                analysis_result['min_size'] = dimensions[0]
                analysis_result['mid_size'] = dimensions[1]
                analysis_result['max_size'] = dimensions[2]
                analysis_result['volume_bar'] = analysis_result['min_size'] * analysis_result['mid_size'] * analysis_result['max_size'] * 1.1

                analysis_result['surface_area_obb'] = 2*(analysis_result['min_size'] * analysis_result['mid_size'] + \
                                                        analysis_result['min_size'] * analysis_result['max_size'] + \
                                                        analysis_result['mid_size'] * analysis_result['max_size'])
                
                # Create dimensions dict for compatibility
                analysis_result['dimensions'] = {
                    'length': dimensions[2],
                    'width': dimensions[1],
                    'height': dimensions[0]
                }
                # Lathe suitability
                analysis_result['check_sizes_for_lathe'] = 1 if any(
                    abs(dimensions[i] - dimensions[j]) < 0.5 
                    for i in range(3) for j in range(i+1, 3)
                ) else 0
            except Exception as e:
                logger.warning(f"Error calculating bounding box: {e}")
            
            # Calculate volume
            try:
                volume = shape.val().Volume()
                analysis_result['volume'] = volume
            except:
                analysis_result['volume'] = 0
                
            # Calculate surface area
            try:
                surface_area = shape.val().Area()
                analysis_result['surface_area'] = sum(s.Area() for s in shape.solids().vals())
            except:
                # Estimate surface area
                analysis_result['surface_area'] = 0
            
            # Extract surface features
            try:
                # General
                faces = shape.faces().vals()
                edges = shape.edges().vals()
                vertices = shape.vertices().vals()
                analysis_result['num_faces'] = len(faces)
                analysis_result['num_edges'] = len(edges)
                analysis_result['num_vertices'] = len(vertices)
                analysis_result['num_wires'] = len(shape.wires().vals())
                analysis_result['euler_char'] = analysis_result['num_vertices'] - analysis_result['num_edges'] + analysis_result['num_faces']

                # Faces
                face_types = Counter(self._safe_geomtype(f) for f in faces)
                analysis_result['num_planar'] = face_types.get('PLANE', 0)
                analysis_result['num_cylindrical'] = face_types.get('CYLINDER', 0)
                analysis_result['num_conical'] = face_types.get('CONE', 0)
                analysis_result['num_toroidal'] = face_types.get('TORUS', 0)
                analysis_result['num_spherical'] = face_types.get('SPHERE', 0)
                analysis_result['num_bspline'] = face_types.get('BSPLINE', 0)
                analysis_result['surface_entropy'] = self._compute_entropy(face_types)

                # Ratios for nums of faces
                analysis_result['ratio_planar'] = analysis_result['num_planar'] / analysis_result['num_faces']
                analysis_result['ratio_cylindrical'] = analysis_result['num_cylindrical'] / analysis_result['num_faces']
                analysis_result['ratio_conical'] = analysis_result['num_conical'] / analysis_result['num_faces']
                analysis_result['ratio_toroidal'] = analysis_result['num_toroidal'] / analysis_result['num_faces']
                analysis_result['ratio_spherical'] = analysis_result['num_spherical'] / analysis_result['num_faces']
                analysis_result['ratio_bspline'] = analysis_result['num_bspline'] / analysis_result['num_faces']

                # Areas by surface type (for machining complexity)
                analysis_result['planar_area'] = sum(f.Area() for f in faces if self._safe_geomtype(f) == 'PLANE')
                analysis_result['cylindrical_area'] = sum(f.Area() for f in faces if self._safe_geomtype(f) == 'CYLINDER')
                analysis_result['conical_area'] = sum(f.Area() for f in faces if self._safe_geomtype(f) == 'CONE')
                analysis_result['toroidal_area'] = sum(f.Area() for f in faces if self._safe_geomtype(f) == 'TORUS')
                analysis_result['spherical_area'] = sum(f.Area() for f in faces if self._safe_geomtype(f) == 'SPHERE')
                analysis_result['bspline_area'] = sum(f.Area() for f in faces if self._safe_geomtype(f) == 'BSPLINE')
                analysis_result['other_area'] = surface_area - \
                    analysis_result['planar_area'] + analysis_result['cylindrical_area'] + analysis_result['conical_area'] + \
                    analysis_result['toroidal_area'] + analysis_result['spherical_area'] + analysis_result['bspline_area']
                analysis_result['curved_area'] = surface_area - analysis_result['planar_area']

                # Ratios for areas of faces
                analysis_result['ratio_planar_area'] = analysis_result['planar_area'] / surface_area
                analysis_result['ratio_cylindrical_area'] = analysis_result['cylindrical_area'] / surface_area
                analysis_result['ratio_conical_area'] = analysis_result['conical_area'] / surface_area
                analysis_result['ratio_toroidal_area'] = analysis_result['toroidal_area'] / surface_area
                analysis_result['ratio_spherical_area'] = analysis_result['spherical_area'] / surface_area
                analysis_result['ratio_bspline_area'] = analysis_result['bspline_area'] / surface_area
                analysis_result['ratio_other_area'] = analysis_result['other_area'] / surface_area
                analysis_result['ratio_planar_cylindrical'] = analysis_result['ratio_cylindrical_area'] - analysis_result['ratio_planar_area'] + \
                    analysis_result['ratio_cylindrical'] - analysis_result['ratio_planar']
                
                # Planar normals clustering (unique directions, rounded)
                planar_normals = [tuple(round(c, 3) for c in f.normalAt().toTuple()) for f in faces if self._safe_geomtype(f) == 'PLANE']
                analysis_result['num_unique_planar_normals'] = len(set(planar_normals)) if planar_normals else 0

                # Edges
                edge_types = Counter(self._safe_geomtype(e) for e in edges)
                analysis_result['num_straight_edges'] = edge_types.get('LINE', 0)
                analysis_result['num_curved_edges'] = analysis_result['num_edges'] - analysis_result['num_straight_edges']
                analysis_result['num_circles'] = edge_types.get('CIRCLE', 0)
                analysis_result['num_bspline_edges'] = edge_types.get('BSPLINE', 0)
                analysis_result['edge_entropy'] = self._compute_entropy(edge_types)

                # Ratios for nums of edges
                analysis_result['ratio_straight_edges'] = analysis_result['num_straight_edges'] / analysis_result['num_edges']
                analysis_result['ratio_curved_edges'] = analysis_result['num_curved_edges'] / analysis_result['num_edges']
                analysis_result['ratio_circles_edges'] = analysis_result['num_circles'] / analysis_result['num_edges']
                analysis_result['ratio_bspline_edges'] = analysis_result['num_bspline_edges'] / analysis_result['num_edges']

                # Lengths by edge type
                analysis_result['length_all_edges'] = sum(e.Length() for e in edges)
                analysis_result['straight_length'] = sum(e.Length() for e in edges if self._safe_geomtype(e) == 'LINE')
                analysis_result['curved_length'] = analysis_result['length_all_edges'] - analysis_result['straight_length']
                analysis_result['circle_length'] = sum(e.Length() for e in edges if self._safe_geomtype(e) == 'CIRCLE')
                analysis_result['bspline_edge_length'] = sum(e.Length() for e in edges if self._safe_geomtype(e) == 'BSPLINE')

                # Ratios for lengths of edges
                analysis_result['ratio_straight_edges_length'] = analysis_result['straight_length'] / analysis_result['length_all_edges']
                analysis_result['ratio_curved_edges_length'] = analysis_result['curved_length'] / analysis_result['length_all_edges']
                analysis_result['ratio_circles_edges_length'] = analysis_result['circle_length'] / analysis_result['length_all_edges']
                analysis_result['ratio_bspline_edges_length'] = analysis_result['bspline_edge_length'] / analysis_result['length_all_edges']

                # Average metrics
                analysis_result['avg_face_area'] = surface_area / analysis_result['num_faces'] if analysis_result['num_faces'] > 0 else 0
                analysis_result['avg_edge_length'] = sum(e.Length() for e in edges) / analysis_result['num_edges'] if analysis_result['num_edges'] > 0 else 0

                # Compactness and ratios
                analysis_result['surface_to_volume_ratio'] = surface_area / volume if volume > 0 else 0
                analysis_result['obb_compactness'] = volume / analysis_result['bbox_volume'] if analysis_result['bbox_volume'] > 0 else 0

                # Sphericity (1 for sphere, <1 for irregular)
                analysis_result['sphericity'] = (np.pi ** (1/3) * (6 * volume) ** (2/3)) / surface_area if surface_area > 0 and volume > 0 else 0

                analysis_result['topology_complexity_score'] = (analysis_result['num_faces'] + analysis_result['num_edges'] + analysis_result['num_vertices']) / 3
                analysis_result['removable_score'] = volume / analysis_result['bbox_volume'] if analysis_result['bbox_volume'] > 0 else 0
                
                
                analysis_result['removable_score_better'] = analysis_result['volume'] / analysis_result['volume_bar'] if analysis_result['volume_bar'] > 0 else 0
                analysis_result['surface_area_detail_obb_ratio'] = analysis_result['surface_area'] / analysis_result['surface_area_obb'] if analysis_result['surface_area_obb'] > 0 else 0
                analysis_result['diff_obb_detail_area'] = surface_area - analysis_result['surface_area_obb']
                analysis_result['removable_volume'] = analysis_result['volume_bar'] - analysis_result['volume']

            except Exception as e:
                logger.warning(f"ERROR extracting surface features: {e}")
            
            logger.info(f"STP analysis completed for {file_path}.")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing STP file {file_path}: {e}")
            return self._basic_stp_analysis(file_path)
    
    def _compute_entropy(self, types_count: Dict[str, int]) -> float:
        """Compute entropy from types of areas"""
        total = sum(types_count.values())
        probs = [count / total for count in types_count.values() if count > 0]
        return -np.sum(probs * np.log2(probs)) if probs else 0.0

    def _safe_geomtype(self, obj) -> str:
        """Get type of geometry"""
        try:
            return (obj.geomType() or "").upper()
        except Exception:
            return ""
    
    def _basic_stp_analysis(self, file_path: Path) -> Dict[str, Any]:
        """Basic STP analysis fallback when CADQuery fails"""
        logger.warning(f"Using basic STP analysis for {file_path}")
        
        return {
            'dimensions': None,
            'volume': None,
            'surface_area': None,
            'features': {
                'file_type': 'stp',
                'analysis_status': 'basic_fallback'
            },
            'bounds': None,
            'obb_x': 0.0,
            'obb_y': 0.0,
            'obb_z': 0.0,
            'aspect_ratio_xy': 1.0,
            'aspect_ratio_yz': 1.0,
            'aspect_ratio_xz': 1.0,
            'min_size': 0.0,
            'mid_size': 0.0,
            'max_size': 0.0,
            'bbox_volume': 0.0,
            'check_sizes_for_lathe': 0
        }
