# Azure VNET API

A small serverless API (Azure Functions, Python) that creates an Azure Virtual
Network with multiple subnets, stores the result in Azure Table Storage, and
lets authenticated users retrieve what was created.

## Architecture

Client → Easy Auth (Entra ID) → Azure Function (HTTP triggers) →
(1) Azure Network SDK creates the VNET, (2) Table Storage stores the record.

- `function_app.py`: HTTP routes and status codes
- `services/validation.py`: request validation (CIDR, containment, overlap, duplicate names)
- `services/vnet_service.py`: builds the Azure request and creates the VNET
- `services/storage.py`: Table Storage read/write
- `infra/main.bicep`: storage, function app, managed identity, role assignment, authentication

## API

| Method | Route | Description |
|---|---|---|
| POST | `/api/vnets` | Create a VNET with subnets and store the result |
| GET | `/api/vnets` | List stored VNETs |
| GET | `/api/vnets/{resource_group}/{name}` | Get one stored VNET |

Example request body:

```json
{
  "name": "vnet1",
  "resource_group": "rg-vnet-api",
  "location": "centralindia",
  "address_space": "10.0.0.0/16",
  "subnets": [
    {"name": "web", "prefix": "10.0.1.0/24"},
    {"name": "db", "prefix": "10.0.2.0/24"}
  ]
}
```

Responses: `201` created, `400` invalid input, `401` not authenticated,
`404` not found, `409` already exists, `502` Azure rejected the request.

## Authentication and authorization

The Function App is protected by its built-in authentication feature (Easy Auth, part of the App Service platform that hosts Function Apps) with Microsoft Entra ID as the identity provider.Requests without a valid token get `401`. Any authenticated
user is authorized; there are no role or group checks, as required.

Separately, the Function's managed identity has the Network Contributor role on
the resource group so it can create VNETs. This is service-to-Azure
authorization, not user authorization.

## Run the tests (no Azure account needed)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Azure calls are replaced by mocks in the tests.

## Deploy to your own subscription

1. Create an Entra ID app registration and note its client ID.
2. Create a resource group and deploy:
```powershell
   az group create --name rg-vnet-api --location centralindia
   az deployment group create --resource-group rg-vnet-api `
     --template-file infra/main.bicep --parameters authClientId=<client-id>
```
3. Publish the code:
```powershell
   func azure functionapp publish <functionAppName>
```
4. Get a token and call the API:
```powershell
   $token = az account get-access-token --resource api://<client-id> --query accessToken -o tsv
   curl -H "Authorization: Bearer $token" https://<hostname>/api/vnets
```

For local runs, copy `local.settings.sample.json` to `local.settings.json`
and fill in the values. That file is git-ignored.

## Status and limitations

- The logic is covered by unit tests with mocked Azure clients. **It has not
  been deployed or run against a real Azure subscription**, and the Bicep
  template has not been deployed.
- VNET creation is synchronous: the request waits for Azure to finish. For
  larger workloads I would move this to a queue and worker.
- Storage uses an account key connection string. I would switch to managed
  identity access.
- No update or delete routes.