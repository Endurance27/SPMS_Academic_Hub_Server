from typing import Any, Dict, Optional

import httpx
from loguru import logger

from app.core.config import settings


class GoogleMapsService:
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY

    async def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Geocode address using Google Maps API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={"address": address, "key": self.api_key},
                    timeout=10.0,
                )

                response.raise_for_status()
                data = response.json()

                if data["status"] == "OK" and data["results"]:
                    location = data["results"][0]["geometry"]["location"]
                    return {
                        "latitude": location["lat"],
                        "longitude": location["lng"],
                        "formatted_address": data["results"][0]["formatted_address"],
                    }

                return None

        except httpx.HTTPError as e:
            logger.error(f"Google Maps geocoding failed: {e}")
            return None

    def get_static_map_url(
        self, latitude: float, longitude: float, zoom: int = 15, size: str = "600x400"
    ) -> str:
        """Get static map image URL"""
        return (
            f"https://maps.googleapis.com/maps/api/staticmap"
            f"?center={latitude},{longitude}"
            f"&zoom={zoom}"
            f"&size={size}"
            f"&markers=color:red%7C{latitude},{longitude}"
            f"&key={self.api_key}"
        )
