from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.ButtonElement import ButtonElement
from _Framework.InputControlElement import *

#IS_MOMENTARY = True

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
        # Initialize the on/off cache for encoders for sequencer

    def mf_init_page_config(self):
        # Initialize configuration parameters
        # Sequencer configuration
        self.sequencer_page_default_color = 1
        self.sequencer_current_page_color = self.sequencer_page_default_color
        self.sequencer_base_default_note = 36
        self.sequencer_current_selected_note = self.sequencer_base_default_note

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
        self.note_page_colors = range(0, 127, 16) * 2
        self.control_page_colors = [1] * 16
        # Status cache for sequencer
        self.switch_encoder_status_cache = [False] * 64
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
        self.switch_encoder_status_cache[light_encoder_cc]

    def dispatch_detail_clip_listener(self):
        current_clip = self.song().view.highlighted_clip_slot.clip
        if current_clip.is_midi_clip:
            # Update leds when notes are added or removed
            current_clip.add_notes_listener(
                self._sequencer_update_notes_to_light)
            self.sequencer()
        else:
            self.sequencer_reset_colors()

    def dispatch_current_song_time_listener(self):
        pass

# Sequencer
    def sequencer(self):
        self._sequencer_update_notes_to_light()

    @property
    def sequencer_current_light_on_color(self):
        # light on color to be relative to page color
        return self.sequencer_current_page_color + 32

    @property
    def sequencer_current_light_beat_color(self):
        # light on color to be relative to page color
        return self.sequencer_current_page_color + 64

    def _sequencer_get_midi_notes(self, note):
        current_clip = self.song().view.highlighted_clip_slot.clip
        # actual_clip.get_notes(start, self.sequencer_current_selected_note,
        # selection_length, hight)
        return current_clip.get_notes(0, note, 4, 1)

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
            self.log_message(str(light_encoder_cc))
            self.log_message(str(self.sequencer_current_page_color))
            self._mf_set_light(light_encoder_cc,
                               self.sequencer_page_default_color, False)
