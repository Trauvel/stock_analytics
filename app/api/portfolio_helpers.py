"""Вспомогательные функции для преобразования между Pydantic и Domain моделями."""

from app.models import Portfolio as PydanticPortfolio, Position as PydanticPosition
from app.domain.portfolio.entities.portfolio import Portfolio as DomainPortfolio
from app.domain.portfolio.entities.position import Position as DomainPosition
from app.domain.portfolio.value_objects import Currency, Money, Quantity
from app.domain.portfolio.entities.position import PositionType


def convert_pydantic_to_domain_portfolio(pydantic_portfolio: PydanticPortfolio) -> DomainPortfolio:
    """
    Преобразовать Pydantic Portfolio в доменную сущность.
    
    Args:
        pydantic_portfolio: Pydantic модель портфеля
        
    Returns:
        DomainPortfolio: Доменная сущность портфеля
    """
    currency = Currency.from_string(pydantic_portfolio.currency)
    cash = Money.from_float(pydantic_portfolio.cash, currency.code)
    
    positions = []
    for pydantic_pos in pydantic_portfolio.positions:
        domain_pos = _convert_pydantic_to_domain_position(pydantic_pos, currency)
        positions.append(domain_pos)
    
    return DomainPortfolio(
        id=pydantic_portfolio.id,
        name=pydantic_portfolio.name,
        currency=currency,
        cash=cash,
        positions=positions,
        created_at=pydantic_portfolio.created_at,
        updated_at=pydantic_portfolio.updated_at
    )


def _convert_pydantic_to_domain_position(
    pydantic_pos: PydanticPosition,
    currency: Currency
) -> DomainPosition:
    """
    Преобразовать Pydantic Position в доменную сущность.
    
    Args:
        pydantic_pos: Pydantic модель позиции
        currency: Валюта портфеля
        
    Returns:
        DomainPosition: Доменная сущность позиции
    """
    quantity_value = pydantic_pos.quantity or pydantic_pos.qty or 0
    quantity = Quantity.from_int(quantity_value)
    
    avg_price = None
    if pydantic_pos.avg_price:
        avg_price = Money.from_float(pydantic_pos.avg_price, currency.code)
    
    current_value = None
    if pydantic_pos.current_value:
        current_value = Money.from_float(pydantic_pos.current_value, currency.code)
    
    return DomainPosition(
        symbol=pydantic_pos.symbol,
        quantity=quantity,
        avg_price=avg_price,
        position_type=PositionType(pydantic_pos.type.value),
        market=pydantic_pos.market,
        notes=pydantic_pos.notes,
        name=pydantic_pos.name,
        current_value=current_value
    )
