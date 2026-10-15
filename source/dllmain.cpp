//// dllmain.cpp : Defines the entry point for the DLL application.
//#include "pch.h"
//#include <windows.h>
//#include <winrt/Windows.Foundation.h>
//#include <winrt/Windows.Foundation.Collections.h>
//#include <winrt/Windows.Gaming.Input.h>
//
//// Automatically link the Windows Runtime library required for WinRT APIs
//#pragma comment(lib, "windowsapp")
//
//using namespace winrt::Windows::Gaming::Input;
//
//extern "C" {
//    __declspec(dllexport) void SetTriggerRumble(float leftTrigger, float rightTrigger) {
//        try {
//            auto gamepads = Gamepad::Gamepads();
//            if (gamepads.Size() > 0) {
//                auto pad = gamepads.GetAt(0);
//                GamepadVibration vibration{};
//                vibration.LeftTrigger = max(0.0f, min(1.0f, leftTrigger));
//                vibration.RightTrigger = max(0.0f, min(1.0f, rightTrigger));
//                vibration.LeftMotor = 0.0f;
//                vibration.RightMotor = 0.0f;
//                pad.Vibration(vibration);
//            }
//        }
//        catch (...) {
//            // Fail silently if controller is disconnected
//        }
//    }
//}

//// dllmain.cpp : Defines the entry point for the DLL application using dynamic GameInput loading
//#include "pch.h"
//#include <windows.h>
//#include <GameInput.h>
//
//static IGameInput* g_gameInput = nullptr;
//static HMODULE g_gameInputLib = nullptr;
//
//typedef HRESULT(STDAPICALLTYPE* PFN_GAMEINPUT_CREATE)(IGameInput**);
//
//struct GameInputInitializer {
//    GameInputInitializer() {
//        g_gameInputLib = LoadLibraryW(L"gameinput.dll");
//        if (g_gameInputLib) {
//            auto createFn = (PFN_GAMEINPUT_CREATE)GetProcAddress(g_gameInputLib, "GameInputCreate");
//            if (createFn) {
//                createFn(&g_gameInput);
//            }
//        }
//    }
//    ~GameInputInitializer() {
//        if (g_gameInput) {
//            g_gameInput->Release();
//            g_gameInput = nullptr;
//        }
//        if (g_gameInputLib) {
//            FreeLibrary(g_gameInputLib);
//            g_gameInputLib = nullptr;
//        }
//    }
//};
//
//extern "C" {
//    __declspec(dllexport) void SetTriggerRumble(float leftTrigger, float rightTrigger) {
//        static GameInputInitializer initializer;
//        if (!g_gameInput) return;
//
//        IGameInputReading* reading = nullptr;
//        if (SUCCEEDED(g_gameInput->GetCurrentReading(GameInputKindGamepad, nullptr, &reading))) {
//            IGameInputDevice* device = nullptr;
//            reading->GetDevice(&device); // GetDevice returns void, check pointer instead
//            if (device != nullptr) {
//                GameInputRumbleParams params{};
//                params.lowFrequency = 0.0f;
//                params.highFrequency = 0.0f;
//                params.leftTrigger = max(0.0f, min(1.0f, leftTrigger));
//                params.rightTrigger = max(0.0f, min(1.0f, rightTrigger));
//
//                device->SetRumbleState(&params);
//                device->Release();
//            }
//            reading->Release();
//        }
//    }
//}

////////////////

//// dllmain.cpp : Unified GameInput bridge supporting both main motors and triggers
//#include "pch.h"
//#include <windows.h>
//#include <GameInput.h>
//#include <cstdio>
//
//static IGameInput* g_gameInput = nullptr;
//static HMODULE g_gameInputLib = nullptr;
//
//typedef HRESULT(STDAPICALLTYPE* PFN_GAMEINPUT_CREATE)(IGameInput**);
//
//struct GameInputInitializer {
//    GameInputInitializer() {
//        g_gameInputLib = LoadLibraryW(L"gameinput.dll");
//        if (g_gameInputLib) {
//            auto createFn = (PFN_GAMEINPUT_CREATE)GetProcAddress(g_gameInputLib, "GameInputCreate");
//            if (createFn) {
//                createFn(&g_gameInput);
//            }
//        }
//    }
//    ~GameInputInitializer() {
//        if (g_gameInput) {
//            g_gameInput->Release();
//            g_gameInput = nullptr;
//        }
//        if (g_gameInputLib) {
//            FreeLibrary(g_gameInputLib);
//            g_gameInputLib = nullptr;
//        }
//    }
//};
//
//extern "C" {
//    // Accepts all 4 telemetry channels from Python
//    __declspec(dllexport) void SetControllerRumble(float leftMotor, float rightMotor, float leftTrigger, float rightTrigger) {
//        static GameInputInitializer initializer;
//        if (!g_gameInput) return;
//
//        IGameInputReading* reading = nullptr;
//        if (SUCCEEDED(g_gameInput->GetCurrentReading(GameInputKindGamepad, nullptr, &reading))) {
//            IGameInputDevice* device = nullptr;
//            reading->GetDevice(&device);
//            if (device != nullptr) {
//                GameInputRumbleParams params{};
//                params.lowFrequency = max(0.0f, min(1.0f, leftMotor));
//                params.highFrequency = max(0.0f, min(1.0f, rightMotor));
//                params.leftTrigger = max(0.0f, min(1.0f, leftTrigger));
//                params.rightTrigger = max(0.0f, min(1.0f, rightTrigger));
//
//                device->SetRumbleState(&params);
//                device->Release();
//            }
//            reading->Release();
//        }
//    }
//}

//////////////////////////

//// dllmain.cpp : Reroutes motor haptics directly into the impulse triggers for crisp tire feedback
//#include "pch.h"
//#include <windows.h>
//#include <GameInput.h>
//
//static IGameInput* g_gameInput = nullptr;
//static HMODULE g_gameInputLib = nullptr;
//
//typedef HRESULT(STDAPICALLTYPE* PFN_GAMEINPUT_CREATE)(IGameInput**);
//
//struct GameInputInitializer {
//    GameInputInitializer() {
//        g_gameInputLib = LoadLibraryW(L"gameinput.dll");
//        if (g_gameInputLib) {
//            auto createFn = (PFN_GAMEINPUT_CREATE)GetProcAddress(g_gameInputLib, "GameInputCreate");
//            if (createFn) {
//                createFn(&g_gameInput);
//            }
//        }
//    }
//    ~GameInputInitializer() {
//        if (g_gameInput) {
//            g_gameInput->Release();
//            g_gameInput = nullptr;
//        }
//        if (g_gameInputLib) {
//            FreeLibrary(g_gameInputLib);
//            g_gameInputLib = nullptr;
//        }
//    }
//};
//
//extern "C" {
//    __declspec(dllexport) void SetControllerRumble(float leftMotor, float rightMotor, float leftTrigger, float rightTrigger) {
//        static GameInputInitializer initializer;
//        if (!g_gameInput) return;
//
//        IGameInputReading* reading = nullptr;
//        if (SUCCEEDED(g_gameInput->GetCurrentReading(GameInputKindGamepad, nullptr, &reading))) {
//            IGameInputDevice* device = nullptr;
//            reading->GetDevice(&device);
//            if (device != nullptr) {
//                GameInputRumbleParams params{};
//                
//                // Route main hand-grip rumbles (collisions, surface bumpiness, engine RPM)
//                params.lowFrequency  = max(0.0f, min(1.0f, leftMotor));
//                params.highFrequency = max(0.0f, min(1.0f, rightMotor));
//                
//                // Route trigger rumbles strictly to braking/accelerating slip with zero motor bleed
//                params.leftTrigger   = max(0.0f, min(1.0f, leftTrigger));
//                params.rightTrigger  = max(0.0f, min(1.0f, rightTrigger));
//                
//                device->SetRumbleState(&params);
//                device->Release();
//            }
//            reading->Release();
//        }
//    }
//}

//////////////////////////////////////////////////////

#include "pch.h"
#include <windows.h>
#include <GameInput.h>
#include <cmath>
#include <algorithm>

static IGameInput* g_gameInput = nullptr;
static HMODULE g_gameInputLib = nullptr;

typedef HRESULT(STDAPICALLTYPE* PFN_GAMEINPUT_CREATE)(IGameInput**);

struct GameInputInitializer {
    GameInputInitializer() {
        g_gameInputLib = LoadLibraryW(L"gameinput.dll");
        if (g_gameInputLib) {
            auto createFn = (PFN_GAMEINPUT_CREATE)GetProcAddress(g_gameInputLib, "GameInputCreate");
            if (createFn) {
                createFn(&g_gameInput);
            }
        }
    }
    ~GameInputInitializer() {
        if (g_gameInput) { g_gameInput->Release(); g_gameInput = nullptr; }
        if (g_gameInputLib) { FreeLibrary(g_gameInputLib); g_gameInputLib = nullptr; }
    }
};

extern "C" {
    __declspec(dllexport) void SetControllerRumble(float leftMotor, float rightMotor, float leftTrigger, float rightTrigger) {
        static GameInputInitializer initializer;
        if (!g_gameInput) return;

        // Hysteresis filter: Skip hardware calls if values haven't changed by at least 1%
        static float lastL = -1.f, lastR = -1.f, lastLT = -1.f, lastRT = -1.f;
        if (std::abs(leftMotor - lastL) < 0.01f &&
            std::abs(rightMotor - lastR) < 0.01f &&
            std::abs(leftTrigger - lastLT) < 0.01f &&
            std::abs(rightTrigger - lastRT) < 0.01f) {
            return;
        }
        lastL = leftMotor; lastR = rightMotor; lastLT = leftTrigger; lastRT = rightTrigger;

        IGameInputReading* reading = nullptr;
        if (SUCCEEDED(g_gameInput->GetCurrentReading(GameInputKindGamepad, nullptr, &reading))) {
            IGameInputDevice* device = nullptr;
            reading->GetDevice(&device);
            if (device != nullptr) {
                GameInputRumbleParams params{};

                // Priority Override: If the right trigger is active, ignore main motors completely
                float finalLeftMotor = leftMotor;
                float finalRightMotor = rightMotor;

                if (rightTrigger > 0.05f) {
                    finalLeftMotor = 0.0f;
                    finalRightMotor = 0.0f;
                }

                params.lowFrequency = max(0.0f, min(1.0f, finalLeftMotor));
                params.highFrequency = max(0.0f, min(1.0f, finalRightMotor));
                params.leftTrigger = max(0.0f, min(1.0f, leftTrigger));
                params.rightTrigger = max(0.0f, min(1.0f, rightTrigger));

                device->SetRumbleState(&params);
                device->Release();
            }
            reading->Release();
        }
    }
}
