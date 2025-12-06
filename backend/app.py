from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uuid
import os
import base64
import json
from typing import List, Optional
import logging
from transcribe import * 
from pymongo import MongoClient
import os
import datetime
import shutil
import logging
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import cloudinary
import cloudinary.uploader
import assemblyai as aai
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
from bson.objectid import ObjectId
from fastapi.responses import StreamingResponse
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
import re
from urllib.parse import urlparse, parse_qs, quote_plus
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict

# Suppress PyMongo debug logs
logging.getLogger("pymongo").setLevel(logging.WARNING)

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

# Check if FFmpeg exists at your specified path
ffmpeg_dir = r"C:\ffmpeg\bin"
ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")

if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
    AudioSegment.converter = ffmpeg_exe
    AudioSegment.ffmpeg = ffmpeg_exe
    AudioSegment.ffprobe = ffprobe_exe
    
    # Add to PATH for this session
    if ffmpeg_dir not in os.environ.get('PATH', ''):
        os.environ['PATH'] += os.pathsep + ffmpeg_dir
        
    logger.info(f"FFmpeg configured: {ffmpeg_exe}")
else:
    logger.error(f"FFmpeg not found at {ffmpeg_dir}")
    logger.error("Please download FFmpeg from https://github.com/BtbN/FFmpeg-Builds/releases")
    raise FileNotFoundError("FFmpeg not found")

mongo_uri ="mongodb+srv://vinitshirbhate_db_user:bfOmEp2aRbZX3UST@cluster0.mx9ptq8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    mongo_client = MongoClient(mongo_uri)
    # Select database and collection
    db = mongo_client["court_transcriptions"] 
    collection = db["transcripts"]
    
    # Test connection
    mongo_client.admin.command("ping")
    logger.info("Connected to MongoDB!")
except Exception as e:
    logger.error(f"MongoDB connection failed: {str(e)}")
    raise

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini AI configured successfully")

# Initialize SentenceTransformer model for case ranking
try:
    embedding_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    logger.info("SentenceTransformer model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {str(e)}")
    embedding_model = None

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
REPORTS_FOLDER = "reports"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# Assembly AI configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    logger.warning("ASSEMBLYAI_API_KEY not found in environment variables")
else:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

# Pydantic models
class FIRRequest(BaseModel):
    complainant_name: str
    contact_number: str
    incident_date: str
    incident_location: str
    incident_details: str
    witness_info: Optional[str] = ""
    photos: Optional[List[str]] = []

class ChatRequest(BaseModel):
    transcript_id: str
    question: str
    conversation_history: Optional[List[dict]] = []

class SummaryRequest(BaseModel):
    transcript_id: str
    summary_type: Optional[str] = "detailed"  # Options: "brief", "detailed", "key_points"

class YouTubeRequest(BaseModel):
    youtube_url: str

# Helper function to extract YouTube video ID from URL
def extract_youtube_video_id(url: str) -> str:
    """
    Extract video ID from various YouTube URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - VIDEO_ID (if just the ID is provided)
    """
    # If it's already just an ID (11 characters, alphanumeric)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    # Try to parse as URL
    try:
        parsed = urlparse(url)
        
        # Handle youtu.be short URLs
        if 'youtu.be' in parsed.netloc:
            video_id = parsed.path.lstrip('/')
            if video_id:
                return video_id.split('?')[0]
        
        # Handle youtube.com/watch?v=VIDEO_ID
        if 'youtube.com' in parsed.netloc or 'www.youtube.com' in parsed.netloc:
            if parsed.path == '/watch':
                query_params = parse_qs(parsed.query)
                if 'v' in query_params:
                    return query_params['v'][0]
            # Handle /embed/VIDEO_ID
            elif '/embed/' in parsed.path:
                video_id = parsed.path.split('/embed/')[-1]
                return video_id.split('?')[0]
        
        # Try regex as fallback
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        raise ValueError("Could not extract video ID from URL")
    except Exception as e:
        logger.error(f"Error extracting video ID: {str(e)}")
        raise ValueError(f"Invalid YouTube URL: {str(e)}")

# Helper function to extract constitution sections from transcript
def extract_constitution_sections(text: str) -> List[str]:
    """
    Extract constitution sections and articles mentioned in the transcript
    Returns a list of unique section/article references
    """
    sections = set()
    
    # Regex patterns for Indian Constitution and legal sections
    patterns = [
        # Article patterns (Constitution of India)
        r'\bArticle\s+(\d+[A-Za-z]?)\b',
        r'\bArt\.\s*(\d+[A-Za-z]?)\b',
        r'\bArt\s+(\d+[A-Za-z]?)\b',
        
        # Section patterns (IPC, CrPC, etc.)
        r'\bSection\s+(\d+[A-Za-z]?)\b',
        r'\bS\.\s*(\d+[A-Za-z]?)\b',
        r'\bSec\.\s*(\d+[A-Za-z]?)\b',
        r'\bS\.\s*(\d+[A-Za-z]?)\s+of',
        
        # IPC sections
        r'\bIPC\s+Section\s+(\d+[A-Za-z]?)\b',
        r'\bSection\s+(\d+[A-Za-z]?)\s+IPC\b',
        
        # CrPC sections
        r'\bCrPC\s+Section\s+(\d+[A-Za-z]?)\b',
        r'\bSection\s+(\d+[A-Za-z]?)\s+CrPC\b',
        
        # Constitution Articles with context
        r'\bConstitution\s+Article\s+(\d+[A-Za-z]?)\b',
        r'\bArticle\s+(\d+[A-Za-z]?)\s+of\s+the\s+Constitution\b',
    ]
    
    # Extract using regex
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            section = match.group(1) if match.groups() else match.group(0)
            # Determine if it's Article or Section based on context
            full_match = match.group(0)
            if 'article' in full_match.lower() or 'art' in full_match.lower():
                sections.add(f"Article {section}")
            elif 'section' in full_match.lower() or 's.' in full_match.lower() or 'sec' in full_match.lower():
                sections.add(f"Section {section}")
            else:
                sections.add(section)
    
    # Also use Gemini for more accurate extraction if available
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""Extract all constitution articles and legal sections mentioned in this court hearing transcript.
            
Focus on:
- Constitution of India Articles (e.g., Article 14, Article 19, Article 21)
- Indian Penal Code (IPC) Sections (e.g., Section 302, Section 420)
- Code of Criminal Procedure (CrPC) Sections
- Other relevant legal sections

Transcript excerpt (first 3000 characters):
{text[:3000]}

Return ONLY a JSON array of unique section/article references in this exact format:
["Article 14", "Article 21", "Section 302", "Section 420"]

If no sections found, return empty array: []
"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Try to extract JSON array
            try:
                if "```" in response_text:
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                
                ai_sections = json.loads(response_text)
                if isinstance(ai_sections, list):
                    sections.update(ai_sections)
            except json.JSONDecodeError:
                # Fallback: extract from text
                lines = [line.strip().strip('"').strip("'").strip('[').strip(']') 
                        for line in response_text.split('\n') if line.strip()]
                for line in lines:
                    if 'Article' in line or 'Section' in line:
                        sections.add(line.strip())
        except Exception as e:
            logger.debug(f"Gemini extraction failed, using regex only: {str(e)}")
    
    # Sort and return unique sections
    sorted_sections = sorted(list(sections), key=lambda x: (
        int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
        x
    ))
    
    logger.info(f"Extracted {len(sorted_sections)} constitution sections: {sorted_sections}")
    return sorted_sections

# Helper function to generate legal search queries from transcript
def generate_queries(text: str) -> List[str]:
    """
    Generate legal search queries from transcript text using Gemini
    """
    try:
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not available, using fallback queries")
            # Fallback: extract key phrases
            sentences = text.split('.')[:5]
            return [s.strip()[:100] for s in sentences if len(s.strip()) > 20][:3]
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Analyze this court hearing transcript and generate 3-5 specific legal search queries 
that would help find relevant case law and precedents. Focus on:
- Legal issues discussed
- Key legal concepts
- Specific legal questions raised
- Important legal terms or doctrines

Transcript excerpt (first 2000 characters):
{text[:2000]}

Return ONLY a JSON array of query strings, one per line, no additional text.
Example format:
["query 1", "query 2", "query 3"]
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Try to extract JSON array
        try:
            # Remove markdown code blocks if present
            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            queries = json.loads(response_text)
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:5]  # Limit to 5 queries
        except json.JSONDecodeError:
            # Fallback: split by lines and clean
            queries = [q.strip().strip('"').strip("'") for q in response_text.split('\n') if q.strip()]
            queries = [q for q in queries if len(q) > 10][:5]
            if queries:
                return queries
        
        # Final fallback
        return ["court hearing legal issues", "judicial precedents", "case law"]
        
    except Exception as e:
        logger.error(f"Error generating queries: {str(e)}")
        return ["court hearing legal issues", "judicial precedents", "case law"]

# Helper function to search Indian Kanoon
def search_indiankanoon(query: str) -> List[Dict]:
    """
    Search Indian Kanoon and return case results
    Returns list of dicts with: title, snippet, url
    """
    try:
        # Indian Kanoon search URL
        search_url = f"https://indiankanoon.org/search/?formInput={quote_plus(query)}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        results = []
        
        # Indian Kanoon search results structure:
        # Results are typically in <div class="result"> or <li> elements
        # Each result has an <a> tag with href pointing to /doc/{doc_id}/
        
        # Method 1: Look for result divs
        result_divs = soup.find_all('div', class_='result')
        if not result_divs:
            result_divs = soup.find_all('div', class_='search_result')
        if not result_divs:
            result_divs = soup.find_all('div', {'class': re.compile(r'result|search', re.I)})
        
        for div in result_divs[:15]:  # Limit to 15 results per query
            try:
                # Extract URL from <a> tag (most reliable)
                link_elem = div.find('a', href=True)
                if not link_elem:
                    continue
                
                url = link_elem.get('href', '')
                if not url:
                    continue
                
                # Ensure URL is absolute
                if url.startswith('/'):
                    url = f"https://indiankanoon.org{url}"
                elif not url.startswith('http'):
                    url = f"https://indiankanoon.org/{url}"
                
                # Extract title from link text or nearby heading
                title = link_elem.get_text(strip=True)
                if not title or len(title) < 5:
                    # Try to find title in heading
                    heading = div.find('h2') or div.find('h3') or div.find('h4')
                    if heading:
                        title = heading.get_text(strip=True)
                
                if not title or len(title) < 5:
                    continue
                
                # Extract snippet
                snippet = ""
                snippet_elem = div.find('div', class_='snippet') or div.find('p', class_='snippet')
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                else:
                    # Try to get any paragraph text
                    p_elems = div.find_all('p')
                    for p in p_elems:
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            snippet = text
                            break
                
                # Clean up snippet
                snippet = snippet[:500] if snippet else ""
                
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url
                })
            except Exception as e:
                logger.debug(f"Error parsing result div: {str(e)}")
                continue
        
        # Method 2: If no results, look for direct document links
        if not results:
            # Look for links to /doc/ (case documents)
            doc_links = soup.find_all('a', href=re.compile(r'/doc/\d+'))
            for link in doc_links[:15]:
                try:
                    url = link.get('href', '')
                    if not url:
                        continue
                    
                    # Make URL absolute
                    if url.startswith('/'):
                        url = f"https://indiankanoon.org{url}"
                    elif not url.startswith('http'):
                        url = f"https://indiankanoon.org/{url}"
                    
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        # Try parent element
                        parent = link.find_parent(['div', 'li', 'td'])
                        if parent:
                            title = parent.get_text(strip=True)[:200]
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # Try to get snippet from nearby elements
                    snippet = ""
                    parent = link.find_parent(['div', 'li'])
                    if parent:
                        p_elem = parent.find('p')
                        if p_elem:
                            snippet = p_elem.get_text(strip=True)[:500]
                    
                    results.append({
                        "title": title[:200],  # Limit title length
                        "snippet": snippet,
                        "url": url
                    })
                except Exception as e:
                    logger.debug(f"Error parsing doc link: {str(e)}")
                    continue
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        logger.info(f"Found {len(unique_results)} unique results for query: {query}")
        return unique_results[:10]  # Return top 10 unique results
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error searching Indian Kanoon: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error searching Indian Kanoon: {str(e)}")
        return []

# Helper function to rank cases by similarity
def rank_cases(text: str, cases: List[Dict]) -> List[Dict]:
    """
    Rank cases by semantic similarity to transcript text
    Returns top 5 cases with similarity scores
    """
    try:
        if not embedding_model or not cases:
            # Return first 5 cases if no model or no cases
            return cases[:5]
        
        # Create embeddings for transcript and cases
        transcript_embedding = embedding_model.encode(text, convert_to_numpy=True)
        
        # Create embeddings for all cases (title + snippet)
        case_texts = [f"{case.get('title', '')} {case.get('snippet', '')}" for case in cases]
        case_embeddings = embedding_model.encode(case_texts, convert_to_numpy=True)
        
        # Calculate cosine similarity
        similarities = np.dot(case_embeddings, transcript_embedding) / (
            np.linalg.norm(case_embeddings, axis=1) * np.linalg.norm(transcript_embedding)
        )
        
        # Add similarity scores to cases
        for i, case in enumerate(cases):
            case['similarity_score'] = float(similarities[i])
        
        # Sort by similarity (descending) and return top 5
        ranked_cases = sorted(cases, key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        return ranked_cases[:5]
        
    except Exception as e:
        logger.error(f"Error ranking cases: {str(e)}")
        # Return first 5 cases as fallback
        return cases[:5]

# YouTube transcript endpoint
@app.post("/transcribe-youtube/")
async def transcribe_youtube(request: YouTubeRequest):
    """
    Fetch transcript from YouTube video using YouTube Transcript API
    """
    logger.info(f"Received YouTube transcription request: {request.youtube_url}")
    
    try:
        # Extract video ID from URL
        video_id = extract_youtube_video_id(request.youtube_url)
        logger.info(f"Extracted video ID: {video_id}")
        
        # Fetch transcript from YouTube
        logger.info("Fetching transcript from YouTube...")
        ytt_api = YouTubeTranscriptApi()
        
        try:
            fetched_transcript = ytt_api.fetch(video_id)
        except TranscriptsDisabled:
            logger.error(f"Transcripts are disabled for video: {video_id}")
            raise HTTPException(
                status_code=400, 
                detail="Transcripts are disabled for this YouTube video. Please use a video with captions enabled."
            )
        except Exception as e:
            logger.error(f"Failed to fetch YouTube transcript: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch transcript from YouTube: {str(e)}"
            )
        
        # Process transcript data
        logger.debug(f"Processing {len(fetched_transcript)} transcript chunks")
        transcript_data = []
        
        for chunk in fetched_transcript:
            text = chunk.text.strip()
            start_time = chunk.start
            duration = chunk.duration
            end_time = start_time + duration
            
            if text:
                # YouTube transcripts don't have speaker labels, so we use speaker 0
                transcript_data.append((0, text, start_time, end_time))
        
        # Merge transcript segments (similar to audio transcription)
        merged_transcript = merge_speaker_text(transcript_data)
        logger.debug(f"Speaker text merged into {len(merged_transcript)} segments")
        
        # Combine full text
        full_text = " ".join([text for _, text, _, _ in merged_transcript])
        logger.info(f"Combined transcript text length: {len(full_text)} characters")
        
        # Create YouTube video URL for reference
        youtube_video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Save transcript to MongoDB
        logger.info("Saving transcript to MongoDB")
        transcript_record = {
            "original_file": f"YouTube Video: {video_id}",
            "youtube_url": youtube_video_url,
            "youtube_video_id": video_id,
            "audio_path": youtube_video_url,  # Store YouTube URL as audio_path for consistency
            "created_at": datetime.datetime.now(),
            "transcription": [
                {
                    "speaker": speaker,
                    "text": text,
                    "start_time": start,
                    "end_time": end
                }
                for speaker, text, start, end in merged_transcript
            ],
            "text": full_text,
        }
        
        logger.debug(f"MongoDB record created with {len(transcript_record['transcription'])} segments")
        
        try:
            record_id = collection.insert_one(transcript_record).inserted_id
            logger.info(f"Transcript saved to MongoDB with ID: {record_id}")
        except Exception as e:
            logger.error(f"Failed to save to MongoDB: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        logger.info("YouTube transcription process completed successfully")
        
        return JSONResponse({
            "message": "YouTube transcription completed successfully",
            "transcript_id": str(record_id),
            "transcription": full_text,
            "transcription_segments": [
                {
                    "speaker": speaker,
                    "text": text,
                    "start_time": start,
                    "end_time": end
                }
                for speaker, text, start, end in merged_transcript
            ],
            "original_file": f"YouTube Video: {video_id}",
            "youtube_url": youtube_video_url,
            "youtube_video_id": video_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube transcription failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"YouTube transcription failed: {str(e)}")

# Existing transcribe endpoint (keeping as is)
@app.post("/transcribe/")
async def transcribe_media(file: UploadFile = File(...)):
    logger.info(f"Received transcription request: file={file.filename}")
    
    # Create unique filename to avoid collisions
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    original_filename = file.filename
    file_extension = os.path.splitext(original_filename)[1].lower()
    logger.debug(f"File type: {file_extension}")
    
    # Handle different file types
    if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        logger.info(f"Processing video file: {file_extension}")
        temp_video_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}{file_extension}")
        logger.debug(f"Saving uploaded video to {temp_video_path}")
        
        with open(temp_video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.debug(f"Video file saved, size: {os.path.getsize(temp_video_path)} bytes")
            
        temp_audio_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}.mp3")
        logger.info(f"Extracting audio to {temp_audio_path}")
        
        try:
            start_time = time.time()
            ffmpeg_extract_audio(temp_video_path, temp_audio_path)
            elapsed_time = time.time() - start_time
            logger.info(f"Audio extraction completed in {elapsed_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed to extract audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to extract audio: {str(e)}")
            
    elif file_extension in ['.mp3', '.wav', '.ogg', '.flac']:
        logger.info(f"Processing audio file: {file_extension}")
        temp_audio_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}{file_extension}")
        logger.debug(f"Saving uploaded audio to {temp_audio_path}")
        
        with open(temp_audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.debug(f"Audio file saved, size: {os.path.getsize(temp_audio_path)} bytes")
    else:
        logger.error(f"Unsupported file format: {file_extension}")
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload audio or video.")
    
    # Upload to Cloudinary
    try:
        logger.info(f"Uploading audio file to Cloudinary: {temp_audio_path}")
        upload_result = cloudinary.uploader.upload(
            temp_audio_path,
            resource_type="raw",
            folder="transcriptions",
            use_filename=False,
            unique_filename=True,
            overwrite=False,
            invalidate=False
        )
        cloudinary_url = upload_result.get("secure_url") or upload_result.get("url")
        if not cloudinary_url:
            raise Exception("Cloudinary upload succeeded but no URL returned")
        logger.info(f"File uploaded to Cloudinary: {cloudinary_url}")
        
        if not cloudinary_url.startswith(('http://', 'https://')):
            raise Exception(f"Invalid Cloudinary URL format: {cloudinary_url}")
            
    except Exception as e:
        error_msg = str(e)
        if "stale request" in error_msg.lower() or "reported time" in error_msg.lower():
            logger.error(f"Cloudinary stale request error - possible system clock sync issue: {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail="Cloudinary upload failed due to timestamp validation. Please check system clock synchronization."
            )
        logger.error(f"Cloudinary upload failed: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to upload to Cloudinary: {error_msg}")
    
    # Process with Assembly AI
    logger.info("Starting Assembly AI transcription")
    start_time = time.time()
    
    try:
        transcriber = aai.Transcriber()
        
        logger.info("Submitting transcription job to Assembly AI")
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            language_code="en"
        )
        transcript = transcriber.transcribe(cloudinary_url, config=config)
        
        logger.info("Waiting for transcription results")
        max_wait_time = 600
        wait_start = time.time()
        
        while transcript.status != aai.TranscriptStatus.completed:
            if time.time() - wait_start > max_wait_time:
                raise Exception("Transcription timeout: exceeded maximum wait time")
            if transcript.status == aai.TranscriptStatus.error:
                error_msg = getattr(transcript, 'error', 'Unknown error')
                raise Exception(f"Transcription failed: {error_msg}")
            logger.debug(f"Transcription status: {transcript.status}, waiting...")
            time.sleep(3)
            transcript = transcriber.get_transcript(transcript.id)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Transcription completed in {elapsed_time:.2f} seconds")
        
        logger.debug("Processing transcription results")
        transcript_data = []
        
        if hasattr(transcript, 'words') and transcript.words:
            for word in transcript.words:
                speaker = getattr(word, 'speaker', 0)
                text = getattr(word, 'text', '')
                start_time = getattr(word, 'start', 0) / 1000.0
                end_time = getattr(word, 'end', 0) / 1000.0
                if text:
                    transcript_data.append((speaker, text, start_time, end_time))
        elif hasattr(transcript, 'utterances') and transcript.utterances:
            for utterance in transcript.utterances:
                speaker = getattr(utterance, 'speaker', 0)
                text = getattr(utterance, 'text', '')
                start_time = getattr(utterance, 'start', 0) / 1000.0
                end_time = getattr(utterance, 'end', 0) / 1000.0
                if text:
                    transcript_data.append((speaker, text, start_time, end_time))
        else:
            logger.warning("No word-level or utterance-level data available, using full text")
            full_text = getattr(transcript, 'text', '')
            if full_text:
                sentences = full_text.split('. ')
                current_time = 0.0
                for sentence in sentences:
                    if sentence.strip():
                        duration = max(2.0, len(sentence) * 0.1)
                        transcript_data.append((0, sentence.strip(), current_time, current_time + duration))
                        current_time += duration
        
        logger.info(f"Processed {len(transcript_data)} words/utterances with speaker tags")
        
        merged_transcript = merge_speaker_text(transcript_data)
        logger.debug(f"Speaker text merged into {len(merged_transcript)} segments")
        
        full_text = " ".join([text for _, text, _, _ in merged_transcript])
        logger.info(f"Combined transcript text length: {len(full_text)} characters")
        
        logger.info("Saving transcript to MongoDB")
        transcript_record = {
            "original_file": original_filename,
            "audio_path": cloudinary_url,
            "created_at": datetime.datetime.now(),
            "transcription": [
                {
                    "speaker": speaker,
                    "text": text,
                    "start_time": start,
                    "end_time": end
                }
                for speaker, text, start, end in merged_transcript
            ],
            "text": full_text,
        }
        
        logger.debug(f"MongoDB record created with {len(transcript_record['transcription'])} segments")
        
        try:
            record_id = collection.insert_one(transcript_record).inserted_id
            logger.info(f"Transcript saved to MongoDB with ID: {record_id}")
                
        except Exception as e:
            logger.error(f"Failed to save to MongoDB: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        logger.info("Cleaning up temporary files")
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.debug(f"Removed temporary file: {temp_audio_path}")
                
        if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm'] and 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            logger.debug(f"Removed temporary video file: {temp_video_path}")
        
        logger.info("Transcription process completed successfully")
        
        return JSONResponse({
            "message": "Transcription completed successfully",
            "transcript_id": str(record_id),
            "transcription": full_text,
            "transcription_segments": [
                {
                    "speaker": speaker,
                    "text": text,
                    "start_time": start,
                    "end_time": end
                }
                for speaker, text, start, end in merged_transcript
            ],
            "original_file": original_filename,
            "audio_url": cloudinary_url
        })
        
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.debug(f"Cleaned up file after error: {temp_audio_path}")
                
        if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            logger.debug(f"Cleaned up video after error: {temp_video_path}")
            
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# NEW ENDPOINT: Generate Summary using Gemini
@app.post("/summarize/")
async def summarize_transcript(request: SummaryRequest):
    """
    Generate a summary of the transcript using Gemini AI
    Also generates legal queries, searches Indian Kanoon, and ranks related cases
    """
    logger.info(f"Generating summary for transcript: {request.transcript_id}")
    
    try:
        # Fetch transcript from MongoDB
        transcript = collection.find_one({"_id": ObjectId(request.transcript_id)})
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Get text from transcript - try multiple sources
        full_text = transcript.get("text", "")
        
        # If text field is empty, try to reconstruct from transcription segments
        if not full_text or not full_text.strip():
            transcription_segments = transcript.get("transcription", [])
            if transcription_segments:
                full_text = " ".join([
                    segment.get("text", "") 
                    for segment in transcription_segments 
                    if segment.get("text", "").strip()
                ])
        
        if not full_text or not full_text.strip():
            raise HTTPException(
                status_code=400, 
                detail="Transcript has no text content. Please ensure the transcript was processed correctly."
            )
        
        # Prepare prompt based on summary type
        prompts = {
            "brief": f"""Provide a brief 2-3 sentence summary of this court hearing transcript:

{full_text}

Summary:""",
            "detailed": f"""Analyze this court hearing transcript and provide a detailed summary including:
1. Main topics discussed
2. Key arguments from each speaker
3. Important decisions or outcomes
4. Action items or next steps

Transcript:
{full_text}

Detailed Summary:""",
            "key_points": f"""Extract the key points from this court hearing transcript in bullet point format:

{full_text}

Key Points:"""
        }
        
        prompt = prompts.get(request.summary_type, prompts["detailed"])
        
        # Generate summary using Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        summary_text = response.text
        
        # Generate legal search queries
        logger.info("Generating legal search queries...")
        queries = generate_queries(full_text)
        logger.info(f"Generated {len(queries)} queries: {queries}")
        
        # Search Indian Kanoon for each query
        all_cases = []
        for query in queries:
            logger.info(f"Searching Indian Kanoon for: {query}")
            cases = search_indiankanoon(query)
            all_cases.extend(cases)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_cases = []
        for case in all_cases:
            url = case.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_cases.append(case)
        
        # Rank cases by similarity
        logger.info(f"Ranking {len(unique_cases)} unique cases...")
        ranked_cases = rank_cases(full_text, unique_cases)
        
        # Save summary and related cases to MongoDB
        collection.update_one(
            {"_id": ObjectId(request.transcript_id)},
            {
                "$set": {
                    f"summary_{request.summary_type}": summary_text,
                    f"summary_{request.summary_type}_generated_at": datetime.datetime.now(),
                    "related_cases": ranked_cases,
                    "legal_queries_used": queries
                }
            }
        )
        
        logger.info(f"Summary generated successfully for transcript: {request.transcript_id}")
        logger.info(f"Found {len(ranked_cases)} related cases")
        
        return JSONResponse({
            "transcript_id": request.transcript_id,
            "summary_type": request.summary_type,
            "summary": summary_text,
            "related_cases": ranked_cases,
            "legal_queries_used": queries,
            "generated_at": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

# NEW ENDPOINT: Chat with Transcript using Gemini
@app.post("/chat/")
async def chat_with_transcript(request: ChatRequest):
    """
    Ask questions about a specific transcript using Gemini AI chatbot
    Includes related case law in context if available
    """
    logger.info(f"Chat request for transcript: {request.transcript_id}")
    
    try:
        # Fetch transcript from MongoDB
        transcript = collection.find_one({"_id": ObjectId(request.transcript_id)})
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Get text from transcript - try multiple sources
        full_text = transcript.get("text", "")
        
        # If text field is empty, try to reconstruct from transcription segments
        if not full_text or not full_text.strip():
            transcription_segments = transcript.get("transcription", [])
            if transcription_segments:
                full_text = " ".join([
                    segment.get("text", "") 
                    for segment in transcription_segments 
                    if segment.get("text", "").strip()
                ])
        
        if not full_text or not full_text.strip():
            raise HTTPException(
                status_code=400, 
                detail="Transcript has no text content. Please ensure the transcript was processed correctly."
            )
        
        # Get related cases and queries if available
        related_cases = transcript.get("related_cases", [])
        queries_used = transcript.get("legal_queries_used", [])
        
        # Build conversation context
        conversation_context = f"""You are an AI assistant helping analyze a court hearing transcript. 

================ TRANSCRIPT ================
{full_text}

"""
        
        # Add related case law if available
        if related_cases:
            cases_text = json.dumps(related_cases, indent=2)
            conversation_context += f"""
================ RELATED CASE LAW ================
{cases_text}

"""
        
        # Add search queries if available
        if queries_used:
            queries_text = "\n".join([f"- {q}" for q in queries_used])
            conversation_context += f"""
================ SEARCH QUERIES USED ================
{queries_text}

"""
        
        conversation_context += """
Instructions:
- When asked about past judgments or precedents, ALWAYS refer to related_cases if available.
- Never answer "no case law available" if related_cases list is not empty.
- Base your answers on the transcript content provided above.
- When referencing case law, mention the case title and provide the URL if available.
- Provide relevant quotes from the transcript when applicable.
"""
        
        # Build chat history for context
        chat_history = []
        for msg in request.conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role and content:
                chat_history.append({"role": role, "parts": [content]})
        
        # Add current question
        chat_history.append({"role": "user", "parts": [request.question]})
        
        # Generate response using Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        chat = model.start_chat(history=[])
        
        # Send context first
        chat.send_message(conversation_context)
        
        # Then send the actual question
        response = chat.send_message(request.question)
        
        answer = response.text
        
        logger.info(f"Chat response generated for transcript: {request.transcript_id}")
        
        return JSONResponse({
            "transcript_id": request.transcript_id,
            "question": request.question,
            "answer": answer,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

# Existing endpoints (keeping as is)
@app.get("/download/{filename:path}")
async def download_file(filename: str):
    logger.info(f"File download requested: {filename}")
    
    if not os.path.exists(filename):
        logger.error(f"File not found: {filename}")
        raise HTTPException(status_code=404, detail="File not found")
    
    actual_filename = os.path.basename(filename)
    return FileResponse(path=filename, filename=actual_filename)

@app.get("/transcripts/")
async def list_transcripts():
    logger.info("Listing all transcripts")
    try:
        transcripts = list(collection.find({}))
        
        logger.debug(f"Found {len(transcripts)} transcripts")
        
        for transcript in transcripts:
            transcript["_id"] = str(transcript["_id"])
            if "created_at" in transcript:
                transcript["created_at"] = transcript["created_at"].isoformat()
                
        return transcripts
    except Exception as e:
        logger.error(f"Error retrieving transcripts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/transcript/{transcript_id}")
async def get_transcript(transcript_id: str):
    logger.info(f"Retrieving transcript: {transcript_id}")
    
    try:
        transcript = collection.find_one({"_id": ObjectId(transcript_id)})
        if not transcript:
            logger.error(f"Transcript not found: {transcript_id}")
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        logger.debug(f"Transcript found: {transcript_id}")
        
        # Ensure text field exists - reconstruct from segments if missing
        full_text = transcript.get("text", "")
        if not full_text or not full_text.strip():
            transcription_segments = transcript.get("transcription", [])
            if transcription_segments:
                full_text = " ".join([
                    segment.get("text", "") 
                    for segment in transcription_segments 
                    if segment.get("text", "").strip()
                ])
                # Update MongoDB with reconstructed text
                if full_text:
                    collection.update_one(
                        {"_id": ObjectId(transcript_id)},
                        {"$set": {"text": full_text}}
                    )
                    transcript["text"] = full_text
        
        # Extract constitution sections if not already stored
        if full_text and "constitution_sections" not in transcript:
            logger.info("Extracting constitution sections from transcript")
            sections = extract_constitution_sections(full_text)
            # Update MongoDB with extracted sections
            collection.update_one(
                {"_id": ObjectId(transcript_id)},
                {"$set": {"constitution_sections": sections}}
            )
            transcript["constitution_sections"] = sections
        elif "constitution_sections" in transcript:
            # Use existing sections
            transcript["constitution_sections"] = transcript.get("constitution_sections", [])
        
        transcript["_id"] = str(transcript["_id"])
        if "created_at" in transcript:
            transcript["created_at"] = transcript["created_at"].isoformat()
        
        return transcript
    except Exception as e:
        logger.error(f"Error retrieving transcript {transcript_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/generate-pdf/{transcript_id}")
async def generate_pdf(transcript_id: str):
    logger.info(f"Generating PDF for transcript: {transcript_id}")

    transcript = collection.find_one({"_id": ObjectId(transcript_id)})
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Heading", fontSize=16, leading=20, spaceAfter=10))
    styles.add(ParagraphStyle(name="SubHeading", fontSize=12, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="Monospace", fontName="Courier", fontSize=9))
    styles.add(ParagraphStyle(name="WrappedText", fontSize=10, leading=14, wordWrap="CJK"))

    story = []

    story.append(Paragraph("Transcription Report", styles["Heading"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>File:</b> {transcript.get('original_file', 'Unknown')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Audio URL:</b> {transcript.get('audio_path', '')}", styles["Normal"]))

    if "created_at" in transcript:
        created_at = transcript["created_at"]
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"<b>Created:</b> {created_at}", styles["Normal"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("Full Transcription:", styles["SubHeading"]))
    story.append(Paragraph(transcript.get("text", ""), styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Transcription Segments:", styles["SubHeading"]))
    segments = transcript.get("transcription", [])

    if segments:
        table_data = [["Speaker", "Start", "End", "Text"]]
        for seg in segments:
            table_data.append([
                str(seg.get("speaker", "")),
                f"{seg.get('start_time', 0):.2f}",
                f"{seg.get('end_time', 0):.2f}",
                Paragraph(seg.get("text", ""), styles["WrappedText"])
            ])

        t = Table(table_data, colWidths=[50, 60, 60, 330])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No segments available.", styles["Normal"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("Full Text Preview:", styles["SubHeading"]))
    story.append(Paragraph(transcript.get("text", ""), styles["Monospace"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Generated by Court Hearing Transcription Backend", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=transcript_{transcript_id}.pdf"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)