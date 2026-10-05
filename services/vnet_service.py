from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient


def get_client(subscription_id: str) -> NetworkManagementClient:
    return NetworkManagementClient(DefaultAzureCredential(), subscription_id)


def build_parameters(payload: dict) -> dict:
    """Convert our request format into the dict Azure expects."""
    return {
        "location": payload["location"],
        "address_space": {"address_prefixes": [payload["address_space"]]},
        "subnets": [
            {"name": s["name"], "address_prefix": s["prefix"]}
            for s in payload["subnets"]
        ],
    }


def create_vnet(client, payload: dict) -> dict:
    """Create the VNET in Azure and return a summary dict."""
    parameters = build_parameters(payload)
    poller = client.virtual_networks.begin_create_or_update(
        payload["resource_group"], payload["name"], parameters
    )
    result = poller.result()
    return {
        "name": result.name,
        "id": result.id,
        "location": result.location,
        "subnets": [
            {"name": s.name, "prefix": s.address_prefix}
            for s in result.subnets
        ],
    }