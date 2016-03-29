from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.SessionComponent import SessionComponent
from _Framework.InputControlElement import *

IS_MOMENTARY = True

class MidiFighterTwister(ControlSurface):
    __module__ = __name__
    __doc__ = "MidiFighterTwister class"

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            self.__c_instance = c_instance
            self.show_message('Script initiated')
            self.init()

    def init(self):
        # initialize listeners, caches and colors
        self.mf_init_page_config()
        self.mf_init_light_pages()

        # Start listeners to call dispatcher
        self.song().view.add_detail_clip_listener(
            self.dispatch_detail_clip_listener)
        self.song().add_current_song_time_listener(
            self.dispatch_current_song_time_listener)
        # Initialize the sequencer buttons
        self.sequencer_init_buttons()
        self.init_clip_page()

    def mf_init_page_config(self):
        # Initialize configuration parameters
        # Sequencer configuration
        self.sequencer_page_default_color = 1
        self.sequencer_current_page_color_index = self.sequencer_page_default_color
        self.sequencer_base_default_note = 36
        self.sequencer_current_selected_note = self.sequencer_base_default_note
        self.sequencer_clip_position_16th = None

        # Midi Channels
        self.rotary_midi_channel = 175 + 1
        self.ring_midi_channel = 175 + 1
        self.switch_midi_channel = 175 + 2
        self.light_midi_channel = 175 + 2
        # Pages cc map
        self.clip_page_cc = range(0, 16)
        self.sequencer_page_cc = range(16, 32)
        self.note_page_cc = range(32, 48)
        self.control_page_cc = range(48, 64)
        # Pages init color
        self.clip_page_colors = [1] * 16
        self.sequencer_page_colors = [self.sequencer_page_default_color] * 16
        self.note_page_colors = range(1, 127, 16) * 2
        self.control_page_colors = [1] * 16
        # Status cache for sequencer
        self.switch_encoder_status_cache = [False] * 64
        # List to store ButtonElements in
        self.switch_encoder_buttons = [False] * 64
        # Status cache for rotaries
        self.rotary_encoder_status_cache = [0] * 64

    def mf_init_light_pages(self):
        sequencer_page_map = zip(self.sequencer_page_cc,
                                 self.sequencer_page_colors)
        for light_encoder_cc, light_color_cc in sequencer_page_map:
            self._mf_set_light(light_encoder_cc, light_color_cc, False)
        note_page_map = zip(self.note_page_cc,
                            self.note_page_colors)
        for light_encoder_cc, light_color_cc in note_page_map:
            self._mf_set_light(light_encoder_cc, light_color_cc, False)

    def _mf_set_light(self, light_encoder_cc, light_color_cc, status):
        # Sets color on midi channel 2 (177) end updates status cache
        # for sequencer to remember statuses
        self._send_midi((self.light_midi_channel, light_encoder_cc,
                         light_color_cc))
        self.switch_encoder_status_cache[light_encoder_cc] = status

    def dispatch_detail_clip_listener(self):
        self.current_clip = self.song().view.highlighted_clip_slot.clip
        if self.current_clip.is_midi_clip:
            # Update leds when notes are added or removed
            self.current_clip.add_notes_listener(
                self._sequencer_update_notes_to_light)
            self.init_sequencer()
        else:
            self.sequencer_reset_colors()

    def dispatch_current_song_time_listener(self):
        self.sequencer_light_follows_beat()

    # Sequencer
    def init_sequencer(self):
        self.sequencer_current_selected_note = self.sequencer_base_default_note
        self.sequencer_current_page_color_index = self.sequencer_page_default_color
        self._sequencer_update_notes_to_light()

    def sequencer_init_buttons(self):
        for switch_encoder_cc in self.sequencer_page_cc:
            self.switch_encoder_buttons[switch_encoder_cc] = ButtonElement(
                IS_MOMENTARY, MIDI_CC_TYPE, 1, switch_encoder_cc)
            self.switch_encoder_buttons[switch_encoder_cc].add_value_listener(
            self.sequencer_button_press, identify_sender=True)
        self.padl14 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 14)
        self.padr17 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 17)
        self.padl14.add_value_listener(self.sequencer_side_button_press,
                                      identify_sender=True)
        self.padr17.add_value_listener(self.sequencer_side_button_press,
                                       identify_sender=True)

    def sequencer_button_press(self, value, sender):
        try:
            self.current_clip
        except AttributeError:
            return False
        if self.current_clip.is_midi_clip:
            cc_value = sender._msg_identifier
            if value > 0:
                self.show_message(str(sender))
                if not self.switch_encoder_status_cache[cc_value]:
                    self.log_message(str(cc_value))
                    self._send_midi((self.light_midi_channel,
                                     cc_value,
                                     self.sequencer_current_light_on_color))
                    self.current_clip.set_notes(((
                        self.sequencer_current_selected_note, cc_value % 16 *
                        0.25, 0.25, 127, False),))
                    self.switch_encoder_status_cache[cc_value] = True
                else:
                    self._send_midi((self.light_midi_channel,
                                     cc_value,
                                     self.sequencer_current_page_color))
                    self.current_clip.remove_notes(
                        cc_value % 16 * 0.25,
                        self.sequencer_current_selected_note,
                        0.25, 1)
                    self.switch_encoder_status_cache[cc_value] = False

    def sequencer_side_button_press(self, value, sender):
            cc_value = sender._msg_identifier
            if value > 0:
                if cc_value == 14 and self.sequencer_current_selected_note != -36:
                    self.sequencer_current_selected_note = self.sequencer_current_selected_note - 1
                    self.sequencer_current_page_color_index = self.sequencer_current_page_color_index - 16
                    self._sequencer_update_notes_to_light()
                    self.sequencer_clip_position_16th = None
                if cc_value == 17 and self.sequencer_current_selected_note != 96:
                    self.sequencer_current_selected_note = self.sequencer_current_selected_note + 1
                    self.sequencer_current_page_color_index = self.sequencer_current_page_color_index + 16
                    self._sequencer_update_notes_to_light()
                    self.sequencer_clip_position_16th = None

    def sequencer_light_follows_beat(self):
        if self.current_clip.is_midi_clip:
            if self.sequencer_clip_position_16th == None:
                self.sequencer_clip_position_16th = int(self.current_clip.playing_position / 0.25)
                if self.switch_encoder_status_cache[self.sequencer_page_cc[self.sequencer_clip_position_16th]]:
                    self._send_midi((177, self.sequencer_page_cc[self.sequencer_clip_position_16th], self.sequencer_current_light_on_color))
                else:
                    self._send_midi((177, self.sequencer_page_cc[self.sequencer_clip_position_16th], self.sequencer_current_page_color))
            elif self.sequencer_clip_position_16th != int(self.current_clip.playing_position/0.25):
                if self.switch_encoder_status_cache[self.sequencer_page_cc[self.sequencer_clip_position_16th]]:
                    self._send_midi((177, self.sequencer_page_cc[self.sequencer_clip_position_16th], self.sequencer_current_light_on_color))
                else:
                    self._send_midi((177, self.sequencer_page_cc[self.sequencer_clip_position_16th], self.sequencer_current_page_color))
                self.sequencer_clip_position_16th = int(self.current_clip.playing_position/0.25)
                self._send_midi((177, self.sequencer_page_cc[self.sequencer_clip_position_16th], self.sequencer_current_light_beat_color))

    @property
    def sequencer_current_light_on_color(self):
        # light on color to be relative to page color
        return self.sequencer_current_page_color + 32 % 128

    @property
    def sequencer_current_light_beat_color(self):
        # light on color to be relative to page color
        return self.sequencer_current_page_color + 64 % 128

    @property
    def sequencer_current_page_color(self):
        return self.sequencer_current_page_color_index % 128

    def _sequencer_get_midi_notes(self, note):
        # self.current_clip.get_notes(start, self.sequencer_current_selected_note,
        # selection_length, hight)
        return self.current_clip.get_notes(0, note, 4, 1)

    def _sequencer_update_notes_to_light(self):
        self.sequencer_reset_colors()
        notes_for_current_selected_note = self._sequencer_get_midi_notes(
            self.sequencer_current_selected_note)
        for note in notes_for_current_selected_note:
            light_encoder_cc = int(note[1]*4+self.sequencer_page_cc[0])
            self._mf_set_light(light_encoder_cc,
                               self.sequencer_current_light_on_color, True)

    def sequencer_reset_colors(self):
        for light_encoder_cc in self.sequencer_page_cc:
            self._mf_set_light(light_encoder_cc,
                               self.sequencer_current_page_color, False)

    def init_clip_page(self):
        self.padl11 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 11)
        self.padr8 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 8)
        self.padl10 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 10)
        self.padr13 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 13)

        num_tracks = 4
        num_scenes = 4

        self.grid = [None for index in self.clip_page_cc]
        for index in self.clip_page_cc:
            self.grid[index] = ButtonElement(
                IS_MOMENTARY, MIDI_CC_TYPE, 1, index)
        self.matrix = ButtonMatrixElement()
        for row in range(num_scenes):
            button_row = []
            for column in range(num_tracks):
                button_row.append(self.grid[column+(row*4)])
                self.log_message(str(column+(row*4)))
            self.matrix.add_row(tuple(button_row))

        self.Session = SessionComponent(num_tracks, num_scenes)
        self.Session.name = "Session"
        self.Session.set_offsets(0, 0)
        self.Session._do_show_highlight()
        self.set_highlighting_session_component(self.Session)
        self.Session.set_track_bank_buttons(self.padl11, self.padr8)
        self.Session.set_scene_bank_buttons(self.padr13, self.padl10)

        self.scene = [None for index in range(num_scenes)]
        for row in range(num_scenes):
            self.scene[row] = self.Session.scene(row)
            self.scene[row].name = 'Scene_'+str(row)
            for column in range(num_tracks):
                clip_slot = self.scene[row].clip_slot(column)
                clip_slot.name = str(column)+'_Clip_Slot'+str(row)
                self.scene[row].clip_slot(column).set_triggered_to_play_value(20)
                self.scene[row].clip_slot(column).set_stopped_value(40)
                self.scene[row].clip_slot(column).set_started_value(60)

        for column in range(num_tracks):
            for row in range(num_scenes):
                self.scene[row].clip_slot(column).set_launch_button(self.grid[row+(column*4)])
            for index in range(num_tracks*num_scenes):
                self.grid[index].clear_send_cache()
