import os
import threading
import logging
import pycountry

from kivy.config import Config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set window icon before other Kivy imports
Config.set(
    "kivy",
    "window_icon",
    os.path.join(BASE_DIR, "assets", "images", "mistlogo.jpeg"),
)

from kivy.resources import resource_add_path
resource_add_path(BASE_DIR)

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
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField

from supabase_client import supabase

# Window settings
Window.size = (360, 640)
Window.title = " "
Window.set_icon(os.path.join(BASE_DIR, "assets", "images", "mistlogo.jpeg"))

# Reduce noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ---------- Helpers ----------
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


# ---------- Screens ----------
class SplashScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.go_next, 2)

    def go_next(self, dt):
        self.manager.current = "create_account"


class CreateAccountScreen(Screen):
    pass


class SignInScreen(Screen):
    pass


class HomeScreen(Screen):
    pass


class NavigationScreen(Screen):
    pass


class ChatScreen(Screen):
    pass


class ReminderScreen(Screen):
    pass


class PairingScreen(Screen):
    pass


class OrgScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass

class TaskScreen(Screen):
    pass


class TaskScreen(Screen):
    def on_enter(self, *args):
        print("Task screen opened")

class KeepTrackApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        return Builder.load_file("keeptrack.kv")

    def back_to_home(self):
        self.root.current = "home"
        #return Builder.load_file("keeptrack.kv")

# ---------- App ----------
class MistApp(MDApp):
    title = " "

    is_signing_up = BooleanProperty(False)
    is_signing_in = BooleanProperty(False)

    def build(self):
        self.theme_cls.theme_style = "Light"

        Window.set_title(" ")
        Window.set_icon(os.path.join(BASE_DIR, "assets", "images", "mistlogo.jpeg"))

        # Load KV files
        Builder.load_file("kv/components.kv")
        Builder.load_file("kv/pages.kv")
        Builder.load_file("kv/splash.kv")
        Builder.load_file("kv/create_account.kv")
        Builder.load_file("kv/signin.kv")
        #Builder.load_file("kv/home.kv")
        root = Builder.load_file("kv/main.kv")

        # Session info
        self.current_user = None
        self.current_profile = None

        # Country data
        self.all_countries = sorted([country.name for country in pycountry.countries])
        self.country_dialog = None
        self.country_search_field = None
        self.country_list_box = None

        create_screen = root.get_screen("create_account")
        create_screen.ids.country_item.text = "United Kingdom"

        return root

    # ---------- UI helpers ----------
    def _toast(self, message: str):
        Clock.schedule_once(lambda dt: toast(message), 0)

    def _go(self, screen_name: str):
        Clock.schedule_once(lambda dt: self.go_to(screen_name), 0)

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

    # ---------- Navigation ----------
    def go_to(self, screen_name: str):
        self.root.current = screen_name

    def back_to_home(self):
        self.root.current = "home"

    # ---------- Country Search ----------
    def open_country_menu(self):
        self.open_country_search()

    def open_country_search(self):
        if self.country_dialog is None:
            content = MDBoxLayout(
                orientation="vertical",
                spacing=dp(10),
                size_hint_y=None,
                height=dp(420),
                padding=[0, 0, 0, 0],
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
            self.country_list_box.add_widget(
                OneLineListItem(text="No country found")
            )
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
                country for country in self.all_countries
                if query in country.lower()
            ]

        self.populate_country_list(filtered)

    def select_country_from_search(self, country_name):
        self.root.get_screen("create_account").ids.country_item.set_item(country_name)
        if self.country_dialog:
            self.country_dialog.dismiss()

    def set_country(self, country_name):
        self.root.get_screen("create_account").ids.country_item.set_item(country_name)

    # ---------- Auth (Supabase) ----------
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

        country = ""
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

                if "over_email_send_rate_limit" in msg or "too many requests" in msg or " 429" in msg:
                    self._toast("Too many signups. Try again in a few minutes.")
                    self.set_signup_status("Too many signups. Try again in a few minutes.")
                elif "already" in msg and ("registered" in msg or "exists" in msg):
                    self._toast("Email already exists. Please sign in.")
                    self.set_signup_status("Email already exists. Please sign in.")
                    self._go("signin")
                else:
                    self._toast(f"Signup error: {str(e)}")
                    self.set_signup_status(f"Signup error: {str(e)}")

            finally:
                self.is_signing_up = False
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
                if "invalid" in msg or "credentials" in msg or "401" in msg:
                    self._toast("Incorrect email or password")
                    self.set_signin_status("Incorrect email or password")
                else:
                    self._toast(f"Signin error: {str(e)}")
                    self.set_signin_status(f"Signin error: {str(e)}")

            finally:
                self.is_signing_in = False
                Clock.schedule_once(lambda dt: self.set_signin_status(" "), 2)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    MistApp().run()