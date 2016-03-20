from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.ButtonElement import ButtonElement
from _Framework.InputControlElement import *

IS_MOMENTARY = True


class MidiFighterTwister(ControlSurface):
    __module__ = __name__
    __doc__ = "MidiFighterTwister class"

    def __init__(self, c_instance):
        self.note_off_color = 1
        self.note_on_color = 60
        self.note_follow_color = 80
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            self.__c_instance = c_instance
            self.show_message('Script initiated')
            self.pad = {}
            self.pad_status = {}
            self.buttons_page_1()
            self.clip_position_16th = None
            self.song().add_current_song_time_listener(self.light_follows_beat)

    def buttons_page_1(self):
        # Set all buttons to NOTE_OFF_COLOR
        for cc_value in range(0, 16):
            self._send_midi((177, cc_value, 1))
            self.pad_status[cc_value] = False
            self.pad[cc_value] = ButtonElement(
                IS_MOMENTARY, MIDI_CC_TYPE, self.note_off_color, cc_value)
            self.pad[cc_value].add_value_listener(
                self.button_press, identify_sender=True)

    def button_press(self, value, sender):
        cc_value = sender._msg_identifier
        if value > 0:
            self.log_message(str(sender._msg_identifier))
            self.show_message(str(sender))
            if not self.pad_status[cc_value]:
                self._send_midi((177, sender._msg_identifier, self.note_on_color))
                self.pad_status[cc_value] = True
            else:
                self._send_midi((177, sender._msg_identifier, self.note_off_color))
                self.pad_status[cc_value] = False

    def light_follows_beat(self):
        actual_clip = self.song().view.highlighted_clip_slot.clip
        if actual_clip and actual_clip.is_midi_clip:
            if self.clip_position_16th == None:
                self.clip_position_16th = int(actual_clip.playing_position/0.25)
                if self.pad_status[self.clip_position_16th]:
                    self._send_midi((177, self.clip_position_16th, self.note_on_color))
                else:
                    self._send_midi((177, self.clip_position_16th, self.note_off_color))
            elif self.clip_position_16th != int(actual_clip.playing_position/0.25):
                if self.pad_status[self.clip_position_16th]:
                    self._send_midi((177, self.clip_position_16th, self.note_on_color))
                else:
                    self._send_midi((177, self.clip_position_16th, self.note_off_color))
                self.clip_position_16th = int(actual_clip.playing_position/0.25)
                self._send_midi((177, self.clip_position_16th, self.note_follow_color))
                #self.log_message(str(self.clip_position_16th))
            #else:
                #self.log_message(str(self.clip_position_16th))
                #self._send_midi((177, self.clip_position_16th, self.note_follow_color))
    #self.first_clipslot = self.actual_song.tracks[0].clip_slots[0]
    #self.first_clipslot.create_clip(length)
