# TAG Mobile

Siri-style mobile client for TAG AI.

## What is included

- TAG voice-first home screen with animated orb.
- Device speech recognition using `speech_to_text`.
- Device text-to-speech using `flutter_tts`.
- `Hey TAG`, `OK TAG`, and `Hi TAG` foreground hands-free mode.
- Secure paired gateway connection using the existing TAG REST/WebSocket stack.
- Existing chat, control, review, and pairing screens remain available.
- Conversation replies are spoken locally on the phone.

## Android / iOS project setup

The repository contains the Flutter `lib/` source but not generated native platform folders. From this directory run:

```powershell
flutter create --platforms=android,ios .
flutter pub get
flutter run
```

For microphone speech recognition, configure the native permissions required by `speech_to_text`.

### Android

In `android/app/src/main/AndroidManifest.xml` add under `<manifest>`:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.BLUETOOTH" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<queries>
    <intent>
        <action android:name="android.speech.RecognitionService" />
    </intent>
</queries>
```

### iOS

In `ios/Runner/Info.plist` add:

```xml
<key>NSSpeechRecognitionUsageDescription</key>
<string>TAG uses speech recognition to understand your voice commands.</string>
<key>NSMicrophoneUsageDescription</key>
<string>TAG uses the microphone for voice conversations.</string>
```

## Connect TAG

1. Start the TAG desktop/gateway.
2. Get the temporary pairing PIN from the TAG gateway.
3. Open TAG Mobile.
4. Enter the gateway LAN address and pairing PIN.
5. Pair the phone.
6. The TAG voice HUD becomes the default screen.

## Voice modes

**Tap mode:** tap the central TAG orb, speak, and release/finish naturally. TAG sends the recognized phrase to the paired gateway, receives the AI response, displays it, and speaks it.

**Hands-free mode:** enable `HANDS-FREE`. TAG stays in a foreground listening loop and only submits a phrase after hearing a TAG wake phrase such as `Hey TAG`. After TAG answers, the loop returns to wake-word listening.

The current implementation intentionally keeps hands-free recognition in the foreground. A true OS-level background assistant requires native Android foreground-service integration and platform-specific restrictions; that is a separate native layer from the Flutter voice UI.
