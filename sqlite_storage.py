import json
import logging
from typing import Dict, Any, Optional
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.fsm.state import State

from db_utils import save_user_state, get_user_state, clear_user_state

logger = logging.getLogger(__name__)

class SQLiteStorage(BaseStorage):
    """
    Хранилище состояний FSM, использующее SQLite для хранения данных.
    """
    
    async def set_state(self, key: StorageKey, state: State | None) -> None:
        """
        Устанавливает состояние в хранилище
        
        Args:
            key: Ключ хранилища
            state: Новое состояние или None для очистки
        """
        if state is None:
            await self.set_data(key, {})
            return
        
        data = await self.get_data(key)
        data["state"] = state.state if state else None
        
        # Сохраняем состояние в базу данных
        user_id = int(key.user_id)
        state_name = state.state if state else None
        await save_user_state(user_id, state_name or "", data)
    
    async def get_state(self, key: StorageKey) -> Optional[State]:
        """
        Получает текущее состояние из хранилища
        
        Args:
            key: Ключ хранилища
            
        Returns:
            Optional[State]: Текущее состояние или None, если состояние не установлено
        """
        data = await self.get_data(key)
        if data and "state" in data and data["state"]:
            return State(data["state"])
        return None
    
    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """
        Устанавливает данные в хранилище
        
        Args:
            key: Ключ хранилища
            data: Новые данные
        """
        user_id = int(key.user_id)
        state_name = data.get("state", "")
        await save_user_state(user_id, state_name, data)
    
    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        """
        Получает данные из хранилища
        
        Args:
            key: Ключ хранилища
            
        Returns:
            Dict[str, Any]: Данные из хранилища
        """
        user_id = int(key.user_id)
        state_name, state_data = await get_user_state(user_id)
        if state_data:
            return state_data
        return {}
    
    async def update_data(self, key: StorageKey, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновляет данные в хранилище
        
        Args:
            key: Ключ хранилища
            data: Новые данные
            
        Returns:
            Dict[str, Any]: Обновленные данные
        """
        current_data = await self.get_data(key)
        current_data.update(data)
        await self.set_data(key, current_data)
        return current_data.copy()
    
    async def close(self) -> None:
        """
        Закрывает хранилище.
        Для SQLite ничего не делает, т.к. соединения закрываются автоматически.
        """
        pass 