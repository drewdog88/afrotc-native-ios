# Territory (iOS) — Design

**Date:** 2026-07-12
**Status:** Approved
**Scope:** Add the web app's "Territory" map feature to the SwiftUI iOS app.

## Goal

Bring the web's Territory map to iOS as a native screen. Every geocoded Contact
and Event drops a pin on a map; a list mirrors the map; selecting one flies
to/highlights the other. Places without coordinates are not dropped silently —
they are counted so a recruiter knows what still needs an address.

**No backend changes.** The API already returns `latitude`/`longitude` on both
`ContactOut` and `EventOut`, and the iOS models (`Contact.swift`, `Event.swift`)
already decode them. This is a pure client-side addition that reads existing data.

## Why it was missing

Territory is a web-era feature (`web/src/pages/Territory.tsx`, routed `/map`).
The iOS secondary screens were added in one batch (commit `c213365`: Contacts,
Events, Follow-ups, Pipeline, Materials) and Territory simply wasn't in it. It is
also the one feature with a heavy native dependency (a map), making it the
natural one to defer. Nothing blocks it now.

## Decisions

- **Map engine: MapKit** (Apple's native SwiftUI `Map` + `Annotation`). Zero
  dependencies — matches this project's deps-free ethos (every other screen is
  plain SwiftUI + JSON). First-class on the iOS 17+ deployment target. No API
  keys. (The web uses MapLibre GL + CARTO tiles; we deliberately do not mirror
  that stack — pins on a basemap don't warrant a SwiftPM dependency.)
- **iPhone layout: full-bleed map + draggable bottom sheet** listing located
  places — the native iOS map pattern (Maps, Find My). The sheet uses
  `presentationBackgroundInteraction` so the map stays interactive behind it.

## Placement & navigation

Territory becomes a fifth destination in the **More hub**
(`MoreView.Destination` in `RootView.swift`), alongside Contacts, Events,
Follow-ups, and Materials.

- Enum case: `territory`; title `"Territory"`; SF Symbol `map`.
- It pushes onto the shared More `NavigationStack`.
- From a selected pin, an "Open contact →" / "Open event →" action pushes the
  existing `ContactDetailView` / `EventDetailView` via the already-shared
  `ContactRoute` / `EventRoute` — detail navigation works with no new plumbing.

We are **not** adding a top-level tab: the tab bar is already full at five, and
the More hub is exactly where the other secondary screens live.

## Data flow

`TerritoryView` fetches both pages concurrently in its `.task` via the existing
`APIClient`:

```swift
async let contacts = APIClient.shared.contacts(limit: 200)
async let events   = APIClient.shared.events(limit: 200)
```

Both responses already carry `latitude`/`longitude`. The view maps them into a
local `Place` value type, mirroring the web's `Place`:

```swift
struct Place: Identifiable, Hashable {
    enum Kind { case contact, event }
    let kind: Kind
    let recordId: Int
    let coordinate: CLLocationCoordinate2D
    let title: String
    let subtitle: String
    // A contact and an event can share a raw record id, so identity is the
    // composite key — not the bare Int.
    var id: String { "\(kind)-\(recordId)" }
}
```

`CLLocationCoordinate2D` is not `Hashable`/`Equatable` on its own, so `Place`'s
conformances key off the stored scalars (or exclude the coordinate and rely on
`id`) rather than synthesizing over the raw struct.

Places lacking coordinates are filtered out of the pin/list set but **counted**
for the "N without coordinates" footnote.

## Components

- **`TerritoryView`** — owns state: `places`, `selected: Place.ID?` (the composite `String` key),
  `showContacts: Bool`, `showEvents: Bool`, `loading`, `error`, and a
  `MapCameraPosition`.
- **`Map`** (MapKit, SwiftUI) — one `Annotation` per *visible* place, tinted by
  kind to match the web's dot colors: contacts `Theme.accent` (amber), events
  `Theme.ok` (green). The selected pin scales up / gains emphasis. The camera
  fits all visible pins on load and whenever the filter changes; it flies to a
  pin on selection.
- **Bottom sheet** — `.sheet` with
  `.presentationDetents([.fraction(0.3), .large])` and
  `.presentationBackgroundInteraction(.enabled)` so the map stays live. Contains:
  - Header: "Located N" + two filter toggles (Schools & contacts / Events), each
    showing its count.
  - The list of visible places (row = colored dot + title + subtitle). Row tap
    sets `selected`.
  - The missing-coordinates footnote when any place lacks coords.
- **Selection sync** — tapping a pin sets `selected`; the sheet list scrolls that
  row into view (`ScrollViewReader`) and the row exposes the "Open …→"
  `NavigationLink`. Tapping a row flies the map to the pin.

## States

- **Loading:** `ProgressView` overlay (consistent with other list screens).
- **Error:** `ContentUnavailableView` showing the `APIError` description.
- **No geocoded places:** the sheet shows the same guidance as web — "Add a
  street address to a contact or event and it will appear here once geocoded" —
  and the map rests at a Pacific-NW default region (Seattle ↔ Portland),
  matching the web's `DEFAULT_CENTER` (`-122.45, 46.65`).

## Testing / verification

The iOS project has no unit-test harness — it is build-and-drive. Verification:

1. `xcodegen generate` + `xcodebuild` for the booted simulator.
2. Drive the running app (autologin), navigate More → Territory, and confirm via
   screenshots:
   - Pins render for geocoded contacts (amber) and events (green).
   - Filter toggles add/remove the corresponding pins and update counts.
   - Selecting a row flies the map and highlights the pin (and vice versa).
   - "Open contact/event →" pushes the correct detail screen.
   - The missing-coordinates footnote reflects non-geocoded records.

Backend already seeds geocoded demo data (`backend/scripts/seed_demo.py`).

## Files

- **New:** `ios/Det695/Views/TerritoryView.swift`
- **Edit:** `ios/Det695/Views/RootView.swift` — add the `.territory` case to
  `MoreView.Destination` (title, icon, and `navigationDestination` branch).

That is the entire surface area — no model, networking, or backend changes.
