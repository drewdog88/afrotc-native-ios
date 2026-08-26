import { describe, expect, it } from "vitest";

import { activityLabel } from "./activityLabel";

describe("activityLabel", () => {
  it("names the entity for every delete", () => {
    expect(activityLabel("DELETE", "potential_recruit")).toBe("Deleted recruit");
    expect(activityLabel("DELETE", "cadet")).toBe("Deleted cadet");
    expect(activityLabel("DELETE", "recruitment_event")).toBe("Deleted event");
    expect(activityLabel("DELETE", "external_link")).toBe("Deleted material link");
    expect(activityLabel("DELETE", "recruitment_document")).toBe("Deleted document");
    expect(activityLabel("DELETE", "university_contact")).toBe("Deleted contact");
    expect(activityLabel("DELETE", "follow_up")).toBe("Deleted follow-up");
    expect(activityLabel("DELETE", "users")).toBe("Deleted user");
  });

  it("reads consistently across the other actions", () => {
    expect(activityLabel("CREATE", "potential_recruit")).toBe("Created recruit");
    expect(activityLabel("UPDATE", "cadet")).toBe("Updated cadet");
    expect(activityLabel("STAGE_CHANGE", "potential_recruit")).toBe("Stage change · recruit");
  });

  it("keeps loginless / entity-less actions readable", () => {
    expect(activityLabel("LOGIN", "users")).toBe("Signed in");
    expect(activityLabel("CONTACT_SUBMITTED", "potential_recruit")).toBe("Contact form submitted");
  });

  it("falls back to the raw action for anything unmapped", () => {
    expect(activityLabel("EXPORTED", "cadet")).toBe("EXPORTED");
    expect(activityLabel("DELETE", null)).toBe("Deleted");
    expect(activityLabel("DELETE", "mystery_table")).toBe("Deleted");
  });
});
