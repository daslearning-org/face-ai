from kivy.lang import Builder
from kivy.metrics import dp, sp

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.button import MDFillRoundFlatIconButton
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.uix.widget import Widget


## The .kv strings
Builder.load_string('''

<SecAfterLogin>:
    orientation: 'vertical'
    spacing: dp(4)

    MDGridLayout:
        cols: 2
        spacing: dp(4)
        size_hint_y: 0.2
        size_hint_max_y: self.parent.height * 0.2
        MDFillRoundFlatIconButton:
            id: vault_up_btn
            text: "Upload File"
            icon: "folder-key"
            font_size: sp(18)
            #md_bg_color: "#333036"
            pos_hint: {"center_x": .5, "center_y": 1}
            size_hint_x: 0.5
            on_release: app.upload_to_vault()
        MDFillRoundFlatIconButton:
            id: add_new_face_btn
            text: "Add Another Face"
            icon: "face-recognition"
            font_size: sp(18)
            md_bg_color: "#333036"
            pos_hint: {"center_x": .5, "center_y": 1}
            size_hint_x: 0.5
            on_release: app.add_new_face()

    MDScrollView:
        size_hint_y: 0.8
        MDList:
            id: sec_file_list
            # add all files here

<NameInput>:
    orientation: 'vertical'
    spacing: dp(4)
    MDGridLayout:
        cols: 2
        padding: 4, 4, 4, 24
        adaptive_height: True
        MDLabel:
            text: "Enter your name"
            halign: "left"
            font_size: sp(14)
            size_hint_x: 0.4
        MDTextField:
            id: sec_name_inp_txt
            text: ""
            hint_text: "Enter Name"
            mode: "rectangle"
            helper_text: "ex: Somnath Das"
            helper_text_mode: "persistent"
            size_hint_x: 0.6
            font_size: sp(18)
            multiline: False
    MDFillRoundFlatIconButton:
        id: sec_cam_btn
        text: root.btn_txt
        icon: "camera"
        font_size: sp(18)
        md_bg_color: "#333036"
        pos_hint: {"center_x": .5, "center_y": 1}
        size_hint_x: 0.5
        on_release: app.sec_capture_frame(sec_name_inp_txt, False)

<SecCamBtn>:
    id: sec_cam_btn
    text: root.btn_txt
    icon: "camera"
    font_size: sp(18)
    md_bg_color: "#333036"
    pos_hint: {"center_x": .5, "center_y": 1}
    size_hint_x: 0.5
    on_release: app.sec_capture_frame(None, False)

<SecCamBox>:
    id: camera_box
    size_hint_y: 0.4
    # add camera feed here

# main box
<SecurityBox>:
    orientation: 'vertical'
    padding: 4, 0, 4, self.bottom_pad # left, top, right, bottom
    spacing: dp(4)

    MDBoxLayout:
        id: sec_elements_box
        orientation: 'vertical'
        spacing: dp(4)
        size_hint_y: 0.8

        # Dynamic things will be added here

    Widget:
        size_hint_y: 0.5
''')

# the classes
class SecAfterLogin(MDBoxLayout):
    pass

class SecCamBox(MDBoxLayout):
    pass

class SecCamBtn(MDFillRoundFlatIconButton):
    btn_txt = StringProperty("Login")

class NameInput(MDBoxLayout):
    btn_txt = StringProperty("Save Face")

class SecurityBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "security_main_bx"
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar
                self.top_pad = int(get_height_of_bar('status'))
                self.bottom_pad = int(get_height_of_bar('navigation'))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48
