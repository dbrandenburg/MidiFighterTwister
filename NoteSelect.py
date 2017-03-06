
self.set_color(2, 12, 80)



def set_color(self, midi_channel, encoder_cc, color_cc):
    # Sets color on midi channel 2 (177)
    midi_channel = 175 + midi_channel
    self._send_midi((midi_channel, encoder_cc, color_cc))
