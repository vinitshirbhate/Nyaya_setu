import os
import datetime
import shutil
import logging
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
# GCP imports removed - using Cloudinary and Assembly AI instead
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio
from pydub import AudioSegment
import os

# Method 1: Set all FFmpeg executables
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffmpeg = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

# Method 2: Alternative - Add to PATH programmatically
# os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Method 3: Verify the files exist (optional debugging)
import logging
logger = logging.getLogger(__name__)

ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
if os.path.exists(ffmpeg_path):
    logger.info("FFmpeg found at specified path")
else:
    logger.warning(f"FFmpeg not found at {ffmpeg_path}")
    logger.info("Please install FFmpeg or update the path")

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Starting Court Transcription API")

# Helper functions
def seconds_to_hms(seconds):
    logger.debug(f"Converting {seconds} seconds to HH:MM:SS format")
    return str(datetime.timedelta(seconds=int(seconds)))

def merge_speaker_text(transcript_data):
    logger.debug(f"Merging speaker text from {len(transcript_data)} word entries")
    merged_transcript = []
    current_speaker, current_sentence, start_time, end_time = None, [], None, None
    
    for speaker, word, word_start, word_end in transcript_data:
        if speaker == current_speaker:
            current_sentence.append(word)
            end_time = word_end
        else:
            if current_sentence:
                merged_transcript.append((current_speaker, " ".join(current_sentence), start_time, end_time))
                logger.debug(f"Added merged sentence for Speaker {current_speaker}: {len(current_sentence)} words")
            current_speaker = speaker
            current_sentence = [word]
            start_time, end_time = word_start, word_end
    
    if current_sentence:
        merged_transcript.append((current_speaker, " ".join(current_sentence), start_time, end_time))
        logger.debug(f"Added final merged sentence for Speaker {current_speaker}: {len(current_sentence)} words")
    
    logger.info(f"Created {len(merged_transcript)} merged transcript entries")
    return merged_transcript

def generate_transcript_pdf(merged_transcript, output_pdf, case_name, hearing_date):
    logger.info(f"Generating PDF transcript at {output_pdf}")
    try:
        c = canvas.Canvas(output_pdf, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(150, 750, "Court Hearing Transcript")
        c.setFont("Helvetica", 12)
        c.drawString(100, 720, f"Case Name: {case_name}")
        c.drawString(100, 700, f"Hearing Date: {hearing_date}")
        c.line(50, 690, 550, 690)
        c.showPage()
        
        c.setFont("Helvetica", 12)
        y_position = 750
        
        page_count = 1
        entry_count = 0
        
        for speaker, sentence, start, end in merged_transcript:
            timestamp = seconds_to_hms(start)
            text = f"[{timestamp}] Speaker {speaker}: {sentence}"
            lines = simpleSplit(text, "Helvetica", 12, 480)
            for line in lines:
                c.drawString(50, y_position, line)
                y_position -= 20
                if y_position < 50:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y_position = 750
                    page_count += 1
                    logger.debug(f"Added new page in PDF: {page_count}")
            entry_count += 1
            
            if entry_count % 50 == 0:
                logger.debug(f"Processed {entry_count}/{len(merged_transcript)} transcript entries")
        
        c.save()
        logger.info(f"PDF generated successfully with {page_count} pages")
        return output_pdf
    except Exception as e:
        logger.error(f"Failed to generate PDF: {str(e)}")
        raise



