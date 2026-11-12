# TraceGraph visual system

The product uses a single, intentionally restrained visual language across the website and research workspace.

## Identity
- **Background:** true near-black (#08090b). Panels are graphite (#111317); dividers are hairline grey (#282c31).
- **Type:** Geist Sans for reading and prominent headlines; Geist Mono for coordinates, numbers, provenance, labels and status. No display gradients, fake-glass cards or neon AI decoration.
- **Logo:** three connected nodes and an incomplete route, symbolizing a trace rather than a chatbot.
- **Color:** white, neutral grey and black define the entire interface. Desaturated green and red are reserved for actual success/offline/error states.
- **Hierarchy:** large, compact tracking on headlines; small uppercase mono labels for operational metadata; clean reading line lengths for answer content.
- **Data surfaces:** the research workspace highlights questions, cited answers, sources, graph facts and timing metrics in that order.

## Interaction principles
- The top-level API indicator states *API reachable*, not *database online*. The document catalog separately reports loading/error/empty states.
- Library scope uses explicit selected/unselected indicators. The composer keeps scope and the keyboard shortcut visible.
- Evidence opens in a dedicated drawer with Escape handling and a keyboard focus cycle. Mobile document browsing is an overlay with a backdrop, Escape handling and scroll lock.
- Only opacity/status pulses and meaningful hover transitions animate. Reduced-motion preferences disable all decorative motion.
- Mobile layouts are authored at 980, 860, 640 and 375 pixel breakpoints; the application keeps a single reading column while the source library becomes a dismissible sheet.

## Verification
Use the production build, then inspect `/` and `/app` at desktop, tablet, and 375px mobile widths. Specifically verify the following states in browser:
- library loading, no documents, document error, and filtered results
- search composition, streaming, cancellation, final answers, degraded/abstained answers
- source/graph drawers, keyboard Tab/Escape navigation, scroll behavior
- 200% zoom, narrow viewport and reduced-motion mode

This document describes design and implementation conventions, not a claim that live visual tests have been performed.
