/* Territory — the detachment's recruiting footprint on a map. Every contact (the
   high schools & universities we recruit through) and every event that has been
   geocoded drops a pin; the list on the left mirrors the map and flies to a pin on
   click. Places without coordinates aren't silently dropped — they're counted so
   the recruiter knows what still needs an address. Basemap follows light/dark theme.
   Map: MapLibre GL + CARTO no-key raster tiles. */
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api } from "../lib/api";
import type { components } from "../api/schema";
import styles from "./Territory.module.css";

type ContactOut = components["schemas"]["ContactOut"];
type ContactPage = components["schemas"]["Page_ContactOut_"];
type EventOut = components["schemas"]["EventOut"];
type EventPage = components["schemas"]["Page_EventOut_"];

type Kind = "contact" | "event";

type Place = {
  key: string;
  kind: Kind;
  id: number;
  lat: number;
  lng: number;
  title: string;
  subtitle: string;
  detailPath: string;
};

// Pacific-NW fallback view (Seattle ↔ Portland) — the detachment's recruiting
// footprint — shown before pins load or when nothing is geocoded yet.
const DEFAULT_CENTER: [number, number] = [-122.45, 46.65];
const DEFAULT_ZOOM = 6.4;

// CARTO raster basemaps — free, no API key. Light by day, dark for night ops.
function styleFor(dark: boolean): maplibregl.StyleSpecification {
  const variant = dark ? "dark_all" : "light_all";
  return {
    version: 8,
    sources: {
      carto: {
        type: "raster",
        tiles: [
          `https://a.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}{r}.png`,
          `https://b.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}{r}.png`,
          `https://c.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}{r}.png`,
        ],
        tileSize: 256,
        attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>',
      },
    },
    layers: [{ id: "carto", type: "raster", source: "carto", minzoom: 0, maxzoom: 20 }],
  };
}

function isDarkTheme(): boolean {
  return document.documentElement.getAttribute("data-theme") === "dark";
}

export function Territory() {
  const contactsQ = useQuery({
    queryKey: ["contacts", "all", "map"],
    queryFn: () => api.get<ContactPage>("/contacts?limit=200"),
    placeholderData: keepPreviousData,
  });
  const eventsQ = useQuery({
    queryKey: ["events", "all", "map"],
    queryFn: () => api.get<EventPage>("/events?limit=200"),
    placeholderData: keepPreviousData,
  });

  const [show, setShow] = useState<{ contact: boolean; event: boolean }>({ contact: true, event: true });
  const [selected, setSelected] = useState<string | null>(null);

  const contacts = contactsQ.data?.items ?? [];
  const events = eventsQ.data?.items ?? [];

  const hasCoords = (v: { latitude?: number | null; longitude?: number | null }) =>
    v.latitude != null && v.longitude != null;

  const places: Place[] = useMemo(() => {
    const out: Place[] = [];
    for (const c of contacts as ContactOut[]) {
      if (!hasCoords(c)) continue;
      out.push({
        key: `contact-${c.id}`,
        kind: "contact",
        id: c.id,
        lat: c.latitude as number,
        lng: c.longitude as number,
        title: c.university_name,
        subtitle: c.contact_name,
        detailPath: `/contacts/${c.id}`,
      });
    }
    for (const e of events as EventOut[]) {
      if (!hasCoords(e)) continue;
      out.push({
        key: `event-${e.id}`,
        kind: "event",
        id: e.id,
        lat: e.latitude as number,
        lng: e.longitude as number,
        title: e.title,
        subtitle: e.location || e.event_type,
        detailPath: `/events/${e.id}`,
      });
    }
    return out;
  }, [contacts, events]);

  const visible = useMemo(
    () => places.filter((p) => show[p.kind]),
    [places, show],
  );

  const missing = {
    contact: contacts.filter((c) => !hasCoords(c)).length,
    event: events.filter((e) => !hasCoords(e)).length,
  };

  // ---- Map lifecycle -----------------------------------------------------
  const mapNode = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markers = useRef<Map<string, maplibregl.Marker>>(new Map());
  const [dark, setDark] = useState(isDarkTheme);
  const [ready, setReady] = useState(false);

  // Init once.
  useEffect(() => {
    if (!mapNode.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapNode.current,
      style: styleFor(isDarkTheme()),
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => setReady(true));
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Follow the app's light/dark theme.
  useEffect(() => {
    const el = document.documentElement;
    const obs = new MutationObserver(() => setDark(isDarkTheme()));
    obs.observe(el, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (mapRef.current && ready) mapRef.current.setStyle(styleFor(dark));
  }, [dark, ready]);

  // Render markers whenever the visible set changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const live = markers.current;
    const wanted = new Set(visible.map((p) => p.key));

    // Drop stale markers.
    for (const [key, marker] of live) {
      if (!wanted.has(key)) {
        marker.remove();
        live.delete(key);
      }
    }

    // Add new markers.
    for (const p of visible) {
      if (live.has(p.key)) continue;
      const el = document.createElement("button");
      el.type = "button";
      el.className = `${styles.pin} ${p.kind === "event" ? styles.pinEvent : styles.pinContact}`;
      el.setAttribute("aria-label", p.title);
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        setSelected(p.key);
      });
      const marker = new maplibregl.Marker({ element: el }).setLngLat([p.lng, p.lat]).addTo(map);
      live.set(p.key, marker);
    }
  }, [visible, ready]);

  // Fit the map to the visible pins whenever they change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.resize(); // measure the current container before fitting (it may have resized)
    if (visible.length === 0) {
      map.easeTo({ center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM });
      return;
    }
    if (visible.length === 1) {
      map.easeTo({ center: [visible[0].lng, visible[0].lat], zoom: 11 });
      return;
    }
    const bounds = new maplibregl.LngLatBounds();
    for (const p of visible) bounds.extend([p.lng, p.lat]);
    map.fitBounds(bounds, { padding: 64, maxZoom: 12, duration: 600 });
  }, [visible, ready]);

  // Reflect the selected pin's active state on its element + fly to it.
  useEffect(() => {
    const map = mapRef.current;
    for (const [key, marker] of markers.current) {
      marker.getElement().classList.toggle(styles.pinActive, key === selected);
    }
    if (selected && map) {
      const p = visible.find((v) => v.key === selected);
      if (p) map.flyTo({ center: [p.lng, p.lat], zoom: Math.max(map.getZoom(), 10), duration: 600 });
    }
  }, [selected, visible]);

  const selectedPlace = visible.find((v) => v.key === selected) ?? null;
  const loading = contactsQ.isLoading || eventsQ.isLoading;

  const toggles: { kind: Kind; label: string }[] = [
    { kind: "contact", label: "Schools & contacts" },
    { kind: "event", label: "Events" },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Territory</h1>
          <p className={styles.subtitle}>
            Where the detachment recruits — mapped from geocoded contacts and events.
          </p>
        </div>
        <div className={styles.toggles} role="group" aria-label="Show on map">
          {toggles.map((t) => (
            <button
              key={t.kind}
              className={`${styles.toggle} ${show[t.kind] ? styles.toggleOn : ""}`}
              onClick={() => setShow((s) => ({ ...s, [t.kind]: !s[t.kind] }))}
              aria-pressed={show[t.kind]}
            >
              <span className={`${styles.dot} ${t.kind === "event" ? styles.dotEvent : styles.dotContact}`} aria-hidden />
              {t.label}
              <span className={styles.toggleCount}>
                {places.filter((p) => p.kind === t.kind).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className={styles.layout}>
        <aside className={`card ${styles.list}`}>
          <div className={styles.listHead}>
            <span className="eyebrow">Located</span>
            <span className={styles.listCount}>{visible.length}</span>
          </div>

          {loading ? (
            <div className={styles.skeleton} style={{ height: 240, margin: "var(--sp-3)" }} />
          ) : visible.length === 0 ? (
            <div className={styles.empty}>
              No mapped places yet. Add a street address to a contact or event and it will appear here
              once geocoded.
            </div>
          ) : (
            <ul className={styles.rows}>
              {visible.map((p) => (
                <li key={p.key}>
                  <button
                    className={`${styles.row} ${selected === p.key ? styles.rowActive : ""}`}
                    onClick={() => setSelected(p.key)}
                  >
                    <span className={`${styles.dot} ${p.kind === "event" ? styles.dotEvent : styles.dotContact}`} aria-hidden />
                    <span className={styles.rowText}>
                      <span className={styles.rowTitle}>{p.title}</span>
                      <span className={styles.rowSub}>{p.subtitle}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {(missing.contact > 0 || missing.event > 0) && (
            <div className={styles.missing}>
              {missing.contact > 0 && <span>{missing.contact} contact{missing.contact === 1 ? "" : "s"} without coordinates</span>}
              {missing.contact > 0 && missing.event > 0 && <span> · </span>}
              {missing.event > 0 && <span>{missing.event} event{missing.event === 1 ? "" : "s"} without coordinates</span>}
            </div>
          )}
        </aside>

        <div className={`card ${styles.mapCard}`}>
          <div ref={mapNode} className={styles.map} />
          {selectedPlace && (
            <div className={styles.popup}>
              <div className={styles.popupHead}>
                <span className={`${styles.dot} ${selectedPlace.kind === "event" ? styles.dotEvent : styles.dotContact}`} aria-hidden />
                <span className={styles.popupKind}>
                  {selectedPlace.kind === "event" ? "Event" : "Contact"}
                </span>
                <button className={styles.popupClose} aria-label="Close" onClick={() => setSelected(null)}>
                  ×
                </button>
              </div>
              <div className={styles.popupTitle}>{selectedPlace.title}</div>
              <div className={styles.popupSub}>{selectedPlace.subtitle}</div>
              <Link className="btn btn-ghost" to={selectedPlace.detailPath}>
                Open {selectedPlace.kind === "event" ? "event" : "contact"} →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
