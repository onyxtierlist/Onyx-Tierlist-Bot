# Onyx Tier API

This patch adds a public HTTP endpoint for the Fabric Onyx Tier Tagger.

Endpoint:
`GET /api/player/{minecraft_username}`

Response example:
```json
{"found":true,"highest_tier":"ht2","emoji":"🔥"}
```

Railway should expose the service on its normal `PORT` environment variable. The mod's config should point at:
`https://YOUR-RAILWAY-DOMAIN/api/player`

The API only returns the highest tier and a display emoji; it does not expose Discord IDs.
