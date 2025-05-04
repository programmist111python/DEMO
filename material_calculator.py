"""
material_calculator.py — модуль расчета материалов
-------------------------------------------------

Функции:
* Расчет количества материала для производства продукции с учетом брака
"""
import math
from sqlalchemy.orm import Session
from DB_prepare import ENGINE, ProductType, MaterialType


def calculate_material_quantity(
    product_type_id: int,
    material_type_id: int,
    quantity: int,
    param1: float,
    param2: float
) -> int:
    """
    Расчет количества материала, необходимого для производства продукции.
    
    Аргументы:
        product_type_id: Идентификатор типа продукции
        material_type_id: Идентификатор типа материала
        quantity: Количество продукции
        param1: Параметр продукции 1 (вещественное положительное число)
        param2: Параметр продукции 2 (вещественное положительное число)
        
    Возвращает:
        Целое число - количество необходимого материала с учетом брака
        или -1 в случае ошибки
    """
    # Проверяем входные данные
    if quantity <= 0 or param1 <= 0 or param2 <= 0:
        return -1
    
    try:
        with Session(ENGINE) as session:
            # Получаем тип продукции
            product_type = session.query(ProductType).get(product_type_id)
            if not product_type:
                return -1
            
            # Получаем тип материала
            material_type = session.query(MaterialType).get(material_type_id)
            if not material_type:
                return -1
            
            # Коэффициент типа продукции
            coefficient = float(product_type.coefficient)
            
            # Процент брака материала
            defect_percentage = float(material_type.defect_percentage)
            
            # Расчет количества материала на единицу продукции
            material_per_unit = param1 * param2 * coefficient
            
            # Общее количество материала без учета брака
            total_material = material_per_unit * quantity
            
            # Учитываем возможный брак (увеличиваем количество)
            total_with_defect = total_material * (1 + defect_percentage / 100)
            
            # Округляем до целого числа в большую сторону
            return math.ceil(total_with_defect)
            
    except Exception:
        return -1