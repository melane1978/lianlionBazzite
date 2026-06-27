#!/usr/bin/env python3
import sys
import os
# Disable GPU acceleration and force X11 (xcb) platform for absolute positioning under Wayland
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon, QStyle
from PyQt6.QtWebEngineWidgets import QWebEngineView

class CustomWebView(QWebEngineView):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window

    def contextMenuEvent(self, event):
        # Intercept right-click and delegate to parent window menu
        self.parent_window.show_custom_menu(event.globalPos())

    def keyPressEvent(self, event):
        # Intercept key presses before Chromium consumes them
        if event.key() == Qt.Key.Key_Escape:
            self.parent_window.showMinimized()
            print("[INFO] Application minimized via Esc key.")
        elif event.key() == Qt.Key.Key_F5:
            self.reload()
            print("[INFO] Reloaded dashboard.")
        else:
            super().keyPressEvent(event)

class SensorPanelApp(QMainWindow):
    def __init__(self, target_geometry=None):
        super().__init__()
        
        # Set window flags: frameless and stay on top (remove Tool flag so it has a taskbar entry)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Enable translucent background for premium look
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set and store geometry to cover target screen (Lian Li display)
        self.target_geometry = target_geometry
        if self.target_geometry:
            self.setGeometry(self.target_geometry)
            print(f"[INFO] Positioned on target screen: {self.target_geometry.x()}, {self.target_geometry.y()} ({self.target_geometry.width()}x{self.target_geometry.height()})")
        else:
            # Fallback size and start screen detection timer
            from PyQt6.QtCore import QRect, QTimer
            self.target_geometry = QRect(0, 0, 480, 1920)
            self.setGeometry(self.target_geometry)
            print("[WARNING] Lian Li screen not detected at startup. Starting screen polling timer...")
            self.screen_timer = QTimer(self)
            self.screen_timer.timeout.connect(self.poll_screens)
            self.screen_timer.start(2000) # Poll every 2 seconds
            
        # Create web view using custom subclass to capture mouse/keyboard events
        self.browser = CustomWebView(self)
        
        # Disable scrollbars for a clean look
        self.browser.settings().setAttribute(self.browser.settings().WebAttribute.ShowScrollBars, False)
        
        # Connect to local Flask server
        self.browser.setUrl(QUrl("http://localhost:5000"))
        
        self.setCentralWidget(self.browser)

        # Setup system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Use a system computer monitor icon
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Lian Li Sensor Panel")
        
        # Create tray context menu
        tray_menu = QMenu()
        
        show_action = QAction("Visa", self)
        show_action.triggered.connect(self.restore_window)
        tray_menu.addAction(show_action)
        
        minimize_action = QAction("Minimera", self)
        minimize_action.triggered.connect(self.showMinimized)
        tray_menu.addAction(minimize_action)
        
        tray_menu.addSeparator()
        
        close_action = QAction("Stäng", self)
        close_action.triggered.connect(self.close)
        tray_menu.addAction(close_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def poll_screens(self):
        print("[INFO] Polling for Lian Li screen...")
        for i, screen in enumerate(QApplication.screens()):
            geom = screen.geometry()
            ratio = geom.width() / geom.height() if geom.height() > 0 else 0
            # Check aspect ratio for 480x1920 (0.25) or 1920x480 (4.0)
            if abs(ratio - 0.25) < 0.05 or abs(ratio - 4.0) < 0.1:
                self.target_geometry = geom
                self.setGeometry(self.target_geometry)
                self.screen_timer.stop()
                print(f"[INFO] Detected target Lian Li display dynamically on Screen #{i}! Repositioned to: {self.target_geometry.x()}, {self.target_geometry.y()}")
                self.browser.reload()
                break

    def restore_window(self):
        self.showNormal()
        if self.target_geometry:
            self.setGeometry(self.target_geometry)
        self.activateWindow()
        self.raise_()

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            if not self.isMinimized() and hasattr(self, 'target_geometry') and self.target_geometry:
                self.setGeometry(self.target_geometry)
        super().changeEvent(event)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isMinimized() or not self.isVisible():
                self.restore_window()
            else:
                self.showMinimized()

    def show_custom_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0a0e17;
                color: #ffffff;
                border: 1px solid #ff9f00;
                font-family: 'Rajdhani', sans-serif;
                font-size: 14px;
            }
            QMenu::item {
                padding: 8px 24px;
            }
            QMenu::item:selected {
                background-color: #ff9f00;
                color: #04060a;
            }
        """)
        
        minimize_action = QAction("Minimera (Esc)", self)
        minimize_action.triggered.connect(self.showMinimized)
        menu.addAction(minimize_action)
        
        reload_action = QAction("Ladda om (F5)", self)
        reload_action.triggered.connect(self.browser.reload)
        menu.addAction(reload_action)
        
        close_action = QAction("Stäng", self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        
        menu.exec(pos)

def main():
    app = QApplication(sys.argv)
    
    # Attempt to locate Lian Li display based on typical aspect ratios (1:4 or 4:1)
    target_screen = None
    target_geometry = None
    
    print("[INFO] Scanning connected screens:")
    for i, screen in enumerate(app.screens()):
        geom = screen.geometry()
        ratio = geom.width() / geom.height() if geom.height() > 0 else 0
        print(f"  Screen #{i}: '{screen.name()}' {geom.width()}x{geom.height()} at ({geom.x()},{geom.y()}) - Aspect Ratio: {ratio:.2f}")
        
        # Check aspect ratio for 480x1920 (0.25) or 1920x480 (4.0)
        if abs(ratio - 0.25) < 0.05 or abs(ratio - 4.0) < 0.1:
            target_screen = screen
            target_geometry = geom
            print(f"    => Detected target Lian Li display on Screen #{i}!")
            
    # Force layout orientation or geometry via argument if needed
    if len(sys.argv) > 1:
        try:
            # Format: gui_app.py x,y,width,height
            parts = [int(x) for x in sys.argv[1].split(',')]
            if len(parts) == 4:
                from PyQt6.QtCore import QRect
                target_geometry = QRect(parts[0], parts[1], parts[2], parts[3])
                print(f"[INFO] Using manual geometry from argument: {target_geometry}")
        except Exception as e:
            print(f"[ERROR] Failed to parse custom geometry: {e}")

    window = SensorPanelApp(target_geometry)
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
