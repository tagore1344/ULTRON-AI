try:
    import pyaudio
except Exception:
    pyaudio = None

if pyaudio is None:
    print("[MIC LIST] Audio backend unavailable")
else:
    p = pyaudio.PyAudio()

    for i in range(p.get_device_count()):

        info = p.get_device_info_by_index(i)

        print(i, info['name'])