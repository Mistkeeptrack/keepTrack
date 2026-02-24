# Keep Track (Figma → Python)

This project now contains **two ways** to view your design:

- **Mobile-style native UI** (Kivy, closer to your Figma mobile design)
- **Web dashboard** (Flask, optional)

## 1. Common setup

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## 2. Run the mobile-style app (Kivy)

From the project folder:

```bash
python main.py
```

This opens a phone-sized window that uses the same dark colors and layout as your Figma Keep Track screen.

## 3. (Optional) Run the web version (Flask)

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

