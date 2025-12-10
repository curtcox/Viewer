# Gauge spec failures

The latest run of `scripts/checks/run_gauge_specs.sh` surfaced multiple failing specs concentrated in specific areas:

- **AI editor**: Default boot image missing server support plus editor page/actions failures and chain rejection cases remain broken. 【c4cad4†L1-L5】【d05d1b†L1-L6】
- **Authorization API**: API requests are still being denied even though other authorization behaviors pass. 【11e105†L1-L6】
- **Default boot servers**: Echo and shell boot servers are not responding with the expected HTML or form outputs. 【98ec73†L1-L6】
- **Server command chaining**: All chaining scenarios (CID inputs, default servers, language-specific CID literals, and server events dashboard) are failing, indicating foundational breakage in chaining and server event tracking. 【c4cad4†L1-L36】
- **UI suggestions**: Viewing a variable with no UI suggestions fails. 【c4019b†L1-L9】
- **Upload templates**: Embedded CID execution guide is missing from the upload page. 【c4019b†L6-L10】
- **URL editor**: Boot image availability, page loading, redirect handling, chain rejection, UI layout, button behaviors, newline handling, and metadata endpoint usage are failing in most URL editor scenarios. 【4204e8†L1-L22】

## Plan to fix

1. **Investigate boot image contents and server registration** for AI editor and URL editor to ensure their servers are included and enabled; update boot image generation or fixture loading as needed. 【d05d1b†L1-L6】【4204e8†L1-L22】
2. **Debug editor route handlers (ai_editor and urleditor)** to serve correct pages, redirects, and client assets; add integration tests to validate page structure and required elements. 【d05d1b†L1-L6】【4204e8†L1-L22】
3. **Review chain rejection logic** for AI and URL editors to confirm they explicitly disallow chaining with appropriate responses. 【d05d1b†L4-L6】【4204e8†L3-L5】
4. **Fix authorization middleware for API paths** so API requests authenticate/authorize correctly without blocking valid calls. 【11e105†L1-L3】
5. **Restore default boot server behaviors** (echo/shell) to return expected HTML and form responses; verify routing and templates. 【98ec73†L1-L6】
6. **Rebuild command chaining pipeline** to correctly pass CIDs through default, named, and literal servers across languages; validate server events dashboard surfacing executions. 【c4cad4†L1-L36】
7. **Address UI suggestions retrieval** for variables to mirror alias/server behavior when no suggestions exist. 【c4019b†L1-L4】
8. **Ensure upload page lists embedded CID execution guide** when templates are configured. 【c4019b†L6-L10】

Tracking these areas and resolving them iteratively should clear the remaining Gauge spec failures.
