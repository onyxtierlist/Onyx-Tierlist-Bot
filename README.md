# ONYX TIERS — Tier Test Bot

A modified self-hosted Minecraft PvP tier-testing bot with **Onyx Tiers** branding, kit selection, custom Discord emojis, and one queue per kit.

## Kits included

- Sword
- Axe
- Vanilla
- UHC
- Mace
- SMP
- NethPot
- Pot

## Queue separation

Queues are keyed by kit:

`KIT`

Examples:

- `vanilla`
- `sword`

Players from every region share the queue for their selected kit. Their saved region is still used for region roles and ticket categories.

## Custom kit emojis

Open `config/config.yml` and put the Discord emoji ID in the matching `emoji_id` field:

```yaml
kits:
    sword:
        label: "Sword"
        emoji_id: 123456789012345678
```

Use `0` if you do not want a custom emoji.

The bot fetches the custom emoji from the Discord guild and places it on the kit button. Make sure the bot can use the emoji (for external emoji, it needs the appropriate Discord permission/server access).

## Setup

1. Create your Discord application/bot in the Discord Developer Portal.
2. Enable all required intents.
3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and put your bot token in it.
5. Configure `config/config.yml`:
   - Onyx branding
   - channel IDs
   - category IDs
   - tester role ID
   - tier role IDs
    - optional per-kit `tier_roles` IDs for gamemode-specific tier roles
    - optional per-kit `ticket_category` IDs for gamemode-specific ticket categories
   - region role IDs
    - kit queue channels
   - kit emoji IDs
    - one `waitlist_role` ID for each kit, or `0` to disable that role
6. Start the bot:

```bash
python main.py
```

## Commands

Tester queue commands now take a kit:

- `/waitlist kit:<kit>`
- `/openqueue kit:<kit>`
- `/closequeue kit:<kit>`
- `/next kit:<kit>`
- `/results`
- `/closetest`
- `/forceclosetest`
- `/passeval`

Players are stored separately for each kit. `/results` requires the kit being graded,
removes that kit's `waitlist_role`, and keeps results for other kits intact. The bot
needs Manage Roles, and its role must be above the configured waitlist and tier roles.

To give each gamemode its own tier roles, add a `tier_roles` mapping inside each kit
in `config/config.yml`, using the same tier names as `bot.tiers`:

```yaml
kits:
    sword:
        tier_roles:
            lt5: 123456789012345678
            ht5: 123456789012345679
    axe:
        tier_roles:
            lt5: 223456789012345678
            ht5: 223456789012345679
```

Any tier omitted from a kit mapping is not assigned. Kits without `tier_roles` use
the legacy global `bot.tiers` mapping.

Regular tickets use the region category when `ticket_category` is `0` or omitted.
Set `ticket_category` inside a kit to place that gamemode's tickets in a specific
Discord category. High-tier tickets continue to use `catagories.highTests`.

## Database migration

SQLite automatically adds the new `kit` column to an existing `users` table and defaults old records to `sword`.

If you use MySQL, add the `kit` column to your existing `users` table before starting the modified bot:

```sql
ALTER TABLE users ADD COLUMN kit VARCHAR(50) NOT NULL DEFAULT 'sword';
```

## Branding

The embed branding is controlled from:

`config/config.yml`

```yaml
branding:
    name: "ONYX TIERS"
    color: 0x111111
    footer: "ONYX TIERS • Minecraft PvP Testing"
```

Change these values to adjust the bot's embeds without editing Python.

## Website sync (Discord bot → Render website)

The bot can push completed `/results` records directly to the live Onyx website.
The website remains the source used by the public tier-list pages; the Discord bot's
own database is not exposed to browsers.

Set these environment variables on the **Railway bot service**:

```text
WEBSITE_API_URL=https://YOUR-ONYX-WEBSITE.onrender.com/api/integrations/discord/result
ONYX_INGEST_TOKEN=the_same_long_random_secret_used_on_Render
```

On the **Render website service**, set:

```text
ONYX_INGEST_TOKEN=the_exact_same_secret
```

Do not put `ONYX_INGEST_TOKEN` into frontend JavaScript or commit it to GitHub.
After changing the Railway variables, redeploy/restart the bot. A successful `/results`
command will update the matching website player and kit ranking; a temporary website
failure will be logged but will not fail the Discord result command.

To test the connection, complete a real test and check the bot log for:
`Synced <player>'s <kit> result to the website.`
