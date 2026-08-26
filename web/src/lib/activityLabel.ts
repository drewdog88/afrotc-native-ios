/* Human phrasing for activity-log rows. The backend stores machine-y
   (action, table_name) pairs — "DELETE" + "potential_recruit" — but the log
   reads far better as "Deleted recruit". This is the single source of truth
   for that phrasing so every action renders consistently. */

/** table_name -> the entity noun shown to a reader. */
const ENTITY: Record<string, string> = {
  potential_recruit: "recruit",
  cadet: "cadet",
  recruitment_event: "event",
  external_link: "material link",
  recruitment_document: "document",
  university_contact: "contact",
  follow_up: "follow-up",
  users: "user",
  intake_settings: "intake settings",
};

/** action -> verb. Actions that aren't "<verb> the <entity>" are handled below. */
const VERB: Record<string, string> = {
  CREATE: "Created",
  UPDATE: "Updated",
  DELETE: "Deleted",
};

/** Actions that stand on their own — no entity noun appended. */
const STANDALONE: Record<string, string> = {
  LOGIN: "Signed in",
  CONTACT_SUBMITTED: "Contact form submitted",
};

export function activityLabel(action: string, tableName: string | null | undefined): string {
  if (STANDALONE[action]) return STANDALONE[action];

  const entity = tableName ? ENTITY[tableName] : undefined;

  if (action === "STAGE_CHANGE") {
    return entity ? `Stage change · ${entity}` : "Stage change";
  }

  const verb = VERB[action];
  if (verb) return entity ? `${verb} ${entity}` : verb;

  // Unknown action: show it as-is rather than inventing phrasing.
  return action;
}
