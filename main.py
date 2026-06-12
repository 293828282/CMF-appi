from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime

# Inicialización de la API de NexApp con inteligencia fundamental v1.3.0
app = FastAPI(title="NexApp Intelligence Unit API", version="1.3.0")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Llave Maestra
CMF_TOKEN = "9e79bf38461c5d4dbc597d81926d97b05022f45f"
BASE_URL_SBIF = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

# DICCIONARIO DE ABSTRACCIÓN: Mapeo corregido
# La CMF usa códigos de 3 dígitos para instituciones financieras, NO RUTs.
TICKER_MAP = {
    # Módulo SBIF - Códigos CMF
    "BANCOCHILE": "001",
    "ESTADO": "012",
    "SANTANDER": "037",
    "BCI": "016",
    
    # Sector salmonero (Se envía RUT porque reportan en FECU, activando el escudo)
    "MULTIX": "76118940-K",
    "AQUACHILE": "70142000-8",
    "BLUMAR": "96656710-3",
}

@app.get("/api/fundamental/{ticker}")
def get_latest_fundamental(ticker: str):
    upper_ticker = ticker.upper().strip()
    identificador = TICKER_MAP.get(upper_ticker)
    
    if not identificador:
        raise HTTPException(
            status_code=404, 
            detail=f"Ticker '{ticker}' no encontrado en el directorio NexApp."
        )
        
    # Último cierre contable anual garantizado
    anio_consulta = "2025"
    mes_consulta = "12" 
        
    clean_id = identificador.replace(".", "").strip()
    url = f"{BASE_URL_SBIF}/balances/{anio_consulta}/{mes_consulta}/instituciones/{clean_id}"
    params = {"apikey": CMF_TOKEN, "formato": "json"}
    
    try:
        response = requests.get(url, params=params)
        
        # Escudo de auditoría para empresas no bancarias
        if response.status_code == 404:
             return {
                "status": "warning",
                "ticker": upper_ticker,
                "identificador": identificador,
                "periodo": f"{anio_consulta}-{mes_consulta}",
                "detail": "La entidad reporta en el módulo de Mercado de Valores (FECU/XBRL), no en Instituciones Financieras (Bancos)."
            }

        # Extracción del error exacto de la CMF si rechazan la solicitud
        if response.status_code != 200:
            cmf_error = "Error desconocido de CMF"
            if "json" in response.headers.get("content-type", ""):
                cmf_error = response.json().get("Mensaje", cmf_error)
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Rechazo de CMF. Código {response.status_code}: {cmf_error}"
            )
            
        cmf_data = response.json()
        institucion = cmf_data.get("Archivo", {}).get("Instituciones", {})
        
        datos_limpios = {
            "activos_totales": institucion.get("ActivosTotales", "N/A"),
            "pasivos_totales": institucion.get("PasivosTotales", "N/A"),
            "patrimonio": institucion.get("Patrimonio", "N/A")
        }
        
        return {
            "status": "success",
            "ticker": upper_ticker,
            "periodo": f"{anio_consulta}-{mes_consulta}",
            "fundamental_data": datos_limpios
        }
        
    except HTTPException:
        # Permitimos que los errores controlados suban limpios al navegador
        raise
    except Exception as e:
        # Atrapamos fallos puros de infraestructura
        raise HTTPException(status_code=500, detail=f"Fallo crítico en el motor: {str(e)}")
