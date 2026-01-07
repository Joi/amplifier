---
name: chanoyu
description: Tea ceremony (chanoyu) knowledge management and formal letter generation. Use when user mentions tea ceremony, chanoyu, writing Japanese tea letters, or adding tea ceremony knowledge.
version: 1.0.0
---

# Chanoyu - Tea Ceremony Tools

Two capabilities for Japanese tea ceremony (茶道/chanoyu):

1. **Add Knowledge** - Add concepts, sources, people to the chanoyu vault
2. **Generate Letters** - Create formal tea ceremony correspondence

## Vault Location

```
~/switchboard/chanoyu/
```

## 1. Adding Knowledge

When user wants to add tea ceremony knowledge:

### Step 1: Read the Structure Guide

```bash
cat ~/switchboard/chanoyu/_STRUCTURE.md
```

This is REQUIRED to understand file formats and conventions.

### Step 2: Create Content

Based on the structure guide:

1. Determine file type (concept, source, person, etc.)
2. Follow the template from _STRUCTURE.md exactly
3. Create file with proper YAML frontmatter
4. Update INDEX.md if adding a new concept
5. Add cross-links to related content

### Important Conventions

- **Japanese terms**: Always include kanji, romaji, and English
- **Cross-links**: Use Obsidian format `[[chanoyu/concepts/name|Display Name]]`
- **YAML frontmatter**: Required on all files
- **One concept = one file** in concepts/

## 2. Generating Letters

Three types of formal tea ceremony letters:

| Type | Japanese | Purpose |
|------|----------|---------|
| 後礼 (kōrei) | Thank-you | After attending a tea gathering |
| 案内状 (annaijō) | Invitation | Inviting guests to your gathering |
| 前礼 (zenrei) | Pre-event reply | Accepting an invitation |

### Interactive Questionnaire Approach

ALWAYS gather ALL information BEFORE generating:

#### For 後礼 (Thank-You Letter)

Ask user for:
1. **Event type**: 茶事 (chaji), 茶会 (chakai), お稽古 (okeiko)
2. **Event date**: When was it? (e.g., 12月15日)
3. **Host name**: Who hosted? (e.g., 斎藤先生)
4. **Venue**: Where? (e.g., 半月亭)
5. **Impressions**: 2-3 specific things that impressed them (utensils, atmosphere, moments)
6. **Formality**: Relationship to host (先生→謹啓/謹言, 同門→拝啓/敬具)
7. **Sender name**: Default 伊藤宗一

#### For 案内状 (Invitation)

Ask user for:
1. **Event date/time**: 令和七年一月十五日 午前十一時
2. **Venue**: 自宅茶室 or specific location
3. **Occasion**: 初釜, 炉開き, 口切, 茶名披露, 一般
4. **Time confirmed?**: Yes or morning/afternoon planned
5. **Recipient**: Name and relationship
6. **Guest count**: Single or multiple
7. **Personal touch**: Optional message
8. **Sender name**: Default 伊藤宗一

#### For 前礼 (Pre-Event Reply)

Ask user for:
1. **Event details**: Date and location accepting
2. **Host name**: Who invited them
3. **Formality**: Relationship to host
4. **Sender name**: Default 伊藤宗一

### Load Context Files

AFTER collecting answers, read:

```bash
cat ~/switchboard/chanoyu/writing/generator.md
cat ~/switchboard/chanoyu/writing/phrases/seasonal-greetings.md
cat ~/switchboard/chanoyu/writing/templates/invitation-patterns.md
cat ~/switchboard/chanoyu/writing/templates/thank-you.md
cat ~/switchboard/chanoyu/SEASONS.md
```

### Seasonal Calculations

Based on TODAY's date:

1. **Determine 旬** (ten-day period):
   - 上旬 (1st-10th)
   - 中旬 (11th-20th)
   - 下旬 (21st-end)

2. **Select 時候の挨拶** matching month + 旬

3. **Select 健康祈願** for season:
   - 春 (March-May)
   - 夏 (June-August)
   - 秋 (September-November)
   - 冬のはじめ (November-December)
   - 真冬 (December-February)

### Critical Formatting Rules

- **NO PUNCTUATION** in letter body (traditional etiquette)
- Do NOT use 、(comma) or 。(period)
- Use line breaks to indicate pauses
- Each phrase on its own line

### Save Location

```
~/switchboard/chanoyu/chakai/YYYY-MM-DD_venue_type/
```

Filename: `type_recipient.md`
- korei_ for 後礼
- annai_ for 案内状
- zenrei_ for 前礼

### Example Letters

```bash
cat ~/switchboard/chanoyu/chakai/2024-12-01_hangetsu-tei_soba-chaji/korei_saito.md
cat ~/switchboard/chanoyu/chakai/2024-12-03_joseian_rougetsu-chakai/korei_shibamura.md
```
