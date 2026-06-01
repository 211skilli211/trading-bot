/**
 * UI Component Library — Enhanced with perception-first design
 * Sources: Impeccable, Taste Skill anti-slop patterns, Perception-First L0-L4
 * 
 * Components:
 *   GlassCard — Primary container (depth via layered shadows, not border)
 *   StatBlock — KPI display with hierarchy
 *   ShimmerCard — Layout-matched skeleton loader
 *   StatusBadge — Squared badges (anti-slop: not pill-shaped)
 *   Divider — Gradient separator
 *   PageHeader — Consistent page header with animation
 *   EmptyState — Composed empty state (not "nothing here")
 *   PriceTag — Formatted price with flash animation
 *   MetricRow — Horizontal metric comparison
 *   SectionCard — Grouped content section
 */

import { GlassCard } from './GlassCard';
import { StatBlock } from './StatBlock';
import { ShimmerCard } from './ShimmerCard';
import { StatusBadge } from './StatusBadge';
import { Divider } from './Divider';
import { PageHeader } from './PageHeader';
import { EmptyState } from './EmptyState';

export {
  GlassCard,
  StatBlock,
  ShimmerCard,
  StatusBadge,
  Divider,
  PageHeader,
  EmptyState,
};

// Re-export individual components for direct import
export { GlassCard as default } from './GlassCard';
