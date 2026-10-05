from types import SimpleNamespace as NS
from unittest.mock import MagicMock
from services.vnet_service import build_parameters, create_vnet


def payload():
    return {
        "name": "vnet1", "resource_group": "rg1", "location": "eastus",
        "address_space": "10.0.0.0/16",
        "subnets": [
            {"name": "web", "prefix": "10.0.1.0/24"},
            {"name": "db", "prefix": "10.0.2.0/24"},
        ],
    }


def test_build_parameters_maps_fields():
    params = build_parameters(payload())
    assert params["location"] == "eastus"
    assert params["address_space"] == {"address_prefixes": ["10.0.0.0/16"]}
    assert params["subnets"] == [
        {"name": "web", "address_prefix": "10.0.1.0/24"},
        {"name": "db", "address_prefix": "10.0.2.0/24"},
    ]


def test_create_vnet_calls_azure_and_returns_summary():
    fake_result = NS(
        name="vnet1",
        id="/subscriptions/x/resourceGroups/rg1/providers/Microsoft.Network/virtualNetworks/vnet1",
        location="eastus",
        subnets=[NS(name="web", address_prefix="10.0.1.0/24"),
                 NS(name="db", address_prefix="10.0.2.0/24")],
    )
    client = MagicMock()
    create = client.virtual_networks.begin_create_or_update
    create.return_value.result.return_value = fake_result

    out = create_vnet(client, payload())

    create.assert_called_once()
    assert create.call_args.args[:2] == ("rg1", "vnet1")
    assert out["name"] == "vnet1"
    assert out["location"] == "eastus"
    assert out["subnets"] == [
        {"name": "web", "prefix": "10.0.1.0/24"},
        {"name": "db", "prefix": "10.0.2.0/24"},
    ]