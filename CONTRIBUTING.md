# Contribuir

1. Crear una rama desde `main`.
2. Instalar dependencias y ejecutar las pruebas:

   ```bash
   uv sync
   uv run pytest
   ```

3. Las pruebas viven en `tests/` y no deben depender de servicios externos: se
   simulan los clientes de Google y Firebase.
4. Al cambiar versiones de `dependencies`, validar el cambio en customer-api
   contra staging (ver `README.md`) y subir `version` en `pyproject.toml`.
5. Abrir un Pull Request hacia `main` describiendo qué cambia y cómo se probó.
