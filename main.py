from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime

# Inicialización de la API de NexApp con inteligencia fundamental
app = FastAPI(title="NexApp Intelligence Unit API", version="1.1.0")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Credenciales de Grado Corporativo
CMF_TOKEN = "9e79bf38461c5d4dbc597d81926d97b05022f45f"
BASE_URL = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# DICCIONARIO DE ABSTRACCIÓN: Mapeo de "Tickers" a RUTs (Grado Auditoría)
# Aquí gestionamos la inteligencia para que el usuario no use RUTs.
TICKER_MAP = {
    # Tickers de ejemplo para pruebas contables
    "BANCOCHILE": "97004000-5",
    "ESTADO": "90200000-2",
    "SANTANDER": "97023000-9",
    
    # Mapeo proyectado para sector salmonero (RUTs reales corporativos)
    "MULTIX": "76118940-K",     # Multi X S.A.
    "AQUACHILE": "70142000-8",   # Empresas AquaChile S.A.
    "BLUMAR": "96656710-3",      # Blumar S.A.
    "INVERMAR": "96839350-1"     # Invermar S.A.
}

@app.get("/api/fundamental/{ticker}")
def get_latest_fundamental(ticker: str):
    """
    Motor de abstracción de inteligencia contable.
    Obtiene los últimos datos fundamentales estructurados utilizando ÚNICAMENTE un 'Ticker'.
    El motor calcula automáticamente RUT, Año y Mes.
    """
    
    # 1. Traducir Ticker a RUT automáticamente
    upper_ticker = ticker.upper().strip()
    rut = TICKER_MAP.get(upper_ticker)
    
    if not rut:
        raise HTTPException(
            status_code=404, 
            detail=f"Ticker '{ticker}' no encontrado en el directorio NexApp. La auditoría requiere un Ticker válido (ej: MULTIX, AQUACHILE)."
        )
        
    # 2. Calcular automáticamente el periodo más reciente disponible (Diciembre Año Anterior)
    # CMF suele tener un delay de 1 trimestre, usar el cierre del año anterior garantiza datos.
    anio_consulta = str(datetime.now().year - 1)
    mes_consulta = "12" # Cierre de diciembre
        
    # 3. Descarga de Datos desde la CMF (Cálculo estructural)
    clean_rut = rut.replace(".", "").strip()
    url = f"{BASE_URL}/balances/{anio_consulta}/{mes_consulta}/instituciones/{clean_rut}"
    params = {"apikey": CMF_TOKEN, "formato": "json"}
    
    try:
        # Petición a la CMF
        response = requests.get(url, params=params)
        
        # Manejo de error si el RUT no está en la base de datos de instituciones financieras
        if response.status_code == 404:
             return {
                "status": "error",
                "ticker": upper_ticker,
                "rut": rut,
                "periodo": f"{anio_consulta}-{mes_consulta}",
                "detail": f"Datos no disponibles. Ticker '{upper_ticker}' reporta en Mercado de Valores (FECU/XBRL), no en Instituciones Financieras."
            }

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Fallo en la extracción. Código CMF: {response.status_code}")
            
        cmf_data = response.json()
        
        # Mapeo contable (Módulo SBIF/Bancos por defecto)
        institucion = cmf_data.get("Archivo", {}).get("Instituciones", {})
        
        datos_limpios = {
            "activos_totales": institucion.get("ActivosTotales", "N/A"),
            "pasivos_totales": institucion.get("PasivosTotales", "N/A"),
            "patrimonio": institucion.get("Patrimonio", "N/A")
        }
        
        # 4. Respuesta Estructurada NexApp
        return {
            "status": "success",
            "ticker": upper_ticker,
            "rut": rut,
            "periodo": f"{anio_consulta}-{mes_consulta}",
            "auditoria_origen": "Comisión para el Mercado Financiero (Chile)",
            "fundamental_data": datos_limpios
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
