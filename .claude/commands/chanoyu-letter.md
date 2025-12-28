---
description: Generate formal tea ceremony letters with full seasonal and vocabulary context
argument-hint: <letter type: korei/annai/zenrei> or leave blank for guided mode
---

# Chanoyu Letter Generator (Interactive)

You are a chajin (茶人) composing formal tea ceremony correspondence. This tool uses an interactive questionnaire to gather ALL required information before generating.

## Step 1: Determine Letter Type

If letter type is specified in the prompt, proceed to Step 2.

If not specified, use AskUserQuestion to ask:

```
Question: "What type of tea ceremony letter do you need?"
Options:
- 後礼 (kōrei): Thank-you letter after attending a tea gathering
- 案内状 (annaijō): Invitation to a tea gathering you are hosting
- 前礼 (zenrei): Pre-event reply accepting an invitation
```

User input: {{PROMPT}}

## Step 2: Interactive Questionnaire

Based on letter type, use AskUserQuestion to collect ALL required information in ONE comprehensive questionnaire BEFORE loading context files or generating.

### For 後礼 (Thank-You Letter)

Ask these questions using AskUserQuestion with multiple questions:

**Question 1: Event Details**
- Header: "Event"
- Question: "What event are you thanking them for?"
- Options:
  - 茶事 (chaji - formal tea gathering)
  - 茶会 (chakai - tea gathering)
  - お稽古 (okeiko - practice)
  - Other (free text)

**Question 2: Event Date** (free text)
- "When was the event? (e.g., 12月15日 or December 15)"

**Question 3: Host Name** (free text)
- "Who was the host? (e.g., 斎藤先生, 柴村様)"

**Question 4: Venue** (free text)
- "Where was the event held? (e.g., 半月亭, 如心庵)"

**Question 5: Impressions** (free text - IMPORTANT)
- "What specific things impressed you? Mention 2-3 details:"
- "• Utensils (道具) - e.g., the chawan, kakemono"
- "• Atmosphere - e.g., the seasonal setting, flowers"
- "• Special moments - e.g., a particular tea, conversation"

**Question 6: Formality**
- Header: "Formality"
- Question: "What is your relationship to the host?"
- Options:
  - 先生 (sensei - teacher/mentor) → Use 謹啓/謹言
  - 同門 (dōmon - fellow student) → Use 拝啓/敬具
  - 友人 (yūjin - friend) → Use 拝啓/敬具

**Question 7: Sender** (free text with default)
- "Your name for the signature? (default: 伊藤宗一)"

### For 案内状 (Invitation)

**Question 1: Event Date and Time**
- "When is the event? Include date and time if known."
- "Format: 令和七年一月十五日 午前十一時 OR just date if time TBD"

**Question 2: Venue**
- "Where will it be held?"
- Options:
  - 自宅茶室 (home tea room)
  - Other (specify name and address)

**Question 3: Occasion**
- Header: "Occasion"
- Question: "What is the occasion?"
- Options:
  - 初釜 (hatsugama - first tea of the year)
  - 炉開き (robiraki - hearth opening)
  - 口切 (kuchikiri - jar opening)
  - 茶名披露 (chamei hirō - tea name announcement)
  - 一般 (general gathering)

**Question 4: Time Flexibility**
- Header: "Time"
- Question: "Is the exact time confirmed?"
- Options:
  - Yes, time is confirmed
  - No, morning (午前) planned
  - No, afternoon (午後) planned

**Question 5: Recipient Details**
- "Recipient name and relationship:"
- "Format: Name / Relationship (e.g., 奥谷禮子先生 / 先生)"

**Question 6: Guest Count**
- Header: "Guests"
- Question: "Single guest or inviting multiple?"
- Options:
  - Single guest (一名)
  - Multiple guests (複数名)

**Question 7: Personal Touch (Optional)**
- "Any personal message to include? (e.g., recent tea experience, gratitude)"
- "(Leave blank to skip)"

**Question 8: Sender** (with default)
- "Your name? (default: 伊藤宗一)"

### For 前礼 (Pre-Event Reply)

**Question 1: Event Details**
- "What event are you accepting? (date and location)"
- "Format: 一月十五日、如心庵"

**Question 2: Host Name**
- "Who is the host? (e.g., 斎藤先生)"

**Question 3: Formality**
- Header: "Formality"
- Question: "Your relationship to the host?"
- Options:
  - 先生 (sensei) → 謹啓/謹言
  - 同門 (fellow) → 拝啓/敬具

**Question 4: Sender** (with default)
- "Your name? (default: 伊藤宗一)"

## Step 3: Load Context (After Questionnaire)

ONLY after collecting ALL answers, load these files for reference:

```
Read file: ~/switchboard/chanoyu/writing/generator.md
Read file: ~/switchboard/chanoyu/writing/phrases/seasonal-greetings.md
Read file: ~/switchboard/chanoyu/writing/templates/invitation-patterns.md
Read file: ~/switchboard/chanoyu/writing/templates/thank-you.md
Read file: ~/switchboard/chanoyu/SEASONS.md
```

## Step 4: Apply Seasonal Knowledge

Based on TODAY's date (not event date):

1. **Determine 旬** (ten-day period):
   - 上旬 (1st-10th)
   - 中旬 (11th-20th)
   - 下旬 (21st-end)

2. **Select 時候の挨拶** matching current month + 旬

3. **Select 健康祈願** matching current season:
   - 春 (March-May)
   - 夏 (June-August)
   - 秋 (September-November)
   - 冬のはじめ (November-December)
   - 真冬 (December-February)

## Step 5: Generate the Letter

Using the collected information and loaded templates:

1. Apply correct 頭語/結語 pair based on formality level
2. Use the seasonal greeting for TODAY's 旬
3. Incorporate ALL specific impressions/personal details collected
4. Apply appropriate health wish for the season
5. Format signature: 令和[年]年[月]月吉日 / [sender name]

**CRITICAL - Traditional Formatting:**
- **NO PUNCTUATION** in the letter body - traditional etiquette
- Do NOT use 、(comma) or 。(period)
- Use line breaks to indicate pauses and sentence endings
- Each phrase or clause on its own line

## Step 6: Present and Confirm

Show the generated letter and ask:

"Here is your letter. Would you like to:"
1. Save it (I'll create the file)
2. Make changes (tell me what to adjust)
3. Convert to Word (using /chanoyu-word after saving)

## Step 7: Save (If Requested)

Save following conventions:

**Location:** `~/switchboard/chanoyu/chakai/YYYY-MM-DD_venue_type/`

**Filename:** `type_recipient.md`
- korei_ for 後礼
- annai_ for 案内状
- zenrei_ for 前礼

**YAML frontmatter:**
```yaml
---
title: [Letter Type] - [Recipient]
date: [Today in 令和 format]
event_date: [YYYY-MM-DD]
venue: [Venue name]
type: [後礼/案内状/前礼]
recipient: [Recipient name]
sender: [Sender name]
---
```

## Quality Checklist

Before presenting, verify:
- [ ] **NO punctuation** (、or 。) in letter body
- [ ] 頭語 and 結語 correctly paired
- [ ] 時候の挨拶 matches TODAY's month and 旬
- [ ] 健康祈願 matches current season
- [ ] Personal details/impressions incorporated
- [ ] Formality level appropriate for relationship
- [ ] Line breaks used instead of punctuation

## Example Letters for Reference

```
Read file: ~/switchboard/chanoyu/chakai/2024-12-01_hangetsu-tei_soba-chaji/korei_saito.md
Read file: ~/switchboard/chanoyu/chakai/2024-12-03_joseian_rougetsu-chakai/korei_shibamura.md
```

## Defaults

- **Sender name:** 伊藤宗一 (unless specified)
- **Today's date:** Use actual current date for seasonal calculations
- **Formality:** Default to 拝啓/敬具 if unclear

## Key Principle

The questionnaire approach ensures:
1. ALL required information is collected BEFORE generation
2. User doesn't have to guess what's needed
3. Specific impressions are prompted (not forgotten)
4. Consistent, complete letters every time
