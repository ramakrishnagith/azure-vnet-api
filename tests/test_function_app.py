import json
from unittest.mock import MagicMock

import azure.functions as func

import function_app


def make_req(body=None, route_params=None):
    return func.HttpRequest(
        method="POST",
        url="/api/vnets",
        body=body if isinstance(body, bytes) else json.dumps(body).encode(),
        route_params=route_params or {},
    )


def good_payload():
    return {
        "name": "vnet1", "resource_group": "rg1", "location": "eastus",
        "address_space": "10.0.0.0/16",
        "subnets": [{"name": "web", "prefix": "10.0.1.0/24"}],
    }


def patch_deps(monkeypatch, existing=None):
    monkeypatch.setattr(function_app, "get_table", lambda: MagicMock())
    monkeypatch.setattr(function_app, "get_network", lambda: MagicMock())
    monkeypatch.setattr(function_app.storage, "get_vnet", lambda t, rg, n: existing)
    monkeypatch.setattr(function_app.storage, "save_vnet", lambda t, rg, r: None)
    monkeypatch.setattr(
        function_app.vnet_service, "create_vnet",
        lambda c, p: {"name": p["name"], "id": "x", "location": p["location"], "subnets": []},
    )


def test_create_rejects_invalid_json(monkeypatch):
    patch_deps(monkeypatch)
    resp = function_app.handle_create(make_req(b"not json"))
    assert resp.status_code == 400


def test_create_rejects_invalid_payload(monkeypatch):
    patch_deps(monkeypatch)
    bad = good_payload()
    bad["address_space"] = "10.0.0.0/99"
    assert function_app.handle_create(make_req(bad)).status_code == 400


def test_create_success_returns_201(monkeypatch):
    patch_deps(monkeypatch)
    resp = function_app.handle_create(make_req(good_payload()))
    assert resp.status_code == 201
    assert json.loads(resp.get_body())["name"] == "vnet1"


def test_create_duplicate_returns_409(monkeypatch):
    patch_deps(monkeypatch, existing={"name": "vnet1"})
    assert function_app.handle_create(make_req(good_payload())).status_code == 409


def test_get_missing_returns_404(monkeypatch):
    patch_deps(monkeypatch, existing=None)
    req = make_req({}, route_params={"resource_group": "rg1", "name": "nope"})
    assert function_app.handle_get(req).status_code == 404