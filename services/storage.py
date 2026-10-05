import json
from datetime import datetime, timezone

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient

TABLE_NAME = "vnets"


def get_table(connection_string: str):
    """Return a client for the 'vnets' table, creating the table if needed."""
    service = TableServiceClient.from_connection_string(connection_string)
    return service.create_table_if_not_exists(TABLE_NAME)


def to_entity(resource_group: str, record: dict) -> dict:
    """Convert a VNET summary into a Table Storage row."""
    return {
        "PartitionKey": resource_group,
        "RowKey": record["name"],
        "id": record["id"],
        "location": record["location"],
        "subnets": json.dumps(record["subnets"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def from_entity(entity: dict) -> dict:
    """Convert a Table Storage row back into a plain dict for the API."""
    return {
        "name": entity["RowKey"],
        "resource_group": entity["PartitionKey"],
        "id": entity["id"],
        "location": entity["location"],
        "subnets": json.loads(entity["subnets"]),
        "created_at": entity["created_at"],
    }


def save_vnet(table, resource_group: str, record: dict) -> None:
    # Raises ResourceExistsError if this VNET is already stored.
    table.create_entity(to_entity(resource_group, record))


def get_vnet(table, resource_group: str, name: str):
    try:
        entity = table.get_entity(partition_key=resource_group, row_key=name)
    except ResourceNotFoundError:
        return None
    return from_entity(entity)


def list_vnets(table) -> list:
    return [from_entity(e) for e in table.list_entities()]