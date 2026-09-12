"""
Nokia Network-as-Code (NaC) client wrapper.

Wraps the official `network_as_code` Python SDK to expose the CAMARA
signals TrustMesh AI needs: SIM Swap, Device Status (reachability),
and Location Verification.

Get your application token at: https://dashboard.networkascode.nokia.io/
Use NaC simulator phone numbers while developing (see README.md) so you
get deterministic responses without needing a real SIM.
"""

import os
from dataclasses import dataclass
from typing import Optional

import network_as_code as nac

NAC_TOKEN = os.getenv("NAC_TOKEN", "")

_client: Optional["nac.NetworkAsCodeClient"] = None


def get_client() -> "nac.NetworkAsCodeClient":
    global _client
    if _client is None:
        if not NAC_TOKEN:
            raise RuntimeError(
                "NAC_TOKEN is not set. Register at "
                "https://dashboard.networkascode.nokia.io/ and put your "
                "application key in the .env file."
            )
        _client = nac.NetworkAsCodeClient(token=NAC_TOKEN)
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
    connectivity: Optional[list]
    error: Optional[str] = None


@dataclass
class LocationSignal:
    phone_number: str
    result_type: Optional[str]  # "TRUE" | "FALSE" | "PARTIAL" | "UNKNOWN"
    error: Optional[str] = None


def check_sim_swap(phone_number: str, max_age_hours: int = 240) -> SimSwapSignal:
    """Has this phone number's SIM been swapped in the last `max_age_hours`?"""
    try:
        client = get_client()
        result = client.sim_swap.check(phone_number=phone_number, max_age=max_age_hours)
        return SimSwapSignal(
            phone_number=phone_number,
            swapped_recently=bool(result.swapped),
            checked_max_age_hours=max_age_hours,
        )
    except Exception as e:  # noqa: BLE001 - surface as a degraded signal, don't crash the agent
        return SimSwapSignal(
            phone_number=phone_number,
            swapped_recently=False,
            checked_max_age_hours=max_age_hours,
            error=str(e),
        )


def check_reachability(phone_number: str) -> ReachabilitySignal:
    """Is the device currently reachable on the network (DATA/SMS)?"""
    try:
        client = get_client()
        device = client.devices.get(phone_number=phone_number)
        status = device.get_reachability()
        return ReachabilitySignal(
            phone_number=phone_number,
            reachable=status.get("reachable"),
            connectivity=status.get("connectivity"),
        )
    except Exception as e:  # noqa: BLE001
        return ReachabilitySignal(
            phone_number=phone_number,
            reachable=None,
            connectivity=None,
            error=str(e),
        )


def verify_location(
    phone_number: str,
    latitude: float,
    longitude: float,
    radius_m: int = 5000,
    max_age_s: int = 3600,
) -> LocationSignal:
    """Is the device within `radius_m` metres of (latitude, longitude)?"""
    try:
        client = get_client()
        device = client.devices.get(phone_number=phone_number)
        result = device.verify_location(
            longitude=longitude,
            latitude=latitude,
            radius=radius_m,
            max_age=max_age_s,
        )
        return LocationSignal(phone_number=phone_number, result_type=result.result_type)
    except Exception as e:  # noqa: BLE001
        return LocationSignal(phone_number=phone_number, result_type=None, error=str(e))
