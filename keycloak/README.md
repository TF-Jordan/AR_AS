# Keycloak Configuration for RaaS Platform

## Overview

Keycloak provides OAuth2/OpenID Connect authentication for the multi-tenant RaaS platform. It manages tenant authentication, authorization, and JWT token issuance with custom claims.

## Architecture

- **Version**: Keycloak 25.0
- **Database**: PostgreSQL (shared with main application, separate schema `keycloak`)
- **Realm**: `raas`
- **Port**: 8080 (default, configurable via `KEYCLOAK_PORT`)

## Realm Configuration

The realm `raas` is automatically imported on first startup from `./keycloak/realms/raas-realm.json`.

### Pre-configured Clients

1. **raas-api** (Backend API)
   - Type: Confidential client
   - Client ID: `raas-api`
   - Client Secret: `raas-api-secret-change-in-production` (⚠️ CHANGE IN PRODUCTION)
   - Flows: Authorization Code, Direct Access Grants, Service Account
   - Custom Claims:
     - `tenant_id`: Tenant identifier for multi-tenant isolation
     - `client_id`: Client identifier for rate limiting and tracking

2. **raas-admin-ui** (Admin Frontend)
   - Type: Public client
   - Client ID: `raas-admin-ui`
   - Flow: Authorization Code (PKCE)
   - Purpose: Next.js admin interface

### Pre-configured Roles

- **admin**: Full platform administrator
- **tenant_admin**: Tenant-level administrator
- **api_user**: Standard API user

### Default Users

- **Username**: `raas-admin`
- **Password**: `admin123` (temporary, must change on first login)
- **Email**: admin@raas-platform.local
- **Roles**: admin
- **Attributes**:
  - `tenant_id`: platform
  - `client_id`: platform-admin

## Environment Variables

Configure in `.env`:

```bash
# Keycloak Authentication
KEYCLOAK_HOST=localhost
KEYCLOAK_PORT=8080
KEYCLOAK_REALM=raas
KEYCLOAK_CLIENT_ID=raas-api
KEYCLOAK_CLIENT_SECRET=your-client-secret-change-in-production
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
```

## Starting Keycloak

### With Docker Compose

```bash
# Start all services including Keycloak
docker compose up -d

# Check Keycloak logs
docker compose logs -f keycloak

# Verify health
curl http://localhost:8080/health/ready
```

### Access Admin Console

- **URL**: http://localhost:8080
- **Admin Username**: admin (from `KEYCLOAK_ADMIN`)
- **Admin Password**: admin (from `KEYCLOAK_ADMIN_PASSWORD`)

## JWT Token Structure

Tokens issued by Keycloak contain the following custom claims:

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "tenant_id": "tenant_abc123",
  "client_id": "client_xyz789",
  "preferred_username": "username",
  "realm_access": {
    "roles": ["api_user"]
  },
  "iat": 1234567890,
  "exp": 1234571490,
  "iss": "http://localhost:8080/realms/raas"
}
```

## Adding Tenants

To add a new tenant, create a user with custom attributes:

1. Navigate to **Users** → **Add User**
2. Fill in basic information
3. Under **Attributes**, add:
   - `tenant_id`: Unique tenant identifier (e.g., `tenant_client123`)
   - `client_id`: Client identifier for API calls (e.g., `client_123`)
4. Assign appropriate roles (`tenant_admin` or `api_user`)
5. Set credentials under **Credentials** tab

## OAuth2 Flow Example

### 1. Get Token (Resource Owner Password Credentials)

```bash
curl -X POST http://localhost:8080/realms/raas/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=raas-api" \
  -d "client_secret=raas-api-secret-change-in-production" \
  -d "username=raas-admin" \
  -d "password=admin123"
```

### 2. Use Token in API Requests

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client_123",
    "product_id": "prod_abc",
    "comment": "Excellent produit!",
    "top_k": 10
  }'
```

## Security Recommendations

### Production Configuration

1. **Change Default Secrets**:
   - Update `KEYCLOAK_ADMIN_PASSWORD`
   - Update `client_secret` for `raas-api` client
   - Generate strong passwords for all users

2. **Enable HTTPS**:
   - Set `KC_HOSTNAME_STRICT=true`
   - Configure SSL certificates
   - Update `KC_HTTP_ENABLED=false`

3. **Password Policy**:
   - Already configured with `hashIterations(27500)`
   - Consider adding: minimum length, special characters, etc.

4. **Brute Force Protection**:
   - Already enabled
   - Max failures: 5
   - Lockout duration: 15 minutes

5. **Token Lifespans**:
   - Access Token: 1 hour (3600s)
   - Refresh Token: 30 days (max)
   - SSO Session: 10 hours
   - Adjust based on security requirements

## Troubleshooting

### Keycloak won't start

```bash
# Check PostgreSQL is healthy
docker compose ps postgres

# Check Keycloak logs
docker compose logs keycloak

# Verify database connection
docker compose exec postgres psql -U postgres -d ar_as_db -c "\dn"
```

### Realm import failed

```bash
# Check realm file exists
ls -la keycloak/realms/raas-realm.json

# Verify JSON syntax
cat keycloak/realms/raas-realm.json | jq .

# Check volume mount
docker compose exec keycloak ls -la /opt/keycloak/data/import
```

### JWT verification fails

1. Verify Keycloak is accessible from API container
2. Check `KEYCLOAK_HOST` environment variable in API
3. Verify token issuer matches: `http://keycloak:8080/realms/raas`

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth2 Flows](https://www.keycloak.org/docs/latest/securing_apps/#_oidc)
- [Token Claims](https://www.keycloak.org/docs/latest/server_admin/#_protocol-mappers)
- [Realm Export/Import](https://www.keycloak.org/docs/latest/server_admin/#_export_import)
