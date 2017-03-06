from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.SessionComponent import SessionComponent
from _Framework.InputControlElement import *
from _Framework.MixerComponent import MixerComponent
from _Framework.EncoderElement import EncoderElement
from _Framework.DeviceComponent import DeviceComponent

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
        self.flush_all()
        self.mf_disable_bank_buttons()
        self.mf_init_page_config()
        self.mf_init_light_pages()

        # Start listeners to call dispatcher
        self.song().view.add_detail_clip_listener(
            self.dispatch_detail_clip_listener)
        self.song().add_current_song_time_listener(
            self.dispatch_current_song_time_listener)
        self.song().view.add_selected_track_listener(
            self.dispatch_selected_track_listener)
        self.device_listener_wrapper()

        # Initialize the sequencer buttons
        self.sequencer_init_buttons()
        self.sequencer_init_rotaries()
        self.init_clip_page()
        self.init_pad_page()
        self.init_device_params()

    def flush_all(self):
        for poti in range(64):
            for channel in range(4):
                self._send_midi((175 + channel, poti, 0))

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
        #self.note_page_colors = [0] * 16
        self.control_page_colors = [1] * 16
        # Status cache for sequencer
        self.switch_encoder_status_cache = [False] * 64
        # List to store ButtonElements in
        self.switch_encoder_buttons = [False] * 64
        # Status cache for rotaries
        self.rotary_encoder_potis = [False] * 64

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

    def mf_disable_bank_buttons(self):
        # Workaround for not sending values to track when pressing bank buttons
        self.padm0 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 4, 0)
        self.padm1 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 4, 1)
        self.padm2 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 4, 2)
        self.padm3 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 4, 3)
        self.padm0.add_value_listener(self.bank_buttons_dummy,
                                      identify_sender=True)
        self.padm1.add_value_listener(self.bank_buttons_dummy,
                                      identify_sender=True)
        self.padm2.add_value_listener(self.bank_buttons_dummy,
                                      identify_sender=True)
        self.padm3.add_value_listener(self.bank_buttons_dummy,
                                      identify_sender=True)

    def bank_buttons_dummy(self):
        pass

    def dispatch_detail_clip_listener(self):
        self.current_clip = self.song().view.highlighted_clip_slot.clip
        self.init_sequencer()
        try:
            if self.current_clip.is_midi_clip and not self.current_clip.notes_has_listener:
                # Update leds when notes are added or removed
                self.current_clip.add_notes_listener(
                    self._sequencer_update_notes_to_light)
                self.init_sequencer()
            else:
                self.sequencer_reset_colors()
        except AttributeError:
            pass

    def dispatch_current_song_time_listener(self):
        self.sequencer_light_follows_beat()

    def dispatch_selected_track_listener(self):
        self.device_auto_select()
        self.device_listener_wrapper()

    def device_listener_wrapper(self):
        selected_track = self.song().view.selected_track
        if not selected_track.devices_has_listener(self.device_auto_select):
            self.song().view.selected_track.add_devices_listener(
                self.device_auto_select)

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
        self.padl16 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 16)
        self.padr19 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 19)
        self.padl14.add_value_listener(self.sequencer_side_button_press,
                                       identify_sender=True)
        self.padr17.add_value_listener(self.sequencer_side_button_press,
                                       identify_sender=True)
        self.padl16.add_value_listener(self.sequencer_side_button_press,
                                       identify_sender=True)
        self.padr19.add_value_listener(self.sequencer_side_button_press,
                                       identify_sender=True)

    def sequencer_init_rotaries(self):
        for rotary_encoder_cc in self.sequencer_page_cc:
            self.rotary_encoder_potis[rotary_encoder_cc] = EncoderElement( MIDI_CC_TYPE, 0, rotary_encoder_cc, Live.MidiMap.MapMode.absolute)
            self.rotary_encoder_potis[rotary_encoder_cc].add_value_listener(self.sequencer_rotary_change, identify_sender=True)

    def sequencer_rotary_change(self, value, sender):
        try:
            self.current_clip
        except AttributeError:
            return False
        if self.current_clip.is_midi_clip:
            cc_value = sender._msg_identifier
            if value > 0:
                if not self.switch_encoder_status_cache[cc_value]:
                    self._send_midi((self.light_midi_channel,
                                     cc_value,
                                     self.sequencer_current_light_on_color))
                    self._send_midi((
                        self.ring_midi_channel, cc_value, 100))
                    self.switch_encoder_status_cache[cc_value] = True
                self.current_clip.set_notes(((self.sequencer_current_selected_note, cc_value % 16 * 0.25, 0.25, value, False),))
            elif value == 0:
                self._send_midi((self.light_midi_channel,
                                cc_value, self.sequencer_current_page_color))
                self.current_clip.remove_notes(
                    cc_value % 16 * 0.25,
                    self.sequencer_current_selected_note,
                    0.25, 1)
                self.switch_encoder_status_cache[cc_value] = False

    def sequencer_button_press(self, value, sender):
        try:
            self.current_clip
        except AttributeError:
            return False
        if self.current_clip.is_midi_clip:
            cc_value = sender._msg_identifier
            if value > 0:
                if not self.switch_encoder_status_cache[cc_value]:
                    self._send_midi((self.light_midi_channel,
                                     cc_value,
                                     self.sequencer_current_light_on_color))
                    self.current_clip.set_notes(((
                        self.sequencer_current_selected_note, cc_value % 16 *
                        0.25, 0.25, 100, False),))
                    self.switch_encoder_status_cache[cc_value] = True
                    self._send_midi((self.ring_midi_channel, cc_value, 100))
                else:
                    self._send_midi((self.light_midi_channel,
                                     cc_value,
                                     self.sequencer_current_page_color))
                    self._send_midi((self.ring_midi_channel, cc_value, 0))
                    self.current_clip.remove_notes(
                        cc_value % 16 * 0.25,
                        self.sequencer_current_selected_note,
                        0.25, 1)
                    self.switch_encoder_status_cache[cc_value] = False

    def sequencer_side_button_press(self, value, sender):
            try:
                cc_value = sender._msg_identifier
                if value > 0:
                    # Note/clolor up/down
                    if cc_value == 14 and self.sequencer_current_selected_note > 0:
                        self.sequencer_current_selected_note = self.sequencer_current_selected_note - 1
                        self.sequencer_current_page_color_index = self.sequencer_current_page_color_index - 16
                        self._sequencer_update_notes_to_light()
                        self.sequencer_clip_position_16th = None
                        self.show_message("Selected Midi Note: "+str(self.sequencer_current_selected_note))
                    if cc_value == 17 and self.sequencer_current_selected_note < 127:
                        self.sequencer_current_selected_note = self.sequencer_current_selected_note + 1
                        self.sequencer_current_page_color_index = self.sequencer_current_page_color_index + 16
                        self._sequencer_update_notes_to_light()
                        self.sequencer_clip_position_16th = None
                        self.show_message("Selected Midi Note: "+str(self.sequencer_current_selected_note))
                    # New/duplicate clip
                    if cc_value == 16 and self.sequencer_current_selected_note > 0:
                        self.duplicate_clip()
                    if cc_value == 19 and self.sequencer_current_selected_note > 0:
                        self.session_record()
            except AttributeError:
                pass

    def sequencer_light_follows_beat(self):
        try:
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
        except IndexError:
            pass

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
        try:
            return self.current_clip.get_notes(0, note, 4, 1)
        except AttributeError:
            return []

    def _sequencer_update_notes_to_light(self):
        self.sequencer_reset_colors()
        notes_for_current_selected_note = self._sequencer_get_midi_notes(
            self.sequencer_current_selected_note)
        for note in notes_for_current_selected_note:
            light_encoder_cc = int(note[1]*4+self.sequencer_page_cc[0])
            self._send_midi((self.ring_midi_channel, light_encoder_cc, note[3]))
            self._mf_set_light(light_encoder_cc,
                               self.sequencer_current_light_on_color, True)

    def sequencer_reset_colors(self):
        for light_encoder_cc in self.sequencer_page_cc:
            self._mf_set_light(light_encoder_cc,
                               self.sequencer_current_page_color, False)
            self._send_midi((self.ring_midi_channel, light_encoder_cc, 0))

    def duplicate_clip(self):
        self.log_message("duplicate clip")
        #if self._clip_slot and self._clip_slot.has_clip:
        #    slot_name = self._clip_slot.clip.name
        #    track = self._clip_slot.canonical_parent
        current_track = self.song().view.selected_track
        current_clip_slot = self.song().view.highlighted_clip_slot
        self.song().duplicate_scene(list(current_track.clip_slots).index(current_clip_slot))
        #new_clip = current_track.duplicate_clip_slot(
        #    list(current_track.clip_slots).index(current_clip_slot)+1)
        #self.log_message(new_clip)
        #selected_track = self.song().view.selected_track
        #selected_track.duplicate_clip_slot(selected_track)

    def session_record(self):
        self.log_message("session record")
        #self.song().trigger_session_record()

# Clip page setion

    def init_clip_page(self):
        num_tracks = 4
        num_scenes = 3
        self.flash_status = 1
        self.Mixer = MixerComponent(4, 3)

        # Volencoder
        self.volencoders = [None for index in range(num_tracks)]
        for index in range(num_tracks):
            self.volencoders[index] = EncoderElement(
                MIDI_CC_TYPE, 0, index, Live.MidiMap.MapMode.absolute)
            self.Mixer.channel_strip(index).set_volume_control(
                self.volencoders[index])

        # Sendencoder
        for index in range(num_tracks):
            encoder_cc_send_1 = index + num_tracks
            encoder_cc_send_2 = index + num_tracks * 2
            send1 = EncoderElement(MIDI_CC_TYPE, 0, encoder_cc_send_1,
                                   Live.MidiMap.MapMode.absolute)
            send2 = EncoderElement(MIDI_CC_TYPE, 0, encoder_cc_send_2,
                                   Live.MidiMap.MapMode.absolute)
            self.Mixer.channel_strip(index).set_send_controls((send1, send2))

        # Panencoder
        for index in range(num_tracks):
            encoder_cc_pan = index + num_tracks * 3
            pan = EncoderElement(MIDI_CC_TYPE, 0, encoder_cc_pan,
                                 Live.MidiMap.MapMode.absolute)
            self.Mixer.channel_strip(index).set_pan_control(pan)

        # Arm-/selectbuttons
        for index in range(num_tracks):
            armbutton = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 1,
                                      index + 12)
            self.Mixer.channel_strip(index).set_arm_button(armbutton)
            self.Mixer.channel_strip(index).set_select_button(armbutton)

        # Navigation buttons
        self.padl11 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 11)
        self.padr8 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 8)
        self.padl10 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 10)
        self.padr13 = ButtonElement(IS_MOMENTARY, MIDI_CC_TYPE, 3, 13)

        self.grid = [None for index in range(num_tracks * 3)]
        for index in range(num_tracks * 3):
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
        self.Session.set_mixer(self.Mixer)
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
                self.scene[row].clip_slot(column).set_triggered_to_play_value(35)
                self.scene[row].clip_slot(column).set_stopped_value(68)
                self.scene[row].clip_slot(column).set_started_value(45)
                self.scene[row].clip_slot(column).set_triggered_to_record_value(100)
                self.scene[row].clip_slot(column).set_recording_value(80)

        for column in range(num_tracks):
            for row in range(num_scenes):
                self.scene[row].clip_slot(column).set_launch_button(self.grid[column+(row*4)])
            for index in range(num_tracks*num_scenes):
                self.grid[index].clear_send_cache()

    def update_display(self):
        # Called every 100 ms
        ControlSurface.update_display(self)
        self.refresh_state()
        self.Session.set_enabled(True)
        self.Session.update()
        # Sequencer hack
        try:
            for light_encoder_cc in self.sequencer_page_cc:
                self._send_midi((self.ring_midi_channel, light_encoder_cc, 0))
            notes_for_current_selected_note = self._sequencer_get_midi_notes(
                self.sequencer_current_selected_note)
            for note in notes_for_current_selected_note:
                light_encoder_cc = int(note[1]*4+self.sequencer_page_cc[0])
                self._send_midi((self.ring_midi_channel, light_encoder_cc,
                                 note[3]))
        except AttributeError:
            pass

    # Pad Section
    def init_pad_page(self):
        self.pad_device_params()
        PAD_TRANSLATION = (
            (0, 0, 32, 1), (1, 0, 33, 1), (2, 0, 34, 1), (3, 0, 35, 1),
            (0, 1, 36, 1), (1, 1, 37, 1), (2, 1, 38, 1), (3, 1, 39, 1),
            (0, 2, 40, 1), (1, 2, 41, 1), (2, 2, 42, 1), (3, 2, 43, 1),
            (0, 3, 44, 1), (1, 3, 45, 1), (2, 3, 46, 1), (3, 3, 47, 1))
        self.set_pad_translations(PAD_TRANSLATION)
        self._device_selection_follows_track_selection = True

    def pad_device_params(self):
        device_param_controls = []
        for param in self.note_page_cc[:8]:
            self.rotary_encoder_potis[param] = EncoderElement(
                MIDI_CC_TYPE, 0, param, Live.MidiMap.MapMode.absolute)
            self.rotary_encoder_potis[param].release_parameter()
            self.rotary_encoder_potis[param].send_value(0, True)
            self.rotary_encoder_potis[param].clear_send_cache()
            device_param_controls.append(self.rotary_encoder_potis[param])

        device = DeviceComponent()
        device.name = 'Device_Component pad'
        device.set_parameter_controls(tuple(device_param_controls))
        self.set_device_component(device)

    #def scrolling(self):
    #    self.application().view.scroll_view(ndir, 'Detail/DeviceChain', True)

    # Live.Song.Song.View.selected_track
    #Live.Song.Song.View.select_device()[0]

    # Device parameter section
    def init_device_params(self):
        device_param_controls = []
        device_bank_buttons = []
        for param in self.control_page_cc[:8]:
            self.rotary_encoder_potis[param] = EncoderElement(
                MIDI_CC_TYPE, 0, param, Live.MidiMap.MapMode.absolute)
            self.switch_encoder_buttons[param] = ButtonElement(
                IS_MOMENTARY, MIDI_CC_TYPE, 1, param)
            self.rotary_encoder_potis[param].release_parameter()
            self.rotary_encoder_potis[param].send_value(0, True)
            self.rotary_encoder_potis[param].clear_send_cache()
            device_param_controls.append(self.rotary_encoder_potis[param])
            device_bank_buttons.append(self.switch_encoder_buttons[param])

        device = DeviceComponent()
        device.name = 'Device_Component'
        device.set_parameter_controls(tuple(device_param_controls))
        device.set_bank_buttons(tuple(device_bank_buttons))
        device.set_on_off_button(ButtonElement(
            IS_MOMENTARY, MIDI_CC_TYPE, 1, 56))
        self.set_device_component(device)

    def device_auto_select(self):
        # Iterates through devices within a track and assigns the first
        # DrumPad device to activate the individual drum's device.
        # Use first device in case none is a DrumPad device.
        selected_track = self.song().view.selected_track
        devices = selected_track.devices
        for device in devices:
            if device.can_have_drum_pads:
                self.current_drum_device = device
                pad_device = self.current_drum_device.view.selected_chain.devices[0]
                self.song().view.select_device(pad_device)
                if not self.current_drum_device.view.selected_drum_pad_has_listener(
                        self.device_update_current_note):
                    self.current_drum_device.view.add_selected_drum_pad_listener(
                            self.device_update_current_note)
                break
            else:
                self.song().view.select_device(devices[0])

    def device_update_current_note(self):
        current_note = self.current_drum_device.view.selected_drum_pad.note
        self.sequencer_current_selected_note = current_note

        # Update light of active pad
        #self._send_midi((self.light_midi_channel, light_encoder_cc, 63))
        try:
            self.current_clip = self.song().view.highlighted_clip_slot.clip
            self.current_clip.is_midi_clip
            self._sequencer_update_notes_to_light()
        except AttributeError:
            pass
        #Live.DrumPad.DrumPad.note
