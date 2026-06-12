from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime

# Inicialización de la API de NexApp con inteligencia fundamental v1.2.0
app = FastAPI(title="NexApp Intelligence Unit API", version="1.2.0")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Credenciales de Grado Corporativo
# Clemente, asegura que esta llave siga activa en https://api.cmfchile.cl/
CMF_TOKEN = "9e79bf38461c5d4dbc597d81926d97b05022f45f"

# Endpoint base de la CMF para Instituciones Financieras (Módulo SBIF)
# NOTA: Basado en auditoría, no existe un endpoint de producción público
# conocido para FECU XBRL (Mercado de Valores) en una sola llamada por Ticker/RUT.
# Seguiremos usando el SBIF, pero mejoraremos el manejo de auditoría.
BASE_URL_SBIF = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# DICCIONARIO DE ABSTRACCIÓN: Mapeo de "Tickers" a RUTs (Grado Auditoría)
TICKER_MAP = {
    # Instituciones Financieras (Bancos, reportan a módulo SBIF)
    "BANCOCHILE": "97004000-5",
    "ESTADO": "90200000-2",
    "SANTANDER": "97023000-9",
    "BCI": "97006000-6",
    
    # Mapeo proyectado para sector salmonero UACh benchmark
    # (RUTs corporativos reales, reportan a módulo Mercado de Valores - FECU)
    "MULTIX": "76118940-K",     # Multi X S.A.
    "AQUACHILE": "70142000-8",   # Empresas AquaChile S.A.
    "BLUMAR": "96656710-3",      # Blumar S.A.
}

@app.get("/api/fundamental/{ticker}")
def get_latest_fundamental(ticker: str):
    """
    Motor de abstracción de inteligencia contable v1.2.0.
    Intenta obtener los últimos datos fundamentales estructurados utilizando un 'Ticker'
    utilizando el módulo SBIF de la CMF.
    Maneja auditoría para tickers que reportan en FECU (Mercado de Valores).
    """
    
    # 1. Traducir Ticker a RUT automáticamente
    upper_ticker = ticker.upper().strip()
    rut = TICKER_MAP.get(upper_ticker)
    
    if not rut:
        raise HTTPException(
            status_code=404, 
            detail=f"Ticker '{ticker}' no encontrado en el directorio NexApp. La auditoría requiere un Ticker válido."
        )
        
    # 2. Calcular automáticamente el periodo más reciente disponible (Año Anterior Completo)
    # Clemente, como estamos en Junio 2026, usaremos Diciembre 2025 para asegurar cierre anual.
    anio_consulta = "2025"
    mes_consulta = "12" # Cierre de diciembre
        
    # 3. Construcción de consulta a CMF (Módulo SBIF/Bancos)
    clean_rut = rut.replace(".", "").strip()
    url = f"{BASE_URL_SBIF}/balances/{anio_consulta}/{mes_consulta}/instituciones/{clean_rut}"
    params = {"apikey": CMF_TOKEN, "formato": "json"}
    
    try:
        # Petición a la CMF
        response = requests.get(url, params=params)
        
        # Manejo de auditoría: 404 CMF SBIF
        if response.status_code == 404:
             return {
                "status": "warning",
                "ticker": upper_ticker,
                "rut": rut,
                "periodo": f"{anio_consulta}-{mes_consulta}",
                "detail": f"Ticker '{upper_ticker}' reporta sus Estados Financieros en el módulo de Mercado de Valores (FECU/XBRL) de la CMF. Este endpoint solo extrae datos del módulo SBIF (Bancos/Instituciones Financieras).",
                "datos_estructurados": False
            }

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Fallo en la extracción. Código CMF: {response.status_code}")
            
        cmf_data = response.json()
        
        # Mapeo contable estructurado
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
            "auditoria_origen": "Comisión para el Mercado Financiero (Chile) - Módulo SBIF",
            "fundamental_data": datos_limpios,
            "datos_estructurados": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
