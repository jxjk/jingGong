import numpy as np
import trimesh
from typing import Dict, List, Any
from enum import Enum
import json
import os
import sys


class ManufacturingDifficulty(Enum):
    """Manufacturing difficulty levels"""
    EASY = "easy"           # Easy
    MODERATE = "moderate"   # Moderate
    DIFFICULT = "difficult" # Difficult
    VERY_DIFFICULT = "very_difficult"  # Very difficult


def analyze_model_machinability(file_path: str) -> Dict[str, Any]:
    """
    Analyze model machinability
    This is a simplified version focusing on core assessment logic
    """
    try:
        # Load model
        mesh = trimesh.load(file_path)
        
        # Basic geometric analysis
        extents = mesh.extents
        volume = mesh.volume
        surface_area = mesh.area
        aspect_ratio = max(extents) / min(extents) if min(extents) > 0 else float('inf')
        
        # Volume and weight estimation
        material_density = 7.85  # Steel density g/cm^3
        volume_cm3 = volume / 1000  # Convert to cm^3
        weight_kg = volume_cm3 * material_density / 1000  # Convert to kg
        
        # Complexity assessment
        complexity_score = 0
        
        # 1. Dimension ratio assessment (ideal ratio close to 1:1:1)
        if aspect_ratio < 3:
            dimension_score = 90
        elif aspect_ratio < 10:
            dimension_score = 70
        else:
            dimension_score = 40
        
        # 2. Volume assessment (smaller volume is easier to process)
        if volume_cm3 < 100:  # Less than 100cm^3
            volume_score = 90
        elif volume_cm3 < 500:  # Less than 500cm^3
            volume_score = 75
        elif volume_cm3 < 1000:  # Less than 1000cm^3
            volume_score = 60
        else:
            volume_score = 40
        
        # 3. Surface area assessment (larger surface area may be more complex)
        if surface_area < 500:  # Less than 500mm^2
            surface_score = 90
        elif surface_area < 2000:  # Less than 2000mm^2
            surface_score = 75
        else:
            surface_score = 60
        
        # Calculate overall complexity
        complexity_score = (dimension_score + volume_score + surface_score) / 3
        
        # Determine difficulty level
        if complexity_score >= 80:
            difficulty_level = ManufacturingDifficulty.EASY.value
        elif complexity_score >= 60:
            difficulty_level = ManufacturingDifficulty.MODERATE.value
        elif complexity_score >= 40:
            difficulty_level = ManufacturingDifficulty.DIFFICULT.value
        else:
            difficulty_level = ManufacturingDifficulty.VERY_DIFFICULT.value
        
        # Estimate processing time (hours)
        base_time = 0.5  # Base time
        complexity_factor = (100 - complexity_score) / 50  # Higher complexity, longer time
        processing_time = base_time * (1 + complexity_factor)
        
        # Estimate costs (Yuan)
        material_cost_per_kg = 20.0  # Material cost 20 Yuan/kg
        machining_rate_per_hour = 150.0  # Machining rate 150 Yuan/hour
        material_cost = weight_kg * material_cost_per_kg
        machining_cost = processing_time * machining_rate_per_hour
        tool_cost = machining_cost * 0.1  # Tool cost is 10% of machining cost
        fixture_cost = 50.0  # Fixture cost
        total_cost = material_cost + machining_cost + tool_cost + fixture_cost
        
        # Generate recommendations
        recommendations = []
        if aspect_ratio > 10:
            recommendations.append("The length-width-height ratio is too large, which may cause clamping difficulties. Consider design optimization.")
        if volume_cm3 > 1000:
            recommendations.append("Large volume, long processing time, high cost")
        if complexity_score < 60:
            recommendations.append("High model complexity, recommend step-by-step processing")
        
        # Generate report
        report = {
            "file_path": file_path,
            "geometry": {
                "volume_mm3": round(volume, 2),
                "volume_cm3": round(volume_cm3, 2),
                "weight_kg": round(weight_kg, 3),
                "surface_area_mm2": round(surface_area, 2),
                "dimensions_mm": {
                    "length": round(extents[0], 2),
                    "width": round(extents[1], 2),
                    "height": round(extents[2], 2)
                },
                "aspect_ratio": round(aspect_ratio, 2)
            },
            "assessment": {
                "difficulty_level": difficulty_level,
                "complexity_score": round(complexity_score, 2),
                "dimension_score": dimension_score,
                "volume_score": volume_score,
                "surface_score": surface_score
            },
            "estimates": {
                "processing_time_hours": round(processing_time, 2),
                "material_cost": round(material_cost, 2),
                "machining_cost": round(machining_cost, 2),
                "tool_cost": round(tool_cost, 2),
                "fixture_cost": round(fixture_cost, 2),
                "total_cost": round(total_cost, 2)
            },
            "recommendations": recommendations
        }
        
        return report
    
    except Exception as e:
        return {"error": f"Error analyzing model: {str(e)}"}


def main():
    """Example usage"""
    print("3D CAM Machinability and Cost Assessment System")
    print("="*50)
    
    # Create a test model
    print("Creating test model...")
    
    # Create a cube model with hole and slot
    base_box = trimesh.creation.box(extents=[50, 40, 20])  # 50x40x20mm block
    
    # Add a hole
    hole = trimesh.creation.cylinder(radius=5, height=25)
    hole.apply_translation([0, 0, -5])  # Move below center
    
    # Add a rectangular slot
    slot = trimesh.creation.box(extents=[20, 5, 25])
    slot.apply_translation([15, 0, -5])  # Move to one side below
    
    try:
        # Perform boolean operation - subtract hole and slot from base
        if hasattr(base_box, 'difference'):
            test_model = base_box.difference([hole, slot], engine='scad')
            if test_model is None:
                test_model = base_box  # If boolean operation fails, use base model
        else:
            test_model = base_box  # If boolean not supported, use base model
    except:
        # If OpenSCAD not available, use base model
        test_model = base_box
    
    # Save test model
    test_file = "test_cam_model.stl"
    test_model.export(test_file)
    print(f"Test model saved as: {test_file}")
    
    # Analyze model
    print(f"\nAnalyzing model: {test_file}")
    report = analyze_model_machinability(test_file)
    
    if "error" in report:
        print(f"Error: {report['error']}")
        return
    
    # Output assessment results
    print(f"\n=== Model Machinability Assessment Report ===")
    print(f"File: {report['file_path']}")
    print(f"Difficulty Level: {report['assessment']['difficulty_level']}")
    print(f"Complexity Score: {report['assessment']['complexity_score']}/100")
    
    print(f"\nGeometric Properties:")
    geom = report['geometry']
    print(f"  Volume: {geom['volume_cm3']} cm^3")
    print(f"  Weight: {geom['weight_kg']} kg")
    print(f"  Dimensions: {geom['dimensions_mm']['length']} × {geom['dimensions_mm']['width']} × {geom['dimensions_mm']['height']} mm")
    print(f"  Aspect Ratio: {geom['aspect_ratio']}")
    
    print(f"\nCost Estimates:")
    est = report['estimates']
    print(f"  Estimated Processing Time: {est['processing_time_hours']} hours")
    print(f"  Material Cost: {est['material_cost']} Yuan")
    print(f"  Machining Cost: {est['machining_cost']} Yuan")
    print(f"  Tool Cost: {est['tool_cost']} Yuan")
    print(f"  Fixture Cost: {est['fixture_cost']} Yuan")
    print(f"  Total Cost: {est['total_cost']} Yuan")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    
    # Save detailed report
    report_file = "cam_assessment_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed report saved to: {report_file}")


if __name__ == "__main__":
    main()