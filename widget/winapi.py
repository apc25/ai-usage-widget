import ctypes
import winreg
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

kernel32 = ctypes.windll.kernel32
kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenEventW.restype = wintypes.HANDLE
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

EVENT_MODIFY_STATE = 0x0002
REFRESH_EVENT = "Local\\AIUsageWidget.Refresh"  # created by host/host.py while Chrome is connected


def taskbar():
    """Primary taskbar window handle, or None while Explorer is (re)starting."""
    return user32.FindWindowW("Shell_TrayWnd", None)


def client_size(hwnd):
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    return rect.right, rect.bottom


def host_connected():
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, REFRESH_EVENT)
    if handle:
        kernel32.CloseHandle(handle)
    return bool(handle)


def request_refresh():
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, REFRESH_EVENT)
    if not handle:
        return False
    kernel32.SetEvent(handle)
    kernel32.CloseHandle(handle)
    return True


def light_theme():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "SystemUsesLightTheme")[0] == 1
    except OSError:
        return False
