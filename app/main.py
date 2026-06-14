import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
import sys
from threading import Thread
import json
import requests

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
from screens.init_screen import ModelDownloder
from screens.face_match import TempSpinWait, FaceMatchBox
from screens.setting import SettingsBox

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
    is_downloading = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self.events)
        self.face_ai = None
        self.txt_dialog = None
        self.is_onnx_running = False
        self.models_ok = False

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
        self.src_image_path = None
        self.trgt_image_path = None
        self.download_file_path = None
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.op_dir, exist_ok=True)
        print(f"Internal model files to be stored in: {self.model_dir}")
        self.detect_model_path = os.path.join(self.model_dir, "faceai", "det_10g.onnx")
        self.recog_model_path = os.path.join(self.model_dir, "faceai","arc.onnx")
        self.is_inp_file_mgr_open = False
        self.is_out_file_mgr_open = False
        Clock.schedule_once(lambda dt: self.model_existance_check())
        print("Init success...")

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

    def model_download_popup(self, instance=None):
        buttons = [
            MDFlatButton(
                text="Cancel",
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
                on_release=self.txt_dialog_closer
            ),
            MDFlatButton(
                text="Ok",
                theme_text_color="Custom",
                text_color="green",
                on_release=self.start_model_download
            ),
        ]
        self.show_text_dialog(
            "Download model files",
            "You need to downlaod the models first.",
            buttons
        )

    def unzip_model(self, filepath):
        import tarfile
        try:
            with tarfile.open(filepath, "r:gz") as tar:
                tar.extractall(path=self.model_dir)
            os.remove(filepath)
            self.show_toast_msg("Model files have been downloaded successfully.")
            self.is_downloading = False
        except Exception as e:
            print(f"Unzip error: {e}")

    def update_download_progress(self, downloaded, total_size):
        if total_size > 0:
            percentage = (downloaded / total_size) * 100
            self.download_progress.text = f"Progress: {percentage:.1f}%"
        else:
            self.download_progress.text = f"Progress: {downloaded} bytes"

    def download_file(self, download_url, download_path):
        filename = download_url.split("/")[-1]
        try:
            self.is_downloading = filename
            with requests.get(download_url, stream=True) as req:
                req.raise_for_status()
                total_size = int(req.headers.get('content-length', 0))
                downloaded = 0
                with open(download_path, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            Clock.schedule_once(lambda dt: self.update_download_progress(downloaded, total_size))
            if os.path.exists(download_path):
                Clock.schedule_once(lambda dt: self.unzip_model(download_path))
            else:
                Clock.schedule_once(lambda dt: self.show_toast_msg(f"Download failed for: {download_path}", is_error=True))
            self.is_downloading = False
        except requests.exceptions.RequestException as e:
            print(f"Error downloading the onnx file: {e} 😞")
            Clock.schedule_once(lambda dt: self.show_toast_msg(f"Download failed for: {download_path}", is_error=True))
            self.is_downloading = False
        Clock.schedule_once(lambda dt: self.download_progress.dismiss())

    def download_model_file(self, model_url, download_path, instance=None):
        self.txt_dialog_closer(instance)
        filename = download_path.split("/")[-1]
        print(f"Starting the download for: {filename}")

        self.download_progress = MDDialog(
            title=f"Downloading {filename}",
            text="Starting download process...",
            #buttons=buttons
        )
        self.download_progress.open()
        Thread(target=self.download_file, args=(model_url, download_path), daemon=True).start()

    def start_model_download(self, instance=None):
        if self.is_downloading:
            self.show_toast_msg("Please wait for the download to finish", is_error=True)
            return
        model_url = "https://github.com/daslearning-org/face-ai/releases/download/vOnnxModels/faceai.tar.gz"
        self.download_model_file(model_url, self.model_dir)

    def model_existance_check(self):
        if os.path.exists(self.detect_model_path) and os.path.exists(self.recog_model_path):
            self.models_ok = True
        else:
            Clock.schedule_once(lambda dt: self.model_download_popup())
            return

    def start_face_services(self, instance=None):
        if os.path.exists(self.detect_model_path) and os.path.exists(self.recog_model_path):
            self.models_ok = True
        else:
            self.model_download_popup()
            return
        self.face_ai = FaceAiSvc(self.detect_model_path, self.recog_model_path, self.op_dir)
        try:
            self.face_ai.start_detection_session()
            self.face_ai.start_recognition_session()
            self.show_toast_msg("Sesstions started successfully")
        except Exception as e:
            print(f"Could not start the sessions: {e}")
            self.show_toast_msg("Couldn't start the services", is_error=True)
            self.face_ai = None

    def goto_face_matcher(self, instance=None):
        self.root.ids.screen_manager.current = "faceFindScr"

    def open_img_file_manager(self, instance=None):
        try:
            if not self.last_upload_path:
                self.last_upload_path = self.external_storage
            filechooser.open_file(
                on_selection = self.handle_img_selection,
                path = self.last_upload_path,
                multiple = False,
                filters = [["*.JPG", "*.jpg", "*.png", "*.jpeg", "*.webp"], "*"],
                preview = True,
            )
            self.is_inp_file_mgr_open = True
            if instance == "btn_fm_src_upload":
                self.img_purpose = "src"
            elif instance == "btn_fm_tgt_upload":
                self.img_purpose = "trgt"
        except Exception as e:
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def handle_img_selection(self, selection=None):
        '''
        Callback function for handling the image selection.
        '''
        self.is_inp_file_mgr_open = False
        if selection:
            image_path = str(selection[0])
            self.last_upload_path = os.path.dirname(image_path)
            Clock.schedule_once(lambda dt: self.select_img_path(image_path))

    def select_img_path(self, path: str):
        if not path.endswith((".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG", ".webp", ".WEBP")):
            self.show_toast_msg(f"Selected file: `{path}` is not an image", is_error=True)
            return

        fitImage = Image(
            source = path,
            fit_mode = "contain"
        )

        if self.img_purpose == "src":
            upload_image_box = self.root.ids.face_match_scr.ids.fm_up_src_box
            self.src_image_path = path
        elif self.img_purpose == "trgt":
            upload_image_box = self.root.ids.face_match_scr.ids.fm_up_trgt_box
            self.trgt_image_path = path

        upload_image_box.clear_widgets()
        upload_image_box.add_widget(fitImage)

    def submit_face_match(self, instance=None):
        """
        Performs the face match job in a separate thread with callback option.
        """
        if not self.face_ai:
            self.show_toast_msg("Please start the session first!", is_error=True)
            return
        if self.is_onnx_running:
            self.show_toast_msg("Please wait for the previous job to finish!", is_error=True)
            return
        if not self.src_image_path or not self.trgt_image_path:
            self.show_toast_msg("Please upload both the source & target image", is_error=True)
            return
        onnx_thread = Thread(
            target=self.face_ai.face_match_group,
            kwargs={
                "img1_path": self.src_image_path,
                "img2_path": self.trgt_image_path,
                "callback": self.face_match_callback
            },
            daemon=True
        )
        onnx_thread.start()
        self.is_onnx_running = True

    def face_match_callback(self, resp):
        self.is_onnx_running = False
        stat = resp["stat"]
        msg = resp["msg"]
        src = resp["src"]
        trgt = resp["trgt"]
        src_box = self.root.ids.face_match_scr.ids.fm_gen_src_box
        trgt_box = self.root.ids.face_match_scr.ids.fm_gen_trgt_box
        src_box.clear_widgets()
        trgt_box.clear_widgets()
        if stat:
            srcImage = Image(
                source = src,
                fit_mode = "contain"
            )
            trgtImage = Image(
                source = trgt,
                fit_mode = "contain"
            )
            src_box.add_widget(srcImage)
            trgt_box.add_widget(trgtImage)
        else:
            label = MDLabel(
                text=msg,
                halign="center",
                #valign="top",
                markup=True
            )
            src_box.add_widget(label)

    def reset_face_matcher(self, instance=None):
        self.src_image_path = None
        self.trgt_image_path = None
        self.img_purpose = ""
        src_box = self.root.ids.face_match_scr.ids.fm_gen_src_box
        trgt_box = self.root.ids.face_match_scr.ids.fm_gen_trgt_box
        src_box.clear_widgets()
        trgt_box.clear_widgets()
        upload_src_box = self.root.ids.face_match_scr.ids.fm_up_src_box
        upload_trgt_box = self.root.ids.face_match_scr.ids.fm_up_trgt_box
        upload_src_box.clear_widgets()
        upload_trgt_box.clear_widgets()

    def show_delete_alert(self):
        op_img_count = 0
        for filename in os.listdir(self.op_dir):
            if filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
                op_img_count += 1
        self.show_text_dialog(
            title="Delete all output files?",
            text=f"There are total: {op_img_count} image files. This action cannot be undone!",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color="red",
                    on_release=self.delete_op_action
                ),
            ],
        )

    def delete_op_action(self, instance):
        # Custom function called when DISCARD is clicked
        for filename in os.listdir(self.op_dir):
            if filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
                file_path = os.path.join(self.op_dir, filename)
                try:
                    os.unlink(file_path)
                    print(f"Deleted {file_path}")
                except Exception as e:
                    print(f"Could not delete the audion files, error: {e}")
        self.show_toast_msg("Executed the audio cleanup!")
        self.txt_dialog_closer(instance)

    def open_link(self, instance, url):
        import webbrowser
        webbrowser.open(url)

    def update_link_open(self, instance=None):
        self.txt_dialog_closer(instance)
        self.open_link(instance=instance, url="https://github.com/daslearning-org/face-ai/releases")

    def update_checker(self, instance=None):
        buttons = [
            MDFlatButton(
                text="Cancel",
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
                on_release=self.txt_dialog_closer
            ),
            MDFlatButton(
                text="Releases",
                theme_text_color="Custom",
                text_color="green",
                on_release=self.update_link_open
            ),
        ]
        self.show_text_dialog(
            "Check for update",
            f"Your version: {__version__}",
            buttons
        )

    def events(self, instance, keyboard, keycode, text, modifiers):
        """Handle mobile device button presses (e.g., Android back button)."""
        #if keyboard in (1001, 27):
        return False

## -- run the app -- ##
if __name__ == '__main__':
    FaceAiApp().run()
