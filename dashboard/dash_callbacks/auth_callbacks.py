"""Authentication Callbacks"""

from dash import Input, Output, State
from dash.exceptions import PreventUpdate


def register_auth_callbacks(app, LOGIN_PASSWORD):
    """Register authentication-related callbacks

    Args:
        app: Dash app instance
        LOGIN_PASSWORD: Password for authentication
    """

    @app.callback(
        Output("auth", "data"),
        [Input("login-btn", "n_clicks"), Input("password", "n_submit")],
        [State("password", "value")],
        prevent_initial_call=True,
    )
    def do_login(n_clicks, n_submit, password):
        print(
            f"DEBUG do_login: n_clicks={n_clicks}, n_submit={n_submit}, password={'***' if password else None}"
        )
        if not (n_clicks or n_submit):
            raise PreventUpdate
        if password == LOGIN_PASSWORD:
            return {"ok": True}
        return {"ok": False, "error": "Onjuist wachtwoord"}

    @app.callback(Output("login-error", "children"), [Input("auth", "data")])
    def login_error(auth):
        if auth and not auth.get("ok") and auth.get("error"):
            return auth.get("error")
        return ""

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        [Input("logout-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_logout(n_clicks):
        if n_clicks:
            return "/"
        raise PreventUpdate
