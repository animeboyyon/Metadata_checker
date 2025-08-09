from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, CommandHandler, filters
import os
import re
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import httpx
import uuid

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram File Metadata Analyzer Bot")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Telegram Bot
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "telegram_bot_webhook_secret_2025")

# Initialize bot only if token is available
bot = None
if BOT_TOKEN:
    try:
        bot = Bot(token=BOT_TOKEN)
        logger.info("Telegram bot initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
else:
    logger.warning("No Telegram bot token provided")

# MongoDB connection
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    app.mongodb = app.mongodb_client.telegram_bot

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

# Pydantic models
class AnalysisResult(BaseModel):
    filename: str
    file_type: str
    quality: Optional[str] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    audio_codec: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    format_details: Dict[str, Any] = {}

class FileMetadata(BaseModel):
    file_id: str
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    file_unique_id: str

# Comprehensive file analysis patterns
class FileAnalyzer:
    def __init__(self):
        # Video quality indicators
        self.quality_patterns = {
            'CAM': r'\b(cam|camrip|cam-rip)\b',
            'CAMRip': r'\b(camrip|cam-rip)\b',
            'TS': r'\b(ts|telesync|tele-sync)\b',
            'TC': r'\b(tc|telecine|tele-cine)\b',
            'WP': r'\b(wp|workprint|work-print)\b',
            'DVDScr': r'\b(dvdscr|dvd-scr|dvdscreener)\b',
            'R5': r'\br5\b',
            'DVDRip': r'\b(dvdrip|dvd-rip)\b',
            'BDRip': r'\b(bdrip|bd-rip|bluray-rip)\b',
            'BRRip': r'\b(brrip|br-rip)\b',
            'HDRip': r'\b(hdrip|hd-rip)\b',
            'HDTV': r'\b(hdtv|hd-tv)\b',
            'PDTV': r'\b(pdtv|pd-tv)\b',
            'DSRip': r'\b(dsrip|ds-rip)\b',
            'WEB-DL': r'\b(web-dl|webdl|web\.dl)\b',
            'WEBRip': r'\b(webrip|web-rip|web\.rip)\b',
            'WEB': r'\bweb(?!rip|dl)\b',
            'BluRay': r'\b(bluray|blu-ray|bdrip|bdremux)\b',
            'UHD': r'\b(uhd|ultra\.hd|4k\.uhd)\b',
            'REMUX': r'\b(remux|re-mux)\b',
            'REPACK': r'\b(repack|re-pack)\b',
            'PROPER': r'\b(proper)\b',
            'REAL': r'\b(real)\b',
            'RETAIL': r'\b(retail)\b',
            'UNCUT': r'\b(uncut)\b',
            'EXTENDED': r'\b(extended|ext)\b',
            'REMASTERED': r'\b(remastered|remaster)\b'
        }
        
        # Resolution patterns
        self.resolution_patterns = {
            '4K': r'\b(4k|2160p|uhd|ultra\.hd)\b',
            '2K': r'\b(2k|1440p)\b',
            '1080p': r'\b(1080p|1080i|full\.hd|fullhd)\b',
            '720p': r'\b(720p|720i|hd)\b',
            '576p': r'\b(576p|576i)\b',
            '480p': r'\b(480p|480i|sd)\b',
            '360p': r'\b(360p)\b',
            '240p': r'\b(240p)\b'
        }
        
        # Video codecs
        self.video_codec_patterns = {
            'H.264': r'\b(h\.?264|x264|avc)\b',
            'H.265': r'\b(h\.?265|x265|hevc)\b',
            'VP9': r'\bvp9\b',
            'VP8': r'\bvp8\b',
            'XviD': r'\bxvid\b',
            'DivX': r'\bdivx\b',
            'AV1': r'\bav1\b'
        }
        
        # Audio codecs
        self.audio_codec_patterns = {
            'AAC': r'\baac\b',
            'AC3': r'\b(ac3|ac-3)\b',
            'DTS': r'\b(dts|dts-hd)\b',
            'MP3': r'\bmp3\b',
            'FLAC': r'\bflac\b',
            'OGG': r'\bogg\b',
            'Opus': r'\bopus\b',
            'EAC3': r'\b(eac3|eac-3|e-ac-3)\b'
        }
        
        # File formats
        self.format_patterns = {
            'MKV': r'\.mkv$',
            'MP4': r'\.mp4$',
            'AVI': r'\.avi$',
            'WMV': r'\.wmv$',
            'FLV': r'\.flv$',
            'MOV': r'\.mov$',
            'M4V': r'\.m4v$',
            'WebM': r'\.webm$',
            'OGV': r'\.ogv$',
            'MTS': r'\.mts$',
            'M2TS': r'\.m2ts$',
            'TS': r'\.ts$',
            'MPG': r'\.(mpg|mpeg)$',
            'VOB': r'\.vob$',
            'ASF': r'\.asf$',
            '3GP': r'\.3gp$'
        }
        
        # Language patterns
        self.language_patterns = {
            'English': r'\b(eng|english|en)\b',
            'Hindi': r'\b(hin|hindi|hi)\b',
            'Spanish': r'\b(spa|spanish|es)\b',
            'French': r'\b(fre|french|fr)\b',
            'German': r'\b(ger|german|de)\b',
            'Italian': r'\b(ita|italian|it)\b',
            'Japanese': r'\b(jpn|japanese|ja)\b',
            'Korean': r'\b(kor|korean|ko)\b',
            'Chinese': r'\b(chi|chinese|zh)\b',
            'Russian': r'\b(rus|russian|ru)\b'
        }
        
        # Source indicators
        self.source_patterns = {
            'Netflix': r'\b(netflix|nf)\b',
            'Amazon Prime': r'\b(amzn|amazon)\b',
            'Disney+': r'\b(dsnp|disney)\b',
            'HBO Max': r'\b(hmax|hbo)\b',
            'Apple TV+': r'\b(atvp|apple)\b',
            'Hulu': r'\bhulu\b',
            'Peacock': r'\bpcok\b',
            'Paramount+': r'\bpmtp\b',
            'YouTube': r'\b(youtube|yt)\b',
            'BBC iPlayer': r'\bbbc\b',
            'iTunes': r'\bitunes\b'
        }
    
    def analyze_filename(self, filename: str) -> AnalysisResult:
        """Analyze filename and extract metadata"""
        filename_lower = filename.lower()
        
        result = AnalysisResult(
            filename=filename,
            file_type="Unknown",
            format_details={}
        )
        
        # Detect file format
        for format_name, pattern in self.format_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.file_type = format_name
                break
        
        # Detect quality
        for quality, pattern in self.quality_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.quality = quality
                break
        
        # Detect resolution
        for resolution, pattern in self.resolution_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.resolution = resolution
                break
        
        # Detect video codec
        for codec, pattern in self.video_codec_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.codec = codec
                break
        
        # Detect audio codec
        for audio_codec, pattern in self.audio_codec_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.audio_codec = audio_codec
                break
        
        # Detect language
        for language, pattern in self.language_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.language = language
                break
        
        # Detect source
        for source, pattern in self.source_patterns.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                result.source = source
                break
        
        # Additional format details
        result.format_details = {
            "has_subtitles": bool(re.search(r'\b(sub|subs|subtitle|subtitles)\b', filename_lower)),
            "has_multiple_audio": bool(re.search(r'\b(dual|multi|multilang)\b', filename_lower)),
            "is_3d": bool(re.search(r'\b3d\b', filename_lower)),
            "is_hdr": bool(re.search(r'\b(hdr|hdr10|dolby.vision)\b', filename_lower)),
            "year": self._extract_year(filename),
            "season_episode": self._extract_season_episode(filename)
        }
        
        return result
    
    def _extract_year(self, filename: str) -> Optional[str]:
        """Extract year from filename"""
        year_match = re.search(r'\b(19|20)\d{2}\b', filename)
        return year_match.group() if year_match else None
    
    def _extract_season_episode(self, filename: str) -> Optional[str]:
        """Extract season/episode information"""
        se_patterns = [
            r's(\d+)e(\d+)',  # S01E01
            r'season.?(\d+).?episode.?(\d+)',  # Season 1 Episode 1
            r'(\d+)x(\d+)'  # 1x01
        ]
        
        for pattern in se_patterns:
            match = re.search(pattern, filename.lower())
            if match:
                return f"S{match.group(1).zfill(2)}E{match.group(2).zfill(2)}"
        
        return None

# Initialize analyzer
analyzer = FileAnalyzer()

async def handle_telegram_message(update: Update) -> None:
    """Handle incoming Telegram messages"""
    if not bot:
        logger.error("Bot not initialized")
        return
        
    message = update.message
    chat_id = message.chat_id
    
    try:
        # Log message to database
        await app.mongodb.messages.insert_one({
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "username": message.from_user.username if message.from_user else None,
            "text": message.text,
            "timestamp": datetime.utcnow(),
            "message_type": "text" if message.text else "media"
        })
        
        # Handle commands
        if message.text:
            if message.text.startswith('/start'):
                welcome_message = """
🤖 **Welcome to File Metadata Analyzer Bot!**

I can analyze Telegram files and extract detailed metadata including:
• File format (MKV, MP4, AVI, etc.)
• Quality (BluRay, WEB-DL, DVDRip, etc.) 
• Resolution (4K, 1080p, 720p, etc.)
• Video/Audio codecs (H.264, H.265, AAC, etc.)
• Source platform (Netflix, Amazon Prime, etc.)
• Language and subtitle information

**How to use:**
1. Forward any file to me
2. Send a file directly
3. Use `/analyze filename.mkv` with any filename

**Commands:**
/start - Show this help message  
/analyze <filename> - Analyze a specific filename
/stats - Show your analysis history

Just send me any file and I'll analyze it! 📁✨
                """
                await bot.send_message(
                    chat_id=chat_id,
                    text=welcome_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            elif message.text.startswith('/analyze'):
                # Extract filename from command
                parts = message.text.split(' ', 1)
                if len(parts) > 1:
                    filename = parts[1]
                    analysis = analyzer.analyze_filename(filename)
                    response = format_analysis_response(analysis)
                    
                    # Save analysis to database
                    await app.mongodb.analyses.insert_one({
                        "id": str(uuid.uuid4()),
                        "chat_id": chat_id,
                        "filename": filename,
                        "analysis": analysis.dict(),
                        "timestamp": datetime.utcnow(),
                        "source": "command"
                    })
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=response,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text="Please provide a filename. Example: `/analyze Movie.2023.1080p.BluRay.x264.mkv`",
                        parse_mode=ParseMode.MARKDOWN
                    )
            
            elif message.text.startswith('/stats'):
                # Get user stats
                stats = await get_user_stats(chat_id)
                await bot.send_message(
                    chat_id=chat_id,
                    text=stats,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        # Handle file messages
        elif message.document or message.video or message.audio:
            file_info = None
            
            if message.document:
                file_info = FileMetadata(
                    file_id=message.document.file_id,
                    file_name=message.document.file_name or "Unknown",
                    file_size=message.document.file_size,
                    mime_type=message.document.mime_type,
                    file_unique_id=message.document.file_unique_id
                )
            elif message.video:
                file_info = FileMetadata(
                    file_id=message.video.file_id,
                    file_name=message.video.file_name or "Unknown Video",
                    file_size=message.video.file_size,
                    mime_type=message.video.mime_type,
                    file_unique_id=message.video.file_unique_id
                )
            elif message.audio:
                file_info = FileMetadata(
                    file_id=message.audio.file_id,
                    file_name=getattr(message.audio, 'file_name', None) or 
                             getattr(message.audio, 'title', 'Unknown Audio'),
                    file_size=message.audio.file_size,
                    mime_type=message.audio.mime_type,
                    file_unique_id=message.audio.file_unique_id
                )
            
            if file_info:
                # Analyze the file
                analysis = analyzer.analyze_filename(file_info.file_name)
                response = format_analysis_response(analysis, file_info)
                
                # Save analysis to database
                await app.mongodb.analyses.insert_one({
                    "id": str(uuid.uuid4()),
                    "chat_id": chat_id,
                    "filename": file_info.file_name,
                    "file_metadata": file_info.dict(),
                    "analysis": analysis.dict(),
                    "timestamp": datetime.utcnow(),
                    "source": "file_upload"
                })
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=response,
                    parse_mode=ParseMode.MARKDOWN
                )
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error analyzing this file. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )

def format_analysis_response(analysis: AnalysisResult, file_info: Optional[FileMetadata] = None) -> str:
    """Format analysis results for Telegram message"""
    
    # Main header
    response = f"🎬 **File Analysis Results**\n\n"
    response += f"📁 **Filename:** `{analysis.filename}`\n"
    
    # File information
    if file_info:
        response += f"💾 **File Size:** {format_file_size(file_info.file_size)}\n"
        if file_info.mime_type:
            response += f"📋 **MIME Type:** `{file_info.mime_type}`\n"
    
    response += "\n**🔍 Detected Metadata:**\n"
    
    # File format
    response += f"• **Format:** {analysis.file_type}\n"
    
    # Quality
    if analysis.quality:
        quality_emoji = get_quality_emoji(analysis.quality)
        response += f"• **Quality:** {quality_emoji} {analysis.quality}\n"
    
    # Resolution
    if analysis.resolution:
        response += f"• **Resolution:** 📺 {analysis.resolution}\n"
    
    # Video codec
    if analysis.codec:
        response += f"• **Video Codec:** 🎥 {analysis.codec}\n"
    
    # Audio codec
    if analysis.audio_codec:
        response += f"• **Audio Codec:** 🔊 {analysis.audio_codec}\n"
    
    # Language
    if analysis.language:
        response += f"• **Language:** 🌐 {analysis.language}\n"
    
    # Source platform
    if analysis.source:
        response += f"• **Source:** 📺 {analysis.source}\n"
    
    # Additional details
    if analysis.format_details:
        details = analysis.format_details
        if details.get("year"):
            response += f"• **Year:** 📅 {details['year']}\n"
        if details.get("season_episode"):
            response += f"• **Episode:** 📺 {details['season_episode']}\n"
        if details.get("has_subtitles"):
            response += f"• **Subtitles:** 💬 Yes\n"
        if details.get("has_multiple_audio"):
            response += f"• **Multi-Audio:** 🎵 Yes\n"
        if details.get("is_3d"):
            response += f"• **3D:** 🕶️ Yes\n"
        if details.get("is_hdr"):
            response += f"• **HDR:** ✨ Yes\n"
    
    response += "\n_Analysis completed successfully!_ ✅"
    
    return response

def get_quality_emoji(quality: str) -> str:
    """Get emoji based on quality"""
    quality_emojis = {
        'CAM': '📷',
        'TS': '📽️',
        'DVDRip': '💿',
        'BluRay': '💎',
        'WEB-DL': '🌐',
        'WEBRip': '🌐',
        'HDTV': '📺',
        'UHD': '👑',
        'REMUX': '✨'
    }
    return quality_emojis.get(quality, '🎬')

def format_file_size(size_bytes: Optional[int]) -> str:
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

async def get_user_stats(chat_id: int) -> str:
    """Get user analysis statistics"""
    try:
        total_analyses = await app.mongodb.analyses.count_documents({"chat_id": chat_id})
        
        # Get most common formats
        pipeline = [
            {"$match": {"chat_id": chat_id}},
            {"$group": {"_id": "$analysis.file_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        
        format_stats = await app.mongodb.analyses.aggregate(pipeline).to_list(5)
        
        response = f"📊 **Your Analysis Stats**\n\n"
        response += f"🔢 **Total Files Analyzed:** {total_analyses}\n\n"
        
        if format_stats:
            response += "📁 **Most Common Formats:**\n"
            for stat in format_stats:
                response += f"• {stat['_id']}: {stat['count']} files\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return "Sorry, couldn't retrieve your stats right now."

# API Endpoints
@app.post("/api/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    """Handle Telegram webhook"""
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot)
        
        if update.message:
            await handle_telegram_message(update)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@app.get("/api/stats")
async def get_bot_stats():
    """Get overall bot statistics"""
    try:
        total_users = await app.mongodb.messages.distinct("chat_id")
        total_analyses = await app.mongodb.analyses.count_documents({})
        
        return {
            "total_users": len(total_users),
            "total_analyses": total_analyses,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": "Could not retrieve stats"}

@app.post("/api/analyze-file")
async def analyze_file_api(filename: str):
    """Analyze file via API"""
    analysis = analyzer.analyze_filename(filename)
    return analysis.dict()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)