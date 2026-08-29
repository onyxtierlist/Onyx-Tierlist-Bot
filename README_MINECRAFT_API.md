# Onyx Minecraft API

The bot now exposes a read-only endpoint for the Onyx Fabric Minecraft mod:

`GET /api/player/<MinecraftUsername>`

Example response:

```json
{
  "username": "Steve",
  "uuid": "...",
  "highest_tier": "HT1",
  "emoji": "◆",
  "kit": "sword",
  "region": "NA",
  "last_test": 1770000000,
  "kits": []
}
```

The highest tier is calculated from every row in `user_kits` for that Minecraft username using the tier order from `config/config.yml`.

A health check is also available at `/health`.

## Railway

Use the normal bot start command. Railway supplies `PORT`; the API binds to `0.0.0.0` automatically.

After deployment, the public endpoint will be:

`https://YOUR-RAILWAY-DOMAIN/api/player/PLAYERNAME`

Put the base URL `https://YOUR-RAILWAY-DOMAIN/api/player` in `config/onyx_tagger.properties` on the Minecraft client.
