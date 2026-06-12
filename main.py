from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

# Inicialización de NexApp Intelligence Unit v2.1.0
app = FastAPI(title="NexApp Intelligence Unit API", version="2.1.0")

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
    Motor Dinámico de Extracción Total (v2.1).
    Captura el libro mayor completo, adaptándose a las inconsistencias de nomenclatura de la CMF.
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
        
        if response.status_code == 404:
             return {
                "status": "warning",
                "ticker": upper_ticker,
                "periodo": f"{anio}-{mes}",
                "detail": "Sin datos. La entidad reporta en FECU o el periodo consultado aún no ha sido publicado por la CMF."
            }

        if response.status_code != 200:
            cmf_error = response.json().get("Mensaje", "Error desconocido") if "json" in response.headers.get("content-type", "") else "Error de conexión"
            raise HTTPException(status_code=response.status_code, detail=f"Rechazo CMF: {cmf_error}")
            
        cmf_data = response.json()
        
        # EXTRACCIÓN INTELIGENTE: Busca ambas nomenclaturas posibles de la CMF
        archivo = cmf_data.get("Archivo", {})
        
        # Algunas veces la CMF lo manda directo en la raíz, otras dentro de "Archivo"
        if "CodigosBalances" in cmf_data:
            cuentas_totales = cmf_data["CodigosBalances"]
        elif "balances" in archivo:
            cuentas_totales = archivo["balances"]
        elif "CodigosBalances" in archivo:
            cuentas_totales = archivo["CodigosBalances"]
        else:
            cuentas_totales = [] # Si cambian el formato de nuevo, no se cae la API
        
        return {
            "status": "success",
            "ticker": upper_ticker,
            "periodo": f"{anio}-{mes}",
            "total_cuentas_extraidas": len(cuentas_totales),
            "libro_mayor": cuentas_totales
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo crítico: {str(e)}")
