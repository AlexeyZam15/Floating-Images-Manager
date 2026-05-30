<div align="center">
  
# 🖼️ Floating Images Manager

**Desktop application for creating floating image windows that stay on top of all other windows**

[![Русский](https://img.shields.io/badge/Язык-Русский-blue)](README.md)
[![English](https://img.shields.io/badge/Language-English-red)](README.en.md)

</div>

---

## 📦 Download the ready-to-use program

**For Windows users** — a ready-made EXE file is available, no Python installation required:

➡️ **[Download the latest version](https://github.com/AlexeyZam15/Floating-Images-Manager/releases/latest)**

1. Go to the **Releases** section on GitHub
2. Download the `FloatingImagesManager.exe` file
3. Run the file — no installation required

---

## 💝 Support the project

If you find this program useful, you can support its development:

➡️ **[Support the author](https://dalink.to/wolfgunt)**

Thank you for your support! ❤️

---

## Features

✨ **Floating windows** — images always on top of other applications  
🖱️ **Zoom and pan** — mouse wheel zoom, drag-to-pan when zoomed in  
📋 **Clipboard paste** — copy images from browsers or editors directly  
🎨 **Resize** — drag borders, preserve aspect ratio with Shift  
🌍 **Bilingual** — Russian and English interface  
⚙️ **Configurable zoom** — three zoom speeds, configurable min/max limits  

---

## 🎮 Usage

### Main Gallery Window

| Action | Hotkey |
|--------|--------|
| Open images | `Ctrl+O` |
| Paste from clipboard | `Ctrl+V` |
| Show all images | `Ctrl+A` |
| Close all floating windows | `Ctrl+W` |
| Hide/show all windows | `H` |
| Open settings | `F1` or `Ctrl+S` |
| Delete selected from list | `Del` |
| Exit program | `Ctrl+Q` |

### Floating Image Window

| Action | Control |
|--------|---------|
| Zoom (normal) | Mouse wheel |
| Zoom (slow) | `Ctrl` + Mouse wheel |
| Zoom (fast) | `Shift` + Mouse wheel |
| Reset zoom | Middle mouse button |
| Pan (when zoom > 100%) | Hold left mouse button and drag |
| Move window | Hold left button on title bar or on image (when zoom is 100%) |
| Resize window | Drag borders or corners |
| Resize while keeping aspect ratio | `Shift` + drag border |
| Resize with image centering | `Ctrl` + drag border |
| Context menu | Right mouse button |
| Close window | `Esc` or via context menu |

### Floating Window Context Menu

- **Zoom In** — zoom in with normal speed
- **Zoom Out** — zoom out with normal speed
- **Reset Window** — reset zoom and window size to original values
- **Keep Aspect Ratio** — toggle aspect ratio lock for zooming
- **Optimal Size** — set to preset optimal window size
- **Copy Path** — copy full image file path to clipboard
- **Close** — close the floating window

---

## 📂 Data storage structure

On first launch, the program creates the following structure in the `Documents/floating_images` folder:

```
Documents/floating_images/
├── config/
│   ├── settings.json         # Program settings (zoom speeds, limits, language, etc.)
│   └── gallery.json          # List of paths to added images
└── storage/                  # Storage for clipboard images
    └── clipboard_*.png       # Automatically saved images
```

**Important:**

- Regular images (opened via the "Open" button) remain in their original locations and are not copied to the `storage/`
  folder
- Images from the clipboard are automatically saved to `storage/` in PNG format
- When deleting images from the gallery, files from `storage/` are completely removed from disk
- When deleting regular images from the gallery, only the entry is removed — original files remain untouched

---

## 🔧 Program Settings

All settings are available in the settings window (open with `F1` or via menu):

### Zoom Speed

- **Slow zoom** — zoom factor when holding `Ctrl` (default: 1.03)
- **Normal zoom** — zoom factor for regular wheel scrolling (default: 1.08)
- **Fast zoom** — zoom factor when holding `Shift` (default: 1.25)

### Zoom Limits

- **Minimum zoom** — smallest possible scale (default: 0.3x)
- **Maximum zoom** — largest possible scale (default: 10x)

### Interface

- **Button hide delay** — time in milliseconds after which UI elements hide when mouse leaves (default: 800 ms)
- **Window border size** — drag area thickness for resizing in pixels (default: 8 pixels)

### Animation

- **Smooth zoom animation** — enable/disable smooth zooming
- **Animation duration** — animation time in milliseconds (default: 150 ms)

### Language

- **Russian** — Russian interface
- **English** — English interface (requires program restart)

### Reset Settings

The "Reset" button restores all settings to their default values.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is distributed under the MIT license. This means free use, modification, and distribution with attribution.

---

## 🙏 Acknowledgments

- [Pillow](https://python-pillow.org/) library for image processing
- Built-in `tkinter` module for GUI

---

<div align="center">

**⭐ Star this project if you find it useful!**

</div>