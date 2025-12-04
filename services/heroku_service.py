import httpx
import logging
import asyncio
import re
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

def extract_app_name(url_or_name: str) -> str:
    """
    Extrae el nombre de la app de Heroku de una URL o retorna el nombre si ya es solo el nombre.
    
    Ejemplos:
        - "https://my-app-123.herokuapp.com/" -> "my-app-123"
        - "https://my-app-123.herokuapp.com" -> "my-app-123"
        - "my-app-123" -> "my-app-123"
    """
    if not url_or_name:
        return ""
    
    # Si es una URL de Heroku, extraer el nombre de la app
    match = re.match(r'https?://([^.]+)\.herokuapp\.com/?', url_or_name)
    if match:
        return match.group(1)
    
    # Si ya es solo el nombre, retornarlo limpio
    return url_or_name.strip().rstrip('/')


class HerokuService:
    """
    Service to interact with Heroku Platform API.
    Used to trigger on-demand execution of microservices.
    """
    
    BASE_URL = "https://api.heroku.com"
    
    def __init__(self):
        self.api_key = settings.HEROKU_API_KEY
        self.enabled = settings.HEROKU_ONDEMAND_ENABLED
        self.headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Extraer nombres de apps desde configuración (pueden ser URLs o nombres)
        self.apps = {
            "home": extract_app_name(settings.HEROKU_APP_HOME),
            "portfolio": extract_app_name(settings.HEROKU_APP_PORTFOLIO),
            "reports": extract_app_name(settings.HEROKU_APP_REPORTS)
        }
        
        logger.info("HerokuService inicializado - Enabled: %s, Apps: %s", self.enabled, self.apps)

    async def trigger_dyno(self, app_id_or_name: str, command: str, size: str = "eco") -> Dict[str, Any]:
        """
        Triggers a one-off dyno on Heroku.
        
        Args:
            app_id_or_name: The name or ID of the Heroku app.
            command: The command to run (e.g., "python orchestrator.py").
            size: Dyno size (default: "eco" for Eco tier apps).
            
        Returns:
            JSON response from Heroku API.
        """
        if not self.enabled:
            logger.info("Heroku on-demand está deshabilitado. Skipping trigger para %s", app_id_or_name)
            return {"status": "skipped", "reason": "disabled"}
            
        if not self.api_key:
            logger.warning("HEROKU_API_KEY not set. Skipping dyno trigger for %s", app_id_or_name)
            return {"status": "skipped", "reason": "missing_api_key"}

        url = f"{self.BASE_URL}/apps/{app_id_or_name}/dynos"
        payload = {
            "command": command,
            "size": size,
            "time_to_live": 1800  # 30 minutes max
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                logger.info("Triggered Heroku dyno for %s: %s", app_id_or_name, command)
                return data
        except httpx.HTTPStatusError as e:
            logger.error("Heroku API error triggering %s: %s - %s", app_id_or_name, e.response.status_code, e.response.text)
            return {"status": "error", "code": e.response.status_code, "detail": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error triggering Heroku dyno for %s", app_id_or_name)
            return {"status": "error", "detail": str(e)}

    async def trigger_on_demand_setup(self, user_id: str) -> Dict[str, Any]:
        """
        Triggers all necessary microservices for a new user setup.
        
        Args:
            user_id: The ID of the user. This is passed to the scripts as an argument
                     so they can generate data specifically for this user.
        
        Returns:
            Dict with results from each triggered service.
        """
        logger.info("Triggering on-demand setup for user: %s", user_id)
        
        # Commands now include user_id as an environment variable or argument
        # Note: portfolio uses --user-id (with hyphen), others use --user_id (with underscore)
        results = await asyncio.gather(
            self.trigger_dyno(self.apps["home"], f"python orchestrator.py --user_id {user_id}"),
            self.trigger_dyno(self.apps["portfolio"], f"python generate_report.py --period 6mo --user-id {user_id}"),
            self.trigger_dyno(self.apps["reports"], f"python orchestrator_utf8.py --user_id {user_id}"),
            return_exceptions=True  # Don't fail all if one fails
        )
        
        # Process results
        processed_results = {}
        for name, result in zip(["home", "portfolio", "reports"], results):
            if isinstance(result, Exception):
                logger.error("Error triggering %s for user %s: %s", name, user_id, result)
                processed_results[name] = {"status": "error", "detail": str(result)}
            else:
                processed_results[name] = result
        
        logger.info("On-demand setup triggered for user %s. Results: %s", user_id, processed_results)
        return processed_results

# Singleton instance
heroku_service = HerokuService()
