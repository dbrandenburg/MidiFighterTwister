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
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            self.__c_instance = c_instance
            self.show_message('Script initiated')
            self.pad = {}
            self.pad_status = {}
            self.buttons_page_1()

    def buttons_page_1(self):
        for cc_value in range(0, 16):
            self._send_midi((177, cc_value, 1))
            self.pad_status[cc_value] = False
            self.pad[cc_value] = ButtonElement(
                IS_MOMENTARY, MIDI_CC_TYPE, 1, cc_value)
            self.pad[cc_value].add_value_listener(
                self.button_press, identify_sender=True)

    def button_press(self, value, sender):
        cc_value = sender._msg_identifier
        if value > 0:
            self.log_message(str(sender._msg_identifier))
            self.show_message(str(sender))
            if not self.pad_status[cc_value]:
                self._send_midi((177, sender._msg_identifier, 63))
                self.pad_status[cc_value] = True
            else:
                self._send_midi((177, sender._msg_identifier, 1))
                self.pad_status[cc_value] = False
