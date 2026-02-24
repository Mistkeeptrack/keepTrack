from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast

from pymongo import MongoClient
import hashlib

Window.size = (360, 640)


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


# ---------- App ----------
class MistApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"

        # Load KV files
        Builder.load_file("kv/components.kv")
        Builder.load_file("kv/pages.kv")
        Builder.load_file("kv/splash.kv")
        Builder.load_file("kv/create_account.kv")
        Builder.load_file("kv/signin.kv")
        Builder.load_file("kv/home.kv")
        root = Builder.load_file("kv/main.kv")

        # --- MongoDB setup ---
        mongo_uri = "YOUR_MONGODB_ATLAS_CONNECTION_STRING"

        self.users = None
        try:
            if "YOUR_MONGODB" not in mongo_uri:
                self.client = MongoClient(mongo_uri)
                self.db = self.client["mist_app"]
                self.users = self.db["users"]
            else:
                self.users = None
        except Exception:
            self.users = None

        # --- Country dropdown menu ---
        create_screen = root.get_screen("create_account")
        menu_items = [
            {"text": "USA", "on_release": lambda x="USA": self.set_country(x)},
            {"text": "Nigeria", "on_release": lambda x="Nigeria": self.set_country(x)},
            {"text": "UK", "on_release": lambda x="UK": self.set_country(x)},
            {"text": "Canada", "on_release": lambda x="Canada": self.set_country(x)},
        ]
        self.country_menu = MDDropdownMenu(
            caller=create_screen.ids.country_item,
            items=menu_items,
            width_mult=4,
        )

        return root

    # ---------- Navigation ----------
    def go_to(self, screen_name: str):
        self.root.current = screen_name

    def back_to_home(self):
        self.root.current = "home"

    def open_country_menu(self):
        self.country_menu.open()

    def set_country(self, country_name):
        self.root.get_screen("create_account").ids.country_item.set_item(country_name)
        self.country_menu.dismiss()

    # ---------- Auth ----------
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def signup_action(self):
        screen = self.root.get_screen("create_account")
        first = screen.ids.first_name.text.strip()
        last = screen.ids.last_name.text.strip()
        email = screen.ids.email.text.strip().lower()
        pwd = screen.ids.password.text
        cpwd = screen.ids.confirm_password.text
        terms = screen.ids.terms_check.active

        if not all([first, last, email, pwd, cpwd]):
            toast("Fill all fields")
            return

        if pwd != cpwd:
            toast("Passwords do not match")
            return

        if not terms:
            toast("Accept terms")
            return

        if not self.users:
            toast("DB not connected (add your MongoDB URI)")
            return

        if self.users.find_one({"email": email}):
            toast("Email already exists")
            return

        hashed = self.hash_password(pwd)
        self.users.insert_one({
            "first_name": first,
            "last_name": last,
            "email": email,
            "password": hashed
        })

        toast("Account created")
        self.root.current = "signin"

    def signin_action(self):
        screen = self.root.get_screen("signin")
        email = screen.ids.signin_email.text.strip().lower()
        pwd = screen.ids.signin_password.text

        if not email or not pwd:
            toast("Enter email & password")
            return

        if not self.users:
            toast("DB not connected (add your MongoDB URI)")
            return

        user = self.users.find_one({"email": email})
        if not user:
            toast("User not found")
            return

        if self.hash_password(pwd) != user["password"]:
            toast("Incorrect password")
            return

        toast(f"Welcome {user['first_name']}")
        self.root.current = "home"


if __name__ == "__main__":
    MistApp().run()
