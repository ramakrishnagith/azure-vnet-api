import pytest
from services.validation import validate_vnet_request, ValidationError

def good():
    return {
        "name": "vnet1", "resource_group": "rg1", "location": "eastus",
        "address_space": "10.0.0.0/16",
        "subnets": [
            {"name": "web", "prefix": "10.0.1.0/24"},
            {"name": "db", "prefix": "10.0.2.0/24"},
        ],
    }

def test_valid_payload_passes():
    validate_vnet_request(good())

@pytest.mark.parametrize("field", ["name", "resource_group", "location", "address_space", "subnets"])
def test_missing_field(field):
    p = good(); del p[field]
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_bad_address_space():
    p = good(); p["address_space"] = "10.0.0.0/99"
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_empty_subnets():
    p = good(); p["subnets"] = []
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_subnet_missing_prefix():
    p = good(); p["subnets"][0] = {"name": "web"}
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_subnet_outside_address_space():
    p = good(); p["subnets"][1]["prefix"] = "192.168.1.0/24"
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_overlapping_subnets():
    p = good(); p["subnets"][1]["prefix"] = "10.0.1.128/25"
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_duplicate_subnet_names():
    p = good(); p["subnets"][1]["name"] = "web"
    with pytest.raises(ValidationError):
        validate_vnet_request(p)

def test_host_bits_set_is_rejected():
    p = good(); p["subnets"][0]["prefix"] = "10.0.1.5/24"
    with pytest.raises(ValidationError):
        validate_vnet_request(p)