from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

# Inicialización de NexApp Intelligence Unit v2.0.0
app = FastAPI(title="NexApp Intelligence Unit API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CMF_TOKEN = "9e79bf38461c5d4dbc597d81926d97b05022f45f"
BASE_URL_SBIF = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

TICKER_MAP = {
    # Módulo SBIF - Códigos CMF
    "BANCOCHILE": "001",
    "ESTADO": "012",
    "SANTANDER": "037",
    "BCI": "016",
    
    # Sector salmonero (FECU)
    "MULTIX": "76118940-K",
    "AQUACHILE": "70142000-8",
    "BLUMAR": "96656710-3",
}

@app.get("/api/fundamental/{ticker}/{anio}/{mes}")
def get_balance_completo(ticker: str, anio: str, mes: str):
    """
    Motor Dinámico de Extracción Total.
    Permite consultar cualquier periodo y devuelve el catálogo completo de cuentas.
    """
    upper_ticker = ticker.upper().strip()
    identificador = TICKER_MAP.get(upper_ticker)
    
    if not identificador:
        raise HTTPException(
            status_code=404, 
            detail=f"Ticker '{ticker}' no encontrado en la base de datos."
        )
        
    clean_id = identificador.replace(".", "").strip()
    url = f"{BASE_URL_SBIF}/balances/{anio}/{mes}/instituciones/{clean_id}"
    params = {"apikey": CMF_TOKEN, "formato": "json"}
    
    try:
        response = requests.get(url, params=params)
        
        # Filtro de seguridad si la entidad no existe en ese periodo o es FECU
        if response.status_code == 404:
             return {
                "status": "warning",
                "ticker": upper_ticker,
                "periodo": f"{anio}-{mes}",
                "detail": "Sin datos. La entidad reporta en FECU o el periodo consultado aún no ha sido publicado por la CMF."
            }

        # Captura del error exacto de CMF
        if response.status_code != 200:
            cmf_error = response.json().get("Mensaje", "Error desconocido") if "json" in response.headers.get("content-type", "") else "Error de conexión"
            raise HTTPException(status_code=response.status_code, detail=f"Rechazo CMF: {cmf_error}")
            
        cmf_data = response.json()
        
        # Extracción pura del arreglo de cuentas
        cuentas_totales = cmf_data.get("Archivo", {}).get("balances", [])
        
        return {
            "status": "success",
            "ticker": upper_ticker,
            "periodo": f"{anio}-{mes}",
            "total_cuentas_extraidas": len(cuentas_totales),
            "libro_mayor": cuentas_totales,
            "raw_cmf_data": cmf_data # Respaldamos la data cruda por seguridad
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo crítico: {str(e)}")
