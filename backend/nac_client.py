"""
Nokia Network-as-Code (NaC) client wrapper.

Wraps the `network_as_code` Python SDK (rapidapi-based CAMARA client) to
expose the signals TrustMesh AI needs: SIM Swap, Device Status
(connectivity), and Location Verification.
"""

import os
from dataclasses import dataclass
from typing import Optional

import network_as_code as nac

NAC_TOKEN = os.getenv("NAC_TOKEN", "")

# These match the working curl example from the Nokia hub playground.
# The SDK's built-in default environment points at a different host
# (network-as-code.p-eu.rapidapi.com) which silently fails for accounts
# provisioned like ours - always set these explicitly.
NAC_BASE_URL = os.getenv("NAC_BASE_URL", "https://network-as-code.p-eu.apihub.nokia.io")
NAC_RAPIDAPI_HOST = os.getenv("NAC_RAPIDAPI_HOST", "network-as-code.nokia.rapidapi.com")

_client: Optional["nac.NetworkAsCodeApi"] = None


def get_client() -> "nac.NetworkAsCodeApi":
    global _client
    if _client is None:
        if not NAC_TOKEN:
            raise RuntimeError("NAC_TOKEN is not set.")
        _client = nac.NetworkAsCodeApi(
            api_key=NAC_TOKEN,
            base_url=NAC_BASE_URL,
            rapidapi_host=NAC_RAPIDAPI_HOST,
        )
    return _client


@dataclass
class SimSwapSignal:
    phone_number: str
    swapped_recently: bool
    checked_max_age_hours: int
    error: Optional[str] = None


@dataclass
class ReachabilitySignal:
    phone_number: str
    reachable: Optional[bool]
    connectivity_status: Optional[str]
    error: Optional[str] = None


@dataclass
class LocationSignal:
    phone_number: str
    result_type: Optional[str]
    error: Optional[str] = None


def check_sim_swap(phone_number: str, max_age_hours: int = 240) -> SimSwapSignal:
    try:
        client = get_client()
        result = client.sim_swap.check(phone_number=phone_number, max_age=max_age_hours)
        return SimSwapSignal(
            phone_number=phone_number,
            swapped_recently=bool(result.swapped),
            checked_max_age_hours=max_age_hours,
        )
    except Exception as e:
        return SimSwapSignal(
            phone_number=phone_number,
            swapped_recently=False,
            checked_max_age_hours=max_age_hours,
            error=str(e),
        )


def check_reachability(phone_number: str) -> ReachabilitySignal:
    try:
        client = get_client()
        result = client.device_status.check_connectivity(device={"phone_number": phone_number})
        status = result.connectivity_status
        return ReachabilitySignal(
            phone_number=phone_number,
            reachable=status in ("CONNECTED_DATA", "CONNECTED_SMS"),
            connectivity_status=status,
        )
    except Exception as e:
        return ReachabilitySignal(
            phone_number=phone_number,
            reachable=None,
            connectivity_status=None,
            error=str(e),
        )


def verify_location(
    phone_number: str,
    latitude: float,
    longitude: float,
    radius_m: int = 5000,
    max_age_s: int = 3600,
) -> LocationSignal:
    try:
        client = get_client()
        result = client.location.verify(
            device={"phone_number": phone_number},
            area={
                "area_type": "CIRCLE",
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_m,
            },
            max_age=max_age_s,
        )
        return LocationSignal(phone_number=phone_number, result_type=result.verification_result)
    except Exception as e:
        return LocationSignal(phone_number=phone_number, result_type=None, error=str(e))