import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

// Shared "case file" for the Tallyzen agents. One table of typed records keyed
// by org + kind, so the Advisor/Accountant/Analyst coordinate through memory.
export default defineSchema({
  memory: defineTable({
    org: v.string(),                 // client id, e.g. "meenakshi"
    kind: v.string(),                // "invoice" | "signal" | "note"
    data: v.any(),                   // the record payload (shape depends on kind)
    ts: v.number(),                  // unix seconds
  })
    .index("by_org", ["org"])
    .index("by_org_kind", ["org", "kind"]),
});
