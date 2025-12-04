import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class HerokuService:
    """
    Service to interact with Heroku Platform API.
    Used to trigger on-demand execution of microservices.
    """
    
    BASE_URL = "https://api.heroku.com"
    
    def __init__(self):
        self.api_key = settings.HEROKU_API_KEY
        self.headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Mapping of app names/ids
        # These could be moved to config if they change often, but for now we keep them here or use config if available
        self.apps = {
            "home": "home-manager-horizon-61a90a214399",
            "portfolio": "portofolio-manager-horizon-8aab12e4e690",
            "reports": "horizon-financial-gafics-be44ac1b7792"
        }

    async def trigger_dyno(self, app_id_or_name: str, command: str, size: str = "basic") -> Dict[str, Any]:
        """
        Triggers a one-off dyno on Heroku.
        
        Args:
            app_id_or_name: The name or ID of the Heroku app.
            command: The command to run (e.g., "python orchestrator.py").
            size: Dyno size (default: "basic").
            
        Returns:
            JSON response from Heroku API.
        """
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
            user_id: The ID of the user (passed as env var or argument if needed by scripts).
                     Note: The scripts currently might not take user_id argument if they process all users 
                     or if they are designed to run globally. 
                     However, the requirement says "backend detect user is new... execute these systems".
                     
                     If the scripts are global (process all users), running them will process the new user too.
                     If they need specific user targeting, the command needs to be updated.
                     Based on the prompt: "ondemand python orchestrator.py", it seems they are global or pick up pending work.
        """
        
        # Define the commands as requested
        # Home: ondemand python orchestrator.py
        # Portfolio: ondemand python generate_report.py --period 6mo
        # Reports: ondemand python orchestrator_utf8.py
        
        # We run them in parallel
        results = await asyncio.gather(
            self.trigger_dyno(self.apps["home"], "python orchestrator.py"),
            self.trigger_dyno(self.apps["portfolio"], "python generate_report.py --period 6mo"),
            self.trigger_dyno(self.apps["reports"], "python orchestrator_utf8.py")
        )
        
        return {
            "home": results[0],
            "portfolio": results[1],
            "reports": results[2]
        }

# Singleton instance
heroku_service = HerokuService()
