from asyncio.log import logger
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional
from plugins.base_plugin import BasePlugin


class PluginManager:
    """Gestor central de plugins - Descubre y registra plugins automáticamente"""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self._discover_plugins()
    
    def _discover_plugins(self):
        """
        Descubre automáticamente todos los plugins en la carpeta plugins/
        Esto permite agregar nuevas marcas sin modificar código existente
        """
        
        plugin_dir = Path(__file__).parent.parent / 'plugins'
        
        # Buscar todos los archivos *_plugin.py
        for plugin_file in plugin_dir.glob('*_plugin.py'):
            if plugin_file.name == 'base_plugin.py':
                continue
            
            # Importar módulo dinámicamente
            module_name = f"plugins.{plugin_file.stem}"
            module = importlib.import_module(module_name)
            
            # Buscar clases que hereden de BasePlugin
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin):
                    
                    # Instanciar y registrar plugin
                    plugin = obj()
                    self.register_plugin(plugin)
    
    def register_plugin(self, plugin: BasePlugin):
        """Registrar un plugin manualmente"""
        self.plugins[plugin.brand] = plugin
        logger.info(f"Plugin registrado: {plugin.brand}")
    
    def get_plugin(self, brand: str) -> Optional[BasePlugin]:
        """Obtener plugin por marca"""
        return self.plugins.get(brand.lower())
    
    def get_all_plugins(self) -> List[BasePlugin]:
        """Obtener todos los plugins registrados"""
        return list(self.plugins.values())