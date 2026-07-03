/* Det 695 mark: the official AFROTC Detachment 695 patch (St. Johns Bridge,
   Mt. Hood, and the diamond flight formation, ringed by "AFROTC DETACHMENT 695 /
   UNIVERSITY OF PORTLAND"). Rendered from the real crest artwork so the web app
   carries the same mark as the iOS app and the detachment. Used in the rail
   header and on the login screen. */
import patch from "../assets/det695-patch.png";

export function Insignia({ size = 34 }: { size?: number }) {
  return (
    <img
      src={patch}
      width={size}
      height={size}
      alt=""
      aria-hidden="true"
      style={{ objectFit: "contain", display: "block" }}
    />
  );
}
