# Responsive Design Guide & AI Agent Prompts

This guide defines global responsive standards for the Job Tracker Vue 3 application and provides modular, copy-pasteable prompts optimized for downstream AI coding agents. Each prompt provides explicit instructions to adapt views and components across mobile, tablet, and desktop viewports while preserving design philosophy, Vue 3 reactivity, and Pinia state management.

---

## 1. Global Responsive Standards

### Breakpoints & Viewport Tokens
| Device Tier | Breakpoint Query | Target Viewport Range | Key Layout Behavior |
| :--- | :--- | :--- | :--- |
| **Mobile** | `@media (max-width: 767px)` | `< 768px` | Single-column stacking, collapsible hamburger menu drawer, full-screen modals, bottom action bars, CSS horizontal scroll snap for Kanban boards. |
| **Tablet** | `@media (min-width: 768px) and (max-width: 1023px)` | `768px - 1023px` | 2-column grids, condensed navigation bar, semi-expanded sidebar drawers, auto-fit card grids. |
| **Desktop** | `@media (min-width: 1024px)` | `>= 1024px` | Full multi-column Kanban board, sticky sidebars, side-by-side split view panes, expanded data tables. |

```css
/* Responsive Design System Tokens (frontend/src/style.css) */
:root {
  --breakpoint-mobile: 767px;
  --breakpoint-tablet: 1023px;
  --breakpoint-desktop: 1024px;

  /* Fluid Spacing Scale */
  --space-xs: clamp(0.25rem, 0.5vw, 0.375rem);
  --space-sm: clamp(0.5rem, 1vw, 0.75rem);
  --space-md: clamp(0.875rem, 1.5vw, 1.25rem);
  --space-lg: clamp(1.25rem, 2.5vw, 2rem);
  --space-xl: clamp(1.75rem, 3.5vw, 3rem);

  /* Fluid Typography Scale */
  --font-size-xs: clamp(0.7rem, 0.75vw, 0.75rem);
  --font-size-sm: clamp(0.75rem, 0.85vw, 0.8125rem);
  --font-size-base: clamp(0.8125rem, 1vw, 0.875rem);
  --font-size-lg: clamp(0.9375rem, 1.25vw, 1.125rem);
  --font-size-xl: clamp(1.125rem, 1.75vw, 1.5rem);
  --font-size-2xl: clamp(1.375rem, 2.25vw, 2rem);

  /* Touch Targets */
  --min-touch-target: 48px;
}
```

### Touch Targets & Accessibility Standards
- **Minimum Interactive Size**: All clickable controls (buttons, icon triggers, tabs, table action items, context menu triggers) MUST have a touch target area of at least `48x48px` on mobile (`< 768px`). Where visual size is smaller (e.g. 24x24px icons), transparent padding or pseudo-elements (`::after`) must expand the hit target to `48x48px`.
- **Form Control Sizing**: Text inputs, drop-down selects, and buttons on mobile must feature a minimum height of `44px` to prevent misclicks and zoom jumps on iOS (`font-size: 16px` on input focus if required).
- **Safe Area Insets**: Fixed floating bars, toasts, and mobile drawers must respect `env(safe-area-inset-bottom)` and `env(safe-area-inset-top)` for modern mobile devices (e.g., iPhone notch/home bar).

### Mobile Navigation & Layout Patterns
1. **Collapsible Header & Drawer**: Navigation controls collapse into a mobile slide-out drawer on `< 768px` viewports, accessed via a sticky top navbar hamburger trigger.
2. **Horizontal Scroll Snap (Kanban & Tables)**:
   - For Kanban columns on mobile, use `scroll-snap-type: x mandatory` with `scroll-snap-align: center` on `.kanban-column` elements to enable natural swipe gestures.
   - For data tables, container viewports wrap in an overflowing box with custom horizontal scroll indicators.
3. **Full-Viewport Overlays**: Modals (`.inner-modal-box`) and slide-over drawers (`.drawer-container`) scale to `width: 100vw; height: 100vh; max-height: 100dvh; border-radius: 0;` on viewports `< 768px` with fixed bottom primary submit buttons.

---
