from typing import Union, Optional, Tuple

def convert_dimensions_to_mm(
    width: Union[int, float, str], 
    height: Union[int, float, str], 
    depth: Union[int, float, str], 
    dimension_unit: str
) -> Tuple[float, float, float]:
    try:
        w = float(width) if width else 0
        h = float(height) if height else 0
        d = float(depth) if depth else 0
        
        if dimension_unit == 'cm':
            return w * 10, h * 10, d * 10
        elif dimension_unit == 'in':
            return w * 25.4, h * 25.4, d * 25.4
        elif dimension_unit == 'mm':
            return w, h, d
        else:
            return w, h, d
            
    except (ValueError, TypeError):
        return 0, 0, 0

def calculate_volume_liters(
    width: Union[int, float, str], 
    height: Union[int, float, str], 
    depth: Union[int, float, str], 
    dimension_unit: str
) -> Optional[float]:
    try:
        w_mm, h_mm, d_mm = convert_dimensions_to_mm(width, height, depth, dimension_unit)
        
        if w_mm and h_mm and d_mm:
            volume_mm3 = w_mm * h_mm * d_mm
            return volume_mm3 / 1_000_000
        return None
    except (ValueError, TypeError):
        return None

def convert_weight_to_kg(
    weight: Union[int, float, str], 
    weight_unit: str
) -> Optional[float]:
    try:
        w = float(weight) if weight else 0
        
        if weight_unit == 'g':
            return w / 1000
        elif weight_unit == 'kg':
            return w
        elif weight_unit == 'lb':
            return w * 0.453592
        elif weight_unit == 'oz':
            return w * 0.0283495
        else:
            return w
    except (ValueError, TypeError):
        return None