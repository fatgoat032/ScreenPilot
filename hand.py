#ToDo: ScreenCast for absolutemousePositioning.
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import time
#initializations
#function declarations
class WaylandPortalHand:
    def __init__(self):
        self.session_handle = None
        self.remote_desktop = None
        self.node_id = None
        self.setup_dbus()
        self.screencast = dbus.Interface(self.portal, "org.freedesktop.portal.ScreenCast")

    def setup_dbus(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self.service = "org.freedesktop.portal.Desktop"
        self.path = "/org/freedesktop/portal/desktop"
        self.portal = self.bus.get_object(self.service, self.path)
        self.remote_desktop = dbus.Interface(self.portal, 'org.freedesktop.portal.RemoteDesktop')
    
    def create_session(self):
        self.session_created = False
        options = dbus.Dictionary({'handle_token': dbus.String('u1', variant_level=1), 'session_handle_token': dbus.String('s1', variant_level=1)}, signature='sv')
        result = self.remote_desktop.CreateSession(options)
        print(f"CreateSession created: {result}")
        request_obj = self.bus.get_object("org.freedesktop.portal.Desktop", result)
        request_interface = dbus.Interface(request_obj, "org.freedesktop.portal.Request")
        print("waiting for signal...")
        request_interface.connect_to_signal("Response", self.on_response)
        success = self.wait_for_response(10)
        if success and self.session_handle:
            self.session_path = dbus.ObjectPath(self.session_handle)
            self.session_created = True
            return True
        else:
            print("No successs in connecting to signal.")
            return False

    def select_devices(self):
        self.select_devices_success = False
        if self.session_created:
           options = dbus.Dictionary({'handle_token': dbus.String('u2', variant_level=1)}, signature='sv')
           result = self.remote_desktop.SelectDevices(self.session_path, options)
           request_obj = self.bus.get_object("org.freedesktop.portal.Desktop", result)
           request_interface = dbus.Interface(request_obj, "org.freedesktop.portal.Request")
           request_interface.connect_to_signal("Response", self.on_select_response)
           print("waiting for SelectDevices response...")
           success = self.wait_for_response(10)
           if success:
               print("got a response.")
               self.select_devices_success = True
               return True
           else:
               print("Access to mouse and keyboard failed")
               return False
           
    def select_sources(self):
        self.select_sources_success = False
        if not self.session_created:
            print("Session not created")
            return False
        options = dbus.Dictionary({'handle_token': dbus.String('u4', variant_level=1)}, signature='sv')
        result = self.screencast.SelectSources(self.session_path, options)
        request_obj = self.bus.get_object('org.freedesktop.portal.Desktop', result)
        request_interface = dbus.Interface(request_obj, "org.freedesktop.portal.Request")
        request_interface.connect_to_signal("Response", self.on_screencast_response)
        print("waiting for SelectSources reponse...")
        success = self.wait_for_response(10)
        if success:
            print("Screen source selected")
            return True
        else:
            print("SelectSources timed out")
            return False
        
    def start(self):
            if not self.select_devices_success or not self.select_sources_success:
               print("Devices or sources not selected")
               return False
            options = dbus.Dictionary({'handle_token': dbus.String('u3', variant_level=1)}, signature='sv')
            result = self.remote_desktop.Start(self.session_path, '', options)
            request_obj = self.bus.get_object("org.freedesktop.portal.Desktop", result)
            request_interface = dbus.Interface(request_obj, "org.freedesktop.portal.Request")
            request_interface.connect_to_signal("Response", self.on_start_response)
            print("Starting session...")
            success = self.wait_for_response(10)
            if not success:
                print("Start timed out or failed.")
                self.session_active = False
                return False
            self.session_active = True
            return True

    def wait_for_response(self, timeout_sec=10):
        self.response_recieved = False
        for i in range(timeout_sec * 10):
            GLib.MainContext.default().iteration(False)
            if self.response_recieved:
                return True
            time.sleep(0.1)
        return False
    
    def on_response(self, code, results):
       self.response_recieved = True
       print(f"Code: {code} Results: {results}")
       if code == 0:
         self.session_handle = str(results['session_handle'])

    def on_select_response(self, code, results):
       self.response_recieved = True 
       print(f"SelectDevices response: code={code}, results={results}")

    def on_start_response(self, code, results):
       self.response_recieved = True 
       print(f"Start response: code={code}, results={results}")
       if code == 0:
         if 'streams' in results:
             self.node_id = results['streams'][0][0]
         else:
             print('No streams in response')
         print("Authorized, session is now active.")

    def on_screencast_response(self, code, results):
        self.response_recieved = True
        print(f"SelectSources response: code={code}, results={results}")
        if code == 0:
            self.select_sources_success = True
    
    def click(self, button='left'): #as default is left
        time.sleep(0.3)
        button_codes = {'left': 0x110, 'right': 0x111, 'middle': 0x112}
        code = button_codes.get(button)
        self.remote_desktop.NotifyPointerButton(self.session_path, dbus.Dictionary({}, signature='sv'), dbus.Int32(code, variant_level=1), dbus.UInt32(1, variant_level=1))
        time.sleep(0.2)
        self.remote_desktop.NotifyPointerButton(self.session_path, dbus.Dictionary({}, signature='sv'), dbus.Int32(code, variant_level=1), dbus.UInt32(0, variant_level=1))
    
    def move_to(self, x, y):
        self.remote_desktop.NotifyPointerMotionAbsolute(self.session_path, dbus.Dictionary({}, signature='sv'), dbus.Int32(self.node_id, variant_level=1), dbus.Double(x, variant_level=1), dbus.Double(y, variant_level=1))
    
    def type_text(self, text):
        special_keys = {
            '\n': 65293, #enter
            '\t': 65289, #tab
        }
        for char in text:
            code = special_keys.get(char, ord(char)) #if char not found in special keys, just get their ASCII value
            self.remote_desktop.NotifyKeyboardKeysym(self.session_path, dbus.Dictionary({}, signature="sv"), dbus.Int32(code, variant_level=1), dbus.UInt32(1, variant_level=1))
            time.sleep(0.05)
            self.remote_desktop.NotifyKeyboardKeysym(self.session_path, dbus.Dictionary({}, signature="sv"), dbus.Int32(code, variant_level=1), dbus.UInt32(0, variant_level=1))
            time.sleep(0.05)

    def key(self, key):
        code = None
        keys = {'Return': 65293, 'Tab': 65289, 'Escape': 65307, 'BackSpace': 65288}
        code = keys.get(key)
        #if ai hallucinates
        if code == None:
            print("Invalid key, ai hallucinated, try again")
            return
        self.remote_desktop.NotifyKeyboardKeysym(self.session_path, dbus.Dictionary({}, signature='sv'), dbus.Int32(code, variant_level=1), dbus.UInt32(1, variant_level=1))
        time.sleep(0.05)
        self.remote_desktop.NotifyKeyboardKeysym(self.session_path, dbus.Dictionary({}, signature='sv'), dbus.Int32(code, variant_level=1), dbus.UInt32(0, variant_level=1))
        time.sleep(0.05)