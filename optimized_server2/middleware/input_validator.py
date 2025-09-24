"""
Валидатор входных данных для защиты от XSS и SQL инъекций
"""
import re
import html
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
# import email_validator  # Временно отключено


class InputValidator:
    """Валидатор входных данных"""
    
    def __init__(self):
        # Паттерны для валидации
        self.phone_pattern = re.compile(r'^\+[1-9]\d{1,14}$')
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.password_pattern = re.compile(r'^.{8,}$')
        self.box_id_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        
        # Максимальные длины полей
        self.max_lengths = {
            'phone_e164': 20,
            'email': 255,
            'fio': 255,
            'box_id': 50,
            'iccid': 50,
            'password': 128
        }
    
    def validate_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидирует данные пользователя"""
        errors = []
        validated_data = {}
        
        # Валидация телефона
        if 'phone_e164' in data:
            phone = self.sanitize_string(data['phone_e164'])
            if not self.phone_pattern.match(phone):
                errors.append('Неверный формат номера телефона')
            else:
                validated_data['phone_e164'] = phone
        
        # Валидация email
        if 'email' in data:
            email = self.sanitize_string(data['email'])
            if not self.email_pattern.match(email):
                errors.append('Неверный формат email')
            else:
                validated_data['email'] = email
        
        # Валидация ФИО
        if 'fio' in data:
            fio = self.sanitize_string(data['fio'])
            if len(fio) > self.max_lengths['fio']:
                errors.append('ФИО слишком длинное')
            else:
                validated_data['fio'] = fio
        
        # Валидация пароля
        if 'password' in data:
            password = data['password']
            if not self.password_pattern.match(password):
                errors.append('Пароль должен содержать минимум 8 символов')
            else:
                validated_data['password'] = password
        
        # Валидация статуса
        if 'status' in data:
            status = self.sanitize_string(data['status'])
            if status not in ['pending', 'active', 'blocked']:
                errors.append('Недопустимый статус пользователя')
            else:
                validated_data['status'] = status
        
        return {
            'validated_data': validated_data,
            'errors': errors
        }
    
    def validate_station_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидирует данные станции"""
        errors = []
        validated_data = {}
        
        # Валидация box_id
        if 'box_id' in data:
            box_id = self.sanitize_string(data['box_id'])
            if not self.box_id_pattern.match(box_id):
                errors.append('Неверный формат box_id')
            else:
                validated_data['box_id'] = box_id
        
        # Валидация ICCID
        if 'iccid' in data:
            iccid = self.sanitize_string(data['iccid'])
            if len(iccid) > self.max_lengths['iccid']:
                errors.append('ICCID слишком длинный')
            else:
                validated_data['iccid'] = iccid
        
        # Валидация slots_declared
        if 'slots_declared' in data:
            try:
                slots = int(data['slots_declared'])
                if slots < 0 or slots > 100:
                    errors.append('Количество слотов должно быть от 0 до 100')
                else:
                    validated_data['slots_declared'] = slots
            except (ValueError, TypeError):
                errors.append('Неверный формат количества слотов')
        
        # Валидация remain_num
        if 'remain_num' in data:
            try:
                remain = int(data['remain_num'])
                if remain < 0:
                    errors.append('Количество оставшихся не может быть отрицательным')
                else:
                    validated_data['remain_num'] = remain
            except (ValueError, TypeError):
                errors.append('Неверный формат количества оставшихся')
        
        # Валидация статуса
        if 'status' in data:
            status = self.sanitize_string(data['status'])
            if status not in ['active', 'inactive', 'pending']:
                errors.append('Недопустимый статус станции')
            else:
                validated_data['status'] = status
        
        return {
            'validated_data': validated_data,
            'errors': errors
        }
    
    def validate_powerbank_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидирует данные повербанка"""
        errors = []
        validated_data = {}
        
        # Валидация серийного номера
        if 'serial_number' in data:
            serial = self.sanitize_string(data['serial_number'])
            if len(serial) > 100:
                errors.append('Серийный номер слишком длинный')
            else:
                validated_data['serial_number'] = serial
        
        # Валидация уровня заряда
        if 'battery_level' in data:
            try:
                level = int(data['battery_level'])
                if level < 0 or level > 100:
                    errors.append('Уровень заряда должен быть от 0 до 100')
                else:
                    validated_data['battery_level'] = level
            except (ValueError, TypeError):
                errors.append('Неверный формат уровня заряда')
        
        # Валидация статуса
        if 'status' in data:
            status = self.sanitize_string(data['status'])
            if status not in ['available', 'borrowed', 'charging', 'maintenance']:
                errors.append('Недопустимый статус повербанка')
            else:
                validated_data['status'] = status
        
        return {
            'validated_data': validated_data,
            'errors': errors
        }
    
    def sanitize_string(self, value: Any) -> str:
        """Очищает строку от потенциально опасных символов"""
        if value is None:
            return ""
        
        # Преобразуем в строку
        str_value = str(value)
        
        # Удаляем HTML теги
        str_value = html.escape(str_value, quote=True)
        
        # Удаляем потенциально опасные символы
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
        for char in dangerous_chars:
            str_value = str_value.replace(char, '')
        
        # Удаляем лишние пробелы
        str_value = ' '.join(str_value.split())
        
        return str_value.strip()
    
    def validate_json_data(self, data: Any) -> Dict[str, Any]:
        """Валидирует JSON данные"""
        errors = []
        
        if isinstance(data, dict):
            # Проверяем глубину вложенности
            if self._get_dict_depth(data) > 10:
                errors.append('Слишком глубокая вложенность данных')
            
            # Проверяем размер
            json_str = json.dumps(data)
            if len(json_str) > 1024 * 1024:  # 1MB
                errors.append('Слишком большой размер данных')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def _get_dict_depth(self, d: Dict, depth: int = 0) -> int:
        """Вычисляет глубину вложенности словаря"""
        if not isinstance(d, dict):
            return depth
        
        max_depth = depth
        for value in d.values():
            if isinstance(value, dict):
                current_depth = self._get_dict_depth(value, depth + 1)
                max_depth = max(max_depth, current_depth)
        
        return max_depth
    
    def validate_query_params(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Валидирует параметры запроса"""
        errors = []
        validated_params = {}
        
        for key, value in params.items():
            # Очищаем ключ
            clean_key = self.sanitize_string(key)
            
            # Очищаем значение
            clean_value = self.sanitize_string(value)
            
            # Проверяем длину
            if len(clean_key) > 100:
                errors.append(f'Ключ параметра {key} слишком длинный')
                continue
            
            if len(clean_value) > 1000:
                errors.append(f'Значение параметра {key} слишком длинное')
                continue
            
            validated_params[clean_key] = clean_value
        
        return {
            'validated_params': validated_params,
            'errors': errors
        }


def create_input_validator():
    """Создает экземпляр валидатора"""
    return InputValidator()
