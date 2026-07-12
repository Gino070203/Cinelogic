# Entry point del servidor: ejecuta uvicorn con la aplicación FastAPI
import sys
import os

# Asegurar que el directorio raíz de python/ esté en el path de módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar API key de TMDB desde variable de entorno
os.environ.setdefault("TMDB_API_KEY", "")

if __name__ == "__main__":
    import uvicorn
    from api.main import app
    # Iniciar servidor en todas las interfaces (0.0.0.0), puerto 8003
    uvicorn.run(app, host="0.0.0.0", port=8003)
