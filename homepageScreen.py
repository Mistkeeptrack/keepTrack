# main.py
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

import threading
import requests

# MapView (OpenStreetMap tiles)
from kivy_garden.mapview import MapView, MapMarkerPopup

# Optional (Android/iOS): live GPS
try:
    from plyer import gps
    HAS_GPS = True
except Exception:
    HAS_GPS = False

KV = r"""
#:import dp kivy.metrics.dp

<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"

        # Top bar
        MDBoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: dp(16), 0
            md_bg_color: 1, 1, 1, 1

            MDLabel:
                text: "LOCK"
                bold: True
                halign: "left"
            MDLabel:
                text: "Jason63"
                bold: True
                halign: "center"
            MDIconButton:
                icon: "plus"
                pos_hint: {"center_y": .5}
                on_release: app.toast("Add action")
            MDIconButton:
                icon: "bookmark-outline"
                pos_hint: {"center_y": .5}
                on_release: app.toast("Bookmark")

        # Profile header
        MDBoxLayout:
            size_hint_y: None
            height: dp(92)
            padding: dp(16), dp(8)
            spacing: dp(12)

            MDBoxLayout:
                size_hint: None, None
                size: dp(56), dp(56)
                md_bg_color: .9, .9, .9, 1
                radius: [dp(28), dp(28), dp(28), dp(28)]
                MDIcon:
                    icon: "account"
                    halign: "center"
                    valign: "center"

            MDBoxLayout:
                orientation: "vertical"
                spacing: dp(4)
                MDLabel:
                    text: "MIST"
                    font_style: "H5"
                    bold: True
                MDLabel:
                    text: "IT Entrepreneur"
                    theme_text_color: "Hint"

        # Tiles grid
        MDGridLayout:
            cols: 2
            padding: dp(16)
            spacing: dp(16)

            TileButton:
                title: "Navigation"
                icon_text: ">"
                on_release: app.go("navigation")

            TileButton:
                title: "Chat"
                icon_text: "C"
                on_release: app.go("chat")

            TileButton:
                title: "Reminder"
                icon_text: "R"
                on_release: app.go("reminder")

            TileButton:
                title: "Device Pairing"
                icon_text: "P"
                on_release: app.go("pairing")

            TileButton:
                title: "Connect to\\norganization"
                icon_text: "L"
                on_release: app.go("org")

            TileButton:
                title: "Settings"
                icon_text: "S"
                on_release: app.go("settings")


<TileButton@MDCard>:
    title: ""
    icon_text: ""
    radius: [dp(22), dp(22), dp(22), dp(22)]
    md_bg_color: .92, .92, .92, 1
    ripple_behavior: True
    elevation: 0
    padding: dp(16)
    size_hint_y: None
    height: dp(170)

    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(18)

        MDBoxLayout:
            size_hint: None, None
            size: dp(56), dp(56)
            md_bg_color: .95, .95, .95, 1
            radius: [dp(18), dp(18), dp(18), dp(18)]
            MDLabel:
                text: root.icon_text
                halign: "center"
                valign: "center"
                bold: True
                font_style: "H6"

        Widget:

        MDLabel:
            text: root.title
            bold: True
            font_style: "H6"


<NavScreen>:
    name: "navigation"
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Navigation"
            left_action_items: [["arrow-left", lambda x: app.go("home")]]
            right_action_items: [["crosshairs-gps", lambda x: root.center_on_me()]]

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(12)
            spacing: dp(10)

            # Destination input row
            MDBoxLayout:
                size_hint_y: None
                height: dp(48)
                spacing: dp(10)

                MDTextField:
                    id: dest
                    hint_text: "Search destination (e.g., '221B Baker Street, London')"
                    mode: "rectangle"

                MDRaisedButton:
                    text: "Route"
                    on_release: root.route_to_destination()

            # Map container
            MDCard:
                radius: [dp(16), dp(16), dp(16), dp(16)]
                elevation: 0
                md_bg_color: 1, 1, 1, 1

                MDBoxLayout:
                    id: map_box
                    orientation: "vertical"

            # Start/Stop
            MDBoxLayout:
                size_hint_y: None
                height: dp(56)
                spacing: dp(10)

                MDRaisedButton:
                    text: "Start GPS Follow"
                    on_release: root.start_gps_follow()

                MDFlatButton:
                    text: "Stop"
                    on_release: root.stop_gps_follow()


<ChatScreen>:
    name: "chat"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Chat"
            left_action_items: [["arrow-left", lambda x: app.go("home")]]

        MDBoxLayout:
            padding: dp(12)
            orientation: "vertical"
            spacing: dp(12)

            MDTextField:
                hint_text: "Search Contact"
                mode: "rectangle"

            MDLabel:
                text: "Placeholder: contact list + chat threads"
                theme_text_color: "Hint"


<ReminderScreen>:
    name: "reminder"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Reminder"
            left_action_items: [["arrow-left", lambda x: app.go("home")]]

        MDBoxLayout:
            padding: dp(12)
            orientation: "vertical"
            spacing: dp(12)

            MDCard:
                radius: [dp(16), dp(16), dp(16), dp(16)]
                md_bg_color: 1,1,1,1
                elevation: 0
                padding: dp(16)
                MDBoxLayout:
                    spacing: dp(12)
                    MDRaisedButton:
                        text: "Personal"
                        on_release: app.toast("Open Personal Reminders")
                    MDRaisedButton:
                        text: "External"
                        on_release: app.toast("Open External Reminders")

            MDRaisedButton:
                text: "+"
                pos_hint: {"center_x": .5}
                on_release: app.toast("Add Reminder")


<PairingScreen>:
    name: "pairing"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Device Pairing"
            left_action_items: [["arrow-left", lambda x: app.go("home")]]

        MDBoxLayout:
            padding: dp(12)
            orientation: "vertical"
            spacing: dp(12)

            MDTextField:
                hint_text: "Search devices"
                mode: "rectangle"
            MDLabel:
                text: "Placeholder: device scan results + pair/unpair"
                theme_text_color: "Hint"


<OrgScreen>:
    name: "org"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Connect to organization"
            left_action_items: [["arrow-left", lambda x: app.go("home")]]

        MDBoxLayout:
            padding: dp(12)
            orientation: "vertical"
            spacing: dp(12)

            MDTextField:
                hint_text: "Search organization"
                mode: "rectangle"
            MDLabel:
                text: "Placeholder: org feed + connect button"
                theme_text_color: "Hint"


<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Settings"
            left_action_items: [["arrow-left", lambda x: app.go("home")]]

        MDBoxLayout:
            padding: dp(12)
            orientation: "vertical"
            spacing: dp(10)

            MDTextField:
                hint_text: "Search"
                mode: "rectangle"

            MDLabel:
                text: "Account"
            MDLabel:
                text: "Notifications"
            MDLabel:
                text: "Appearance"
            MDLabel:
                text: "Privacy & security"
            MDLabel:
                text: "Help and Support"
            MDLabel:
                text: "About"
"""


class HomeScreen(MDScreen):
    pass


class ChatScreen(MDScreen):
    pass


class ReminderScreen(MDScreen):
    pass


class PairingScreen(MDScreen):
    pass


class OrgScreen(MDScreen):
    pass


class SettingsScreen(MDScreen):
    pass


class NavScreen(MDScreen):
    """
    Live navigation screen:
      - OSM map tiles via MapView
      - live GPS follow (plyer.gps) where available
      - geocode destination via Nominatim
      - route via OSRM and draw polyline
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mapview = None
        self.me_marker = None
        self.dest_marker = None
        self.route_line = None
        self.following = False

        # Default starting point (fallback)
        self.current_lat = 37.7749
        self.current_lon = -122.4194

    def on_kv_post(self, *args):
        if not self.mapview:
            self.mapview = MapView(zoom=13, lat=self.current_lat, lon=self.current_lon)
            self.ids.map_box.add_widget(self.mapview)

            self.me_marker = MapMarkerPopup(lat=self.current_lat, lon=self.current_lon)
            self.mapview.add_marker(self.me_marker)

    def _alert(self, title, text):
        dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()

    def center_on_me(self):
        if not self.mapview:
            return
        self.mapview.center_on(self.current_lat, self.current_lon)

    def start_gps_follow(self):
        self.following = True
        if not HAS_GPS:
            self._alert("GPS not available",
                        "plyer.gps is not available on this platform.\n"
                        "This usually works on Android/iOS builds.\n"
                        "We will keep using the fallback location.")
            return

        try:
            gps.configure(on_location=self._on_gps_location, on_status=self._on_gps_status)
            gps.start(minTime=1000, minDistance=1)
        except Exception as e:
            self._alert("GPS error", str(e))

    def stop_gps_follow(self):
        self.following = False
        if HAS_GPS:
            try:
                gps.stop()
            except Exception:
                pass

    def _on_gps_status(self, stype, status):
        # status events from platform
        pass

    def _on_gps_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is None or lon is None:
            return
        self.current_lat = float(lat)
        self.current_lon = float(lon)

        def ui_update(_dt):
            if self.me_marker:
                self.me_marker.lat = self.current_lat
                self.me_marker.lon = self.current_lon
            if self.following and self.mapview:
                self.mapview.center_on(self.current_lat, self.current_lon)

        Clock.schedule_once(ui_update, 0)

    def route_to_destination(self):
        query = (self.ids.dest.text or "").strip()
        if not query:
            self._alert("Destination required", "Type a destination to route to.")
            return

        # Network work in background thread
        threading.Thread(target=self._route_worker, args=(query,), daemon=True).start()

    def _route_worker(self, query: str):
        try:
            # 1) Geocode destination using Nominatim
            geo = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": "KeepTrackApp/1.0"},
                timeout=15,
            )
            geo.raise_for_status()
            data = geo.json()
            if not data:
                Clock.schedule_once(lambda dt: self._alert("Not found", "No results for that destination."), 0)
                return

            dlat = float(data[0]["lat"])
            dlon = float(data[0]["lon"])

            # 2) Route using OSRM (driving)
            route = requests.get(
                f"https://router.project-osrm.org/route/v1/driving/"
                f"{self.current_lon},{self.current_lat};{dlon},{dlat}",
                params={"overview": "full", "geometries": "geojson"},
                timeout=20,
            )
            route.raise_for_status()
            rj = route.json()
            if rj.get("code") != "Ok":
                Clock.schedule_once(lambda dt: self._alert("Routing failed", "OSRM could not build a route."), 0)
                return

            coords = rj["routes"][0]["geometry"]["coordinates"]  # list of [lon,lat]

            # Update UI
            Clock.schedule_once(lambda dt: self._draw_route(dlat, dlon, coords), 0)

        except Exception as e:
            Clock.schedule_once(lambda dt: self._alert("Network error", str(e)), 0)

    def _draw_route(self, dlat, dlon, coords):
        if not self.mapview:
            return

        # Destination marker
        if self.dest_marker:
            self.mapview.remove_marker(self.dest_marker)
        self.dest_marker = MapMarkerPopup(lat=dlat, lon=dlon)
        self.mapview.add_marker(self.dest_marker)

        # Center map to show start roughly
        self.mapview.center_on(self.current_lat, self.current_lon)

        # Remove previous route line if any
        if self.route_line:
            try:
                self.mapview.canvas.after.remove(self.route_line)
            except Exception:
                pass
            self.route_line = None

        # Convert geo coords -> screen points, draw on canvas.after.
        # We redraw when map moves/zooms for accuracy (simple approach: redraw periodically).
        self._last_route_coords = coords
        self._schedule_route_redraw()

    def _schedule_route_redraw(self):
        # cancel previous schedule and redraw a few times per second while user interacts
        if hasattr(self, "_redraw_ev") and self._redraw_ev is not None:
            self._redraw_ev.cancel()
        self._redraw_ev = Clock.schedule_interval(lambda dt: self._redraw_route_line(), 0.2)

        # stop frequent redraw after a bit
        Clock.schedule_once(lambda dt: self._stop_route_redraw(), 5)

    def _stop_route_redraw(self):
        if hasattr(self, "_redraw_ev") and self._redraw_ev is not None:
            self._redraw_ev.cancel()
            self._redraw_ev = None
        # final redraw
        self._redraw_route_line()

    def _redraw_route_line(self):
        if not self.mapview or not getattr(self, "_last_route_coords", None):
            return

        # remove old line
        if self.route_line:
            try:
                self.mapview.canvas.after.remove(self.route_line)
            except Exception:
                pass
            self.route_line = None

        points = []
        for lon, lat in self._last_route_coords:
            x, y = self.mapview.get_window_xy_from(lat, lon, self.mapview.zoom)
            points.extend([x, y])

        # If points are off-screen or too few, skip
        if len(points) < 4:
            return

        with self.mapview.canvas.after:
            Color(1, 0.6, 0, 1)  # amber-ish like your UI
            self.route_line = Line(points=points, width=2)


class KeepTrackApp(MDApp):
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)
        Builder.load_string(KV)

        from kivy.uix.screenmanager import ScreenManager
        sm = ScreenManager()

        sm.add_widget(HomeScreen())
        sm.add_widget(NavScreen())
        sm.add_widget(ChatScreen())
        sm.add_widget(ReminderScreen())
        sm.add_widget(PairingScreen())
        sm.add_widget(OrgScreen())
        sm.add_widget(SettingsScreen())

        self.sm = sm
        return sm

    def go(self, screen_name: str):
        self.sm.current = screen_name

    def toast(self, msg: str):
        try:
            from kivymd.toast import toast
            toast(msg)
        except Exception:
            print(msg)


if __name__ == "__main__":
    KeepTrackApp().run()