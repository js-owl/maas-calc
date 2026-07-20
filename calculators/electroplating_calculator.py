"""Automatic galvanic coating price calculator."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import HTTPException

from .base_calculator import BaseCalculator
from calculations.core import build_unified_unit_price, calculate_k_quantity
from calculations.electroplating import calculate_electroplating_parameters
from constants import VAT_RATE
from commercial_constants import COST_STRUCTURE
from MATERIALS_gen import MATERIALS
from models.calculation_models import ElectroplatingCalculationRequest
from models.response_models import UnifiedCalculationResponse
from utils.electroplating_config import ELECTROPLATING_SERVICE_ID

logger = logging.getLogger(__name__)


class ElectroplatingAutoCalculator(BaseCalculator):
    """Rule-based calculator for service_id='electroplating_auto'."""

    def __init__(self) -> None:
        super().__init__()
        self.service_id = ELECTROPLATING_SERVICE_ID
        self.calculation_method = "Electroplating Auto Calculation"

    async def calculate(self, request: ElectroplatingCalculationRequest) -> UnifiedCalculationResponse:
        self._validate_request(request)
        self._log_calculation_start(request.file_id, "electroplating_auto")

        try:
            features = request.ml_features or {}
            if not features:
                raise ValueError("STP/STEP geometry features are required for electroplating_auto")

            material_info = None
            if request.material_id:
                material_info = MATERIALS.get(request.material_id)
                if not material_info:
                    raise ValueError(f"Unknown material_id: {request.material_id!r}")

            quantity = max(int(request.quantity or 1), 1)
            location = request.location
            process_params = calculate_electroplating_parameters(
                features=features,
                material_id=request.material_id,
                material_info=material_info,
                electroplating_family=request.electroplating_family,
                process_id=request.electroplating_process_id,
                cover_id=request.cover_id,
                coating_thickness_microns=request.coating_thickness_microns,
                processing_depth_microns=request.processing_depth_microns,
                quantity=quantity,
            )
            
            logger.info(
                "Successfully calculated process params for %s: %r",
                self.service_id,
                process_params
            )

            layout = process_params["layout"]

            price_of_hour = COST_STRUCTURE.get(location, {}).get("price_of_hour", 0)
            if price_of_hour <= 0:
                raise ValueError(f"Invalid or missing price_of_hour for location={location!r}")

            base_work_price = process_params["labor_time_hours"] * price_of_hour
            k_quantity = calculate_k_quantity(quantity)
            k_otk = float(request.k_otk or 1.0)
            work_price_without_quantity = base_work_price * k_otk

            # This calculation branch currently prices galvanic treatment by labor.
            # Bath chemistry/fill cost can be added later as a material component.
            mat_price = 0.0
            price_special_equipment_to_quantity = 0.0
            unified_price = build_unified_unit_price(
                mat_price=mat_price,
                work_price=work_price_without_quantity,
                location=location,
                quantity=quantity,
                k_quantity=k_quantity,
                price_special_equipment_to_quantity=price_special_equipment_to_quantity,
            )
            detail_price = unified_price["detail_price"]
            detail_price_one = unified_price["detail_price_one"]
            total_price = unified_price["total_price"]
            price_breakdown = unified_price["total_price_breakdown"]

            price_breakdown.update({
                "total_price (include quantity)": total_price,
                "total_time": process_params["order_labor_time_hours"],
                "work_time_per_part": process_params["labor_time_hours"],
                "order_labor_time_hours": process_params["order_labor_time_hours"],
                "order_labor_time_min": process_params["order_labor_time_min"],
                "process_id": process_params["process"]["id"],
                "process_label": process_params["process"].get("label"),
                "electroplating_family": process_params["material_family"].get("id"),
                "process_time_model": process_params["time_model"],
                "thickness_role": process_params["thickness_role"],
                "uses_fixed_operation_time_by_process": process_params.get("uses_fixed_operation_time_by_process"),
                "uses_thickness_dependent_operation_time": process_params.get("uses_thickness_dependent_operation_time"),
                "coating_thickness_microns": process_params.get("coating_thickness_microns"),
                "processing_depth_microns": process_params.get("processing_depth_microns"),
                "process_parameter_name": process_params.get("process_parameter_name"),
                "process_parameter_microns": process_params.get("process_parameter_microns"),
                "surface_area_dm2": process_params["geometry"]["surface_area_dm2"],
                "volume_dm3": process_params["geometry"]["volume_dm3"],
                "part_weight_kg": process_params["part_weight_kg"],
                "requested_quantity": layout["requested_quantity"],
                "batch_quantity_used_as_n": layout["batch_quantity"],
                "bath_batch_capacity": layout["batch_capacity"],
                "bath_geometric_capacity": layout["geometric_capacity"],
                "bath_practical_geometric_capacity": layout["practical_geometric_capacity"],
                "bath_current_capacity": layout["current_capacity"],
                "bath_weight_capacity": layout["weight_capacity"],
                "bath_max_weight_kg": layout["max_weight_kg"],
                "requested_total_weight_kg": layout["requested_total_weight_kg"],
                "batch_weight_kg": layout["batch_weight_kg"],
                "batch_count": layout["batch_count"],
                "batch_quantity_limited_by": layout["batch_quantity_limited_by"],
            })

            detail_price_calculation = unified_price["detail_price_calculation"]

            response_data = self._create_base_response(
                file_id=request.file_id,
                filename=request.filename,
                part_price=detail_price,
                detail_price=detail_price,
                part_price_one=detail_price_one,
                detail_price_one=detail_price_one,
                total_price=total_price,
                total_time=process_params["order_labor_time_hours"],
                mat_volume=process_params["geometry"]["volume_dm3"],
                mat_weight=process_params["part_weight_kg"],
                mat_price=mat_price,
                work_price=work_price_without_quantity,
                work_time=process_params["labor_time_hours"],
                k_quantity=k_quantity,
                k_otk=k_otk,
                k_cover=1.0,
                manufacturing_cycle=None,
                suitable_machines=None,
                extracted_dimensions=features.get("dimensions"),
                calculation_engine="rule_based",
                electroplating_process_id=process_params["process"]["id"],
                electroplating_family=process_params["material_family"].get("id"),
                coating_thickness_microns=process_params.get("coating_thickness_microns"),
                processing_depth_microns=process_params.get("processing_depth_microns"),
                process_parameter_microns=process_params.get("process_parameter_microns"),
                process_parameter_name=process_params.get("process_parameter_name"),
                process_time_model=process_params.get("time_model"),
                thickness_role=process_params.get("thickness_role"),
                coating_surface_area_dm2=process_params["geometry"]["surface_area_dm2"],
                coating_mass_kg=process_params["part_weight_kg"],
                batch_quantity=layout["batch_quantity"],
                requested_quantity=layout["requested_quantity"],
                bath_batch_capacity=layout["batch_capacity"],
                bath_geometric_capacity=layout["geometric_capacity"],
                bath_practical_geometric_capacity=layout["practical_geometric_capacity"],
                bath_current_capacity=layout["current_capacity"],
                bath_weight_capacity=layout["weight_capacity"],
                bath_max_weight_kg=layout["max_weight_kg"],
                batch_weight_kg=layout["batch_weight_kg"],
                batch_count=layout["batch_count"],
                batch_quantity_limited_by=layout["batch_quantity_limited_by"],
                material_costs={
                    "material_id": request.material_id,
                    "electroplating_family": process_params["material_family"].get("id"),
                    "material_family": process_params["material_family"],
                    "part_volume_dm3": process_params["geometry"]["volume_dm3"],
                    "part_weight_kg": process_params["part_weight_kg"],
                    "requested_total_weight_kg": layout["requested_total_weight_kg"],
                    "batch_weight_kg": layout["batch_weight_kg"],
                    "bath_max_weight_kg": layout["max_weight_kg"],
                    "treatment_material_price": mat_price,
                },
                work_price_breakdown={
                    "base_work_price": base_work_price,
                    "k_quantity": k_quantity,
                    "k_otk": k_otk,
                    "final_work_price": work_price_without_quantity,
                    "final_work_price_before_quantity": work_price_without_quantity,
                    "final_work_price_after_quantity": work_price_without_quantity * k_quantity,
                    "labor_time_hours": process_params["labor_time_hours"],
                    "labor_time_min": process_params["labor_time_min"],
                    "order_labor_time_hours": process_params["order_labor_time_hours"],
                    "order_labor_time_min": process_params["order_labor_time_min"],
                    "labor_formula_n": layout["batch_quantity"],
                    "per_detail_operation_labor_min": process_params["per_detail_operation_labor_min"],
                    "operation_time_min": process_params["operation_time_min"],
                    "operation_time_component_min": process_params.get("operation_time_component_min"),
                    "coating_time_min": process_params["coating_time_min"],
                    "process_time_model": process_params.get("time_model"),
                    "thickness_role": process_params.get("thickness_role"),
                    "uses_fixed_operation_time_by_process": process_params.get("uses_fixed_operation_time_by_process"),
                    "uses_thickness_dependent_operation_time": process_params.get("uses_thickness_dependent_operation_time"),
                    "coating_thickness_microns": process_params.get("coating_thickness_microns"),
                    "processing_depth_microns": process_params.get("processing_depth_microns"),
                    "process_parameter_name": process_params.get("process_parameter_name"),
                    "process_parameter_microns": process_params.get("process_parameter_microns"),
                    "preparation_time_min": process_params["preparation_time_min"],
                    "workers_count": process_params["workers_count"],
                    "mount_unmount_time_min": process_params["mount_unmount_time_min"],
                    "requested_quantity": layout["requested_quantity"],
                    "bath_batch_capacity": layout["batch_capacity"],
                    "bath_geometric_capacity": layout["geometric_capacity"],
                    "bath_practical_geometric_capacity": layout["practical_geometric_capacity"],
                    "bath_current_capacity": layout["current_capacity"],
                    "bath_weight_capacity": layout["weight_capacity"],
                    "bath_max_weight_kg": layout["max_weight_kg"],
                    "requested_total_weight_kg": layout["requested_total_weight_kg"],
                    "batch_weight_kg": layout["batch_weight_kg"],
                    "batch_count": layout["batch_count"],
                    "batch_quantity_limited_by": layout["batch_quantity_limited_by"],
                },
                total_price_breakdown=price_breakdown,
                detail_price_calculation=detail_price_calculation,
                features_extracted={
                    "surface_area_mm2": process_params["geometry"]["surface_area_mm2"],
                    "surface_area_dm2": process_params["geometry"]["surface_area_dm2"],
                    "volume_mm3": process_params["geometry"]["volume_mm3"],
                    "volume_dm3": process_params["geometry"]["volume_dm3"],
                    "dimensions_mm": process_params["dimensions_mm"],
                    "process_time_model": process_params.get("time_model"),
                    "thickness_role": process_params.get("thickness_role"),
                    "uses_fixed_operation_time_by_process": process_params.get("uses_fixed_operation_time_by_process"),
                    "uses_thickness_dependent_operation_time": process_params.get("uses_thickness_dependent_operation_time"),
                    "coating_thickness_microns": process_params.get("coating_thickness_microns"),
                    "processing_depth_microns": process_params.get("processing_depth_microns"),
                    "process_parameter_name": process_params.get("process_parameter_name"),
                    "process_parameter_microns": process_params.get("process_parameter_microns"),
                    "bath_layout": process_params["layout"],
                    "requested_quantity": layout["requested_quantity"],
                    "batch_quantity_used_as_n": layout["batch_quantity"],
                    "bath_batch_capacity": layout["batch_capacity"],
                    "bath_geometric_capacity": layout["geometric_capacity"],
                    "bath_practical_geometric_capacity": layout["practical_geometric_capacity"],
                    "bath_weight_capacity": layout["weight_capacity"],
                    "bath_max_weight_kg": layout["max_weight_kg"],
                    "batch_weight_kg": layout["batch_weight_kg"],
                    "batch_count": layout["batch_count"],
                },
            )
            self._log_calculation_complete(request.file_id, "electroplating_auto")
            return UnifiedCalculationResponse(**response_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error in electroplating calculation for file_id %s: %s", request.file_id, e)
            raise HTTPException(status_code=500, detail=str(e))

