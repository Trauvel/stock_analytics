"""Use case для получения списка всех тикеров (universe + portfolio)."""

from typing import List
from pathlib import Path
import json
from loguru import logger

from app.config.loader import get_config


class GetUniverseUseCase:
    """Use case для получения списка всех тикеров для анализа."""
    
    def __init__(self):
        """Инициализация use case."""
        self.config = get_config()
    
    def execute(self, include_portfolio: bool = True) -> List[str]:
        """
        Выполнить use case - получить список всех тикеров.
        
        Args:
            include_portfolio: Включить ли тикеры из портфеля
            
        Returns:
            List[str]: Список всех тикеров (universe + portfolio)
        """
        # Получаем тикеры из конфигурации (universe)
        universe_tickers = [
            ticker_config.symbol 
            for ticker_config in self.config.universe
        ]
        
        logger.debug(f"Universe tickers: {len(universe_tickers)}")
        
        if not include_portfolio:
            return universe_tickers
        
        # Загружаем тикеры из портфелей
        portfolio_tickers = self._load_portfolio_tickers()
        logger.debug(f"Portfolio tickers: {len(portfolio_tickers)}")
        
        # Объединяем и убираем дубликаты
        all_tickers = list(set(universe_tickers + portfolio_tickers))
        logger.info(f"Total tickers (universe + portfolio): {len(all_tickers)}")
        
        return all_tickers
    
    def _load_portfolio_tickers(self) -> List[str]:
        """
        Загрузить тикеры из всех портфелей пользователя.
        
        Returns:
            List[str]: Список тикеров из всех портфелей
        """
        try:
            project_root = Path(__file__).parent.parent.parent.parent
            portfolios_dir = project_root / "data" / "portfolios"
            old_portfolio_path = project_root / "data" / "portfolio.json"
            
            tickers = []
            seen = set()
            
            # Загружаем из нового формата (несколько портфелей)
            if portfolios_dir.exists():
                index_path = portfolios_dir / "index.json"
                if index_path.exists():
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index = json.load(f)
                    
                    for portfolio_id in index.get('ids', []):
                        portfolio_file = portfolios_dir / f"{portfolio_id}.json"
                        if portfolio_file.exists():
                            try:
                                with open(portfolio_file, 'r', encoding='utf-8') as f:
                                    portfolio = json.load(f)
                                
                                for position in portfolio.get('positions', []):
                                    symbol = position.get('symbol')
                                    if symbol and symbol not in seen:
                                        clean_symbol = symbol.rstrip('@')
                                        tickers.append(clean_symbol)
                                        seen.add(symbol)
                            except Exception as e:
                                logger.warning(f"Error loading portfolio {portfolio_id}: {e}")
                                continue
            
            # Загружаем из старого формата (если есть)
            if old_portfolio_path.exists():
                try:
                    with open(old_portfolio_path, 'r', encoding='utf-8') as f:
                        portfolio = json.load(f)
                    
                    for position in portfolio.get('positions', []):
                        symbol = position.get('symbol')
                        if symbol and symbol not in seen:
                            clean_symbol = symbol.rstrip('@')
                            tickers.append(clean_symbol)
                            seen.add(symbol)
                except Exception as e:
                    logger.warning(f"Error loading old portfolio: {e}")
            
            return tickers
            
        except Exception as e:
            logger.warning(f"Failed to load portfolio tickers: {e}")
            return []
