from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty

KV = """
#:kivy 2.2.0

<HomeScreen>:
    canvas.before:
        Color:
            rgba: 1,1,1,1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: "vertical"
        padding: dp(18), dp(12)
        spacing: dp(14)

        # Top row
        BoxLayout:
            size_hint_y: None
            height: dp(44)
            orientation: "horizontal"

            BoxLayout:
                size_hint_x: 0.7
                orientation: "horizontal"
                spacing: dp(10)
                padding: 0, dp(8), 0, 0

                IconLabel:
                    text: "🔒"
                    font_size: "18sp"

                BoxLayout:
                    size_hint_x: None
                    width: self.minimum_width
                    spacing: dp(6)
                    IconLabel:
                        text: "Jason63"
                        font_size: "15sp"
                        bold: True
                    IconLabel:
                        text: "▾"
                        font_size: "16sp"

            BoxLayout:
                size_hint_x: 0.3
                orientation: "horizontal"
                spacing: dp(10)
                padding: 0, dp(6), 0, 0
                Widget:

                IconButton:
                    text: "+"
                    on_release: app.on_tile("Add")

                IconButton:
                    text: "≡"
                    on_release: app.on_tile("Menu")

        # Profile row
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(12)
            padding: 0, dp(2), 0, 0

            Avatar:
                size_hint: None, None
                size: dp(44), dp(44)

            BoxLayout:
                orientation: "vertical"
                spacing: dp(2)
                padding: 0, dp(6), 0, 0

                Label:
                    text: "MIST"
                    color: 0.07, 0.07, 0.07, 1
                    font_size: "16sp"
                    bold: True
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

                Label:
                    text: "IT Entrepreneur"
                    color: 0.30, 0.30, 0.30, 1
                    font_size: "13sp"
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

        # Grid tiles (2 columns)
        GridLayout:
            cols: 2
            spacing: dp(14)
            row_default_height: dp(140)
            row_force_default: True

            TileCard:
                title: "Navigation"
                icon_text: "➤"
                bg_hex: "B79BFF"
                on_release: app.on_tile("Navigation")

            TileCard:
                title: "Chat"
                icon_text: "💬"
                bg_hex: "FF9C9C"
                on_release: app.on_tile("Chat")

            TileCard:
                title: "Reminder"
                icon_text: "🗓"
                bg_hex: "F5D24B"
                on_release: app.on_tile("Reminder")

            TileCard:
                title: "Device Pairing"
                icon_text: "⟐"
                bg_hex: "7EC9FF"
                on_release: app.on_tile("Device Pairing")

            TileCard:
                title: "Connect to\\norganization"
                icon_text: "⛓"
                bg_hex: "65E0A0"
                on_release: app.on_tile("Connect to organization")

            TileCard:
                title: "Settings"
                icon_text: "⚙"
                bg_hex: "56E1D6"
                on_release: app.on_tile("Settings")


<IconButton@Button>:
    size_hint: None, None
    size: dp(34), dp(34)
    background_normal: ""
    background_color: 1,1,1,0
    color: 0.07,0.07,0.07,1
    font_size: "20sp"
    bold: True


<IconLabel@Label>:
    color: 0.07,0.07,0.07,1
    halign: "left"
    valign: "middle"
    text_size: self.size


<Avatar@FloatLayout>:
    canvas.before:
        # Circle avatar background
        Color:
            rgba: 0.88, 0.88, 0.88, 1
        Ellipse:
            pos: self.pos
            size: self.size

    # blue status dot
    Widget:
        size_hint: None, None
        size: dp(10), dp(10)
        pos: root.x + root.width - dp(12), root.y + dp(2)
        canvas:
            Color:
                rgba: 0.17, 0.49, 1, 1
            Ellipse:
                pos: self.pos
                size: self.size


<TileCard>:
    canvas.before:
        Color:
            rgba: self.bg_rgba
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(18), dp(18), dp(18), dp(18)]
        # soft shadow-ish border
        Color:
            rgba: 0,0,0,0.06
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(18))
            width: 1.2

    BoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(10)

        # Icon badge
        FloatLayout:
            size_hint_y: None
            height: dp(50)

            Widget:
                size_hint: None, None
                size: dp(44), dp(44)
                pos: root.x + dp(16), root.top - dp(16) - dp(44)
                canvas.before:
                    Color:
                        rgba: 1,1,1,0.25
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(14), dp(14), dp(14), dp(14)]

            Label:
                text: root.icon_text
                font_size: "24sp"
                color: 0.07,0.07,0.07,1
                size_hint: None, None
                size: dp(44), dp(44)
                pos: root.x + dp(16), root.top - dp(16) - dp(44)
                halign: "center"
                valign: "middle"
                text_size: self.size

        # Title
        Label:
            text: root.title
            color: 0.07,0.07,0.07,1
            font_size: "15sp"
            bold: True
            halign: "left"
            valign: "bottom"
            text_size: self.size
"""

def hex_to_rgba(hex_str: str):
    hex_str = hex_str.strip().lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return [r, g, b, 1.0]


class TileCard(ButtonBehavior, BoxLayout):
    title = StringProperty("Title")
    icon_text = StringProperty("★")
    bg_hex = StringProperty("DDDDDD")

    @property
    def bg_rgba(self):
        return hex_to_rgba(self.bg_hex)


class HomeScreen(BoxLayout):
    pass


class DemoApp(App):
    def build(self):
        Builder.load_string(KV)
        return HomeScreen()

    def on_tile(self, name: str):
        print(f"Pressed: {name}")


if __name__ == "__main__":
    DemoApp().run()
