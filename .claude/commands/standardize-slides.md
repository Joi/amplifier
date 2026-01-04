---
description: Standardize the visual style of a Google Slides presentation using AI analysis
category: productivity
allowed-tools: Bash, Read, Write, Glob
---

# Claude Command: Standardize Slides

This command analyzes a Google Slides presentation and standardizes its visual style across all slides.

## Usage

```
/standardize-slides <google-slides-url>
```

Or interactively:

```
/standardize-slides
```

## What This Command Does

1. **Parses** the Google Slides URL to extract the presentation ID
2. **Authenticates** with Google APIs (prompts for OAuth on first run)
3. **Exports** each slide as an image for AI analysis
4. **Analyzes** visual inconsistencies using Nano Banana Pro (Gemini 3 Pro):
   - Font families and sizes
   - Color schemes
   - Header/body text styles
   - Background colors
   - Spacing and alignment
5. **Generates** a standardization recommendation based on the most common styles
6. **Presents** proposed changes interactively for your review
7. **Applies** approved changes via Google Slides API (keeps slides editable)

## Prerequisites

1. **Google Cloud Project** with Slides API enabled
2. **OAuth credentials** (credentials.json) or service account
3. **GEMINI_API_KEY** environment variable set

## First-Time Setup

If you haven't set up Google Slides API access:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Enable the "Google Slides API" and "Google Drive API"
4. Create OAuth 2.0 credentials (Desktop App type)
5. Download as `credentials.json` and place in `~/.config/amplifier/google/`

## Interactive Flow

```
$ /standardize-slides https://docs.google.com/presentation/d/1abc.../edit

Analyzing 24 slides...

Style Analysis:
  FONTS DETECTED:
  - Headers: Montserrat Bold 32pt (18 slides), Arial 28pt (6 slides)
  - Body: Open Sans 16pt (20 slides), Roboto 14pt (4 slides)

  COLORS DETECTED:
  - Backgrounds: #FFFFFF (22), #F5F5F5 (2)
  - Header text: #333333 (21), #000000 (3)

  INCONSISTENCIES:
  - Slide 4, 7, 12: Different header font
  - Slide 9: Different background color
  - Slide 15, 22: Body text size varies

Recommended Standard (based on majority):
  Header: Montserrat Bold 32pt #333333
  Body: Open Sans 16pt #666666
  Background: #FFFFFF

Accept? [Y/n/edit]
```

## Arguments

$ARGUMENTS

## Notes

- Changes preserve editability - this uses the Slides API, not image replacement
- Original presentation is modified in-place (consider making a copy first)
- Rate limited to avoid Google API quotas
