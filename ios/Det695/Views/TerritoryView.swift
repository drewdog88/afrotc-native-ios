import SwiftUI
import MapKit

/// The Territory map, mirroring the web Territory page (web/src/pages/Territory.tsx):
/// every geocoded contact and event drops a pin on a native MapKit map, a bottom
/// sheet lists the located places, and selecting one flies the map to it (and vice
/// versa). Records without coordinates aren't dropped silently — they're counted in
/// a footnote so a recruiter knows what still needs an address.
///
/// Pure client-side: `ContactOut`/`EventOut` already carry `latitude`/`longitude`,
/// so this reads existing data with no backend or model changes.
struct TerritoryView: View {
    @State private var places: [Place] = []
    @State private var missingCount = 0
    @State private var selected: Place.ID?
    @State private var showContacts = true
    @State private var showEvents = true
    @State private var loading = false
    @State private var error: String?
    @State private var camera: MapCameraPosition = .region(Place.defaultRegion)
    @State private var sheetPresented = true

    /// Places passing the current kind filters — the pin/list set.
    private var visible: [Place] {
        places.filter { ($0.kind == .contact && showContacts) || ($0.kind == .event && showEvents) }
    }
    private var contactCount: Int { places.filter { $0.kind == .contact }.count }
    private var eventCount: Int { places.filter { $0.kind == .event }.count }

    var body: some View {
        Map(position: $camera, selection: $selected) {
            ForEach(visible) { place in
                Annotation(place.title, coordinate: place.coordinate) {
                    PinMarker(place: place, isSelected: place.id == selected)
                        .onTapGesture { select(place) }
                }
                .tag(place.id)
            }
        }
        .mapStyle(.standard(pointsOfInterest: .excluding([.restaurant, .store])))
        .overlay { if loading && places.isEmpty { ProgressView().controlSize(.large) } }
        .ignoresSafeArea(edges: .bottom)
        .navigationTitle("Territory")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .onChange(of: showContacts) { fitVisible() }
        .onChange(of: showEvents) { fitVisible() }
        .sheet(isPresented: $sheetPresented) {
            TerritorySheet(visible: visible, selected: $selected,
                           showContacts: $showContacts, showEvents: $showEvents,
                           contactCount: contactCount, eventCount: eventCount,
                           missingCount: missingCount, error: error,
                           onSelect: select)
                .presentationDetents([.fraction(0.3), .large])
                .presentationBackgroundInteraction(.enabled(upThrough: .fraction(0.3)))
                .presentationDragIndicator(.visible)
                .interactiveDismissDisabled()
        }
    }

    private func select(_ place: Place) {
        selected = place.id
        withAnimation {
            camera = .region(MKCoordinateRegion(
                center: place.coordinate,
                span: MKCoordinateSpan(latitudeDelta: 0.5, longitudeDelta: 0.5)))
        }
    }

    /// Frame all currently-visible pins; fall back to the default region if none.
    private func fitVisible() {
        let coords = visible.map(\.coordinate)
        withAnimation {
            camera = coords.isEmpty ? .region(Place.defaultRegion)
                                    : .region(Place.region(fitting: coords))
        }
    }

    private func load() async {
        loading = true
        error = nil
        defer { loading = false }
        do {
            async let contacts = APIClient.shared.contacts(limit: 200)
            async let events = APIClient.shared.events(limit: 200)
            let (cs, es) = try await (contacts, events)

            var located: [Place] = []
            var missing = 0
            for c in cs.items {
                if let coord = coordinate(c.latitude, c.longitude) {
                    located.append(Place(kind: .contact, recordId: c.id, coordinate: coord,
                                         title: c.universityName,
                                         subtitle: c.contactName))
                } else { missing += 1 }
            }
            for e in es.items {
                if let coord = coordinate(e.latitude, e.longitude) {
                    located.append(Place(kind: .event, recordId: e.id, coordinate: coord,
                                         title: e.title,
                                         subtitle: e.location ?? DateDisplay.mediumDate(e.eventDate)))
                } else { missing += 1 }
            }
            places = located
            missingCount = missing
            fitVisible()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    /// Both must be present and non-zero (0/0 is the API's "not geocoded" sentinel).
    private func coordinate(_ lat: Double?, _ lon: Double?) -> CLLocationCoordinate2D? {
        guard let lat, let lon, !(lat == 0 && lon == 0) else { return nil }
        return CLLocationCoordinate2D(latitude: lat, longitude: lon)
    }
}

// MARK: - Place

/// A located record on the map. Mirrors the web `Place`. A contact and an event
/// can share a raw record id, so identity is the composite `kind-id` key; the
/// `CLLocationCoordinate2D` (not `Hashable` itself) is excluded from conformances.
struct Place: Identifiable, Hashable {
    enum Kind { case contact, event }
    let kind: Kind
    let recordId: Int
    let coordinate: CLLocationCoordinate2D
    let title: String
    let subtitle: String

    var id: String { "\(kind)-\(recordId)" }

    static func == (lhs: Place, rhs: Place) -> Bool { lhs.id == rhs.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }

    var tint: Color { kind == .contact ? Theme.accent : Theme.ok }

    /// Pacific-NW default (Seattle ↔ Portland), matching the web `DEFAULT_CENTER`.
    static let defaultRegion = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 46.65, longitude: -122.45),
        span: MKCoordinateSpan(latitudeDelta: 4, longitudeDelta: 4))

    /// A region that frames every coordinate with a little padding.
    static func region(fitting coords: [CLLocationCoordinate2D]) -> MKCoordinateRegion {
        guard let first = coords.first else { return defaultRegion }
        var minLat = first.latitude, maxLat = first.latitude
        var minLon = first.longitude, maxLon = first.longitude
        for c in coords {
            minLat = min(minLat, c.latitude);  maxLat = max(maxLat, c.latitude)
            minLon = min(minLon, c.longitude); maxLon = max(maxLon, c.longitude)
        }
        let center = CLLocationCoordinate2D(latitude: (minLat + maxLat) / 2,
                                            longitude: (minLon + maxLon) / 2)
        let span = MKCoordinateSpan(latitudeDelta: max((maxLat - minLat) * 1.4, 0.05),
                                    longitudeDelta: max((maxLon - minLon) * 1.4, 0.05))
        return MKCoordinateRegion(center: center, span: span)
    }
}

// MARK: - Pin

private struct PinMarker: View {
    let place: Place
    let isSelected: Bool

    var body: some View {
        Image(systemName: place.kind == .contact ? "building.columns.fill" : "calendar.circle.fill")
            .font(.system(size: isSelected ? 22 : 16, weight: .bold))
            .foregroundStyle(.white)
            .padding(isSelected ? 8 : 6)
            .background(Circle().fill(place.tint))
            .overlay(Circle().stroke(.white, lineWidth: 2))
            .shadow(radius: isSelected ? 4 : 1)
            .scaleEffect(isSelected ? 1.1 : 1)
            .animation(.spring(duration: 0.25), value: isSelected)
    }
}

// MARK: - Bottom sheet

private struct TerritorySheet: View {
    let visible: [Place]
    @Binding var selected: Place.ID?
    @Binding var showContacts: Bool
    @Binding var showEvents: Bool
    let contactCount: Int
    let eventCount: Int
    let missingCount: Int
    let error: String?
    let onSelect: (Place) -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack(spacing: 10) {
                        FilterChip(label: "Schools & contacts", count: contactCount,
                                   tint: Theme.accent, on: $showContacts)
                        FilterChip(label: "Events", count: eventCount,
                                   tint: Theme.ok, on: $showEvents)
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                }

                if let error {
                    Text(error).foregroundStyle(Theme.danger)
                } else if visible.isEmpty {
                    ContentUnavailableView {
                        Label("No places on the map", systemImage: "mappin.slash")
                    } description: {
                        Text("Add a street address to a contact or event and it will appear here once geocoded.")
                    }
                } else {
                    ScrollViewReader { proxy in
                        Section("Located \(visible.count)") {
                            ForEach(visible) { place in
                                PlaceRow(place: place, isSelected: place.id == selected,
                                         onTap: { onSelect(place) })
                                    .id(place.id)
                            }
                        }
                        .onChange(of: selected) { _, id in
                            guard let id else { return }
                            withAnimation { proxy.scrollTo(id, anchor: .center) }
                        }
                    }
                }

                if missingCount > 0 {
                    Text("\(missingCount) record\(missingCount == 1 ? "" : "s") without coordinates aren't shown. Add a street address to place them.")
                        .font(.caption).foregroundStyle(.secondary)
                        .listRowSeparator(.hidden)
                }
            }
            .listStyle(.plain)
            .navigationTitle("Territory")
            .navigationBarTitleDisplayMode(.inline)
            // Detail pushes onto the sheet's own stack, keeping the map behind it.
            .navigationDestination(for: ContactRoute.self) { ContactDetailView(contactId: $0.id) }
            .navigationDestination(for: EventRoute.self) { EventDetailView(eventId: $0.id) }
        }
    }
}

private struct FilterChip: View {
    let label: String
    let count: Int
    let tint: Color
    @Binding var on: Bool

    var body: some View {
        Button { on.toggle() } label: {
            HStack(spacing: 6) {
                Circle().fill(tint).frame(width: 8, height: 8)
                Text(label).font(.caption.weight(.medium))
                Text("\(count)").font(.caption2.weight(.bold))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 12).padding(.vertical, 7)
            .background(Capsule().fill(on ? tint.opacity(0.18) : Color(.tertiarySystemFill)))
            .overlay(Capsule().stroke(on ? tint : .clear, lineWidth: 1))
            .opacity(on ? 1 : 0.55)
        }
        .buttonStyle(.plain)
    }
}

private struct PlaceRow: View {
    let place: Place
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onTap) {
                HStack(spacing: 12) {
                    Circle().fill(place.tint).frame(width: 10, height: 10)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(place.title).font(.body.weight(.medium)).foregroundStyle(.primary)
                        Text(place.subtitle).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer(minLength: 0)
                }
            }
            .buttonStyle(.plain)

            // Push the existing detail screen for this record.
            Group {
                if place.kind == .contact {
                    NavigationLink(value: ContactRoute(id: place.recordId)) { openLabel }
                } else {
                    NavigationLink(value: EventRoute(id: place.recordId)) { openLabel }
                }
            }
            .fixedSize()
        }
        .listRowBackground(isSelected ? place.tint.opacity(0.12) : Color(.systemBackground))
    }

    private var openLabel: some View {
        Text("Open").font(.caption.weight(.semibold))
    }
}
