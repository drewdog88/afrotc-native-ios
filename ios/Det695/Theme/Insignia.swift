import SwiftUI

/// Det 695 mark: three ascending chevrons (the ascent motif) rising toward a
/// beacon point — the top chevron in beacon gold, the two below in navy at
/// falling opacity. A vector redraw of the web app's `Insignia.tsx` (same
/// 40×40 geometry) so the two clients read as one product.
struct Insignia: View {
    var size: CGFloat = 34
    /// Color of the two lower chevrons. Defaults to navy for light surfaces;
    /// pass `.white` on the dark login screen so they stay visible.
    var base: Color = Theme.ink

    var body: some View {
        ZStack {
            Chevron(apexY: 3).fill(Theme.accent)
            Chevron(apexY: 14).fill(base.opacity(0.85))
            Chevron(apexY: 25).fill(base.opacity(0.55))
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }

    /// One chevron band in the shared 40×40 coordinate space, scaled to fit.
    /// `apexY` is the peak's y; the band drops 10 units, notching 5 units down
    /// at center — matching the web path `M20 aY L33 bY L27 bY L20 nY L13 bY L7 bY Z`.
    private struct Chevron: Shape {
        let apexY: CGFloat

        func path(in rect: CGRect) -> Path {
            let s = min(rect.width, rect.height) / 40
            func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }
            let baseY = apexY + 10
            let notchY = apexY + 5
            var path = Path()
            path.move(to: p(20, apexY))
            path.addLine(to: p(33, baseY))
            path.addLine(to: p(27, baseY))
            path.addLine(to: p(20, notchY))
            path.addLine(to: p(13, baseY))
            path.addLine(to: p(7, baseY))
            path.closeSubpath()
            return path
        }
    }
}

/// The brand lockup used in navigation bars: the insignia beside the "Det 695"
/// wordmark. Placed as a `.principal` toolbar item so every screen carries the
/// mark, mirroring the persistent rail header on web.
struct BrandLockup: View {
    var body: some View {
        HStack(spacing: 7) {
            Insignia(size: 22)
            Text("Det 695")
                .font(.headline.weight(.bold))
                .foregroundStyle(Theme.ink)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Det 695")
    }
}

extension View {
    /// Adds the Det 695 brand lockup to a screen's navigation bar. Apply inside a
    /// `NavigationStack` so it renders in the bar's principal (centered) slot,
    /// giving every screen the mark — mirroring the persistent rail header on web.
    func det695BrandBar() -> some View {
        toolbar { ToolbarItem(placement: .principal) { BrandLockup() } }
    }
}
