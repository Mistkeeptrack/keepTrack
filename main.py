import logging
import os
import threading
import uuid
from datetime import datetime
from functools import partial

import pycountry
import requests

from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    BooleanProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.resources import resource_add_path
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from kivy_garden.mapview import MapMarker, MapView

from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem
from kivymd.uix.textfield import MDTextField

from plyer import compass, gps

from supabase_client import supabase


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "images",
    "mistlogo.jpeg",
)

if os.path.exists(ICON_PATH):
    Config.set("kivy", "window_icon", ICON_PATH)

resource_add_path(BASE_DIR)

Window.size = (360, 640)
Window.title = " "

if os.path.exists(ICON_PATH):
    Window.set_icon(ICON_PATH)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def hex_to_rgba(hex_str: str):
    hex_str = hex_str.strip().lstrip("#")

    red = int(hex_str[0:2], 16) / 255.0
    green = int(hex_str[2:4], 16) / 255.0
    blue = int(hex_str[4:6], 16) / 255.0

    return [red, green, blue, 1.0]


class TileCard(ButtonBehavior, BoxLayout):
    title = StringProperty("")
    icon_text = StringProperty("")
    bg_hex = StringProperty("DDDDDD")

    @property
    def bg_rgba(self):
        return hex_to_rgba(self.bg_hex)


class SplashScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.go_next, 2)

    def go_next(self, _dt):
        self.manager.current = "create_account"


class CreateAccountScreen(Screen):
    pass


class SignInScreen(Screen):
    pass


class DesiredHomeScreen(Screen):
    pass


class NavigationScreen(Screen):
    """
    Embedded map, GPS tracking, destination search, routing,
    distance, ETA and reservation-aware navigation.
    """

    # Used as a desktop fallback until mobile GPS supplies a location.
    current_lat = NumericProperty(54.9783)
    current_lon = NumericProperty(-1.6178)

    destination_lat = NumericProperty(0.0)
    destination_lon = NumericProperty(0.0)
    destination_name = StringProperty("")

    mapview = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.current_marker = None
        self.destination_marker = None
        self.gps_running = False
        self._reservation = None

    def on_kv_post(self, *_args):
        """
        Create the MapView after the KV interface and map_box exist.
        """

        if self.mapview is not None:
            return

        if "map_box" not in self.ids:
            return

        self.mapview = MapView(
            zoom=13,
            lat=self.current_lat,
            lon=self.current_lon,
        )

        self.ids.map_box.add_widget(self.mapview)

        self.current_marker = MapMarker(
            lat=self.current_lat,
            lon=self.current_lon,
        )

        self.mapview.add_marker(self.current_marker)

    def on_enter(self, *_args):
        self.ids.location_label.text = (
            "Using Newcastle until GPS updates"
        )

        Clock.schedule_once(
            lambda _dt: self.load_next_reservation(),
            0.15,
        )

    def start_navigation(self):
        """
        Start GPS tracking on a supported mobile device.
        Desktop testing continues with the fallback location.
        """

        self.ids.location_label.text = "Getting your location..."

        try:
            gps.configure(
                on_location=self.on_location,
                on_status=self.on_status,
            )

            gps.start(
                minTime=1000,
                minDistance=1,
            )

            self.gps_running = True
            toast("Location tracking started")

        except Exception as error:
            print("GPS unavailable:", error)

            self.ids.location_label.text = (
                "GPS is unavailable here; "
                "using Newcastle preview location"
            )

            toast("Live GPS works on a supported mobile device")

    def stop_navigation(self, show_message=True):
        if self.gps_running:
            try:
                gps.stop()
            except Exception:
                pass

        self.gps_running = False

        if show_message:
            toast("Location tracking stopped")

    def on_leave(self, *_args):
        self.stop_navigation(show_message=False)

    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")

        if lat is None or lon is None:
            return

        self.current_lat = float(lat)
        self.current_lon = float(lon)

        Clock.schedule_once(
            self._apply_location,
            0,
        )

    def _apply_location(self, _dt):
        self.ids.location_label.text = (
            f"{self.current_lat:.5f}, "
            f"{self.current_lon:.5f}"
        )

        if self.current_marker:
            self.current_marker.lat = self.current_lat
            self.current_marker.lon = self.current_lon

        if self.mapview:
            self.mapview.center_on(
                self.current_lat,
                self.current_lon,
            )

    def on_status(self, status_type, status):
        print(
            "GPS status:",
            status_type,
            status,
        )

    def center_on_me(self):
        if self.mapview:
            self.mapview.center_on(
                self.current_lat,
                self.current_lon,
            )

    def search_destination(self):
        query = self.ids.destination_search.text.strip()

        if not query:
            toast("Enter a destination")
            return

        self.ids.route_status.text = "Searching..."

        threading.Thread(
            target=self._search_worker,
            args=(query,),
            daemon=True,
        ).start()

    def _search_worker(self, query):
        """
        Search OpenStreetMap without blocking the Kivy interface.
        """

        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": 1,
                },
                headers={
                    "User-Agent": "MIST-KeepTrack/1.0",
                },
                timeout=15,
            )

            response.raise_for_status()
            results = response.json()

            if not results:
                Clock.schedule_once(
                    lambda _dt: self._set_route_error(
                        "Destination not found"
                    ),
                    0,
                )
                return

            result = results[0]

            latitude = float(result["lat"])
            longitude = float(result["lon"])

            name = (
                result.get("display_name")
                or query
            )

            Clock.schedule_once(
                lambda _dt: self.set_destination(
                    name,
                    latitude,
                    longitude,
                ),
                0,
            )

        except Exception as error:
            print("Destination search error:", error)

            Clock.schedule_once(
                lambda _dt: self._set_route_error(
                    "Unable to search right now"
                ),
                0,
            )

    def set_destination(self, name, latitude, longitude):
        self.destination_name = name
        self.destination_lat = float(latitude)
        self.destination_lon = float(longitude)

        self.ids.destination_label.text = name
        self.ids.route_status.text = "Destination selected"

        if self.destination_marker and self.mapview:
            try:
                self.mapview.remove_marker(
                    self.destination_marker
                )
            except Exception:
                pass

        self.destination_marker = MapMarker(
            lat=self.destination_lat,
            lon=self.destination_lon,
        )

        if self.mapview:
            self.mapview.add_marker(
                self.destination_marker
            )

            self.mapview.center_on(
                self.destination_lat,
                self.destination_lon,
            )

        self.calculate_route()

    def calculate_route(self):
        if not self.destination_name:
            toast("Choose a destination first")
            return

        self.ids.route_status.text = "Calculating route..."

        threading.Thread(
            target=self._route_worker,
            daemon=True,
        ).start()

    def _route_worker(self):
        """
        Request driving distance and ETA from OSRM.
        """

        try:
            route_url = (
                "https://router.project-osrm.org/"
                "route/v1/driving/"
                f"{self.current_lon},{self.current_lat};"
                f"{self.destination_lon},{self.destination_lat}"
            )

            response = requests.get(
                route_url,
                params={
                    "overview": "false",
                    "steps": "false",
                },
                timeout=20,
            )

            response.raise_for_status()
            result = response.json()

            routes = result.get("routes") or []

            if not routes:
                raise ValueError("No route was returned")

            route = routes[0]

            distance_km = (
                float(route.get("distance", 0)) / 1000
            )

            duration_minutes = max(
                1,
                round(
                    float(route.get("duration", 0)) / 60
                ),
            )

            Clock.schedule_once(
                lambda _dt: self._show_route(
                    distance_km,
                    duration_minutes,
                ),
                0,
            )

        except Exception as error:
            print("Routing error:", error)

            Clock.schedule_once(
                lambda _dt: self._set_route_error(
                    "Route unavailable"
                ),
                0,
            )

    def _show_route(
        self,
        distance_km,
        duration_minutes,
    ):
        self.ids.eta_label.text = (
            f"{duration_minutes} min"
        )

        self.ids.distance_label.text = (
            f"{distance_km:.1f} km"
        )

        self.ids.route_status.text = "Route ready"

    def _set_route_error(self, message):
        self.ids.route_status.text = message
        toast(message)

    def load_next_reservation(self):
        """
        Load the newest reservation when a compatible Supabase
        reservations table is available.

        The Navigation screen continues to work if that table has
        not been created yet.
        """

        app = MDApp.get_running_app()

        if not app.current_user:
            self._show_no_reservation()
            return

        user_id = app.current_user.id

        def worker():
            try:
                reservations = (
                    supabase.table("reservations")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                    .data
                ) or []

                reservation = (
                    reservations[0]
                    if reservations
                    else None
                )

                Clock.schedule_once(
                    lambda _dt: self._apply_reservation(
                        reservation
                    ),
                    0,
                )

            except Exception as error:
                print(
                    "Reservation lookup skipped:",
                    error,
                )

                Clock.schedule_once(
                    lambda _dt: self._show_no_reservation(),
                    0,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _apply_reservation(self, reservation):
        if not reservation:
            self._show_no_reservation()
            return

        self._reservation = reservation

        venue = (
            reservation.get("venue_name")
            or reservation.get("business_name")
            or reservation.get("title")
            or "Upcoming reservation"
        )

        address = (
            reservation.get("address")
            or reservation.get("venue_address")
            or reservation.get("location")
            or ""
        )

        self.ids.reservation_title.text = venue

        self.ids.reservation_address.text = (
            address
            or "Tap this card to search for the venue"
        )

        self.ids.reservation_card.opacity = 1
        self.ids.reservation_card.disabled = False

    def _show_no_reservation(self):
        self._reservation = None

        self.ids.reservation_title.text = (
            "No upcoming reservation"
        )

        self.ids.reservation_address.text = (
            "Search for any destination below"
        )

        self.ids.reservation_card.opacity = 1
        self.ids.reservation_card.disabled = True

    def navigate_to_reservation(self):
        if not self._reservation:
            return

        destination = (
            self._reservation.get("address")
            or self._reservation.get("venue_address")
            or self._reservation.get("location")
            or self.ids.reservation_title.text
        )

        self.ids.destination_search.text = destination
        self.search_destination()


class ChatScreen(Screen):
    def on_enter(self, *_args):
        self.load_contacts()

    def load_contacts(self):
        self.ids.contact_list.clear_widgets()

        app = MDApp.get_running_app()

        if not app.current_user:
            self.ids.contact_list.add_widget(
                OneLineListItem(
                    text="Please sign in first"
                )
            )
            return

        try:
            contacts = (
                supabase.table("chat_contacts")
                .select("*")
                .eq(
                    "user_id",
                    app.current_user.id,
                )
                .execute()
                .data
            ) or []

            for contact in contacts:
                item = OneLineListItem(
                    text=contact.get(
                        "contact_name",
                        "Unknown",
                    )
                )

                item.bind(
                    on_release=partial(
                        self.open_chat,
                        contact,
                    )
                )

                self.ids.contact_list.add_widget(item)

        except Exception as error:
            self.ids.contact_list.add_widget(
                OneLineListItem(
                    text=f"Error loading contacts: {error}"
                )
            )

    def add_contact(self):
        toast("Add contact coming next")

    def delete_contact(self):
        toast("Delete contact coming next")

    def open_chat(self, contact, *_args):
        contact_name = contact.get(
            "contact_name",
            "Unknown",
        )

        toast(f"Opening chat with {contact_name}")


class ReminderScreen(Screen):
    pass


class PairingScreen(Screen):
    pass


class OrgScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass

class TaskScreen(Screen):
    """
    Displays the signed-in user's tasks as an iPhone-style
    searchable notes list.

    Records are stored in the existing Supabase tasks table.
    """

    def on_enter(self, *_args):
        # Allow the screen to appear before contacting Supabase.
        Clock.schedule_once(
            self.start_loading_notes,
            0.2,
        )

    def start_loading_notes(self, _dt):
        self.load_notes()

    def create_note(self):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        editor = self.manager.get_screen(
            "note_editor"
        )

        editor.open_new_note()
        self.manager.current = "note_editor"

    def search_notes(self, search_text):
        self.load_notes(search_text)

    def load_notes(self, search_text=""):
        app = MDApp.get_running_app()

        if not app.current_user:
            self.display_notes([])
            toast("Please sign in first")
            return

        query = search_text.strip().lower()

        if "notes_list" in self.ids:
            self.ids.notes_list.clear_widgets()

            self.ids.notes_list.add_widget(
                MDLabel(
                    text="Loading notes...",
                    halign="center",
                    theme_text_color="Hint",
                    size_hint_y=None,
                    height=dp(100),
                )
            )

        user_id = app.current_user.id

        def worker():
            try:
                notes = (
                    supabase.table("tasks")
                    .select("*")
                    .eq("user_id", user_id)
                    .order(
                        "created_at",
                        desc=True,
                    )
                    .execute()
                    .data
                ) or []

                if query:
                    notes = [
                        note
                        for note in notes
                        if query
                        in (
                            note.get("title") or ""
                        ).lower()
                        or query
                        in (
                            note.get("description") or ""
                        ).lower()
                    ]

                Clock.schedule_once(
                    lambda _dt: self.display_notes(
                        notes
                    ),
                    0,
                )

            except Exception as error:
                print(
                    "Error loading tasks:",
                    error,
                )

                Clock.schedule_once(
                    lambda _dt: self.show_load_error(),
                    0,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def show_load_error(self):
        self.display_notes([])
        toast("Unable to load notes")

    def display_notes(self, notes):
        if "notes_list" not in self.ids:
            return

        notes_list = self.ids.notes_list
        notes_list.clear_widgets()

        if not notes:
            notes_list.add_widget(
                MDLabel(
                    text="No Notes",
                    halign="center",
                    theme_text_color="Hint",
                    size_hint_y=None,
                    height=dp(100),
                )
            )
            return

        for note in notes:
            note_id = note.get("id", "")

            title = (
                note.get("title") or ""
            ).strip() or "New Note"

            description = (
                note.get("description") or ""
            ).strip().replace("\n", " ")

            if len(description) > 65:
                description = (
                    description[:65] + "..."
                )

            date_text = self.format_note_date(
                note.get("created_at", "")
            )

            card = MDCard(
                orientation="vertical",
                size_hint_y=None,
                height=dp(92),
                padding=[
                    dp(15),
                    dp(8),
                    dp(15),
                    dp(6),
                ],
                spacing=dp(1),
                radius=[
                    dp(12),
                    dp(12),
                    dp(12),
                    dp(12),
                ],
                elevation=1,
                ripple_behavior=True,
                md_bg_color=(1, 1, 1, 1),
            )

            title_label = MDLabel(
                text=title,
                bold=True,
                font_size="17sp",
                size_hint_y=None,
                height=dp(30),
                shorten=True,
                shorten_from="right",
                theme_text_color="Custom",
                text_color=(0, 0, 0, 1),
            )

            preview_text = date_text

            if description:
                preview_text += (
                    f"   {description}"
                )

            preview_label = MDLabel(
                text=preview_text,
                font_size="13sp",
                size_hint_y=None,
                height=dp(34),
                shorten=True,
                shorten_from="right",
                theme_text_color="Hint",
            )

            card.add_widget(title_label)
            card.add_widget(preview_label)

            card.bind(
                on_release=partial(
                    self.open_note,
                    note_id,
                )
            )

            notes_list.add_widget(card)

    def open_note(self, note_id, *_args):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        editor = self.manager.get_screen(
            "note_editor"
        )

        editor.open_existing_note(note_id)
        self.manager.current = "note_editor"

    @staticmethod
    def format_note_date(date_string):
        if not date_string:
            return ""

        try:
            cleaned_date = date_string.replace(
                "Z",
                "+00:00",
            )

            note_date = datetime.fromisoformat(
                cleaned_date
            )

            if note_date.tzinfo:
                current_date = datetime.now(
                    note_date.tzinfo
                )
            else:
                current_date = datetime.now()

            if (
                note_date.date()
                == current_date.date()
            ):
                return note_date.strftime("%H:%M")

            return note_date.strftime(
                "%d/%m/%Y"
            )

        except (ValueError, TypeError):
            return ""


class NoteEditorScreen(Screen):
    """
    Creates, opens, automatically saves and deletes notes
    using the existing Supabase tasks table.
    """

    current_note_id = StringProperty("")
    created_at = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.loading_note = False
        self.save_event = None
        self.note_exists = False
        self.saving_note = False

    def open_new_note(self):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        self.loading_note = True

        now = datetime.now().isoformat()

        self.current_note_id = str(
            uuid.uuid4()
        )

        self.created_at = now
        self.note_exists = False

        self.ids.note_title.text = ""
        self.ids.note_body.text = ""

        self.ids.note_date.text = (
            self.display_date(now)
        )

        self.loading_note = False

    def open_existing_note(self, note_id):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        self.loading_note = True

        self.ids.note_title.text = ""
        self.ids.note_body.text = ""
        self.ids.note_date.text = "Loading..."

        user_id = app.current_user.id

        def worker():
            try:
                selected_note = (
                    supabase.table("tasks")
                    .select("*")
                    .eq("id", note_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                    .data
                )

                Clock.schedule_once(
                    lambda _dt: self.apply_opened_note(
                        selected_note
                    ),
                    0,
                )

            except Exception as error:
                print(
                    "Error opening task:",
                    error,
                )

                Clock.schedule_once(
                    lambda _dt: self.open_note_failed(),
                    0,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def apply_opened_note(self, selected_note):
        if not selected_note:
            self.loading_note = False
            toast("Note not found")
            self.manager.current = "tasks"
            return

        self.current_note_id = selected_note.get(
            "id",
            "",
        )

        self.created_at = selected_note.get(
            "created_at",
            datetime.now().isoformat(),
        )

        self.note_exists = True

        self.ids.note_title.text = (
            selected_note.get("title") or ""
        )

        self.ids.note_body.text = (
            selected_note.get("description")
            or ""
        )

        self.ids.note_date.text = (
            self.display_date(
                self.created_at
            )
        )

        self.loading_note = False

    def open_note_failed(self):
        self.loading_note = False
        toast("Unable to open note")
        self.manager.current = "tasks"

    def note_changed(self):
        if self.loading_note:
            return

        if not self.current_note_id:
            return

        if self.save_event:
            self.save_event.cancel()

        # Save after the user stops typing for a short time.
        self.save_event = Clock.schedule_once(
            self.auto_save_note,
            0.7,
        )

    def auto_save_note(self, _dt):
        self.save_event = None
        self.save_note()

    def save_note(self):
        if self.loading_note:
            return

        if self.saving_note:
            return

        if not self.current_note_id:
            return

        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        title = self.ids.note_title.text.strip()
        description = self.ids.note_body.text

        # Do not create a completely empty note.
        if not title and not description.strip():
            return

        now = datetime.now().isoformat()
        user_id = app.current_user.id

        note_data = {
            "id": self.current_note_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "created_at": self.created_at or now,
            "priority": "normal",
            "status": "active",
        }

        self.saving_note = True

        def worker():
            try:
                (
                    supabase.table("tasks")
                    .upsert(
                        note_data,
                        on_conflict="id",
                    )
                    .execute()
                )

                Clock.schedule_once(
                    lambda _dt: self.note_saved(
                        now
                    ),
                    0,
                )

            except Exception as error:
                print(
                    "Error saving task:",
                    error,
                )

                Clock.schedule_once(
                    lambda _dt: self.note_save_failed(),
                    0,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def note_saved(self, saved_at):
        self.saving_note = False
        self.note_exists = True

        self.ids.note_date.text = (
            self.display_date(saved_at)
        )

    def note_save_failed(self):
        self.saving_note = False
        toast("Unable to save note")

    def close_editor(self):
        if self.save_event:
            self.save_event.cancel()
            self.save_event = None

        # Save immediately before leaving.
        self.save_note()

        task_screen = self.manager.get_screen(
            "tasks"
        )

        self.manager.current = "tasks"

        Clock.schedule_once(
            lambda _dt: task_screen.load_notes(),
            0.3,
        )

    def confirm_delete(self):
        if not self.note_exists:
            self.close_editor()
            return

        dialog = MDDialog(
            title="Delete Note?",
            text=(
                "This note will be permanently "
                "deleted."
            ),
        )

        cancel_button = MDFlatButton(
            text="CANCEL",
            on_release=lambda _button: (
                dialog.dismiss()
            ),
        )

        delete_button = MDFlatButton(
            text="DELETE",
            theme_text_color="Custom",
            text_color=(0.9, 0.1, 0.1, 1),
            on_release=lambda _button: (
                self.delete_note(dialog)
            ),
        )

        dialog.buttons = [
            cancel_button,
            delete_button,
        ]

        dialog.open()

    def delete_note(self, dialog):
        app = MDApp.get_running_app()

        if not app.current_user:
            dialog.dismiss()
            toast("Please sign in first")
            return

        note_id = self.current_note_id
        user_id = app.current_user.id

        def worker():
            try:
                (
                    supabase.table("tasks")
                    .delete()
                    .eq("id", note_id)
                    .eq("user_id", user_id)
                    .execute()
                )

                Clock.schedule_once(
                    lambda _dt: self.note_deleted(
                        dialog
                    ),
                    0,
                )

            except Exception as error:
                print(
                    "Error deleting task:",
                    error,
                )

                Clock.schedule_once(
                    lambda _dt: self.note_delete_failed(
                        dialog
                    ),
                    0,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def note_deleted(self, dialog):
        dialog.dismiss()

        self.note_exists = False
        self.current_note_id = ""
        self.created_at = ""

        self.loading_note = True

        self.ids.note_title.text = ""
        self.ids.note_body.text = ""
        self.ids.note_date.text = ""

        self.loading_note = False

        task_screen = self.manager.get_screen(
            "tasks"
        )

        self.manager.current = "tasks"

        Clock.schedule_once(
            lambda _dt: task_screen.load_notes(),
            0.1,
        )

    def note_delete_failed(self, dialog):
        dialog.dismiss()
        toast("Unable to delete note")

    @staticmethod
    def display_date(date_string):
        if not date_string:
            return ""

        try:
            cleaned_date = date_string.replace(
                "Z",
                "+00:00",
            )

            date_value = datetime.fromisoformat(
                cleaned_date
            )

            return date_value.strftime(
                "%d %B %Y at %H:%M"
            )

        except (ValueError, TypeError):
            return ""
class MistApp(MDApp):
    title = " "

    is_signing_up = BooleanProperty(False)
    is_signing_in = BooleanProperty(False)

    def build(self):
        self.theme_cls.theme_style = "Light"

        # These must be defined before the KV screens are created.
        self.current_user = None
        self.current_profile = None

        Window.set_title(" ")

        if os.path.exists(ICON_PATH):
            Window.set_icon(ICON_PATH)

        Builder.load_file(
            os.path.join(
                BASE_DIR,
                "kv",
                "components.kv",
            )
        )

        Builder.load_file(
            os.path.join(
                BASE_DIR,
                "kv",
                "pages.kv",
            )
        )

        Builder.load_file(
            os.path.join(
                BASE_DIR,
                "kv",
                "splash.kv",
            )
        )

        Builder.load_file(
            os.path.join(
                BASE_DIR,
                "kv",
                "create_account.kv",
            )
        )

        Builder.load_file(
            os.path.join(
                BASE_DIR,
                "kv",
                "signin.kv",
            )
        )

        root = Builder.load_file(
            os.path.join(
                BASE_DIR,
                "kv",
                "main.kv",
            )
        )

        self.all_countries = sorted(
            country.name
            for country in pycountry.countries
        )

        self.country_dialog = None
        self.country_search_field = None
        self.country_list_box = None

        create_screen = root.get_screen(
            "create_account"
        )

        if "country_item" in create_screen.ids:
            try:
                create_screen.ids.country_item.set_item(
                    "United Kingdom"
                )

            except Exception:
                create_screen.ids.country_item.text = (
                    "United Kingdom"
                )

        return root

    def _toast(self, message: str):
        Clock.schedule_once(
            lambda _dt: toast(message),
            0,
        )

    def _go(self, screen_name: str):
        Clock.schedule_once(
            lambda _dt: self.go_to(screen_name),
            0,
        )

    def _set_signing_up(self, value: bool):
        Clock.schedule_once(
            lambda _dt: setattr(
                self,
                "is_signing_up",
                value,
            ),
            0,
        )

    def _set_signing_in(self, value: bool):
        Clock.schedule_once(
            lambda _dt: setattr(
                self,
                "is_signing_in",
                value,
            ),
            0,
        )

    def set_signup_status(self, text: str):
        def update_status(_dt):
            try:
                screen = self.root.get_screen(
                    "create_account"
                )

                screen.ids.signup_status.text = text

            except Exception:
                pass

        Clock.schedule_once(
            update_status,
            0,
        )

    def set_signin_status(self, text: str):
        def update_status(_dt):
            try:
                screen = self.root.get_screen(
                    "signin"
                )

                screen.ids.signin_status.text = text

            except Exception:
                pass

        Clock.schedule_once(
            update_status,
            0,
        )

    def go_to(self, screen_name: str):
        if not self.root:
            return

        if not self.root.has_screen(screen_name):
            print(
                f'No screen registered with name '
                f'"{screen_name}"'
            )

            toast(
                f"{screen_name.title()} page is unavailable"
            )
            return

        self.root.current = screen_name

    def back_to_home(self):
        self.go_to("home")

    def open_country_menu(self):
        self.open_country_search()

    def open_country_search(self):
        if self.country_dialog is None:
            content = MDBoxLayout(
                orientation="vertical",
                spacing=dp(10),
                size_hint_y=None,
                height=dp(420),
            )

            self.country_search_field = MDTextField(
                hint_text="Search country",
                mode="line",
                size_hint_x=1,
            )

            self.country_search_field.bind(
                text=self.filter_countries
            )

            self.country_list_box = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                spacing=0,
            )

            self.country_list_box.bind(
                minimum_height=(
                    self.country_list_box.setter(
                        "height"
                    )
                )
            )

            scroll = ScrollView(
                size_hint=(1, 1)
            )

            scroll.add_widget(
                self.country_list_box
            )

            content.add_widget(
                self.country_search_field
            )

            content.add_widget(scroll)

            self.country_dialog = MDDialog(
                title="Select Country",
                type="custom",
                content_cls=content,
            )

        self.country_search_field.text = ""

        self.populate_country_list(
            self.all_countries
        )

        self.country_dialog.open()

    def populate_country_list(self, countries):
        if not self.country_list_box:
            return

        self.country_list_box.clear_widgets()

        if not countries:
            self.country_list_box.add_widget(
                OneLineListItem(
                    text="No country found"
                )
            )
            return

        for country in countries:
            item = OneLineListItem(
                text=country,
            )

            item.bind(
                on_release=partial(
                    self.select_country_from_search,
                    country,
                )
            )

            self.country_list_box.add_widget(item)

    def filter_countries(self, _instance, value):
        query = value.strip().lower()

        if not query:
            filtered_countries = (
                self.all_countries
            )

        else:
            filtered_countries = [
                country
                for country in self.all_countries
                if query in country.lower()
            ]

        self.populate_country_list(
            filtered_countries
        )

    def select_country_from_search(
        self,
        country_name,
        *_args,
    ):
        create_screen = self.root.get_screen(
            "create_account"
        )

        country_item = (
            create_screen.ids.country_item
        )

        try:
            country_item.set_item(country_name)

        except Exception:
            country_item.text = country_name

        if self.country_dialog:
            self.country_dialog.dismiss()

    def set_country(self, country_name):
        create_screen = self.root.get_screen(
            "create_account"
        )

        country_item = (
            create_screen.ids.country_item
        )

        try:
            country_item.set_item(country_name)

        except Exception:
            country_item.text = country_name

    def signup_action(self):
        if self.is_signing_up:
            toast("Please wait...")
            return

        screen = self.root.get_screen(
            "create_account"
        )

        first_name = (
            screen.ids.first_name.text.strip()
        )

        last_name = (
            screen.ids.last_name.text.strip()
        )

        email = (
            screen.ids.email.text
            .strip()
            .lower()
        )

        password = screen.ids.password.text

        confirm_password = (
            screen.ids.confirm_password.text
        )

        accepted_terms = (
            screen.ids.terms_check.active
        )

        try:
            country = (
                screen.ids.country_item.text.strip()
            )
        except Exception:
            country = ""

        if not all(
            [
                first_name,
                last_name,
                email,
                password,
                confirm_password,
            ]
        ):
            toast("Fill all fields")
            return

        if "@" not in email:
            toast("Enter a valid email address")
            return

        if len(password) < 6:
            toast(
                "Password must contain at least "
                "six characters"
            )
            return

        if password != confirm_password:
            toast("Passwords do not match")
            return

        if not accepted_terms:
            toast("Accept terms")
            return

        self.is_signing_up = True

        self.set_signup_status(
            "Creating account..."
        )

        def worker():
            try:
                auth_response = (
                    supabase.auth.sign_up(
                        {
                            "email": email,
                            "password": password,
                        }
                    )
                )

                user = auth_response.user

                if not user:
                    self._toast("Sign up failed")

                    self.set_signup_status(
                        "Sign up failed."
                    )
                    return

                profile_data = {
                    "id": user.id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "country": country,
                }

                try:
                    (
                        supabase.table("profiles")
                        .upsert(
                            profile_data,
                            on_conflict="id",
                        )
                        .execute()
                    )

                except Exception as profile_error:
                    print(
                        "Profile creation error:",
                        profile_error,
                    )

                self._toast(
                    "Account created. Please sign in."
                )

                self.set_signup_status(
                    "Account created. Please sign in."
                )

                self._go("signin")

            except Exception as error:
                error_message = str(error)
                lower_message = (
                    error_message.lower()
                )

                if (
                    "over_email_send_rate_limit"
                    in lower_message
                    or "too many requests"
                    in lower_message
                    or " 429" in lower_message
                ):
                    message = (
                        "Too many signups. Try again "
                        "in a few minutes."
                    )

                    self._toast(message)
                    self.set_signup_status(message)

                elif (
                    "email_not_confirmed"
                    in lower_message
                ):
                    message = (
                        "Check your email and confirm "
                        "your account."
                    )

                    self._toast(message)
                    self.set_signup_status(message)

                elif (
                    "already" in lower_message
                    and (
                        "registered" in lower_message
                        or "exists" in lower_message
                    )
                ):
                    message = (
                        "Email already exists. "
                        "Please sign in."
                    )

                    self._toast(message)
                    self.set_signup_status(message)
                    self._go("signin")

                else:
                    print(
                        "Signup error:",
                        error_message,
                    )

                    self._toast(
                        f"Signup error: {error_message}"
                    )

                    self.set_signup_status(
                        f"Signup error: {error_message}"
                    )

            finally:
                self._set_signing_up(False)

                Clock.schedule_once(
                    lambda _dt: (
                        self.set_signup_status(" ")
                    ),
                    2,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def signin_action(self):
        if self.is_signing_in:
            toast("Please wait...")
            return

        screen = self.root.get_screen(
            "signin"
        )

        email = (
            screen.ids.signin_email.text
            .strip()
            .lower()
        )

        password = (
            screen.ids.signin_password.text
        )

        if not email or not password:
            toast("Enter email and password")
            return

        self.is_signing_in = True

        self.set_signin_status(
            "Signing in..."
        )

        def worker():
            try:
                auth_response = (
                    supabase.auth
                    .sign_in_with_password(
                        {
                            "email": email,
                            "password": password,
                        }
                    )
                )

                user = auth_response.user

                if not user:
                    self._toast("Login failed")

                    self.set_signin_status(
                        "Login failed."
                    )
                    return

                self.current_user = user

                try:
                    profile = (
                        supabase.table("profiles")
                        .select("*")
                        .eq("id", user.id)
                        .single()
                        .execute()
                        .data
                    )

                except Exception as profile_error:
                    print(
                        "Profile loading error:",
                        profile_error,
                    )

                    profile = None

                self.current_profile = (
                    profile or {}
                )

                first_name = (
                    self.current_profile.get(
                        "first_name"
                    )
                    or ""
                ).strip()

                if first_name:
                    self._toast(
                        f"Welcome {first_name}"
                    )
                else:
                    self._toast("Welcome")

                self.set_signin_status(" ")
                self._go("home")

            except Exception as error:
                error_message = str(error)
                lower_message = (
                    error_message.lower()
                )

                if (
                    "email_not_confirmed"
                    in lower_message
                ):
                    message = (
                        "Email not confirmed. "
                        "Check your inbox."
                    )

                    self._toast(message)
                    self.set_signin_status(message)

                elif (
                    "invalid" in lower_message
                    or "credentials" in lower_message
                    or "401" in lower_message
                ):
                    message = (
                        "Incorrect email or password"
                    )

                    self._toast(message)
                    self.set_signin_status(message)

                else:
                    print(
                        "Signin error:",
                        error_message,
                    )

                    self._toast(
                        f"Signin error: {error_message}"
                    )

                    self.set_signin_status(
                        f"Signin error: {error_message}"
                    )

            finally:
                self._set_signing_in(False)

                Clock.schedule_once(
                    lambda _dt: (
                        self.set_signin_status(" ")
                    ),
                    2,
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def sign_out(self):
        try:
            supabase.auth.sign_out()

        except Exception as error:
            print("Sign-out error:", error)

        self.current_user = None
        self.current_profile = None

        toast("Signed out")
        self.go_to("signin")


if __name__ == "__main__":
    MistApp().run()        