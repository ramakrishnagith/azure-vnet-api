import ipaddress
from itertools import combinations

REQUIRED_FIELDS = ["name", "resource_group", "location", "address_space", "subnets"]


class ValidationError(Exception):
    pass


def validate_vnet_request(payload: dict) -> None:
    # Rule 1: every required field must be present
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValidationError(f"Missing field: {field}")

    # Rule 2: address_space must be a valid CIDR
    try:
        space = ipaddress.ip_network(payload["address_space"])
    except ValueError:
        raise ValidationError(f"Invalid address_space: {payload['address_space']}")

    # Rule 3: subnets must be a non-empty list
    subnets = payload["subnets"]
    if not isinstance(subnets, list) or len(subnets) == 0:
        raise ValidationError("subnets must be a non-empty list")

    names_seen = set()
    networks = []

    for subnet in subnets:
        # Rule 3 (continued): each subnet needs a name and a prefix
        if not isinstance(subnet, dict) or "name" not in subnet or "prefix" not in subnet:
            raise ValidationError("Each subnet needs a name and a prefix")

        # Rule 5: subnet names must be unique
        if subnet["name"] in names_seen:
            raise ValidationError(f"Duplicate subnet name: {subnet['name']}")
        names_seen.add(subnet["name"])

        # Rule 4: prefix must be a valid CIDR and sit inside the address space
        try:
            network = ipaddress.ip_network(subnet["prefix"])
        except ValueError:
            raise ValidationError(f"Invalid subnet prefix: {subnet['prefix']}")
        if not network.subnet_of(space):
            raise ValidationError(f"Subnet {subnet['prefix']} is outside {payload['address_space']}")
        networks.append(network)

    # Rule 6: no two subnets may overlap
    for a, b in combinations(networks, 2):
        if a.overlaps(b):
            raise ValidationError(f"Subnets {a} and {b} overlap")