---
version: alpha
name: Apple
description: A photography-first interface that turns marketing into a museum gallery. Edge-to-edge product tiles alternate light and dark canvases, framed by SF Pro Display headlines with negative letter-spacing and a single Action Blue (#0066cc) interactive color.

colors:
  primary: "#0066cc"
  primary-focus: "#0071e3"
  primary-on-dark: "#2997ff"
  ink: "#1d1d1f"
  body: "#1d1d1f"
  body-on-dark: "#ffffff"
  body-muted: "#cccccc"
  ink-muted-80: "#333333"
  ink-muted-48: "#7a7a7a"
  divider-soft: "#f0f0f0"
  hairline: "#e0e0e0"
  canvas: "#ffffff"
  canvas-parchment: "#f5f5f7"
  surface-pearl: "#fafafc"
  surface-tile-1: "#272729"
  surface-tile-2: "#2a2a2c"
  surface-tile-3: "#252527"
  surface-black: "#000000"
  on-primary: "#ffffff"
  on-dark: "#ffffff"

typography:
  hero-display:
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif"
    fontSize: 56px
    fontWeight: 600
    lineHeight: 1.07
    letterSpacing: -0.28px
  display-lg:
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif"
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: 0
  display-md:
    fontFamily: "SF Pro Text, system-ui, -apple-system, sans-serif"
    fontSize: 34px
    fontWeight: 600
    lineHeight: 1.47
    letterSpacing: -0.374px
  lead:
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif"
    fontSize: 28px
    fontWeight: 400
    lineHeight: 1.14
    letterSpacing: 0.196px
  tagline:
    fontFamily: "SF Pro Display, system-ui, -apple-system, sans-serif"
    fontSize: 21px
    fontWeight: 600
    lineHeight: 1.19
    letterSpacing: 0.231px
  body-strong:
    fontFamily: "SF Pro Text, system-ui, -apple-system, sans-serif"
    fontSize: 17px
    fontWeight: 600
    lineHeight: 1.24
    letterSpacing: -0.374px
  body:
    fontFamily: "SF Pro Text, system-ui, -apple-system, sans-serif"
    fontSize: 17px
    fontWeight: 400
    lineHeight: 1.47
    letterSpacing: -0.374px
  caption:
    fontFamily: "SF Pro Text, system-ui, -apple-system, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.43
    letterSpacing: -0.224px
  button-large:
    fontFamily: "SF Pro Text, system-ui, -apple-system, sans-serif"
    fontSize: 18px
    fontWeight: 300
    lineHeight: 1.0
    letterSpacing: 0
  nav-link:
    fontFamily: "SF Pro Text, system-ui, -apple-system, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: -0.12px

rounded:
  none: 0px
  sm: 8px
  md: 11px
  lg: 18px
  pill: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 17px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 80px
---

## Apple Design Principles

### Key Characteristics
- Photography-first presentation; UI recedes so the product can speak
- Alternating full-bleed tile sections: white/parchment ↔ near-black
- Single blue accent (#0066cc) for all interactive elements
- SF Pro Display + SF Pro Text with negative letter-spacing at display sizes
- Whisper-soft elevation used only for product imagery
- No decorative gradients, no shadows on chrome

### Color Usage
- **Action Blue** (#0066cc): All links, CTAs, focus signals
- **Near-Black Ink** (#1d1d1f): All text on light surfaces
- **Pure White** (#ffffff): Dominant canvas
- **Parchment** (#f5f5f7): Alternating light tiles, footer

### Typography Rules
- Body copy at 17px, not 16px
- Weight 600 for headlines, not 700
- Negative letter-spacing at display sizes (-0.28 → -0.374px)
- Line-height 1.47 for body copy

### Button Styles
- Primary: Blue pill (#0066cc), rounded pill shape
- Secondary: Ghost pill with blue border
- Active state: transform scale(0.95)

### Layout
- Full-bleed tiles with 80px vertical padding
- Color change acts as section divider
- Max content width ~980px for text, ~1440px for grids

### Do's
- Use single blue accent for all interactions
- Set headlines with negative letter-spacing
- Alternate light and dark tiles for rhythm
- Reserve shadow for product imagery only

### Don'ts
- Don't introduce second accent color
- Don't add shadows to cards or buttons
- Don't use gradients as decorative backgrounds
- Don't set body copy at weight 500
