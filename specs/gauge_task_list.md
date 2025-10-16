# Gauge spec backlog

The existing Gauge coverage only verifies that the source browser renders. The following scenarios capture high-value flows that should gain end-to-end Gauge specs next.

1. **Authentication, invitation, and onboarding guardrails**  
   Cover the full login flow, including invitation code verification (`InvitationCodeForm`), mandatory terms acceptance (`TermsAcceptanceForm`), and the transition onto the authenticated home page. Exercise both successful and failure states to protect the multi-step onboarding gates implemented in `routes/core.py` and `auth_providers.py`.
2. **Home dashboard cross-reference graph**  
   Validate that the authenticated landing page surfaces alias, server, and CID relationship data produced by `_build_cross_reference_data` in `routes/core.py`, and that the entity cards link into the detail views. Include scenarios with and without related data to ensure empty states stay informative.
3. **Upload workflows across file, text, and URL modes**  
   Walk through `/upload` in each mode (`FileUploadForm.upload_type`), confirming CID generation, duplicate detection feedback, and the rendered success summary from `routes/uploads.py`. Include the interaction log side effects for text uploads so regressions in telemetry are caught.
4. **Alias and routing management lifecycle**  
   Exercise creating, editing, testing, and deleting aliases via `routes/aliases.py` and the validation helpers in `AliasForm`. Gauge should assert that pattern testing feedback appears, that saved aliases route traffic as expected, and that conflicts or invalid patterns show clear messaging.
5. **Server, variable, and secret editors**  
   Add specs that cover the CRUD flows served from `routes/servers.py`, `routes/variables.py`, and `routes/secrets.py`, verifying change history integration, preview rendering, and CID updates (e.g., `update_secret_definitions_cid`). Focus on ensuring the edit forms persist data and expose the expected flash messaging.
6. **Upload and server event history views**  
   Traverse `/uploads` and `/history` to confirm that stored records render previews, filter out server events where appropriate, and link back to the originating CIDs or server invocations, as implemented in `routes/uploads.py` and `routes/history.py`.
