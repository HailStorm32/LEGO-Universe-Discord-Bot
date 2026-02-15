# LEGO Universe Discord Bot (Python Edition)

A Python rewrite of the original LEGO Universe Discord bot using `discord.py` (`discord` module), while preserving the original bot command surface and user-facing behavior.

## Overview

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Features](#features)
4. [Commands](#commands)

## Prerequisites

1. **Create a Discord Application**

   Follow Discord's official guide: https://discord.com/developers/docs/getting-started

   Invite URL template:

   `https://discord.com/api/oauth2/authorize?client_id={YOUR_BOTS_ID}&permissions=242666032192&scope=applications.commands%20bot`

2. **Have a LEGO Universe client data source**

   You need:

   - `locale.xml`
   - `cdclient.sqlite` (converted from `cdclient.fdb`)

   Typical paths/tools are unchanged from the original project.

## Setup

1. Clone:

   ```bash
   git clone https://github.com/MasterTemple/LEGO-Universe-Discord-Bot.git
   cd LEGO-Universe-Discord-Bot
   ```

2. Configure:

   ```bash
   cp .env.template .env
   ```

   Fill all required values in `.env`.

3. Install Python dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Start the bot:

   ```bash
   python main.py
   ```

5. Reload game data at runtime:

   Use `/reload` after changing `cdclient.sqlite` or `locale.xml`.

## Features

## Autocomplete

This allows users to search objects by their name instead of relying on knowing the internal object id.
![autocomplete](screenshots/autocomplete.gif)

## Message Embeds

Message embeds allow for organizing and displaying data in a much more visually appealing way.

They are indicated below by the colored bar on the left and the darker background.

**Normal Message**

![no embed](screenshots/no_embed.png)

**Message Embed**

![embed](screenshots/item.png)

## Message Components

Message components are the buttons underneath the embed. These allow for the user to execute related commands on an object.

For example, an item that can be earned can also be bought. Instead of having to use `/earn` and then `/buy`, the user can use `/earn` and then click the `Buy` button.

The green button indicates the current command. Disabled/faded buttons show that an item cannot be obtained through a certain method.

![message components](screenshots/components.png)

If the user clicks the `Buy` button, the message is edited to display the following

![message components](screenshots/component_buy.png)

## Paging

The current page index is indicated between the parenthesis in the title.

Page navigation can be controlled through the buttons on the bottom.

![/buy](screenshots/buy.png)

## External Links

The blue hyper-linked text will take the user to the corresponding page of hosted [LU Explorer](https://github.com/LUDevNet/lu-explorer) that is specified in the configuration.

## Commands

All original command names are preserved:

- `/activity`
- `/achievement`
- `/drop`
- `/get`
- `/mission`
- `/reload`
- `/skillitems`
- `/vendor`
- `/brick`
- `/earn`
- `/item`
- `/npc`
- `/report`
- `/skills`
- `/buy`
- `/enemy`
- `/level`
- `/package`
- `/reward`
- `/smash`
- `/cooldowngroup`
- `/execute`
- `/loottable`
- `/preconditions`
- `/skill`
- `/unpack`

### `/achievement`

View the stats of an achievement!

![/achievement](screenshots/achievement.png)

### `/activity`

View all rewards given from an activity!

![/activity](screenshots/activity.png)

### `/drop`

View all smashables that drop an item!

![/drop](screenshots/drop.png)

### `/get`

View how to get an item!

![/get](screenshots/get.png)

### `/mission`

View the stats of a mission!

![/mission](screenshots/mission.png)

### `/reload`

Reload the data from the cdclient.sqlite and locale.xml!

![/reload](screenshots/reload.png)

### `/skillitems`

View all items that have a skill!

![/skillitems](screenshots/skillitems.png)

### `/vendor`

View all items sold from a vendor!

![/vendor](screenshots/vendor.png)

### `/brick`

View the stats of a brick!

![/brick](screenshots/brick.png)

### `/earn`

View all missions that reward an item!

![/earn](screenshots/earn.png)

### `/item`

View the stats of an item!

![/item](screenshots/item.png)

### `/npc`

View all missions from an NPC!

![/npc](screenshots/npc.png)

### `/report`

Open a dialog to report anything about this bot!

### `/skills`

View all skills attached to an item!

![/skills](screenshots/skills.png)

### `/buy`

View all vendors that sell an item!

![/buy](screenshots/buy.png)

### `/enemy`

View the stats of an enemy!

![/enemy](screenshots/enemy.png)

### `/level`

View stats about a level in LEGO Universe!

![/level](screenshots/level.png)

### `/package`

View all items given from a package!

![/package](screenshots/package.png)

### `/reward`

View all activities that drop an item!

![/reward](screenshots/reward.png)

### `/smash`

View all enemys given from a package!

![/smash](screenshots/smash.png)

### `/cooldowngroup`

View the skills in a cooldowngroup!

![/cooldowngroup](screenshots/cooldowngroup.png)

### `/execute`

Open a dialog to execute multiple commands on this bot!

![/execute dialog](screenshots/execute_dialog.png)

![/execute](screenshots/execute.png)

### `/loottable`

View all items in a loot table!

![/loottable](screenshots/loottable.png)

### `/preconditions`

View the preconditions to use an item!

![/preconditions](screenshots/preconditions.png)

### `/skill`

View the stats of a skill!

![/skill](screenshots/skill.png)

### `/unpack`

View all packages that drop an item!

![/unpack](screenshots/unpack.png)
