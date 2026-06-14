import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
import sys
from threading import Thread
import json

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawerMenu
from kivymd.uix.menu import MDDropdownMenu
#from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDFloatingActionButton

from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.lang import Builder
from kivy.uix.image import Image
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty

from plyer import filechooser

# local imports
from services.faceAi import FaceAiSvc

# IMPORTANT: Set this property for keyboard behavior
Window.softinput_mode = "below_target"

## Global definitions
__version__ = "0.0.1" # App version

# Determine the base path for your application's resources
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running in a normal Python environment
    base_path = os.path.dirname(os.path.abspath(__file__))
kv_file_path = os.path.join(base_path, 'main_layout.kv')

# imprt platform specific modules
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method

## -- kivy custom classes -- ##
## define custom kivymd classes
class ContentNavigationDrawer(MDNavigationDrawerMenu):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()

class MainScreenBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar
                self.top_pad = int(get_height_of_bar('status'))
                self.bottom_pad = int(get_height_of_bar('navigation'))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48

### --- main app --- ###
class FaceAiApp(MDApp):


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self.events)
        self.face_ai = None
        self.txt_dialog = None

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Orange"
        return Builder.load_file(kv_file_path)

    def on_start(self):
        # paths setup
        if platform == "android":
            from android.permissions import request_permissions, Permission
            from android.storage import app_storage_path
            sdk_version = 28
            try:
                VERSION = autoclass('android.os.Build$VERSION')
                sdk_version = VERSION.SDK_INT
                print(f"Android SDK: {sdk_version}")
                #self.show_toast_msg(f"Android SDK: {sdk_version}")
            except Exception as e:
                print(f"Could not check the android SDK version: {e}")
                #self.show_toast_msg(f"Error checking SDK: {e}", is_error=True)
            self.permissions = [Permission.CAMERA]
            if sdk_version >= 33:  # Android 13+
                self.permissions.append(Permission.READ_MEDIA_IMAGES)
            else:  # Android 9–12
                self.permissions.extend([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            request_permissions(self.permissions)
            self.internal_storage = app_storage_path()
            try:
                Environment = autoclass("android.os.Environment")
                self.external_storage = Environment.getExternalStorageDirectory().getAbsolutePath()
            except Exception:
                self.external_storage = os.path.abspath("/storage/emulated/0/")
        # non android platforms
        else:
            self.internal_storage = self.user_data_dir
            self.external_storage = os.path.expanduser("~")
        # remaining start activities
        self.model_dir = os.path.join(self.internal_storage, 'model_files')
        self.op_dir = os.path.join(self.internal_storage, 'outputs')
        self.last_upload_path = None
        self.image_path = ""
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.op_dir, exist_ok=True)
        print(f"Internal model files to be stored in: {self.model_dir}")
        self.detect_model_path = os.path.join(self.model_dir, "det_10g.onnx")
        self.recog_model_path = os.path.join(self.model_dir, "arc.onnx")
        self.is_inp_file_mgr_open = False
        self.is_out_file_mgr_open = False

    def show_toast_msg(self, message, is_error=False, duration=3):
        from kivymd.uix.snackbar import MDSnackbar
        bg_color = (0.2, 0.6, 0.2, 1) if not is_error else (0.8, 0.2, 0.2, 1)
        MDSnackbar(
            MDLabel(
                text = message,
                font_style = "Subtitle1"
            ),
            md_bg_color=bg_color,
            y=dp(24),
            pos_hint={"center_x": 0.5},
            duration=duration
        ).open()

    def show_text_dialog(self, title, text="", buttons=[]):
        self.txt_dialog = MDDialog(
            title=title,
            text=text,
            buttons=buttons
        )
        self.txt_dialog.open()

    def txt_dialog_closer(self, instance):
        if self.txt_dialog:
            self.txt_dialog.dismiss()

    def start_face_services(self, instance=None):
        self.face_ai = FaceAiSvc(self.detect_model_path, self.recog_model_path, self.op_dir)
        try:
            self.face_ai.start_detection_session()
            self.face_ai.start_recognition_session()
            self.show_toast_msg("Sesstions started successfully")
        except Exception as e:
            print(f"Could not start the sessions: {e}")
            self.face_ai = None

    def goto_face_matcher(self, instance=None):
        self.root.ids.screen_manager.current = "faceFindScr"

    def open_img_file_manager(self, instance=None):
        if not self.face_ai:
            self.show_toast_msg("Please start the session first!", is_error=True)
            return
        try:
            #self.img_file_manager.show(self.external_storage)  # native app specific path
            if not self.last_upload_path:
                self.last_upload_path = self.external_storage
            filechooser.open_file(
                on_selection = self.handle_img_selection,
                path = self.last_upload_path,
                multiple = False,
                filters = [["*.JPG", "*.jpg", "*.png", "*.jpeg", "*.webp"], "*"],
                preview = True,
            )
            self.is_img_manager_open = True
        except Exception as e:
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def handle_img_selection(self, selection=None):
        '''
        Callback function for handling the image selection.
        '''
        self.is_img_manager_open = False
        if selection:
            image_path = str(selection[0])
            self.last_upload_path = os.path.dirname(image_path)
            Clock.schedule_once(lambda dt: self.select_img_path(image_path))

    def select_img_path(self, path: str):
        if not path.endswith((".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG", ".webp", ".WEBP")):
            self.show_toast_msg(f"Selected file: `{path}` is not an image", is_error=True)
            self.image_path = ""
            return
        self.image_path = path


    def events(self, instance, keyboard, keycode, text, modifiers):
        """Handle mobile device button presses (e.g., Android back button)."""
        #if keyboard in (1001, 27):
        return False

## -- run the app -- ##
if __name__ == '__main__':
    FaceAiApp().run()
