from google.cloud import speech

def test_speech_credentials():
    try:
        client = speech.SpeechClient()
        print("Credenciales válidas y API de Speech-to-Text accesible.")
    except Exception as e:
        print(f"Error al verificar credenciales: {str(e)}")

if __name__ == "__main__":
    test_speech_credentials()