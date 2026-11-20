"""Send real keyboard presses to the game (TMInterface cannot navigate Trackmania's menus)."""  # module docstring
import ctypes                                                           # Win32 calls to find / focus the game window
import time                                                             # delays between key presses
import pydirectinput                                                    # SendInput with scan codes, which games accept
import config                                                           # shared settings

pydirectinput.PAUSE = 0                                                 # no built-in delay, we time the presses ourselves
user32 = ctypes.windll.user32                                           # Windows window functions


def focus_game():                                                       # bring the game window to the foreground
    found = []                                                          # matching window handles

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)  # callback type for EnumWindows
    def check(hwnd, _):                                                 # called once per top-level window
        length = user32.GetWindowTextLengthW(hwnd)                      # title length
        if length and user32.IsWindowVisible(hwnd):                     # only visible windows with a title
            buf = ctypes.create_unicode_buffer(length + 1)              # text buffer
            user32.GetWindowTextW(hwnd, buf, length + 1)                # read the title
            if buf.value.strip().lower() == config.GAME_WINDOW_TITLE.lower():  # exact match (terminals contain the project name)
                found.append(hwnd)                                      # remember it
        return True                                                     # keep enumerating

    user32.EnumWindows(check, 0)                                        # scan all windows
    if not found:                                                       # game window not found
        print(f"WARNING: no window titled '{config.GAME_WINDOW_TITLE}' found; "
              "keep the game focused or fix GAME_WINDOW_TITLE in config.py")  # tell the user
        return False                                                    # rely on the game already having focus
    user32.keybd_event(0x12, 0, 0, 0)                                   # tap Alt: Windows then allows focus switching
    user32.keybd_event(0x12, 0, 2, 0)                                   # release Alt
    user32.ShowWindow(found[0], 9)                                      # SW_RESTORE in case it is minimised
    user32.SetForegroundWindow(found[0])                                # focus it
    return True                                                         # done


def press_enter(times=2):                                               # press Enter the given number of times
    focus_game()                                                        # key presses go to the focused window
    time.sleep(config.FINISH_MENU_DELAY_S)                              # let the end screen appear first
    for i in range(times):                                              # e.g. twice: confirm, then restart
        pydirectinput.keyDown("enter")                                  # press
        time.sleep(0.08)                                                # hold long enough for the game to see it
        pydirectinput.keyUp("enter")                                    # release
        if i < times - 1:                                               # not after the last one
            time.sleep(config.ENTER_GAP_S)                              # wait before the next press
