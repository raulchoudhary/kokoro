import os
import io
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn


# --- Actual Kokoro TTS import ---
# Import the necessary class from the kokoro library
from kokoro import KPipeline
# You might also need soundfile if you need to explicitly write WAV,
# but KPipeline might return bytes directly or in a format easily usable.
# import soundfile as sf
# --- End of Kokoro TTS import ---


# --- Actual Kokoro TTS initialization and synthesis ---
# Define a variable to hold your loaded Kokoro model/engine
kokoro_pipeline: KPipeline | None = None # Use type hinting for clarity

# Define a function to load the Kokoro model
# This function will run ONCE when the FastAPI app starts up
async def load_kokoro_model():
    global kokoro_pipeline
    print("Loading Kokoro TTS pipeline...")
    try:
        # --- Replace with the actual code to load your Kokoro pipeline ---
        # Based on the documentation, you initialize KPipeline with a language code.
        # You might want to make the language code configurable via environment variable.
        lang_code = os.environ.get("KOKORO_LANG_CODE", "a") # Default to American English 'a'
        device = "cuda" if torch.cuda.is_available() and os.environ.get("USE_GPU", "true").lower() == "true" else "cpu"
        print(f"Using device: {device}")

        # Initialize the KPipeline
        # The KPipeline internally handles loading models and moving them to the device
        kokoro_pipeline = KPipeline(lang_code=lang_code, device=device)

        print(f"Kokoro TTS pipeline loaded successfully for language code: {lang_code}.")
    except Exception as e:
        print(f"Error loading Kokoro pipeline: {e}")
        # If the model fails to load, the service is unusable.
        # Raising the exception will stop the FastAPI app from starting.
        raise e
# --- End of Kokoro TTS section ---


# Define the FastAPI application
app = FastAPI()

# Register the startup event to load the Kokoro model
@app.on_event("startup")
async def startup_event():
    await load_kokoro_model()

# Define a request body model for the API call
class SynthesisRequest(BaseModel):
    text: str
    # The Kokoro documentation uses 'voice' instead of 'speaker_id'
    # Map speaker_id from your API to Kokoro's 'voice' parameter
    voice: str = "af_heart" # Use a default voice from Kokoro examples
    # Add other parameters your Kokoro synthesis function might need (e.g., speed, split_pattern)
    speed: float = 1.0
    split_pattern: str = r'\n+' # Example split pattern

# Define the API endpoint for synthesis
@app.post("/synthesize")
async def synthesize(request: SynthesisRequest):
    # Use kokoro_pipeline instead of kokoro_engine
    if kokoro_pipeline is None:
        # This case should ideally not happen if startup was successful,
        # but it's good practice to check.
        raise HTTPException(status_code=503, detail="Kokoro TTS pipeline is not loaded yet.")

    print(f"Received request to synthesize text: {request.text[:50]}... for voice: {request.voice}")

    try:
        # --- Actual Kokoro synthesis call ---
        # Call the loaded pipeline object with the text and voice
        # The documentation shows pipeline returning a generator of (gs, ps, audio) tuples
        generator = kokoro_pipeline(
            request.text,
            voice=request.voice,
            speed=request.speed,
            split_pattern=request.split_pattern # Pass other parameters
        )

        # Kokoro returns audio segments. We need to concatenate them or return the first one.
        # For simplicity, let's collect all audio segments from the generator
        # and concatenate them.
        full_audio_data = b""
        sample_rate = 24000 # Based on Kokoro examples

        for i, (gs, ps, audio_segment) in enumerate(generator):
             # Assuming 'audio_segment' is a numpy array or similar that can be converted to bytes
             # KPipeline documentation implies 'audio' in the tuple is a numpy array
             # We need to convert the numpy array segment to bytes (e.g., WAV format)
             # This requires a library like soundfile or scipy.io.wavfile
             # If soundfile is installed (which you did via pip install soundfile), you can use it:
             import soundfile as sf
             from io import BytesIO

             buffer = BytesIO()
             sf.write(buffer, audio_segment, sample_rate, format='WAV')
             full_audio_data += buffer.getvalue()

        # --- End of Kokoro synthesis call ---

        # Return the concatenated audio data as a streaming response
        return StreamingResponse(io.BytesIO(full_audio_data), media_type="audio/wav")

    except Exception as e:
        print(f"Error during synthesis: {e}")
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")

# Optional: Add a root endpoint for health check
@app.get("/")
async def read_root():
    return {"status": "Kokoro TTS API is running", "pipeline_loaded": kokoro_pipeline is not None}
