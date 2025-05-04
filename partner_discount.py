"""
partner_discount.py — модуль расчета скидок для партнеров
---------------------------------------------------------

Функции:
* Расчет скидки в зависимости от объема закупок
* Получение общего количества продукции партнера
"""
from sqlalchemy.orm import Session
from DB_prepare import PartnerProduct


def get_partner_total_qty(session: Session, partner_id: int) -> int:
    """
    Получение общего количества продукции, закупленной партнером.
    
    Аргументы:
        session: Сессия SQLAlchemy
        partner_id: Идентификатор партнера
        
    Возвращает:
        Целое число - общее количество продукции
    """
    result = (
        session.query(PartnerProduct)
        .filter(PartnerProduct.partner_id == partner_id)
        .all()
    )
    
    total_qty = sum(pp.quantity or 0 for pp in result)
    return total_qty


def calculate_discount(total_qty: int) -> int:
    """
    Расчет скидки в зависимости от объема закупок.
    
    Аргументы:
        total_qty: Общее количество закупленной продукции
        
    Возвращает:
        Целое число - процент скидки
    """
    if total_qty < 10_000:
        return 0
    elif total_qty < 50_000:
        return 5
    elif total_qty < 100_000:
        return 10
    else:
        return 15