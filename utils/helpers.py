"""
Helper functions for accessing configuration data
"""

from typing import Dict, Any, Optional
from constants import MATERIALS, LOCATIONS, COVER, TOLERANCE, FINISH


def get_material_info(material_id: str) -> Dict[str, Any]:
    """Get material information by ID"""
    return MATERIALS.get(material_id, {})


def get_location_info(location_id: str) -> Dict[str, Any]:
    """Get location information by ID"""
    return LOCATIONS.get(location_id, {})


def get_cover_processing_info(cover_id: str) -> Dict[str, Any]:
    """Get cover processing information by ID"""
    return COVER.get(cover_id, {})


def get_tolerance_info(tolerance_id: str) -> Dict[str, Any]:
    """Get tolerance information by ID"""
    return TOLERANCE.get(tolerance_id, {})


def get_finish_info(finish_id: str) -> Dict[str, Any]:
    """Get finish information by ID"""
    return FINISH.get(finish_id, {})


def get_material_by_process(process: str) -> Dict[str, Dict[str, Any]]:
    """Get all materials applicable to a specific process"""
    return {
        material_id: material_info 
        for material_id, material_info in MATERIALS.items()
        if process in material_info.get("applicable_processes", [])
    }


def get_cover_processing_list() -> list:
    """Get list of all cover processing options"""
    return [{"id": k, **v} for k, v in COVER.items()]


def get_tolerance_list() -> list:
    """Get list of all tolerance options"""
    return [{"id": k, **v} for k, v in TOLERANCE.items()]


def get_finish_list() -> list:
    """Get list of all finish options"""
    return [{"id": k, **v} for k, v in FINISH.items()]


def get_location_list() -> list:
    """Get list of all location options"""
    return [{"id": k, "name": v} for k, v in LOCATIONS.items()]
