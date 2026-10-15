"""
Simple Impulse H2 runner with native game rumble muting, utilising FH2TriggerBridge.
"""
import ctypes
import os
import time
import azimuth_hook

# Rumble intensity scalers
RUMBLE_SCALE = 1
MOTOR_SCALE  = 1

def main():
    dll_path = os.path.abspath("FH2TriggerBridge.dll")
    trigger_dll = None
    if os.path.exists(dll_path):
        try:
            trigger_dll = ctypes.CDLL(dll_path)
            trigger_dll.SetControllerRumble.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float
            ]
            print(f"[+] Loaded trigger DLL successfully from {dll_path}")
        except Exception as e:
            print(f"[-] Failed to load DLL: {e}")
    else:
        print(f"[-] Warning: FH2TriggerBridge.dll not found at {dll_path}.")

    hk = azimuth_hook.wait_for_game()
    
    # --- CRITICAL FIX: Mute game executable's native rumble stream ---
    hk.mute_rumble(True)
    print("[+] Native game rumble muted! Only our clean, managed stream will reach the controller.")
    print("Hooked! Streaming full 4-channel telemetry (Ctrl+C to stop):")

    try:
        while hk.alive():
            lm, rm, lt, rt, n = hk.levels()
            print(f"\rmotors L {lm:4.2f} R {rm:4.2f} | triggers L2 {lt:4.2f} R2 {rt:4.2f} | calls {n:8d}", end="")

            # Priority logic: If either trigger is active (slip detected), cut the main motors
            # to give the trigger motors 100% hardware power headroom!
            if lt > 0.05 or rt > 0.05:
                final_lm = 0.0
                final_rm = 0.0
            else:
                final_lm = lm * MOTOR_SCALE
                final_rm = rm * MOTOR_SCALE

            if trigger_dll:
                trigger_dll.SetControllerRumble(
                    ctypes.c_float(final_lm),
                    ctypes.c_float(final_rm),
                    ctypes.c_float(lt * RUMBLE_SCALE),
                    ctypes.c_float(rt * RUMBLE_SCALE)
                )

            time.sleep(0.016)  # ~60 FPS update rate

    except KeyboardInterrupt:
        pass
    finally:
        if trigger_dll:
            trigger_dll.SetControllerRumble(0.0, 0.0, 0.0, 0.0)
        # Restore normal game rumble on exit
        hk.mute_rumble(False)
        hk.unhook()
        print("\n[+] Exited cleanly and restored native game settings.")

if __name__ == "__main__":
    main()