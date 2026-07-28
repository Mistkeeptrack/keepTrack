import os
import threading
import logging
import pycountry

import uuid
from kivy.config import Config
from supabase_auth import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "images", "mistlogo.jpeg")

if os.path.exists(ICON_PATH):
    Config.set("kivy", "window_icon", ICON_PATH)

from kivy.resources import resource_add_path
resource_add_path(BASE_DIR)

from datetime import datetime
from functools import partial
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

from supabase_client import supabase

from plyer import gps
from plyer import compass


Window.size = (360, 640)
Window.title = " "
if os.path.exists(ICON_PATH):
    Window.set_icon(ICON_PATH)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def hex_to_rgba(hex_str: str):
    hex_str = hex_str.strip().lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return [r, g, b, 1.0]


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

    def go_next(self, dt):
        self.manager.current = "create_account"


class CreateAccountScreen(Screen):
    pass


class SignInScreen(Screen):
    pass


class DesiredHomeScreen(Screen):
    pass

    
class NavigationScreen(Screen):
    def on_enter(self, *args):
        self.ids.compass_label.text = "Navigation Ready"
        self.ids.location_label.text = "Tap Start Navigation"

    def start_navigation(self):
        self.ids.compass_label.text = "Compass Starting..."
        self.ids.location_label.text = "Getting GPS location..."

        try:
            gps.configure(
                on_location=self.on_location,
                on_status=self.on_status
            )

            gps.start(minTime=1000, minDistance=1)

            try:
                compass.enable()
            except Exception:
                pass

            self.update_compass()
            toast("Navigation Started")

        except Exception as e:
            self.ids.location_label.text = "GPS/Compass works on real mobile device"
            print("Navigation error:", e)
            toast("GPS only works on mobile device")

    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")

        self.ids.location_label.text = f"Latitude: {lat}\nLongitude: {lon}"

    def on_status(self, stype, status):
        print("GPS Status:", stype, status)

    def update_compass(self):
        try:
            direction = compass.orientation
            self.ids.compass_label.text = f"Compass: {direction}"
        except Exception:
            self.ids.compass_label.text = "Compass not available on this device"

        Clock.schedule_once(lambda dt: self.update_compass(), 1)

class ChatScreen(Screen):
    def on_enter(self, *args):
        self.load_contacts()

    def load_contacts(self):
        self.ids.contact_list.clear_widgets()

        try:
            user_id = self.manager.app.current_user.id
        except Exception:
            self.ids.contact_list.add_widget(
                OneLineListItem(text="Please sign in first")
            )
            return

        try:
            contacts = (
                supabase.table("chat_contacts")
                .select("*")
                .eq("user_id", user_id)
                .execute()
                .data
            )

            for contact in contacts:
                self.ids.contact_list.add_widget(
                    OneLineListItem(
                        text=contact.get("contact_name", "Unknown"),
                        on_release=lambda x, c=contact: self.open_chat(c)
                    )
                )

        except Exception as e:
            self.ids.contact_list.add_widget(
                OneLineListItem(text=f"Error loading contacts: {e}")
            )

    def add_contact(self):
        toast("Add contact coming next")

    def delete_contact(self):
        toast("Delete contact coming next")

    def open_chat(self, contact):
        toast(f"Opening chat with {contact.get('contact_name')}")


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
    Displays the signed-in user's tasks as iPhone-style notes.
    Data is loaded from the existing Supabase 'tasks' table.
    """

    def on_enter(self, *args):
        # Allow the task screen to render before contacting Supabase.
        Clock.schedule_once(self.start_loading_notes, 0.2)

    def start_loading_notes(self, _dt):
        self.load_notes()

    def create_note(self):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        editor = self.manager.get_screen("note_editor")
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

        try:
            notes = (
                supabase.table("tasks")
                .select("*")
                .eq("user_id", app.current_user.id)
                .order("created_at", desc=True)
                .execute()
                .data
            ) or []

        except Exception as error:
            print("Error loading tasks:", error)
            toast("Unable to load notes")
            notes = []

        query = search_text.strip().lower()

        if query:
            notes = [
                note
                for note in notes
                if query in (note.get("title") or "").lower()
                or query in (note.get("description") or "").lower()
            ]

        self.display_notes(notes)

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
                    height=dp(100)
                )
            )
            return

        for note in notes:
            note_id = note.get("id", "")
            title = (note.get("title") or "").strip() or "New Note"

            body = (
                note.get("description") or ""
            ).strip().replace("\n", " ")

            if len(body) > 65:
                body = body[:65] + "..."

            date_text = self.format_note_date(
                note.get("created_at", "")
            )

            card = MDCard(
                orientation="vertical",
                size_hint_y=None,
                height=dp(92),
                padding=[dp(15), dp(8), dp(15), dp(6)],
                spacing=dp(1),
                radius=[dp(12), dp(12), dp(12), dp(12)],
                elevation=1,
                ripple_behavior=True,
                md_bg_color=(1, 1, 1, 1)
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
                text_color=(0, 0, 0, 1)
            )

            preview_text = date_text

            if body:
                preview_text += f"   {body}"

            preview_label = MDLabel(
                text=preview_text,
                font_size="13sp",
                size_hint_y=None,
                height=dp(34),
                shorten=True,
                shorten_from="right",
                theme_text_color="Hint"
            )

            card.add_widget(title_label)
            card.add_widget(preview_label)

            card.bind(
                on_release=partial(self.open_note, note_id)
            )

            notes_list.add_widget(card)

    def open_note(self, note_id, *_args):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        editor = self.manager.get_screen("note_editor")
        editor.open_existing_note(note_id)
        self.manager.current = "note_editor"

    @staticmethod
    def format_note_date(date_string):
        if not date_string:
            return ""

        try:
            cleaned_date = date_string.replace("Z", "+00:00")
            note_date = datetime.fromisoformat(cleaned_date)

            current_date = (
                datetime.now(note_date.tzinfo)
                if note_date.tzinfo
                else datetime.now()
            )

            if note_date.date() == current_date.date():
                return note_date.strftime("%H:%M")

            return note_date.strftime("%d/%m/%Y")

        except (ValueError, TypeError):
            return ""
        
class NoteEditorScreen(Screen):
    """
    Creates, edits, automatically saves and deletes records
    in the existing Supabase 'tasks' table.
    """

    current_note_id = StringProperty("")
    created_at = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.loading_note = False
        self.save_event = None
        self.note_exists = False

    def open_new_note(self):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        self.loading_note = True

        now = datetime.now().isoformat()

        self.current_note_id = str(uuid.uuid4())
        self.created_at = now
        self.note_exists = False

        self.ids.note_title.text = ""
        self.ids.note_body.text = ""
        self.ids.note_date.text = self.display_date(now)

        self.loading_note = False

    def open_existing_note(self, note_id):
        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        try:
            selected_note = (
                supabase.table("tasks")
                .select("*")
                .eq("id", note_id)
                .eq("user_id", app.current_user.id)
                .single()
                .execute()
                .data
            )

        except Exception as error:
            print("Error opening task:", error)
            toast("Unable to open note")
            return

        if not selected_note:
            toast("Note not found")
            return

        self.loading_note = True

        self.current_note_id = selected_note.get("id", "")
        self.created_at = selected_note.get(
            "created_at",
            datetime.now().isoformat()
        )

        self.note_exists = True

        self.ids.note_title.text = selected_note.get("title") or ""
        self.ids.note_body.text = selected_note.get("description") or ""

        self.ids.note_date.text = self.display_date(
            self.created_at
        )

        self.loading_note = False

    def note_changed(self):
        if self.loading_note or not self.current_note_id:
            return

        if self.save_event:
            self.save_event.cancel()

        self.save_event = Clock.schedule_once(
            self.auto_save_note,
            0.5
        )

    def auto_save_note(self, _dt):
        self.save_event = None
        self.save_note()

    def save_note(self):
        if self.loading_note or not self.current_note_id:
            return

        app = MDApp.get_running_app()

        if not app.current_user:
            toast("Please sign in first")
            return

        title = self.ids.note_title.text.strip()
        description = self.ids.note_body.text

        if not title and not description.strip():
            return

        note_data = {
            "id": self.current_note_id,
            "user_id": app.current_user.id,
            "title": title,
            "description": description,
            "created_at": self.created_at,
            "priority": "normal",
            "status": "active"
        }

        try:
            (
                supabase.table("tasks")
                .upsert(note_data, on_conflict="id")
                .execute()
            )

            self.note_exists = True

            self.ids.note_date.text = self.display_date(
                self.created_at
            )

        except Exception as error:
            print("Error saving task:", error)
            toast("Unable to save note")

    def close_editor(self):
        if self.save_event:
            self.save_event.cancel()
            self.save_event = None

        self.save_note()

        task_screen = self.manager.get_screen("tasks")
        task_screen.load_notes()

        self.manager.current = "tasks"

    def confirm_delete(self):
        if not self.note_exists:
            self.close_editor()
            return

        dialog = MDDialog(
            title="Delete Note?",
            text="This note will be permanently deleted."
        )

        cancel_button = MDFlatButton(
            text="CANCEL",
            on_release=lambda button: dialog.dismiss()
        )

        delete_button = MDFlatButton(
            text="DELETE",
            theme_text_color="Custom",
            text_color=(0.9, 0.1, 0.1, 1),
            on_release=lambda button: self.delete_note(dialog)
        )

        dialog.buttons = [
            cancel_button,
            delete_button
        ]

        dialog.open()

    def delete_note(self, dialog):
        app = MDApp.get_running_app()

        if not app.current_user:
            dialog.dismiss()
            toast("Please sign in first")
            return

        try:
            (
                supabase.table("tasks")
                .delete()
                .eq("id", self.current_note_id)
                .eq("user_id", app.current_user.id)
                .execute()
            )

        except Exception as error:
            print("Error deleting task:", error)
            dialog.dismiss()
            toast("Unable to delete note")
            return

        dialog.dismiss()

        self.note_exists = False
        self.current_note_id = ""
        self.created_at = ""

        self.loading_note = True

        self.ids.note_title.text = ""
        self.ids.note_body.text = ""
        self.ids.note_date.text = ""

        self.loading_note = False

        task_screen = self.manager.get_screen("tasks")
        task_screen.load_notes()

        self.manager.current = "tasks"

    @staticmethod
    def display_date(date_string):
        if not date_string:
            return ""

        try:
            cleaned_date = date_string.replace("Z", "+00:00")
            date_value = datetime.fromisoformat(cleaned_date)

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

        Window.set_title(" ")
        if os.path.exists(ICON_PATH):
            Window.set_icon(ICON_PATH)

        Builder.load_file(os.path.join(BASE_DIR, "kv", "components.kv"))
        Builder.load_file(os.path.join(BASE_DIR, "kv", "pages.kv"))
        Builder.load_file(os.path.join(BASE_DIR, "kv", "splash.kv"))
        Builder.load_file(os.path.join(BASE_DIR, "kv", "create_account.kv"))
        Builder.load_file(os.path.join(BASE_DIR, "kv", "signin.kv"))
        root = Builder.load_file(os.path.join(BASE_DIR, "kv", "main.kv"))

        self.current_user = None
        self.current_profile = None

        self.all_countries = sorted([country.name for country in pycountry.countries])
        self.country_dialog = None
        self.country_search_field = None
        self.country_list_box = None

        create_screen = root.get_screen("create_account")
        if "country_item" in create_screen.ids:
            try:
                create_screen.ids.country_item.set_item("United Kingdom")
            except Exception:
                create_screen.ids.country_item.text = "United Kingdom"

        return root

    def _toast(self, message: str):
        Clock.schedule_once(lambda dt: toast(message), 0)

    def _go(self, screen_name: str):
        Clock.schedule_once(lambda dt: self.go_to(screen_name), 0)

    def _set_signing_up(self, value: bool):
        Clock.schedule_once(lambda dt: setattr(self, "is_signing_up", value), 0)

    def _set_signing_in(self, value: bool):
        Clock.schedule_once(lambda dt: setattr(self, "is_signing_in", value), 0)

    def set_signup_status(self, text: str):
        def _set(_dt):
            try:
                self.root.get_screen("create_account").ids.signup_status.text = text
            except Exception:
                pass

        Clock.schedule_once(_set, 0)

    def set_signin_status(self, text: str):
        def _set(_dt):
            try:
                self.root.get_screen("signin").ids.signin_status.text = text
            except Exception:
                pass

        Clock.schedule_once(_set, 0)

    def go_to(self, screen_name: str):
        self.root.current = screen_name

    def back_to_home(self):
        self.root.current = "home"

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
            self.country_search_field.bind(text=self.filter_countries)

            self.country_list_box = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                spacing=0,
            )
            self.country_list_box.bind(
                minimum_height=self.country_list_box.setter("height")
            )

            scroll = ScrollView(size_hint=(1, 1))
            scroll.add_widget(self.country_list_box)

            content.add_widget(self.country_search_field)
            content.add_widget(scroll)

            self.country_dialog = MDDialog(
                title="Select Country",
                type="custom",
                content_cls=content,
            )

        self.country_search_field.text = ""
        self.populate_country_list(self.all_countries)
        self.country_dialog.open()

    def populate_country_list(self, countries):
        self.country_list_box.clear_widgets()

        if not countries:
            self.country_list_box.add_widget(OneLineListItem(text="No country found"))
            return

        for country in countries:
            item = OneLineListItem(
                text=country,
                on_release=lambda x, c=country: self.select_country_from_search(c),
            )
            self.country_list_box.add_widget(item)

    def filter_countries(self, instance, value):
        query = value.strip().lower()

        if not query:
            filtered = self.all_countries
        else:
            filtered = [
                country
                for country in self.all_countries
                if query in country.lower()
            ]

        self.populate_country_list(filtered)

    def select_country_from_search(self, country_name):
        self.root.get_screen("create_account").ids.country_item.set_item(country_name)
        if self.country_dialog:
            self.country_dialog.dismiss()

    def set_country(self, country_name):
        self.root.get_screen("create_account").ids.country_item.set_item(country_name)

    def signup_action(self):
        if self.is_signing_up:
            toast("Please wait...")
            return

        screen = self.root.get_screen("create_account")
        first = screen.ids.first_name.text.strip()
        last = screen.ids.last_name.text.strip()
        email = screen.ids.email.text.strip().lower()
        pwd = screen.ids.password.text
        cpwd = screen.ids.confirm_password.text
        terms = screen.ids.terms_check.active

        try:
            country = screen.ids.country_item.text.strip()
        except Exception:
            country = ""

        if not all([first, last, email, pwd, cpwd]):
            toast("Fill all fields")
            return

        if pwd != cpwd:
            toast("Passwords do not match")
            return

        if not terms:
            toast("Accept terms")
            return

        self.is_signing_up = True
        self.set_signup_status("Creating account...")

        def worker():
            try:
                auth_resp = supabase.auth.sign_up({"email": email, "password": pwd})
                user = auth_resp.user

                if not user:
                    self._toast("Sign up failed")
                    self.set_signup_status("Sign up failed.")
                    return

                supabase.table("profiles").insert(
                    {
                        "id": user.id,
                        "first_name": first,
                        "last_name": last,
                        "country": country,
                    }
                ).execute()

                self._toast("Account created. Please sign in.")
                self.set_signup_status("Account created. Please sign in.")
                self._go("signin")

            except Exception as e:
                msg = str(e).lower()

                if (
                    "over_email_send_rate_limit" in msg
                    or "too many requests" in msg
                    or " 429" in msg
                ):
                    self._toast("Too many signups. Try again in a few minutes.")
                    self.set_signup_status(
                        "Too many signups. Try again in a few minutes."
                    )
                elif "email_not_confirmed" in msg:
                    self._toast("Please confirm your email first.")
                    self.set_signup_status(
                        "Check your email and confirm your account."
                    )
                elif "already" in msg and ("registered" in msg or "exists" in msg):
                    self._toast("Email already exists. Please sign in.")
                    self.set_signup_status("Email already exists. Please sign in.")
                    self._go("signin")
                else:
                    self._toast(f"Signup error: {str(e)}")
                    self.set_signup_status(f"Signup error: {str(e)}")

            finally:
                self._set_signing_up(False)
                Clock.schedule_once(lambda dt: self.set_signup_status(" "), 2)

        threading.Thread(target=worker, daemon=True).start()

    def signin_action(self):
        if self.is_signing_in:
            toast("Please wait...")
            return

        screen = self.root.get_screen("signin")
        email = screen.ids.signin_email.text.strip().lower()
        pwd = screen.ids.signin_password.text

        if not email or not pwd:
            toast("Enter email & password")
            return

        self.is_signing_in = True
        self.set_signin_status("Signing in...")

        


        def worker():
            try:
                auth_resp = supabase.auth.sign_in_with_password(
                    {"email": email, "password": pwd}
                )
                user = auth_resp.user

                if not user:
                    self._toast("Login failed")
                    self.set_signin_status("Login failed.")
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
                except Exception:
                    profile = None

                self.current_profile = profile or {}
                first_name = (self.current_profile.get("first_name") or "").strip()

                self._toast(f"Welcome {first_name}" if first_name else "Welcome")
                self.set_signin_status(" ")
                self._go("home")

            except Exception as e:
                msg = str(e).lower()

                if "email_not_confirmed" in msg:
                    self._toast("Email not confirmed. Please check your inbox.")
                    self.set_signin_status("Email not confirmed. Check your inbox.")
                elif "invalid" in msg or "credentials" in msg or "401" in msg:
                    self._toast("Incorrect email or password")
                    self.set_signin_status("Incorrect email or password")
                else:
                    self._toast(f"Signin error: {str(e)}")
                    self.set_signin_status(f"Signin error: {str(e)}")
                    

            finally:
                self._set_signing_in(False)
                Clock.schedule_once(lambda dt: self.set_signin_status(" "), 2)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    MistApp().run()