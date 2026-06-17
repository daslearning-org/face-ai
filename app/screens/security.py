from kivy.lang import Builder
from kivy.metrics import dp, sp

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDFillRoundFlatIconButton
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.uix.widget import Widget

Builder.load_string('''

<NameInput>:
    cols: 2
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

# main box
<SecurityBox>:
    orientation: 'vertical'
    padding: 4, 0, 4, self.bottom_pad # left, top, right, bottom
    spacing: dp(4)

    MDBoxLayout:
        orientation: 'vertical'
        spacing: dp(4)
        size_hint_y: 0.8
        #adaptive_height: True

        MDBoxLayout:
            id: camera_box
            size_hint_y: 0.8

        MDGridLayout:
            cols: 2
            adaptive_height: True
            padding: 0, 4, 0, 24
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
            id: save_face_btn
            text: "Save Face"
            icon: "camera"
            font_size: sp(18)
            md_bg_color: "#333036"
            pos_hint: {"center_x": .5, "center_y": 1}
            size_hint_x: 0.5
            #on_release: app.open_img_file_manager("btn_fm_tgt_upload")
        # add camera feed here

    BoxLayout:
        size_hint_y: 0.5

''')

class NameInput(MDGridLayout):
    pass

class SecurityBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings_main_bx"
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar
                self.top_pad = int(get_height_of_bar('status'))
                self.bottom_pad = int(get_height_of_bar('navigation'))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48
