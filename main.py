#!/usr/bin/env python3
"""
Punto de entrada principal de Homebridge HAP
"""
import logging
import sys
from core.app_manager import AppManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('.smarthome/homebridge_hap.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Función principal"""
    try:
        # Crear y iniciar el gestor de aplicación
        app = AppManager()
        app.start()
        
    except KeyboardInterrupt:
        logger.info("\n\n⏹  Deteniendo aplicación...")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()