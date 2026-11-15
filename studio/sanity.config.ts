import { defineConfig } from "sanity";
import { structureTool } from "sanity/structure";
import { schemaTypes } from "./schemas";

// Set these in studio/.env (SANITY_STUDIO_PROJECT_ID, SANITY_STUDIO_DATASET). See README.md.
const projectId = process.env.SANITY_STUDIO_PROJECT_ID ?? "";
const dataset = process.env.SANITY_STUDIO_DATASET ?? "production";

export default defineConfig({
  name: "peopleforce",
  title: "PeopleForce content",
  projectId,
  dataset,
  plugins: [structureTool()],
  schema: { types: schemaTypes },
});
