import SwiftUI

/// The official AFROTC Detachment 695 patch (St. Johns Bridge, Mt. Hood, and the
/// diamond flight formation, ringed by "AFROTC DETACHMENT 695 / UNIVERSITY OF
/// PORTLAND"). Rendered from the real crest artwork in `Assets.xcassets` so the
/// iOS app carries the same mark as the detachment and the web app.
struct Insignia: View {
    var size: CGFloat = 34

    var body: some View {
        Image("DetPatch")
            .resizable()
            .scaledToFit()
            .frame(width: size, height: size)
            .accessibilityHidden(true)
    }
}

/// The AFROTC wordmark ("U.S. AIR FORCE ROTC"), shown on the login screen beneath
/// the patch. Tinted white so it reads on the dark login surface.
struct AFROTCWordmark: View {
    var height: CGFloat = 22

    var body: some View {
        Image("AFROTCWordmark")
            .resizable()
            .renderingMode(.template)
            .scaledToFit()
            .frame(height: height)
            .accessibilityLabel("U.S. Air Force ROTC")
    }
}

/// The brand lockup used in navigation bars: the patch beside the "Det 695"
/// wordmark. Placed as a `.principal` toolbar item so every screen carries the
/// mark, mirroring the persistent rail header on web.
struct BrandLockup: View {
    var body: some View {
        HStack(spacing: 7) {
            Insignia(size: 24)
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
