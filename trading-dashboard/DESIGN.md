# DESIGN.md — IBT Trading Bot

## Overview

The IBT Trading Bot is a multi-platform cryptocurrency trading system combining centralized exchange (CEX) arbitrage, decentralized exchange (DEX) trading on Solana, and AI-driven market prediction. The dashboard provides real-time monitoring, strategy management, and performance analytics.

The visual language merges **financial precision** with **Caribbean energy** — dark backgrounds with deep ocean blues and vibrant tropical accents. The interface is mobile-first, optimized for touch interaction on phones and tablets.

## Colors

- **Primary (#0A0E17):** Deep ocean navy — the base. Used for page backgrounds and the deepest layers.
- **Secondary (#111827):** Dark slate — card backgrounds, panels, navigation. Sits one layer above primary.
- **Tertiary (#0F4C75):** Caribbean blue — primary accent. Used for active states, buy signals, key metrics highlights.
- **Accent (#D4AF37):** Gold — secondary accent. Used for profit indicators, premium features, and key alerts.
- **Alert (#FF6B35):** Tropical orange — negative/urgent states. Used for sell signals, stop-loss triggers, risk warnings.
- **Success (#00C9A7):** Seafoam green — positive states. Used for wins, profitable trades, active positions.
- **Danger (#EF476F):** Coral red — critical states. Used for max drawdown, critical errors, liquidation risk.
- **Neutral (#F1F5F9):** Ice white — primary text. High contrast on dark backgrounds.
- **Muted (#64748B):** Slate gray — secondary text, labels, timestamps. Reduces visual noise.
- **Glow-Blue (#3B82F6):** Electric blue — interactive elements, links, hover states. Creates depth with glow effects.
- **Glow-Gold (#FBBF24):** Warm gold — sparkle effects on achievements, milestone animations.
- **Gradient-Ocean:** `linear-gradient(135deg, #0F4C75 0%, #0A0E17 50%, #1A1C1E 100%)` — used for hero sections and card backgrounds.
- **Gradient-Sunset:** `linear-gradient(135deg, #FF6B35 0%, #D4AF37 50%, #00C9A7 100%)` — used for P&L charts and performance visualizations.
- **Glass-BG:** `rgba(17, 24, 39, 0.6)` — translucent glass-morphism background with `backdrop-filter: blur(12px)`.

## Typography

- **Display (h1):**
  - fontFamily: Inter
  - fontSize: 1.75rem
  - fontWeight: 700
  - lineHeight: 1.2
  - letterSpacing: "-0.02em"
  - textShadow: "0 0 20px rgba(59, 130, 246, 0.3)" — subtle blue glow on headings

- **Heading (h2):**
  - fontFamily: Inter
  - fontSize: 1.25rem
  - fontWeight: 600
  - lineHeight: 1.3

- **Subheading (h3):**
  - fontFamily: Inter
  - fontSize: 1rem
  - fontWeight: 600
  - lineHeight: 1.4

- **Body:**
  - fontFamily: Inter
  - fontSize: 0.875rem
  - fontWeight: 400
  - lineHeight: 1.5

- **Mono (numbers, prices):**
  - fontFamily: JetBrains Mono
  - fontSize: 0.875rem
  - fontWeight: 500
  - fontFeature: "tnum" — tabular numbers for aligned columns
  - fontVariantNumeric: tabular-nums

- **Label:**
  - fontFamily: Inter
  - fontSize: 0.75rem
  - fontWeight: 500
  - letterSpacing: "0.05em"
  - textTransform: uppercase

- **Stat:**
  - fontFamily: JetBrains Mono
  - fontSize: 1.5rem
  - fontWeight: 700
  - lineHeight: 1.0
  - fontVariantNumeric: tabular-nums

## Layout & Spacing

- **Spacing scale:** 4px grid system
  - xs: 4px
  - sm: 8px
  - md: 16px
  - lg: 24px
  - xl: 32px
  - 2xl: 48px
  - 3xl: 64px

- **Safe areas (mobile):**
  - Top: env(safe-area-inset-top) — notch/status bar
  - Bottom: env(safe-area-inset-bottom) — home indicator
  - Side: 16px minimum margin

- **Touch targets:** 44px minimum height/width per Apple HIG

- **Grid:**
  - Dashboard: single column on mobile, 2-col tablet, 3-col desktop
  - Chart area: minimum 200px height, expands to fill available space
  - Navigation: bottom tab bar on mobile, sidebar on desktop (>768px)

## Elevation & Depth

Trading bot uses a dark theme with subtle 3D depth via layered glass-morphism:

- **Level 0 (background):** #0A0E17 — pure dark base
- **Level 1 (surface):** #111827 with border #1E293B — cards, panels
- **Level 2 (elevated):** #1E293B with subtle box-shadow — modals, dropdowns
- **Level 3 (floating):** Glass-morphism with blur — tooltips, popovers
- **Level 4 (overlay):** rgba(0,0,0,0.8) — modal overlays

- **Shadow system:**
  - sm: "0 1px 2px rgba(0,0,0,0.3)"
  - md: "0 4px 6px rgba(0,0,0,0.4), 0 0 15px rgba(15, 76, 117, 0.1)"
  - lg: "0 10px 15px rgba(0,0,0,0.5), 0 0 30px rgba(15, 76, 117, 0.15)"
  - glow-blue: "0 0 20px rgba(59, 130, 246, 0.3)"
  - glow-gold: "0 0 20px rgba(212, 175, 55, 0.3)"
  - glow-green: "0 0 20px rgba(0, 201, 167, 0.3)"

## Shapes

- **Border radius:**
  - sm: 6px — badges, tags
  - md: 10px — cards, inputs
  - lg: 16px — modals, panels
  - xl: 24px — hero sections, feature cards
  - full: 9999px — buttons, pills

- **Card style:** `bg-{secondary} rounded-xl border border-dark-700/50 p-4 md:p-6`
  - With optional glass variant: `backdrop-blur-lg bg-opacity-60`

- **Input style:** `bg-dark-900 border border-dark-600 rounded-lg px-4 py-3 focus:border-tertiary focus:ring-1 focus:ring-tertiary/30`

## Components

- **button-primary:**
  - backgroundColor: #0F4C75
  - textColor: #F1F5F9
  - rounded: 10px
  - padding: 12px 24px
  - typography: Inter, 0.875rem, 600
  - boxShadow: "0 0 20px rgba(15, 76, 117, 0.3)"
  - transition: all 0.2s ease

- **button-primary-hover:**
  - backgroundColor: #1A5F8A
  - boxShadow: "0 0 30px rgba(15, 76, 117, 0.5)"
  - transform: translateY(-1px)

- **button-danger:**
  - backgroundColor: #EF476F
  - textColor: #F1F5F9

- **button-gold:**
  - backgroundColor: #D4AF37
  - textColor: #0A0E17

- **card-glass:**
  - backgroundColor: "rgba(17, 24, 39, 0.6)"
  - backdropFilter: blur(12px)
  - border: 1px solid rgba(30, 41, 59, 0.5)
  - rounded: 16px

- **card-price-up:**
  - borderLeft: 3px solid #00C9A7
  - backgroundColor: "rgba(0, 201, 167, 0.05)"

- **card-price-down:**
  - borderLeft: 3px solid #EF476F
  - backgroundColor: "rgba(239, 71, 111, 0.05)"

- **badge-live:**
  - backgroundColor: #EF476F
  - textColor: white
  - rounded: 9999px
  - padding: 4px 10px
  - animation: pulse 2s infinite

- **badge-paper:**
  - backgroundColor: "rgba(212, 175, 55, 0.2)"
  - textColor: #D4AF37
  - border: 1px solid rgba(212, 175, 55, 0.3)

- **badge-strategy:**
  - backgroundColor: "rgba(15, 76, 117, 0.2)"
  - textColor: #3B82F6
  - border: 1px solid rgba(15, 76, 117, 0.3)

## Animation & Motion Design

The trading bot uses purposeful animation to convey real-time data changes:

- **Price updates:** Color flash → green flash on price up, red flash on price down, 300ms fade
- **Portfolio value:** Smooth GSAP number counting, eased transitions
- **Card hover:** Subtle lift (translateY -2px) + glow intensification, 200ms
- **Strategy status:** Rotating spinner for active, pulsing dot signal for live trading
- **Page transitions:** Framer Motion slide-up on mobile navigation
- **Chart animations:** Recharts/Recharts-style smooth interpolation between data points
- **Toast/slide notifications:** Slide in from bottom-right, auto-dismiss after 5s
- **Loading states:** Shimmer placeholder animation on cards (wave effect)

## 3D Visual Effects

Specialized dashboard effects for immersive trading experience:

- **Volumetric candlestick charts:** Three.js-powered 3D volume-rendered candlesticks where height = price, width = time, depth = volume
- **Particle trade bursts:** On trade execution, particle system emits gold/green particles from trade entry point
- **Holographic portfolio sphere:** 3D sphere where each segment = an asset allocation, sized by allocation %
- **Shader backgrounds:** GLSL animated wave shader on dashboard hero section (subtle ocean waves)
- **Glass-morphism depth:** Multi-layered translucent panels with realistic light refraction
- **Parallax card stack:** Dashboard cards respond to scroll/tilt with 3D parallax depth
- **Animated gradients:** Slowly shifting ocean-to-sunset gradients on key metrics cards

## Sound Design (optional, future)

- **Trade execution:** Subtle confirmation chime
- **Price alert:** Gentle notification tone
- **Stop-loss triggered:** Urgent alert sound
- **Button press:** Tactile micro-sound
- **Background:** Ambient option (muted by default) — soft ocean waves loop

## Do's and Don'ts

### Do
- Use JetBrains Mono for ALL price displays, P&L numbers, and tabular data
- Use glass-morphism for floating elements (tooltips, modals, dropdowns)
- Animate number changes smoothly — never snap without transition
- Show real-time status indicators (LIVE/PAPER) prominently
- Use green/red for price direction consistently throughout
- Provide haptic-like visual feedback on touch interactions (ripple, glow)
- Keep the bottom navigation within thumb reach zone
- Use skeleton loaders instead of spinners for data-heavy cards

### Don't
- Use light backgrounds — dark mode only, always
- Mix serif and sans-serif fonts (Inter everywhere, JetBrains Mono for numbers only)
- Animate everything — reserve motion for meaningful state changes
- Use pure white (#FFFFFF) for text — always use #F1F5F9 for reduced eye strain
- Show more than 6 cards per screen on mobile
- Use red/green without text labels (accessibility — color blindness)
- Clutter the chart area — keep candlestick charts clean
- Use fixed pixel sizes for spacing — always use relative spacing scale
