---
name: truong-ton-app-developer
description: Master prompt guidelines and instructions for developing the Streamlit + Supabase app. Includes Streamlit rendering patterns, Supabase table querying, Role-Based Access Control (RBAC), Plotly data visualization, and Clean Code principles.
---

# Truong Ton App Developer Guidelines

You are an expert full-stack developer specialized in Python, Streamlit, and Supabase. Use this skill when modifying `app.py` or adding new functionality to the project.

## 1. Clean Code & Python Standards
- **Clarity over Cleverness**: Write readable code. Use functions for modular logic (e.g. `check_quantity_limit`, `validate_timeline_logic`). 
- **Type Hinting**: Use type hints for function signatures (`def fetch_table_data(table_name: str, farm: str) -> pd.DataFrame:`).
- **Error Handling**: Ensure robust error handling (e.g. duplicating unique constraint checks, user-friendly `st.error` alerts).

## 2. Streamlit Component Structure
- **Global State**: Maintain login state and contextual filtering variables in `st.session_state` (`logged_in`, `current_farm`, `current_team`).
- **Dialog Decorators**: Use `@dialog_decorator` for pop-up UI components (e.g., edit dialogs) and ensure `st.rerun()` is called on successful database mutate actions to force UI refreshes.
- **UI & CSS**: Output cohesive HTML styled visually with the core application. Reuse structures like `.farm-badge` and `.team-badge`.

## 3. Supabase Database Practices
- **SDK Methodology**: Interact with the DB using `supabase.table("table_name").select/insert/update().eq(...).execute()`.
- **Soft Deletion**: Always append `.eq("is_deleted", False)` when executing read queries. **Never** execute hard DELETE instructions. Instead, update `is_deleted` flags to `True`.
- **Consistency**: Centralize reads via utility functions like `fetch_table_data()`. Keep database calls efficient.

## 4. Plotly & Pandas Data Visualization
- **Plotly Express (`px`)**: Favor Plotly Express for rendering dashboards. Group and aggregate data cleanly through Pandas `groupby()` before passing it into Plotly.
- **Charts Style**: Override layout defaults slightly for better aesthetic integration: e.g., `fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")`.
- **Streamlit Integration**: Render visualizations seamlessly using `st.plotly_chart(fig, use_container_width=True)` or `st.area_chart` / `st.line_chart` where appropriate.

## 5. Security & RBAC
- Validate `current_farm` and `current_team` constraints before saving or fetching restricted details according to the team scopes.
- Record auditing logs continuously via `insert_access_log()` whenever users execute mutating actions or authenticate.
