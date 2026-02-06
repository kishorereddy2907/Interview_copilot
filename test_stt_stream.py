from speech_listener import listen_stream

print("🎤 Speak your interview question...")
for text in listen_stream():
    print("LIVE:", text)

print("✅ Done")
