from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.toast import toast

from supabase_client import supabase

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

class TaskScreen(Screen):
    def on_enter(self, *args):
        print("Task screen opened")

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

        # Keep auth/session info here (optional)
        self.current_user = None
        self.current_profile = None

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

    # ---------- Auth (Supabase) ----------
    def signup_action(self):
        screen = self.root.get_screen("create_account")
        first = screen.ids.first_name.text.strip()
        last = screen.ids.last_name.text.strip()
        email = screen.ids.email.text.strip().lower()
        pwd = screen.ids.password.text
        cpwd = screen.ids.confirm_password.text
        terms = screen.ids.terms_check.active

        # If your country_item is an MDTextField with set_item, it will store the text
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

        try:
            # 1) Create Auth user
            auth_resp = supabase.auth.sign_up({"email": email, "password": pwd})
            user = auth_resp.user

            if not user:
                toast("Sign up failed")
                return

            # 2) Insert profile row linked to auth.users(id)
            supabase.table("profiles").insert({
                "id": user.id,
                "first_name": first,
                "last_name": last,
                "country": country,
            }).execute()

            toast("Account created. Please sign in.")
            self.root.current = "signin"

        except Exception as e:
            msg = str(e)
            # A nicer message for common “already registered” case
            if "already" in msg.lower() and "registered" in msg.lower():
                toast("Email already exists")
            else:
                toast(f"Signup error: {msg}")

    def signin_action(self):
        screen = self.root.get_screen("signin")
        email = screen.ids.signin_email.text.strip().lower()
        pwd = screen.ids.signin_password.text

        if not email or not pwd:
            toast("Enter email & password")
            return

        try:
            auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
            user = auth_resp.user

            if not user:
                toast("Login failed")
                return

            self.current_user = user

            # Fetch profile (optional, but useful for welcome name)
            profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute().data
            self.current_profile = profile or {}

            first_name = (self.current_profile.get("first_name") or "").strip()
            toast(f"Welcome {first_name}" if first_name else "Welcome")

            self.root.current = "home"

        except Exception:
            toast("Incorrect email or password")


if __name__ == "__main__":
    MistApp().run()