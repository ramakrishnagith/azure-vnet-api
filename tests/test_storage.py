import json
from unittest.mock import MagicMock

from azure.core.exceptions import ResourceNotFoundError

from services.storage import to_entity, from_entity, save_vnet, get_vnet, list_vnets


def record():
    return {
        "name": "vnet1",
        "id": "/subscriptions/x/virtualNetworks/vnet1",
        "location": "eastus",
        "subnets": [{"name": "web", "prefix": "10.0.1.0/24"}],
    }


def test_entity_round_trip():
    entity = to_entity("rg1", record())
    assert entity["PartitionKey"] == "rg1"
    assert entity["RowKey"] == "vnet1"
    out = from_entity(entity)
    assert out["name"] == "vnet1"
    assert out["resource_group"] == "rg1"
    assert out["subnets"] == record()["subnets"]


def test_save_vnet_creates_entity():
    table = MagicMock()
    save_vnet(table, "rg1", record())
    table.create_entity.assert_called_once()
    entity = table.create_entity.call_args.args[0]
    assert entity["PartitionKey"] == "rg1"
    assert json.loads(entity["subnets"]) == record()["subnets"]


def test_get_vnet_returns_record():
    table = MagicMock()
    table.get_entity.return_value = to_entity("rg1", record())
    out = get_vnet(table, "rg1", "vnet1")
    assert out["name"] == "vnet1"
    assert out["location"] == "eastus"


def test_get_vnet_returns_none_when_missing():
    table = MagicMock()
    table.get_entity.side_effect = ResourceNotFoundError()
    assert get_vnet(table, "rg1", "nope") is None


def test_list_vnets_returns_all():
    table = MagicMock()
    table.list_entities.return_value = [to_entity("rg1", record())]
    out = list_vnets(table)
    assert len(out) == 1
    assert out[0]["name"] == "vnet1"