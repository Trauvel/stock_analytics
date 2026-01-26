"""Use case для импорта портфеля из HTML отчёта Сбера."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.entities.position import Position, PositionType
from app.domain.portfolio.value_objects import Currency, Money, Quantity
from app.ingest.sber_html_parser import parse_sber_html, extract_cash_from_html


class ImportSberHTMLUseCase:
    """Use case для импорта портфеля из HTML отчёта Сбера."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелем
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(
        self,
        html_file_path: str | Path,
        merge_with_existing: bool = True,
        portfolio_id: Optional[str] = None
    ) -> Portfolio:
        """
        Выполнить импорт портфеля из HTML файла.
        
        Args:
            html_file_path: Путь к HTML файлу отчёта Сбера
            merge_with_existing: Если True, объединить с существующим портфелем
            portfolio_id: ID портфеля для импорта (если None, используется дефолтный)
            
        Returns:
            Portfolio: Импортированный/обновлённый портфель
        """
        logger.info(f"Importing portfolio from Sber HTML: {html_file_path} (portfolio_id: {portfolio_id})")
        
        # Парсим HTML
        positions_data = parse_sber_html(html_file_path)
        cash_data = extract_cash_from_html(html_file_path)
        
        # Преобразуем в доменные сущности
        currency = Currency.rub()  # По умолчанию RUB
        cash_amount = cash_data.get("RUB", 0.0) if cash_data else 0.0
        cash = Money(amount=cash_amount, currency=currency)
        
        positions = []
        for pos_data in positions_data:
            try:
                position = self._create_position_from_data(pos_data, currency)
                if position:
                    positions.append(position)
            except Exception as e:
                logger.warning(f"Error creating position from {pos_data}: {e}")
                continue
        
        # Создаём или обновляем портфель
        if merge_with_existing:
            existing_portfolio = await self._portfolio_repo.get(portfolio_id)
            
            if existing_portfolio:
                # Объединяем с существующим
                portfolio = existing_portfolio
                
                # Обновляем кеш
                if cash_amount > 0:
                    portfolio = portfolio.update_cash(cash)
                
                # Добавляем/обновляем позиции
                for new_position in positions:
                    existing_pos = portfolio.get_position(new_position.symbol)
                    if existing_pos:
                        # Если позиция уже есть, обновляем количество и цену
                        # (просто заменяем на новую)
                        portfolio = portfolio.remove_position(new_position.symbol)
                    
                    portfolio = portfolio.add_position(new_position)
            else:
                # Создаём новый портфель
                portfolio = Portfolio(
                    id=portfolio_id,  # Сохраняем ID если указан
                    name="Импортированный из Сбера",
                    currency=currency,
                    cash=cash,
                    positions=positions
                )
        else:
            # Создаём новый портфель (заменяем существующий)
            portfolio = Portfolio(
                id=portfolio_id,  # Сохраняем ID если указан
                name="Импортированный из Сбера",
                currency=currency,
                cash=cash,
                positions=positions
            )
        
        # Сохраняем
        await self._portfolio_repo.save(portfolio)
        
        logger.info(f"Imported {len(positions)} positions, cash: {cash_amount:.2f} {currency.code}")
        
        return portfolio
    
    def _create_position_from_data(
        self,
        data: Dict[str, Any],
        currency: Currency
    ) -> Optional[Position]:
        """Создать Position из данных парсера."""
        try:
            symbol = data.get("symbol")
            if not symbol:
                return None
            
            quantity_value = data.get("quantity", 0)
            if quantity_value <= 0:
                return None
            
            price_value = data.get("price") or data.get("avg_price")
            
            position_type_str = data.get("type", "stock")
            try:
                position_type = PositionType(position_type_str)
            except ValueError:
                position_type = PositionType.STOCK
            
            # Формируем заметки: для облигаций добавляем название, для остальных - ISIN
            if position_type == PositionType.BOND:
                notes_parts = [data.get("name", "")]
                if data.get("isin"):
                    notes_parts.append(f"ISIN: {data.get('isin')}")
                notes = " | ".join(notes_parts) if notes_parts[0] else f"Импортировано из Сбера (ISIN: {data.get('isin', 'N/A')})"
            else:
                notes = f"Импортировано из Сбера (ISIN: {data.get('isin', 'N/A')})"
            
            return Position(
                symbol=symbol,
                quantity=Quantity.from_int(quantity_value),
                avg_price=Money.from_float(price_value, currency.code) if price_value else None,
                position_type=position_type,
                market=data.get("market", "moex"),
                name=data.get("name"),
                notes=notes
            )
        except Exception as e:
            logger.error(f"Error creating position: {e}")
            return None
