// dllmain.cpp : GameInput bridge exposing SetControllerRumble(leftMotor, rightMotor, leftTrigger, rightTrigger)
#include "pch.h"
#include <windows.h>
#include <GameInput.h>
#include <cmath>
#include <algorithm>

static IGameInput* g_gameInput = nullptr;
static HMODULE g_gameInputLib = nullptr;

typedef HRESULT(STDAPICALLTYPE* PFN_GAMEINPUT_CREATE)(IGameInput**);

static float Clamp01(float v) { return (std::max)(0.0f, (std::min)(1.0f, v)); }

static bool AllZero(const float v[4]) {
    return v[0] == 0.0f && v[1] == 0.0f && v[2] == 0.0f && v[3] == 0.0f;
}

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

        // Priority Override: If the right trigger is active, ignore main motors completely.
        // This is the only place that decision is made; callers just pass the values through.
        float finalLeftMotor = leftMotor;
        float finalRightMotor = rightMotor;

        if (rightTrigger > 0.05f) {
            finalLeftMotor = 0.0f;
            finalRightMotor = 0.0f;
        }

        const float target[4] = {
            Clamp01(finalLeftMotor), Clamp01(finalRightMotor),
            Clamp01(leftTrigger),    Clamp01(rightTrigger)
        };

        // What the controller was last successfully told. Only updated after a real send, so a
        // failed or skipped read can never make us think the controller has values it doesn't.
        static float sent[4] = {};
        static bool haveSent = false;
        static const void* sentDevice = nullptr;

        IGameInputReading* reading = nullptr;
        if (SUCCEEDED(g_gameInput->GetCurrentReading(GameInputKindGamepad, nullptr, &reading))) {
            IGameInputDevice* device = nullptr;
            reading->GetDevice(&device);
            if (device != nullptr) {
                // Hysteresis filter: Skip hardware calls if values haven't changed by at least 1%
                // on the same controller we last talked to.
                bool unchanged = haveSent && device == sentDevice;
                for (int i = 0; unchanged && i < 4; ++i) {
                    unchanged = std::abs(target[i] - sent[i]) < 0.01f;
                }
                // ...but always let an exact "all off" through, so a faint rumble can't get stuck.
                if (unchanged && AllZero(target) && !AllZero(sent)) {
                    unchanged = false;
                }

                if (!unchanged) {
                    GameInputRumbleParams params{};
                    params.lowFrequency = target[0];
                    params.highFrequency = target[1];
                    params.leftTrigger = target[2];
                    params.rightTrigger = target[3];

                    device->SetRumbleState(&params);

                    std::copy(target, target + 4, sent);
                    haveSent = true;
                    sentDevice = device;
                }
                device->Release();
            }
            else {
                haveSent = false;
            }
            reading->Release();
        }
        else {
            // Controller unplugged or unavailable: it will have lost our rumble state,
            // so make sure the next successful read sends everything again.
            haveSent = false;
        }
    }
}
