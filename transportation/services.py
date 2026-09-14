from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

from .models import WeddingTransportationSettings


@dataclass(frozen=True)
class RouteRequest:
    destination_name: str
    destination_latitude: Optional[str] = None
    destination_longitude: Optional[str] = None
    origin_latitude: Optional[str] = None
    origin_longitude: Optional[str] = None


@dataclass(frozen=True)
class RouteOption:
    route_number: str = ""
    bus_name: str = ""
    boarding_stop: str = ""
    transfer_details: str = ""
    drop_off_stop: str = ""
    walking_distance: str = ""
    estimated_duration: str = ""
    fare: str = ""
    service_status: str = ""


@dataclass(frozen=True)
class RouteLookupResult:
    available: bool
    provider_key: str
    message: str
    routes: list[RouteOption] = field(default_factory=list)
    fetched_at: object = None
    is_stale: bool = False


class BaseTransportationProvider:
    key = "BASE"

    def lookup_routes(self, request: RouteRequest) -> RouteLookupResult:
        raise NotImplementedError


class ManualGuidanceProvider(BaseTransportationProvider):
    key = WeddingTransportationSettings.Provider.MANUAL

    def lookup_routes(self, request: RouteRequest) -> RouteLookupResult:
        return RouteLookupResult(
            available=False,
            provider_key=self.key,
            message="Live bus routes are not connected for this wedding.",
            fetched_at=timezone.now(),
        )


class BusProjectProvider(BaseTransportationProvider):
    """Stable adapter boundary for the future Bus Project API.

    v11.0 intentionally does not call an external API. When the Bus Project API
    is ready, only this adapter should need network/authentication logic; invitation
    templates should continue using RouteLookupResult.
    """

    key = WeddingTransportationSettings.Provider.BUS_PROJECT

    def lookup_routes(self, request: RouteRequest) -> RouteLookupResult:
        return RouteLookupResult(
            available=False,
            provider_key=self.key,
            message="Bus Project API adapter is ready, but live route lookup is not connected yet.",
            fetched_at=timezone.now(),
        )


PROVIDERS = {
    ManualGuidanceProvider.key: ManualGuidanceProvider(),
    BusProjectProvider.key: BusProjectProvider(),
}


def ensure_settings(wedding):
    settings_obj, _ = WeddingTransportationSettings.objects.get_or_create(wedding=wedding)
    return settings_obj


def destination_payload(wedding):
    return {
        "name": (wedding.wedding_location or "").strip(),
        "address": (getattr(wedding, "venue_full_address", "") or "").strip(),
        "latitude": getattr(wedding, "venue_latitude", None),
        "longitude": getattr(wedding, "venue_longitude", None),
        "landmark": (getattr(wedding, "venue_landmark", "") or "").strip(),
        "location_note": (getattr(wedding, "venue_location_note", "") or "").strip(),
    }


def map_urls(wedding):
    try:
        from event_tools.services import build_map_urls

        return build_map_urls(wedding)
    except Exception:
        google = (getattr(wedding, "google_maps_url", "") or "").strip()
        return google, ""


def route_request_for_wedding(wedding):
    destination = destination_payload(wedding)
    lat = destination["latitude"]
    lng = destination["longitude"]
    return RouteRequest(
        destination_name=destination["name"],
        destination_latitude=str(lat) if lat is not None else None,
        destination_longitude=str(lng) if lng is not None else None,
    )


def lookup_routes(wedding, settings_obj=None):
    settings_obj = settings_obj or ensure_settings(wedding)
    provider = PROVIDERS.get(settings_obj.provider, PROVIDERS[WeddingTransportationSettings.Provider.MANUAL])
    return provider.lookup_routes(route_request_for_wedding(wedding))
