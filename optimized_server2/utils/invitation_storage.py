"""
Хранилище приглашений в памяти
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import os
from utils.centralized_logger import get_logger

logger = get_logger('invitation_storage')


class InvitationStorage:
    """Хранилище приглашений в памяти с сохранением в файл"""
    
    def __init__(self, storage_file: str = 'invitations_storage.json'):
        self.storage_file = storage_file
        self.invitations: Dict[str, Dict[str, Any]] = {}
        self.expiration_days = 7
        
        # Загружаем существующие приглашения при старте
        self._load_from_file()
    
    def _load_from_file(self):
        """Загружает приглашения из файла"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Фильтруем устаревшие приглашения
                    current_time = datetime.now()
                    self.invitations = {
                        token: inv for token, inv in data.items()
                        if datetime.fromisoformat(inv['created_at']) + timedelta(days=self.expiration_days) > current_time
                    }
                    logger.info(f"Загружено {len(self.invitations)} активных приглашений из файла")
        except Exception as e:
            logger.error(f"Ошибка загрузки приглашений из файла: {e}")
            self.invitations = {}
    
    def _save_to_file(self):
        """Сохраняет приглашения в файл"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.invitations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения приглашений в файл: {e}")
    
    def save_invitation(self, token: str, org_unit_id: int, role: str, creator_id: int) -> bool:
        """Сохраняет приглашение"""
        try:
            self.invitations[token] = {
                'token': token,
                'org_unit_id': org_unit_id,
                'role': role,
                'creator_id': creator_id,
                'created_at': datetime.now().isoformat(),
                'used': False
            }
            self._save_to_file()
            logger.info(f"Сохранено приглашение: {token}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения приглашения: {e}")
            return False
    
    def get_invitation(self, token: str) -> Optional[Dict[str, Any]]:
        """Получает приглашение по токену"""
        # Очищаем устаревшие приглашения перед поиском
        self._cleanup_expired()
        
        if token in self.invitations:
            invitation = self.invitations[token]
            # Проверяем срок действия
            created_at = datetime.fromisoformat(invitation['created_at'])
            if datetime.now() - created_at > timedelta(days=self.expiration_days):
                # Удаляем устаревшее приглашение
                del self.invitations[token]
                self._save_to_file()
                return None
            return invitation
        return None
    
    def mark_as_used(self, token: str) -> bool:
        """Помечает приглашение как использованное"""
        if token in self.invitations:
            self.invitations[token]['used'] = True
            self._save_to_file()
            return True
        return False
    
    def _cleanup_expired(self):
        """Удаляет устаревшие приглашения"""
        current_time = datetime.now()
        expired_tokens = []
        
        for token, invitation in self.invitations.items():
            created_at = datetime.fromisoformat(invitation['created_at'])
            if current_time - created_at > timedelta(days=self.expiration_days):
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.invitations[token]
        
        if expired_tokens:
            logger.info(f"Удалено {len(expired_tokens)} устаревших приглашений")
            self._save_to_file()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику по приглашениям"""
        self._cleanup_expired()
        
        total = len(self.invitations)
        used = sum(1 for inv in self.invitations.values() if inv.get('used', False))
        active = total - used
        
        return {
            'total': total,
            'used': used,
            'active': active
        }


# Глобальный экземпляр хранилища
invitation_storage = InvitationStorage()

