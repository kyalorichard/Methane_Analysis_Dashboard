# v11 — navigation, workflow and usability refinement

## Six refinements implemented
1. **Grouped navigation:** analytical pages are organised into Workspace, Data preparation, Explore & validate, Model & explain, and Outputs. Native duplicate navigation is hidden in favour of the curated sidebar.
2. **Project and dataset selectors:** the sidebar can switch accessible persistent projects when the database is configured, and switch among datasets loaded in the current session. Project persistence still requires the configured database/object storage services.
3. **Guided analysis workflow:** a dedicated page links the user through import, variable mapping, phenotype development/validation, modelling and reporting.
4. **Progress and empty states:** sidebar readiness indicators and workflow completion indicators explain what is ready and what to do next; no-data states are explicit.
5. **Consistent analytical presentation:** shared Plotly styling, restrained ICARDA-inspired colours, consistent legends/typography/margins, and clearer dataframe/download styling.
6. **Responsive layout:** sidebar, cards, metric tiles and page padding adapt for smaller screens; the standard Streamlit sidebar collapse remains available.

## Preserved
- Existing analytical pages and scientific methods.
- Existing session-based custom phenotype builder and emitter tracking.
- Existing authentication and persistent project architecture scaffolding.
- No new package dependencies.

## Validation
- Python source compilation passed.
- Automated test suite: 25 passed, 1 benign warning in the existing formula-builder sqrt test.
- Visual QA still needs to be performed in a running browser, especially on phone-sized screens and with long project/dataset names.
