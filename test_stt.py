from speech_listener import listen_once_streamed

print("🎤 Speak now...")
text = listen_once_streamed()
print("You said:", text)
