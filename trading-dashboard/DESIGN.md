# DESIGN.md — IBT Trading Bot v2.0 (Enhanced)

## Overview

The IBT Trading Bot dashboard provides real-time monitoring, strategy management, and performance analytics for cryptocurrency trading. The visual language merges **financial precision** with **Caribbean energy** — dark backgrounds with deep ocean blues and vibrant tropical accents.

Mobile-first, optimized for touch interaction on phones and tablets.

---

## Design Philosophy (Enhanced)

### Perception-First Framework (5-Layer Stack)
Design decisions follow the Perception-First diagnostic framework — fix lower layers before higher ones:

- **L0 — Visual Noise**: Reduce competing elements, establish breathing room
- **L1 — Focal Hierarchy**: Clear eye path, dominant metrics stand out
- **L2 — Trust Rhythm**: Consistent spacing, aligned baselines, tinted neutrals
- **L3 — Value Communication**: Stats tell a story, not just display numbers
- **L4 — Arousal**: Does it feel premium before the user can explain why?

### Anti-Slop Rules (from Taste Skill / Impeccable)
- NO Inter-for-everywhere (domain-appropriate hierarchy)
- NO purple-to-blue generic gradients (Caribbean-specific palette)
- NO cards-nested-in-cards (flat hierarchy, depth via layered shadows)
- NO pill-shaped badges (squared with 6px radius)
- NO pure `#000000` backgrounds (tinted navy-black `#090d14`)
- NO pure gray neutrals (blue-tinted grays `#5a6a7e`, `#3d4d60`)
- NO `box-shadow` using pure black (tinted shadows matching background hue)

---

## Colors (OKLCH-Derived Tinted System)

### Core Backgrounds
| Token | Hex | Role | Usage |
|-------|-----|------|-------|
| `--color-primary` | `#090d14` | Deep navy-black | Page background (tinted, NOT pure black) |
| `--color-secondary` | `#0f1620` | Dark slate | Cards, panels, nav (blue undertone) |

### Accents
| Token | Hex | Role | Usage |
|-------|-----|------|-------|
| `--color-tertiary` | `#0F4C75` | Caribbean blue | Primary accent, CTAs, active states |
| `--color-accent` | `#D4AF37` | Gold | Profit indicators, premium, achievements |
| `--color-alert` | `#FF6B35` | Tropical orange | Negative/urgent states |
| `--color-success` | `#00C9A7` | Seafoam green | Positive states, wins |
| `--color-danger` | `#EF476F` | Coral red | Critical, stop-loss, liquidation |

### Tinted Neutrals (NOT Pure Gray)
| Token | Hex | Role |
|-------|-----|------|
| `--color-neutral` | `#e8ecf1` | Ice white — primary text |
| `--color-muted` | `#5a6a7e` | Slate — secondary text, labels |
| `--color-dim` | `#3d4d60` | Dim — borders, placeholders |

### Glass System
| Token | Value | Usage |
|-------|-------|-------|
| `--color-glass-bg` | `rgba(15, 22, 32, 0.65)` | Translucent card background |
| `--color-glass-border` | `rgba(30, 50, 70, 0.45)` | Card border (tinted blue) |

### Gradients
- **Ocean**: `radial-gradient(ellipse at 30% 20%, rgba(15,76,117,0.3) 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, rgba(15,76,117,0.15) 0%, transparent 50%)`
- **Sunset P&L**: `linear-gradient(135deg, #FF6B35 0%, #D4AF37 50%, #00C9A7 100%)`

---

## Typography

| Style | Font | Size | Weight | Line-height | Letter-spacing | Usage |
|-------|------|------|--------|-------------|----------------|-------|
| Display-LG | Inter | 2.0rem | 700 | 1.0 | -0.04em | Hero portfolio value |
| Display | Inter | 1.5rem | 700 | 1.0 | -0.03em | Large KPI numbers |
| Stat | Inter | 1.0rem | 600 | 1.0 | -0.02em | Standard metrics |
| Body | Inter | 0.875rem | 400 | 1.5 | normal | Body text |
| Label | Inter | 0.65rem | 600 | 1.0 | 0.06em | Uppercase section labels |
| Mono-LG | JetBrains Mono | 2.0rem | 700 | 1.0 | -0.04em | Large prices |
| Mono | JetBrains Mono | 1.0rem | 600 | 1.0 | -0.02em | Standard numbers |
| Mono-SM | JetBrains Mono | 0.75rem | 600 | 1.0 | normal | Small data |

---

## Layout & Spacing

- **Grid**: 4px base grid system
- **Container**: max-width 1440px, auto margins, 16px padding
- **Sections**: 24px gap between sections (16px on mobile)
- **Touch targets**: 44px minimum height/width
- **Safe areas**: `env(safe-area-inset-bottom)` for home indicator
- **Dashboard columns**: Single column mobile → 2-col tablet → 5-col desktop (3+2 split)

---

## Elevation (Layered Depth)

NOT just `box-shadow: 0 4px 6px black`. Layered shadows with tinted ambient glow:

| Level | Shadow | Usage |
|-------|--------|-------|
| Default | `0 1px 2px rgba(0,0,0,0.3), 0 4px 12px rgba(0,0,0,0.2), 0 0 1px rgba(15,76,117,0.1)` | Standard cards |
| Elevated | above + `0 8px 24px rgba(0,0,0,0.25)` | Important metrics |
| Sunken | `inset 0 1px 3px rgba(0,0,0,0.3)` | Secondary info |
| Float | `0 16px 40px rgba(0,0,0,0.3)` | Modals |

---

## Motion & Animation

| Effect | Duration | Easing | Usage |
|--------|----------|--------|-------|
| Page enter | 300ms | `cubic-bezier(0.4, 0, 0.2, 1)` | Fade-in-up |
| Card hover | 250ms | same | translateY(-1px) + shadow |
| Button press | 150ms | same | translateY(1px) |
| Price flash | 400ms | same | Green/red background sweep |
| Skeleton shimmer | 1600ms | infinite | Wave animation |
| Live pulse | 2000ms | cubic-bezier | LIVE badge |

**Respect** `prefers-reduced-motion: reduce` — all animations disabled.

---

## Components

### GlassCard
Primary container. Depth via layered shadows (not border-heavy).
- Variants: `default`, `up` (green sweep), `down` (red sweep), `gold`, `alert`
- Depths: `default`, `elevate`, `sunken`, `float`
- Padding: `sm` (12px), `md` (16px), `lg` (20px), `none`

### StatusBadge
Squared badge (6px radius, NOT pill-shaped).
- `live` — red with pulsing dot
- `paper` — gold tinted
- `strategy` — blue tinted
- `success` — green, `alert` — orange

### StatBlock
Three-line KPI display: label → value → change%. Uses `mono` font for numbers, tabular-nums for alignment.

### ShimmerCard
Skeleton loader matching layout shape. Supports `height` for simple blocks or `lines` for text-like skeletons.

## Texture (Anti-Slop)

Noise grain overlay via SVG turbulence filter at 2.5% opacity. Applied to `body::before` as fixed layer. Creates subtle texture that breaks the "sterile flat vector" look.

---

*Version: 2.0 — Enhanced with Impeccable, Taste Skill, Perception-First Design*
*Last updated: 2026-06-01*
