# ============================
# CONFIGURACIÓN
# ============================
REQUIRED_MAJOR = 3
REQUIRED_MINOR = 10

OS := $(shell uname 2>/dev/null || echo Windows)

VENV = .venv
PY = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

ifeq ($(OS), Windows)
	PY = $(VENV)/Scripts/python.exe
	PIP = $(VENV)/Scripts/pip.exe
endif

# ============================
# DETECCIÓN DE PYTHON
# ============================
PYTHON_VERSION := $(shell python3 --version 2>/dev/null | awk '{print $$2}')
ifeq ($(PYTHON_VERSION),)
	PYTHON_VERSION := $(shell py -3 --version 2>NUL | awk '{print $$2}')
endif

INSTALLED_MAJOR := $(shell echo $(PYTHON_VERSION) | cut -d. -f1)
INSTALLED_MINOR := $(shell echo $(PYTHON_VERSION) | cut -d. -f2)

VERSION_OK := $(shell \
	if [ "$(INSTALLED_MAJOR)" -gt "$(REQUIRED_MAJOR)" ]; then echo yes; \
	elif [ "$(INSTALLED_MAJOR)" -eq "$(REQUIRED_MAJOR)" ] && [ "$(INSTALLED_MINOR)" -ge "$(REQUIRED_MINOR)" ]; then echo yes; \
	else echo no; fi)

# ============================
# REGLAS
# ============================

check:
	@echo "Sistema operativo detectado: $(OS)"
	@echo "Python detectado: $(PYTHON_VERSION)"
	@echo "Versión mínima requerida: $(REQUIRED_MAJOR).$(REQUIRED_MINOR)"
	@echo "¿Versión suficiente?: $(VERSION_OK)"

install:
	@echo "Sistema operativo: $(OS)"
	@if [ "$(VERSION_OK)" = "yes" ]; then \
		echo "Python es suficientemente nuevo."; \
	else \
		echo "Python es viejo o no existe. Instalando..."; \
		if [ "$(OS)" = "Windows" ]; then \
			winget install --id Python.Python.3 --source winget --silent; \
		elif [ "$(OS)" = "Linux" ]; then \
			sudo apt update && sudo apt install -y python3 python3-venv; \
		elif [ "$(OS)" = "Darwin" ]; then \
			brew install python; \
		fi; \
	fi

	@echo "Creando entorno virtual..."
	python3 -m venv $(VENV) || py -3 -m venv $(VENV)

	@echo "Instalando dependencias..."
	$(PIP) install --upgrade pip
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi

	@echo "Instalación completa."

run:
	$(PY) main.py

clean:
	@if [ "$(OS)" = "Windows" ]; then \
		if exist $(VENV) rmdir /s /q $(VENV); \
	else \
		rm -rf $(VENV); \
	fi

test:
	$(PY) -m pytest tests/ -v