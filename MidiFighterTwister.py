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
        self.note_off_color = 36
        self.note_on_color = 60
        self.note_follow_color = 80
        self.sequencer_note = 36
        self.pad_status = {}
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            self.__c_instance = c_instance
            self.show_message('Script initiated')
            self.pad = {}
            self.init_buttons_page_1()
            self.clip_position_16th = None
            self.song().view.add_detail_clip_listener(self.trigger_listener)
            self.song().add_current_song_time_listener(self.light_follows_beat)

            self.init_buttons_page_2()

    def init_buttons_page_1(self):
        # Create encode buttons
        for cc_value in range(0, 16):
            self.pad[cc_value] = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 1,
                                               cc_value)
            self.pad[cc_value].add_value_listener(self.encoder_button_press,
                                                  identify_sender=True)
        # Create side buttons
        self.padl8 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 8)
        self.padr11 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 11)
        self.padl8.add_value_listener(self.side_button_press,
                                      identify_sender=True)
        self.padr11.add_value_listener(self.side_button_press,
                                      identify_sender=True)
        self.reset_buttons_page_1()

    def reset_buttons_page_1(self):
        for cc_value in range(0, 16):
            self._send_midi((177, cc_value, self.note_off_color))
            self.pad_status[cc_value] = False

    def encoder_button_press(self, value, sender):
        actual_clip = self.song().view.highlighted_clip_slot.clip
        if actual_clip and actual_clip.is_midi_clip:
            cc_value = sender._msg_identifier
            if value > 0:
                self.log_message(str(sender._msg_identifier))
                self.show_message(str(sender))
                actual_clip = self.song().view.highlighted_clip_slot.clip
                if not self.pad_status[cc_value]:
                    self._send_midi((177, sender._msg_identifier, self.note_on_color))
                    actual_clip.set_notes(((self.sequencer_note, cc_value*0.25, 0.25, 127, False),))
                    self.pad_status[cc_value] = True
                else:
                    self._send_midi((177, sender._msg_identifier, self.note_off_color))
                    actual_clip.remove_notes(cc_value*0.25, self.sequencer_note, 0.25, 1)
                    self.pad_status[cc_value] = False

    def side_button_press(self, value, sender):
        cc_value = sender._msg_identifier
        if value > 0:
            if cc_value == 8 and self.sequencer_note != 0:
                self.sequencer_note = self.sequencer_note - 1
                self.note_off_color = self.note_off_color - 5
                self.update_sequencer()
            if cc_value == 11 and self.sequencer_note != 127:
                self.sequencer_note = self.sequencer_note + 1
                self.note_off_color = self.note_off_color + 9
                self.update_sequencer()

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

    def trigger_listener(self):
        self.show_message('Listener triggered')
        self.update_sequencer()

    def update_sequencer(self):
        self.reset_buttons_page_1()
        actual_clip = self.song().view.highlighted_clip_slot.clip
        if actual_clip and actual_clip.is_midi_clip:
            notes = actual_clip.get_notes(0, self.sequencer_note, 4, 1)
            self.reset_buttons_page_1()
            for note in notes:
                cc_value = int(note[1]*4)
                self._send_midi((177, cc_value, self.note_on_color))
                self.pad_status[cc_value] = True

##########################################

    def init_buttons_page_2(self):
        # Create encode buttons
        for cc_value in range(16, 32):
            self.pad[cc_value] = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 1,
                                               cc_value)
            self.pad[cc_value].add_value_listener(self.encoder_button_press,
                                                  identify_sender=True)
        # Create side buttons
        self.padl14 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 14)
        self.padr17 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 17)
        self.padl14.add_value_listener(self.side_button_press,
                                      identify_sender=True)
        self.padr17.add_value_listener(self.side_button_press,
                                      identify_sender=True)
        self.reset_buttons_page_2()

    def reset_buttons_page_2(self):
        cc_values = range(16, 32)
        note_colors = range(0, 127, 8)

        for cc_value, note_color in zip(cc_values, note_colors):
            self._send_midi((177, cc_value, note_color))
            #self.pad_status[cc_value] = False
