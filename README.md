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
   - region role IDs
    - kit queue channels
   - kit emoji IDs
6. Start the bot:

```bash
python main.py
```

## Commands

Tester queue commands now take a kit:

- `/openqueue kit:<kit>`
- `/closequeue kit:<kit>`
- `/next kit:<kit>`
- `/results`
- `/closetest`
- `/forceclosetest`
- `/passeval`

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
