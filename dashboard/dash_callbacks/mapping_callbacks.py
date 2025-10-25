"""Mapping Configuration Callbacks"""

from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate


def register_mapping_callbacks(app):
    """Register mapping configuration callbacks"""

    def update_map_disabled(prop_values, price_range, name_query, current_run):
        if not current_run or not current_run.get("run_path"):
            raise PreventUpdate
        run_path = current_run["run_path"]
        excel_files = [
            f
            for f in os.listdir(run_path)
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        if not excel_files:
            return html.Div("Geen kaart beschikbaar")
        try:
            df = load_run_data(run_path)
        except Exception:
            return html.Div("Geen kaart beschikbaar")
        if prop_values and "property_type_airbnb" in df.columns:
            df = df[df["property_type_airbnb"].isin(prop_values)]
        if price_range and "price" in df.columns:
            low, high = price_range
            df = df[(df["price"] >= low) & (df["price"] <= high)]
        if name_query and "listing_title" in df.columns:
            s = str(name_query).lower()
            df = df[df["listing_title"].astype(str).str.lower().str.contains(s)]
        if df.empty or not {"latitude", "longitude"}.issubset(set(df.columns)):
            return html.Div("Geen kaartgegevens")
        df_map = df.drop_duplicates("room_id").copy()
        for col, default in [
            ("availability_rate", 100.0),
            ("days_available", 1),
            ("total_days", 1),
        ]:
            if col not in df_map.columns:
                df_map[col] = default
        try:
            gdf_gemeenten = gpd.read_file(GPKG_PATH, layer="gemeentegebied")
        except Exception:
            gdf_gemeenten = None  # type: ignore
        m = None
        if create_map is not None and gdf_gemeenten is not None:
            try:
                m = create_map(df_map, gdf_gemeenten, current_run.get("gemeenten", []))
            except Exception:
                m = None
        if m is None:
            return html.Div("Kaartfunctie niet beschikbaar")
        map_html = m.get_root().render()
        return html.Iframe(
            srcDoc=map_html,
            style={
                "width": "100%",
                "height": "600px",
                "border": "1px solid #e0e0e0",
                "borderRadius": "10px",
            },
        )

    # Details: update table based on the same filters - TEMPORARILY DISABLED FOR DEBUG

    def update_table_disabled(prop_values, price_range, name_query, current_run):
        if not current_run or not current_run.get("run_path"):
            raise PreventUpdate
        run_path = current_run["run_path"]
        excel_files = [
            f
            for f in os.listdir(run_path)
            if f.endswith(".xlsx") and not f.startswith("~$")
        ]
        if not excel_files:
            return [], []
        try:
            df = load_run_data(run_path)
        except Exception:
            return [], []
        if prop_values and "property_type_airbnb" in df.columns:
            df = df[df["property_type_airbnb"].isin(prop_values)]
        if price_range and "price" in df.columns:
            low, high = price_range
            df = df[(df["price"] >= low) & (df["price"] <= high)]
        if name_query and "listing_title" in df.columns:
            s = str(name_query).lower()
            df = df[df["listing_title"].astype(str).str.lower().str.contains(s)]
        candidate_cols = ["name", "price", "room_type", "bedrooms", "beds"]
        display_cols = [c for c in candidate_cols if c in df.columns]
        if not display_cols:
            display_cols = df.columns[: min(6, len(df.columns))].tolist()
        columns = [{"name": c, "id": c} for c in display_cols]
        data = df[display_cols].head(200).to_dict("records") if not df.empty else []
        return columns, data

    @app.callback(
        Output("mapping-tab-content", "children"),
        [Input("mapping-tabs", "value")],
        prevent_initial_call=False,
    )
    def render_mapping_tab(active_tab):
        from src.config.room_type_config import (
            ROOM_TYPE_MAPPING,
            STANDARD_PROPERTY_TYPES,
        )

        if active_tab == "tab-view":
            mapping_by_target = {}
            for source, target in ROOM_TYPE_MAPPING.items():
                if target not in mapping_by_target:
                    mapping_by_target[target] = []
                mapping_by_target[target].append(source)

            return html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            html.I(
                                                "search",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "18px",
                                                    "marginRight": "8px",
                                                    "color": "#616161",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Zoeken",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Input(
                                        id="mapping-search-input",
                                        type="text",
                                        placeholder="Zoek op type naam...",
                                        style={
                                            "width": "100%",
                                            "padding": "10px",
                                            "borderRadius": "6px",
                                            "border": "1px solid #ddd",
                                            "fontSize": "14px",
                                        },
                                    ),
                                ],
                                style={"flex": "2"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            html.I(
                                                "filter_list",
                                                className="material-icons",
                                                style={
                                                    "fontSize": "18px",
                                                    "marginRight": "8px",
                                                    "color": "#616161",
                                                    "verticalAlign": "middle",
                                                },
                                            ),
                                            html.Span(
                                                "Filter op Categorie",
                                                style={"verticalAlign": "middle"},
                                            ),
                                        ],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "flex",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="mapping-category-filter",
                                        options=[{"label": "Alle", "value": "Alle"}]
                                        + [
                                            {"label": cat, "value": cat}
                                            for cat in STANDARD_PROPERTY_TYPES
                                        ],
                                        value="Alle",
                                        clearable=False,
                                    ),
                                ],
                                style={"flex": "1"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "16px",
                            "marginBottom": "20px",
                        },
                    ),
                    html.Div(id="filtered-mappings-display"),
                ]
            )

        elif active_tab == "tab-edit":
            return html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                "info",
                                className="material-icons",
                                style={
                                    "fontSize": "20px",
                                    "marginRight": "12px",
                                    "color": "#ff9800",
                                },
                            ),
                            html.Span(
                                "Let op: Wijzigingen worden direct naar het configuratiebestand geschreven.",
                                style={"fontSize": "14px", "fontWeight": "500"},
                            ),
                        ],
                        style={
                            "background": "#fff3e0",
                            "padding": "16px",
                            "borderRadius": "8px",
                            "border": "1px solid #ffb74d",
                            "marginBottom": "24px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                    html.H4(
                        "Nieuwe Mapping Toevoegen",
                        style={
                            "marginBottom": "16px",
                            "color": "#10357e",
                            "fontSize": "18px",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Gedetecteerd Type",
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Input(
                                        id="new-detected-type",
                                        type="text",
                                        placeholder="Bijv: Entire vacation home",
                                        style={
                                            "width": "100%",
                                            "padding": "10px",
                                            "borderRadius": "6px",
                                            "border": "1px solid #ddd",
                                            "fontSize": "14px",
                                        },
                                    ),
                                ],
                                style={"flex": "1"},
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Map naar Categorie",
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                            "color": "#424242",
                                            "marginBottom": "8px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="new-mapped-category",
                                        options=[
                                            {"label": cat, "value": cat}
                                            for cat in STANDARD_PROPERTY_TYPES
                                        ],
                                        value=STANDARD_PROPERTY_TYPES[0]
                                        if STANDARD_PROPERTY_TYPES
                                        else None,
                                        clearable=False,
                                        style={"fontSize": "14px"},
                                    ),
                                ],
                                style={"flex": "1"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "16px",
                            "marginBottom": "16px",
                        },
                    ),
                    html.Button(
                        [
                            html.I(
                                "add",
                                className="material-icons",
                                style={
                                    "fontSize": "18px",
                                    "marginRight": "8px",
                                    "verticalAlign": "middle",
                                },
                            ),
                            html.Span("Toevoegen", style={"verticalAlign": "middle"}),
                        ],
                        id="add-mapping-btn",
                        n_clicks=0,
                        style={
                            "background": "#1565c0",
                            "color": "white",
                            "border": "none",
                            "padding": "12px 24px",
                            "borderRadius": "8px",
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    ),
                    html.Div(id="add-mapping-feedback", style={"marginTop": "16px"}),
                    html.Hr(
                        style={
                            "margin": "32px 0",
                            "border": "none",
                            "borderTop": "1px solid #e0e0e0",
                        }
                    ),
                    html.H4(
                        "Bulk Toevoegen",
                        style={
                            "marginBottom": "16px",
                            "color": "#10357e",
                            "fontSize": "18px",
                        },
                    ),
                    html.P(
                        "Voeg meerdere mappings toe, één per regel in het formaat: detected_type -> category",
                        style={
                            "fontSize": "13px",
                            "color": "#757575",
                            "marginBottom": "12px",
                        },
                    ),
                    dcc.Textarea(
                        id="bulk-mappings-input",
                        placeholder="Entire beach house -> Entire home\nPrivate room in villa -> Private room\nRoom in hostel -> Hotel",
                        style={
                            "width": "100%",
                            "height": "150px",
                            "padding": "12px",
                            "borderRadius": "6px",
                            "border": "1px solid #ddd",
                            "fontSize": "13px",
                            "fontFamily": "monospace",
                        },
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Standaard categorie (indien niet gespecificeerd)",
                                style={
                                    "fontSize": "14px",
                                    "fontWeight": "600",
                                    "color": "#424242",
                                    "marginBottom": "8px",
                                    "display": "block",
                                },
                            ),
                            dcc.Dropdown(
                                id="bulk-default-category",
                                options=[
                                    {"label": cat, "value": cat}
                                    for cat in STANDARD_PROPERTY_TYPES
                                ],
                                value=STANDARD_PROPERTY_TYPES[0]
                                if STANDARD_PROPERTY_TYPES
                                else None,
                                clearable=False,
                                style={"fontSize": "14px"},
                            ),
                        ],
                        style={
                            "marginTop": "16px",
                            "marginBottom": "16px",
                            "maxWidth": "400px",
                        },
                    ),
                    html.Button(
                        [
                            html.I(
                                "add_circle",
                                className="material-icons",
                                style={
                                    "fontSize": "18px",
                                    "marginRight": "8px",
                                    "verticalAlign": "middle",
                                },
                            ),
                            html.Span(
                                "Bulk Toevoegen", style={"verticalAlign": "middle"}
                            ),
                        ],
                        id="bulk-add-btn",
                        n_clicks=0,
                        style={
                            "background": "#1565c0",
                            "color": "white",
                            "border": "none",
                            "padding": "12px 24px",
                            "borderRadius": "8px",
                            "fontSize": "14px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    ),
                    html.Div(id="bulk-add-feedback", style={"marginTop": "16px"}),
                ],
                style={
                    "background": "white",
                    "padding": "24px",
                    "borderRadius": "8px",
                    "border": "1px solid #e0e0e0",
                },
            )

        return html.Div("Select a tab")

    @app.callback(
        Output("filtered-mappings-display", "children"),
        [
            Input("mapping-tabs", "value"),
            Input("mapping-search-input", "value"),
            Input("mapping-category-filter", "value"),
        ],
        prevent_initial_call=False,
    )
    def filter_mappings_display(active_tab, search_term, filter_category):
        from src.config.room_type_config import (
            ROOM_TYPE_MAPPING,
            STANDARD_PROPERTY_TYPES,
        )

        if active_tab != "tab-view":
            return html.Div()

        search_term = search_term or ""
        filter_category = filter_category or "Alle"

        filtered_mappings = {}
        for key, value in sorted(ROOM_TYPE_MAPPING.items()):
            if filter_category != "Alle" and value != filter_category:
                continue
            if search_term and search_term.lower() not in key.lower():
                continue
            filtered_mappings[key] = value

        mapping_by_target = {}
        for source, target in filtered_mappings.items():
            if target not in mapping_by_target:
                mapping_by_target[target] = []
            mapping_by_target[target].append(source)

        count_div = html.Div(
            f"Weergave van {len(filtered_mappings)} van {len(ROOM_TYPE_MAPPING)} mappings",
            style={"fontSize": "13px", "color": "#757575", "marginBottom": "16px"},
        )

        category_cards = []
        for category in STANDARD_PROPERTY_TYPES:
            category_mappings = mapping_by_target.get(category, [])

            if category_mappings:
                category_cards.append(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.I(
                                        "label",
                                        className="material-icons",
                                        style={
                                            "fontSize": "20px",
                                            "marginRight": "10px",
                                            "color": "#10357e",
                                        },
                                    ),
                                    html.H4(
                                        f"{category} ({len(category_mappings)} mappings)",
                                        style={
                                            "margin": 0,
                                            "color": "#10357e",
                                            "fontSize": "16px",
                                            "fontWeight": "600",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "marginBottom": "12px",
                                    "paddingBottom": "12px",
                                    "borderBottom": "2px solid #e0e0e0",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Span(
                                                source_type,
                                                style={
                                                    "background": "#f5f5f5",
                                                    "padding": "6px 12px",
                                                    "borderRadius": "4px",
                                                    "fontSize": "13px",
                                                    "color": "#424242",
                                                    "display": "inline-block",
                                                },
                                            )
                                        ],
                                        style={"marginBottom": "8px"},
                                    )
                                    for source_type in sorted(category_mappings)
                                ]
                            ),
                        ],
                        style={
                            "background": "white",
                            "padding": "20px",
                            "borderRadius": "8px",
                            "border": "1px solid #e0e0e0",
                            "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                            "marginBottom": "16px",
                        },
                    )
                )

        if not category_cards:
            return html.Div(
                [
                    count_div,
                    html.Div(
                        [
                            html.I(
                                "search_off",
                                className="material-icons",
                                style={
                                    "fontSize": "48px",
                                    "color": "#bdbdbd",
                                    "marginBottom": "16px",
                                },
                            ),
                            html.P(
                                "Geen mappings gevonden met de huidige filters",
                                style={"fontSize": "14px", "color": "#757575"},
                            ),
                        ],
                        style={
                            "textAlign": "center",
                            "padding": "40px",
                            "background": "white",
                            "borderRadius": "8px",
                            "border": "1px solid #e0e0e0",
                        },
                    ),
                ]
            )

        return html.Div([count_div] + category_cards)

    @app.callback(
        Output("add-mapping-feedback", "children"),
        [Input("add-mapping-btn", "n_clicks")],
        [State("new-detected-type", "value"), State("new-mapped-category", "value")],
        prevent_initial_call=True,
    )
    def add_single_mapping(n_clicks, detected_type, mapped_category):
        if not n_clicks:
            return ""

        if not detected_type or not detected_type.strip():
            return html.Div(
                [
                    html.I(
                        "warning",
                        className="material-icons",
                        style={
                            "fontSize": "20px",
                            "marginRight": "12px",
                            "verticalAlign": "middle",
                        },
                    ),
                    html.Span(
                        "Vul een gedetecteerd type in",
                        style={"verticalAlign": "middle"},
                    ),
                ],
                style={
                    "background": "#fff3e0",
                    "padding": "16px",
                    "borderRadius": "8px",
                    "border": "1px solid #ffb74d",
                    "display": "flex",
                    "alignItems": "center",
                    "color": "#f57c00",
                },
            )

        from src.config.room_type_updater import add_mapping_to_config

        success, message = add_mapping_to_config(detected_type.strip(), mapped_category)

        if success:
            return html.Div(
                [
                    html.I(
                        "check_circle",
                        className="material-icons",
                        style={
                            "fontSize": "20px",
                            "marginRight": "12px",
                            "verticalAlign": "middle",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(message, style={"marginBottom": "8px"}),
                            html.P(
                                "Herlaad de pagina om de nieuwe mapping te zien",
                                style={
                                    "fontSize": "13px",
                                    "color": "#616161",
                                    "margin": 0,
                                },
                            ),
                        ],
                        style={"verticalAlign": "middle"},
                    ),
                ],
                style={
                    "background": "#e8f5e9",
                    "padding": "16px",
                    "borderRadius": "8px",
                    "border": "1px solid #81c784",
                    "display": "flex",
                    "alignItems": "flex-start",
                    "color": "#2e7d32",
                },
            )
        else:
            return html.Div(
                [
                    html.I(
                        "error",
                        className="material-icons",
                        style={
                            "fontSize": "20px",
                            "marginRight": "12px",
                            "verticalAlign": "middle",
                        },
                    ),
                    html.Span(message, style={"verticalAlign": "middle"}),
                ],
                style={
                    "background": "#ffebee",
                    "padding": "16px",
                    "borderRadius": "8px",
                    "border": "1px solid #e57373",
                    "display": "flex",
                    "alignItems": "center",
                    "color": "#c62828",
                },
            )
