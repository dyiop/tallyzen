import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Called by the context plugin as  client.mutation("memory:remember", {...})
export const remember = mutation({
  args: {
    org: v.string(),
    kind: v.string(),
    data: v.any(),
    ts: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("memory", args);
  },
});

// Called by the context plugin as  client.query("memory:recall", {...})
// Returns newest-first, optionally filtered by kind.
export const recall = query({
  args: {
    org: v.string(),
    kind: v.optional(v.union(v.string(), v.null())),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const rows =
      args.kind == null
        ? await ctx.db
            .query("memory")
            .withIndex("by_org", (q) => q.eq("org", args.org))
            .collect()
        : await ctx.db
            .query("memory")
            .withIndex("by_org_kind", (q) =>
              q.eq("org", args.org).eq("kind", args.kind as string),
            )
            .collect();
    rows.sort((a, b) => b.ts - a.ts);
    return rows.slice(0, args.limit ?? 20);
  },
});
