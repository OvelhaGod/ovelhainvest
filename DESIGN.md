# The Design System: Operational Precision

## 1. Overview & Creative North Star: "The Brutalist Quantitative"
This design system is not a consumer-facing app; it is a high-performance instrument. The Creative North Star is **The Brutalist Quantitative**. It rejects the "softness" of modern web design in favor of the raw, unapologetic density of financial terminals. 

We break the "template" look by treating the screen as a high-fidelity data grid. By using a strict **0px radius** across the board and replacing traditional borders with tonal shifts, we create a layout that feels forged rather than assembled. It is an editorial approach to high-frequency data—where hierarchy is driven by typographic scale and color-coded logic rather than decorative containers.

---

## 2. Colors: Tonal Logic over Structural Lines
The palette is rooted in the `surface` (#0e0e0e), providing a deeper-than-black foundation that allows data to "pop" with clinical clarity.

*   **Primary (`#c6c6c7`) & Neutrals:** Used for utilitarian UI elements. It is a desaturated, high-readability silver that avoids the "blue-ish" tint of standard dark modes.
*   **Success (`secondary`: `#0abc56`) & Error (`tertiary`: `#ff716a`):** These are the primary communicators. In a portfolio context, these are not just accents; they are the interface's heartbeat.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to section off content. Sectioning must be achieved through:
1.  **Background Shifts:** Placing a `surface_container_low` (#131313) block against the `background` (#0e0e0e).
2.  **Negative Space:** Using the spacing scale (e.g., `8` or `12`) to create mental boundaries.

### Surface Hierarchy & Nesting
Treat the UI as a series of recessed or elevated plates.
*   **Base:** `surface` (#0e0e0e)
*   **Primary Data Cells:** `surface_container_low` (#131313)
*   **Active/Hover States:** `surface_container_high` (#1f2020)
*   **Floating Command Menus:** `surface_bright` (#2c2c2c)

### Signature Textures
Avoid flat "app" aesthetics. For main portfolio headers or high-level totals, use a subtle linear gradient from `primary` (#c6c6c7) to `primary_container` (#454747) at a 45-degree angle to give the text a metallic, "printed" quality.

---

## 3. Typography: The Dual-Engine Engine
We utilize a split-typeface system to separate narrative from data.

*   **The Narrative (Inter):** Used for labels, headers, and UI controls. Inter provides the "Professional" weight. Use `label-sm` (0.6875rem) in All-Caps with +5% letter spacing for table headers to mimic terminal telemetry.
*   **The Data (JetBrains Mono):** **Mandatory** for all numerical values, tickers, and timestamps. Monospaced fonts ensure that when numbers fluctuate, the layout does not "jitter," maintaining a rock-solid visual grid.
*   **Hierarchy:** `display-lg` (3.5rem) is reserved strictly for Total Portfolio Value. `headline-sm` (1.5rem) is used for sector headings.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are forbidden. We define depth through "Luminance Stacking."

*   **The Layering Principle:** To "lift" a component, move it one step up the surface scale. A context menu should be `surface_container_highest` (#252626) sitting on a `surface` (#0e0e0e) background.
*   **The "Ghost Border" Fallback:** If a data grid requires a separator for legibility, use a "Ghost Border": the `outline_variant` (#484848) set to **15% opacity**. It should be felt, not seen.
*   **Interaction Depth:** When a user interacts with a data row, do not use a shadow. Instead, shift the background to `surface_bright` (#2c2c2c) and change the text from `on_surface_variant` to `on_surface`.

---

## 5. Components: Instrument-Grade Primitives

*   **Buttons:**
    *   **Primary:** Solid `primary` (#c6c6c7) with `on_primary` (#3f4041) text. **0px radius**.
    *   **Ghost (Secondary):** No background, `outline` border at 20% opacity. Shifts to 100% opacity on hover.
*   **Data Grids (The Core Component):** 
    *   Forbid dividers. Use `0.15rem` (1) padding between rows to let the `background` bleed through as a "natural" divider.
    *   Positive values: `secondary` (#0abc56).
    *   Negative values: `tertiary` (#ff716a).
*   **Input Fields:**
    *   Background: `surface_container_lowest` (#000000).
    *   Border: `outline_variant` at 20% opacity. Focus state: `primary` (#c6c6c7) 1px solid border.
*   **Chips:**
    *   Rectangular, no radius. Use `surface_container_highest` with `label-sm` text.
*   **The "Terminal" Input:**
    *   A custom component: A full-width, single-line input at the bottom of the screen (Command + K style) using `JetBrains Mono`. This reinforces the "Terminal" persona.

---

## 6. Do's and Don'ts

### Do:
*   **Do** lean into high information density. Users of this system value "Data-at-a-glance" over "Whitespace."
*   **Do** use JetBrains Mono for *any* character that is a digit, including dates and percentages.
*   **Do** use strict 0px corners. Hard edges signify precision.

### Don't:
*   **Don't** use icons unless they are functional (e.g., an arrow for trend). Never use icons for "decoration."
*   **Don't** use "Soft Blue" or "Success Green" from standard libraries. Use the specific `#0abc56` (High-Vis Green) and `#ff716a` (Warning Red).
*   **Don't** use center-alignment. In financial terminals, everything is either left-aligned (labels) or right-aligned (values) to allow for quick vertical scanning.