"""Реализация репозитория портфеля через файловое хранилище."""

import uuid
from pathlib import Path
from typing import Optional, List
from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from app.store.io import save_json, load_json, StorageError


class PortfolioRepositoryImpl(PortfolioRepository):
    """Реализация репозитория через файловое хранилище с поддержкой нескольких портфелей."""
    
    def __init__(self, portfolios_dir: str = "data/portfolios"):
        """
        Инициализация репозитория.
        
        Args:
            portfolios_dir: Директория для хранения портфелей
        """
        self._portfolios_dir = Path(portfolios_dir)
        self._index_file = self._portfolios_dir / "index.json"
        self._default_id = "default"  # ID дефолтного портфеля
        
        # Создаём директорию, если её нет
        self._portfolios_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_portfolio_file(self, portfolio_id: str) -> Path:
        """Получить путь к файлу портфеля."""
        return self._portfolios_dir / f"{portfolio_id}.json"
    
    def _load_index(self) -> dict:
        """Загрузить индекс портфелей."""
        if not self._index_file.exists():
            return {}
        
        try:
            return load_json(self._index_file) or {}
        except Exception as e:
            logger.warning(f"Error loading portfolio index: {e}")
            return {}
    
    def _save_index(self, index: dict) -> None:
        """Сохранить индекс портфелей."""
        try:
            save_json(self._index_file, index)
        except Exception as e:
            logger.error(f"Error saving portfolio index: {e}")
            raise
    
    def _generate_id(self) -> str:
        """Сгенерировать уникальный ID для портфеля."""
        return str(uuid.uuid4())
    
    async def get(self, portfolio_id: Optional[str] = None) -> Optional[Portfolio]:
        """
        Получить портфель по ID (или дефолтный, если ID не указан).
        
        Args:
            portfolio_id: ID портфеля (если None, возвращает дефолтный)
        
        Returns:
            Portfolio или None если не найден
        """
        if portfolio_id is None:
            portfolio_id = self._default_id
        
        return await self.get_by_id(portfolio_id)
    
    async def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        """
        Получить портфель по ID.
        
        Args:
            portfolio_id: ID портфеля
        
        Returns:
            Portfolio или None если не найден
        """
        try:
            portfolio_file = self._get_portfolio_file(portfolio_id)
            
            if not portfolio_file.exists():
                logger.debug(f"Portfolio {portfolio_id} not found at {portfolio_file}")
                return None
            
            portfolio_data = load_json(portfolio_file)
            
            if portfolio_data is None:
                return None
            
            # Преобразуем в доменную сущность
            portfolio = Portfolio.from_dict(portfolio_data)
            
            # Убеждаемся, что ID установлен
            if not portfolio.id:
                portfolio.id = portfolio_id
            
            logger.info(f"Loaded portfolio {portfolio_id}: {len(portfolio.positions)} positions")
            return portfolio
            
        except StorageError as e:
            logger.error(f"Storage error loading portfolio {portfolio_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading portfolio {portfolio_id}: {e}")
            return None
    
    async def list_all(self) -> List[Portfolio]:
        """
        Получить список всех портфелей.
        
        Returns:
            List[Portfolio]: Список всех портфелей
        """
        portfolios = []
        
        try:
            index = self._load_index()
            
            # Если индекс пуст, проверяем старый формат (data/portfolio.json)
            if not index:
                old_file = Path("data/portfolio.json")
                if old_file.exists():
                    logger.info("Found old portfolio format, migrating...")
                    try:
                        old_data = load_json(old_file)
                        if old_data:
                            # Создаём дефолтный портфель из старого файла
                            if not old_data.get("id"):
                                old_data["id"] = self._default_id
                            portfolio = Portfolio.from_dict(old_data)
                            await self.save(portfolio)
                            portfolios.append(portfolio)
                            logger.info("Migrated old portfolio to new format")
                    except Exception as e:
                        logger.warning(f"Error migrating old portfolio: {e}")
            
            # Загружаем все портфели из индекса
            for portfolio_id in index.get("ids", []):
                portfolio = await self.get_by_id(portfolio_id)
                if portfolio:
                    portfolios.append(portfolio)
            
            logger.info(f"Listed {len(portfolios)} portfolios")
            return portfolios
            
        except Exception as e:
            logger.error(f"Error listing portfolios: {e}")
            return []
    
    async def save(self, portfolio: Portfolio) -> Portfolio:
        """
        Сохранить портфель.
        
        Args:
            portfolio: Портфель для сохранения
            
        Returns:
            Сохранённый портфель с обновлённым ID (если был создан новый)
        """
        try:
            # Если у портфеля нет ID, генерируем новый
            if not portfolio.id:
                portfolio.id = self._generate_id()
                logger.info(f"Generated new portfolio ID: {portfolio.id}")
            
            portfolio_id = portfolio.id
            
            # Преобразуем в словарь
            portfolio_dict = portfolio.to_dict()
            
            # Сохраняем портфель
            portfolio_file = self._get_portfolio_file(portfolio_id)
            save_json(portfolio_file, portfolio_dict)
            
            # Обновляем индекс
            index = self._load_index()
            if "ids" not in index:
                index["ids"] = []
            
            if portfolio_id not in index["ids"]:
                index["ids"].append(portfolio_id)
                index[portfolio_id] = {
                    "name": portfolio.name or f"Портфель {portfolio_id[:8]}",
                    "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
                    "updated_at": portfolio.updated_at.isoformat() if portfolio.updated_at else None
                }
            else:
                # Обновляем метаданные
                index[portfolio_id]["name"] = portfolio.name or f"Портфель {portfolio_id[:8]}"
                index[portfolio_id]["updated_at"] = portfolio.updated_at.isoformat() if portfolio.updated_at else None
            
            self._save_index(index)
            
            logger.info(f"Saved portfolio {portfolio_id}: {len(portfolio.positions)} positions")
            
            return portfolio
            
        except StorageError as e:
            logger.error(f"Storage error saving portfolio: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
            raise
    
    async def delete(self, portfolio_id: Optional[str] = None) -> None:
        """
        Удалить портфель.
        
        Args:
            portfolio_id: ID портфеля (если None, удаляет дефолтный)
        """
        if portfolio_id is None:
            portfolio_id = self._default_id
        
        await self.delete_by_id(portfolio_id)
    
    async def delete_by_id(self, portfolio_id: str) -> None:
        """
        Удалить портфель по ID.
        
        Args:
            portfolio_id: ID портфеля
        """
        try:
            portfolio_file = self._get_portfolio_file(portfolio_id)
            
            if portfolio_file.exists():
                portfolio_file.unlink()
                logger.info(f"Deleted portfolio file: {portfolio_file}")
            
            # Обновляем индекс
            index = self._load_index()
            if "ids" in index and portfolio_id in index["ids"]:
                index["ids"].remove(portfolio_id)
                if portfolio_id in index:
                    del index[portfolio_id]
                self._save_index(index)
                logger.info(f"Removed portfolio {portfolio_id} from index")
            else:
                logger.warning(f"Portfolio {portfolio_id} not found in index")
                
        except Exception as e:
            logger.error(f"Error deleting portfolio {portfolio_id}: {e}")
            raise
