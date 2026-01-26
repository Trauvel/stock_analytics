"""Парсер HTML отчётов Сбера для импорта в портфель."""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from html.parser import HTMLParser
from loguru import logger


class SberHTMLParser(HTMLParser):
    """Парсер HTML отчётов Сбера."""
    
    def __init__(self):
        """Инициализация парсера."""
        super().__init__()
        self.positions: List[Dict[str, Any]] = []
        self.current_row: List[str] = []
        self.in_table = False
        self.in_position_row = False
        self.header_found = False
        self.current_section = None  # "Фондовый рынок", "Срочный рынок" и т.д.
        # Справочник: название -> код
        self.reference_book: Dict[str, str] = {}
        self.in_reference_book = False
        self.reference_header_found = False
        
    def handle_starttag(self, tag, attrs):
        """Обработка открывающих тегов."""
        if tag == 'tr':
            self.current_row = []
            self.in_position_row = False
        elif tag == 'td':
            self.current_cell = ""
    
    def handle_endtag(self, tag):
        """Обработка закрывающих тегов."""
        if tag == 'td':
            if hasattr(self, 'current_cell'):
                # Очищаем от пробелов и форматируем
                cell_text = self.current_cell.strip()
                # Убираем пробелы в числах (например "7 355.60" -> "7355.60")
                cell_text = cell_text.replace(' ', '')
                self.current_row.append(cell_text)
                delattr(self, 'current_cell')
        elif tag == 'tr':
            self._process_row()
            self.current_row = []
    
    def handle_data(self, data):
        """Обработка текстовых данных."""
        if hasattr(self, 'current_cell'):
            self.current_cell += data
        else:
            self.current_cell = data
    
    def _process_row(self):
        """Обработка строки таблицы."""
        if not self.current_row:
            return
        
        # Ищем заголовок таблицы позиций
        row_text = ' '.join(self.current_row)
        
        # Проверяем, находимся ли мы в справочнике (первый проход)
        if self.in_reference_book:
            if 'Наименование' in row_text and 'Код' in row_text and 'ISIN' in row_text:
                self.reference_header_found = True
                return
            
            if self.reference_header_found:
                # Пропускаем строку с номерами
                if all(cell.isdigit() or cell == '' for cell in self.current_row[:6]):
                    return
                
                # Обрабатываем строку справочника
                if len(self.current_row) >= 3:
                    name = self.current_row[0].strip()
                    code = self.current_row[1].strip()
                    if name and code:
                        # Сохраняем и с пробелами, и без (для надёжности)
                        self.reference_book[name] = code
                        self.reference_book[name.replace(' ', '')] = code
                return
            # Если не нашли заголовок справочника, пропускаем строку
            return
        
        # Если справочник уже заполнен (второй проход), пропускаем его
        if self.reference_book and 'Справочник Ценных Бумаг' in row_text:
            return
        
        # Проверяем, является ли это заголовком таблицы позиций
        if 'Наименование' in row_text and 'Количество' in row_text and 'ISIN' in row_text:
            self.header_found = True
            return
        
        # Проверяем, является ли это разделом (например "Площадка: Фондовый рынок")
        if 'Площадка:' in row_text:
            # Извлекаем название площадки
            match = re.search(r'Площадка:\s*([^<]+)', row_text)
            if match:
                self.current_section = match.group(1).strip()
            return
        
        # Пропускаем строки с номерами столбцов
        if all(cell.isdigit() or cell == '' for cell in self.current_row[:5]):
            return
        
        # Пропускаем строки-итого
        if 'Итого' in row_text or 'summary' in ' '.join(self.current_row).lower():
            return
        
        # Если заголовок найден и есть данные, обрабатываем позицию
        if self.header_found and not self.in_reference_book and len(self.current_row) >= 11:
            position = self._extract_position()
            if position:
                self.positions.append(position)
    
    def _extract_position(self) -> Optional[Dict[str, Any]]:
        """
        Извлечь позицию из строки таблицы.
        
        Структура столбцов (из анализа HTML):
        0: Наименование
        1: ISIN
        2: Валюта
        3: Количество (начало периода)
        4: Номинал (начало)
        5: Рыночная цена (начало)
        6: Рыночная стоимость (начало)
        7: НКД (начало)
        8: Количество (конец периода) - используем это
        9: Номинал (конец)
        10: Рыночная цена (конец) - используем это
        11: Рыночная стоимость (конец)
        12: НКД (конец)
        """
        try:
            name = self.current_row[0].strip() if len(self.current_row) > 0 else ""
            if not name or name == "":
                return None
            
            # Пропускаем строки без позиций (количество = 0)
            quantity_str = self.current_row[8] if len(self.current_row) > 8 else "0"
            try:
                quantity = float(quantity_str.replace(',', '.'))
                if quantity == 0:
                    return None
            except (ValueError, AttributeError):
                return None
            
            # ISIN
            isin = self.current_row[1].strip() if len(self.current_row) > 1 else None
            
            # Определяем тип инструмента по названию
            position_type = self._detect_position_type(name)
            
            # Используем справочник для определения кода (тикера)
            # Ищем точное совпадение или совпадение без пробелов
            name_normalized = name.replace(' ', '')
            symbol = None
            
            # Сначала ищем точное совпадение
            if name in self.reference_book:
                symbol = self.reference_book[name]
            # Затем ищем без пробелов
            elif name_normalized in self.reference_book:
                symbol = self.reference_book[name_normalized]
            else:
                # Ищем частичное совпадение (название без пробелов в ключах)
                for ref_name, ref_code in self.reference_book.items():
                    ref_name_normalized = ref_name.replace(' ', '')
                    if ref_name_normalized == name_normalized:
                        symbol = ref_code
                        break
            
            # Если не нашли в справочнике, используем старую логику
            if not symbol:
                if position_type == "bond" and isin:
                    # Для облигаций используем ISIN
                    symbol = isin
                    logger.info(f"Bond {name}: using ISIN {isin} as symbol (not found in reference book)")
                else:
                    # Для остальных извлекаем из названия
                    symbol = self._extract_symbol(name)
                    if not symbol:
                        logger.warning(f"Could not find symbol for {name} in reference book or by extraction")
                        return None
            else:
                logger.debug(f"Found symbol for {name}: {symbol} (from reference book)")
            
            # Валюта
            currency = self.current_row[2] if len(self.current_row) > 2 else "RUB"
            
            # Рыночная цена (конец периода)
            price_str = self.current_row[10] if len(self.current_row) > 10 else ""
            try:
                price = float(price_str.replace(',', '.')) if price_str else None
            except (ValueError, AttributeError):
                price = None
            
            return {
                "symbol": symbol,
                "name": name,
                "quantity": int(quantity),
                "currency": currency,
                "price": price,
                "avg_price": price,  # Используем текущую цену как среднюю
                "type": position_type,
                "market": "moex",
                "isin": isin
            }
        except Exception as e:
            logger.warning(f"Error extracting position from row: {e}, row: {self.current_row}")
            return None
    
    def _extract_symbol(self, name: str) -> Optional[str]:
        """
        Извлечь тикер из наименования.
        
        Примеры:
        - "Сбербанк" -> "SBER"
        - "МосБиржа" -> "MOEX"
        - "SBGB ETF" -> "SBGB"
        - "Абрау2P-01" -> "Абрау2P-01" (облигация)
        """
        # Убираем лишние пробелы
        name = name.strip()
        
        # Пропускаем даты и другие служебные строки
        if re.match(r'^\d{2}\.\d{2}\.\d{4}', name):
            return None
        
        # Маппинг известных названий в тикеры
        name_to_symbol = {
            "Сбербанк": "SBER",
            "МосБиржа": "MOEX",
            "СевСт-ао": "CHMF",
            "Спб биржа ао_": "SPBE",
            "ГМКНорНик": "GMKN",
            "iОзонФарм": "OZON",
        }
        
        if name in name_to_symbol:
            return name_to_symbol[name]
        
        # Если название содержит "ETF", берём первую часть
        if "ETF" in name or "БПИФ" in name:
            parts = name.split()
            if parts:
                symbol = parts[0].upper()
                # Убираем "ETF" если есть
                symbol = symbol.replace('ETF', '').strip()
                return symbol if symbol else None
        
        # Для облигаций и других инструментов с кириллицей используем название как есть
        # (но только если оно короткое и не содержит пробелов)
        if re.match(r'^[А-Яа-яA-Za-z0-9\-_]+$', name) and len(name) <= 20:
            # Если начинается с кириллицы - это облигация или специальный инструмент
            if re.match(r'^[А-Яа-я]', name):
                return name
            # Если только латиница и цифры - это тикер
            if re.match(r'^[A-Za-z0-9\-_]+$', name):
                return name.upper()
        
        # Пытаемся найти тикер в скобках или после дефиса
        match = re.search(r'\(([A-Z0-9]+)\)|([A-Z]{2,6})', name)
        if match:
            return match.group(1) or match.group(2)
        
        # Если ничего не подошло, возвращаем None
        logger.warning(f"Could not extract symbol from name: {name}")
        return None
    
    def _detect_position_type(self, name: str) -> str:
        """Определить тип инструмента по названию."""
        name_lower = name.lower()
        name_clean = name.replace(' ', '').replace('-', '')  # Убираем пробелы и дефисы для проверки паттернов
        
        if "etf" in name_lower or "бпиф" in name_lower:
            return "etf"
        elif any(keyword in name_lower for keyword in ["облигация", "bond", "p-", "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"]):
            return "bond"
        # Проверяем паттерны облигаций:
        # - Название с цифрой и буквой/цифрой в конце (например "ЭЛРЕШ1Р2", "ОилРес1P2", "Абрау2P-01")
        # - Паттерн: буквы + цифра + буква(Р/P) + цифра
        elif re.match(r'^[А-Яа-яA-Za-z]+[0-9]+[РPрp][0-9]+$', name_clean, re.IGNORECASE):
            return "bond"
        # Паттерн: буквы + цифра + буквы + цифра (например "Росинтер02")
        elif re.match(r'^[А-Яа-яA-Za-z]+[0-9]+[А-Яа-яA-Za-z]*[0-9]+$', name_clean):
            # Но не акции типа "СевСт-ао" (одна цифра в конце)
            if not re.match(r'^[А-Яа-яA-Za-z]+[0-9]*[А-Яа-яA-Za-z]+$', name_clean):
                return "bond"
        elif any(keyword in name_lower for keyword in ["валюта", "currency", "usd", "eur"]):
            return "currency"
        else:
            return "stock"


def parse_sber_html(file_path: str | Path) -> List[Dict[str, Any]]:
    """
    Парсить HTML отчёт Сбера и извлечь позиции.
    
    Args:
        file_path: Путь к HTML файлу
        
    Returns:
        List[Dict]: Список позиций
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    logger.info(f"Parsing Sber HTML report: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Первый проход: собираем справочник
    parser_ref = SberHTMLParser()
    parser_ref.in_reference_book = True  # Пропускаем позиции, только справочник
    parser_ref.feed(html_content)
    reference_book = parser_ref.reference_book
    
    logger.info(f"Reference book contains {len(reference_book)} entries")
    
    # Второй проход: обрабатываем позиции с использованием справочника
    parser = SberHTMLParser()
    parser.reference_book = reference_book
    parser.feed(html_content)
    
    logger.info(f"Extracted {len(parser.positions)} positions from HTML")
    
    return parser.positions


def extract_cash_from_html(file_path: str | Path) -> Optional[Dict[str, float]]:
    """
    Извлечь информацию о денежных средствах из HTML отчёта.
    
    Args:
        file_path: Путь к HTML файлу
        
    Returns:
        Dict: {"RUB": amount, ...} или None
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Ищем "Исходящий остаток" в разделе денежных средств
    # Паттерн ищет строку с "Исходящий остаток" и числом после неё
    # Формат: <td>Исходящий остаток</td><td>8 735.44</td><td>RUB</td>
    cash_pattern = r'Исходящий остаток[^<]*</td>\s*<td[^>]*>([\d\s,\.]+)</td>\s*<td[^>]*>RUB</td>'
    match = re.search(cash_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    if match:
        cash_str = match.group(1).strip().replace(' ', '').replace(',', '.')
        try:
            cash_amount = float(cash_str)
            logger.info(f"Extracted cash: {cash_amount} RUB")
            return {"RUB": cash_amount}
        except ValueError:
            logger.warning(f"Could not parse cash amount: {cash_str}")
    
    # Альтернативный паттерн - ищем в таблице денежных средств (более гибкий)
    cash_pattern2 = r'<td[^>]*class="l"[^>]*>Исходящий остаток</td>\s*<td[^>]*class="ri"[^>]*>([\d\s,\.]+)</td>\s*<td[^>]*class="c"[^>]*>RUB</td>'
    match2 = re.search(cash_pattern2, html_content, re.DOTALL | re.IGNORECASE)
    
    if match2:
        cash_str = match2.group(1).strip().replace(' ', '').replace(',', '.')
        try:
            cash_amount = float(cash_str)
            logger.info(f"Extracted cash (pattern 2): {cash_amount} RUB")
            return {"RUB": cash_amount}
        except ValueError:
            pass
    
    logger.warning("Could not extract cash from HTML")
    return None
