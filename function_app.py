import json
import logging
import os

import azure.functions as func
from azure.core.exceptions import HttpResponseError, ResourceExistsError

from services import storage, vnet_service
from services.validation import ValidationError, validate_vnet_request

# Authentication is enforced by the platform (App Service Authentication / Entra ID),
# so the function itself is anonymous at the Functions level.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

_table = None
_network = None


def get_table():
    global _table
    if _table is None:
        _table = storage.get_table(os.environ["STORAGE_CONNECTION_STRING"])
    return _table


def get_network():
    global _network
    if _network is None:
        _network = vnet_service.get_client(os.environ["AZURE_SUBSCRIPTION_ID"])
    return _network


def json_response(body, status=200):
    return func.HttpResponse(
        json.dumps(body), status_code=status, mimetype="application/json"
    )


def handle_create(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return json_response({"error": "Body must be valid JSON"}, 400)
    if not isinstance(payload, dict):
        return json_response({"error": "Body must be a JSON object"}, 400)

    try:
        validate_vnet_request(payload)
    except ValidationError as e:
        return json_response({"error": str(e)}, 400)

    table = get_table()
    rg, name = payload["resource_group"], payload["name"]

    if storage.get_vnet(table, rg, name) is not None:
        return json_response({"error": f"VNET {name} already exists in {rg}"}, 409)

    try:
        record = vnet_service.create_vnet(get_network(), payload)
    except HttpResponseError:
        logging.exception("Azure rejected the VNET request")
        return json_response({"error": "Azure request failed"}, 502)

    try:
        storage.save_vnet(table, rg, record)
    except ResourceExistsError:
        return json_response({"error": f"VNET {name} already exists in {rg}"}, 409)

    return json_response(record, 201)


def handle_list(req: func.HttpRequest) -> func.HttpResponse:
    return json_response(storage.list_vnets(get_table()))


def handle_get(req: func.HttpRequest) -> func.HttpResponse:
    rg = req.route_params.get("resource_group")
    name = req.route_params.get("name")
    record = storage.get_vnet(get_table(), rg, name)
    if record is None:
        return json_response({"error": "VNET not found"}, 404)
    return json_response(record)


@app.route(route="vnets", methods=["POST"])
def create_vnet_route(req: func.HttpRequest) -> func.HttpResponse:
    return handle_create(req)


@app.route(route="vnets", methods=["GET"])
def list_vnets_route(req: func.HttpRequest) -> func.HttpResponse:
    return handle_list(req)


@app.route(route="vnets/{resource_group}/{name}", methods=["GET"])
def get_vnet_route(req: func.HttpRequest) -> func.HttpResponse:
    return handle_get(req)