#!/usr/bin/env python3
"""
Telegram Bot Polling Script
This script runs the actual Telegram bot that listens for messages
"""

import asyncio
import logging
import os
import sys
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from dotenv import load_dotenv
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from server import analyzer, format_analysis_response, FileMetadata

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token
TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

if not TOKEN:
    logger.error("No TELEGRAM_TOKEN provided")
    sys.exit(1)

class TelegramFileBot:
    def __init__(self):
        self.application = Application.builder().token(TOKEN).build()
        self.mongodb_client = None
        self.mongodb = None
        
    async def start_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            self.mongodb_client = AsyncIOMotorClient(MONGO_URL)
            self.mongodb = self.mongodb_client.telegram_bot
            logger.info("MongoDB connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
    
    async def start_command(self, update: Update, context) -> None:
        """Handle /start command"""
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
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
        
        # Log to database
        if self.mongodb:
            await self.mongodb.messages.insert_one({
                "id": str(uuid.uuid4()),
                "chat_id": update.effective_chat.id,
                "username": update.effective_user.username,
                "command": "/start",
                "timestamp": datetime.utcnow(),
                "message_type": "command"
            })

    async def analyze_command(self, update: Update, context) -> None:
        """Handle /analyze command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide a filename. Example:\n`/analyze Movie.2023.1080p.BluRay.x264.mkv`",
                parse_mode='Markdown'
            )
            return
        
        filename = " ".join(context.args)
        analysis = analyzer.analyze_filename(filename)
        response = format_analysis_response(analysis)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # Log to database
        if self.mongodb:
            await self.mongodb.analyses.insert_one({
                "id": str(uuid.uuid4()),
                "chat_id": update.effective_chat.id,
                "username": update.effective_user.username,
                "filename": filename,
                "analysis": analysis.dict(),
                "timestamp": datetime.utcnow(),
                "source": "command"
            })

    async def stats_command(self, update: Update, context) -> None:
        """Handle /stats command"""
        chat_id = update.effective_chat.id
        
        if not self.mongodb:
            await update.message.reply_text("Stats not available right now.")
            return
        
        try:
            total_analyses = await self.mongodb.analyses.count_documents({"chat_id": chat_id})
            
            # Get most common formats
            pipeline = [
                {"$match": {"chat_id": chat_id}},
                {"$group": {"_id": "$analysis.file_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            
            format_stats = await self.mongodb.analyses.aggregate(pipeline).to_list(5)
            
            response = f"📊 **Your Analysis Stats**\n\n"
            response += f"🔢 **Total Files Analyzed:** {total_analyses}\n\n"
            
            if format_stats:
                response += "📁 **Most Common Formats:**\n"
                for stat in format_stats:
                    response += f"• {stat['_id']}: {stat['count']} files\n"
            else:
                response += "No analyses yet. Send me some files to analyze!"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text("Sorry, couldn't retrieve your stats right now.")

    async def handle_document(self, update: Update, context) -> None:
        """Handle document files"""
        document = update.message.document
        
        file_info = FileMetadata(
            file_id=document.file_id,
            file_name=document.file_name or "Unknown",
            file_size=document.file_size,
            mime_type=document.mime_type,
            file_unique_id=document.file_unique_id
        )
        
        await self.analyze_and_respond(update, file_info)

    async def handle_video(self, update: Update, context) -> None:
        """Handle video files"""
        video = update.message.video
        
        file_info = FileMetadata(
            file_id=video.file_id,
            file_name=video.file_name or "Unknown Video",
            file_size=video.file_size,
            mime_type=video.mime_type,
            file_unique_id=video.file_unique_id
        )
        
        await self.analyze_and_respond(update, file_info)

    async def handle_audio(self, update: Update, context) -> None:
        """Handle audio files"""
        audio = update.message.audio
        
        file_info = FileMetadata(
            file_id=audio.file_id,
            file_name=getattr(audio, 'file_name', None) or 
                     getattr(audio, 'title', 'Unknown Audio'),
            file_size=audio.file_size,
            mime_type=audio.mime_type,
            file_unique_id=audio.file_unique_id
        )
        
        await self.analyze_and_respond(update, file_info)

    async def analyze_and_respond(self, update: Update, file_info: FileMetadata):
        """Analyze file and send response"""
        try:
            # Analyze the file
            analysis = analyzer.analyze_filename(file_info.file_name)
            response = format_analysis_response(analysis, file_info)
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
            # Log to database
            if self.mongodb:
                await self.mongodb.analyses.insert_one({
                    "id": str(uuid.uuid4()),
                    "chat_id": update.effective_chat.id,
                    "username": update.effective_user.username,
                    "filename": file_info.file_name,
                    "file_metadata": file_info.dict(),
                    "analysis": analysis.dict(),
                    "timestamp": datetime.utcnow(),
                    "source": "file_upload"
                })
                
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            await update.message.reply_text(
                "Sorry, there was an error analyzing this file. Please try again."
            )

    async def handle_text(self, update: Update, context) -> None:
        """Handle text messages that might be filenames"""
        text = update.message.text
        
        # Check if text looks like a filename
        if ('.' in text and 
            any(ext in text.lower() for ext in ['.mkv', '.mp4', '.avi', '.webm', '.mov', '.flv', '.wmv'])):
            
            analysis = analyzer.analyze_filename(text)
            response = format_analysis_response(analysis)
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
            # Log to database
            if self.mongodb:
                await self.mongodb.analyses.insert_one({
                    "id": str(uuid.uuid4()),
                    "chat_id": update.effective_chat.id,
                    "username": update.effective_user.username,
                    "filename": text,
                    "analysis": analysis.dict(),
                    "timestamp": datetime.utcnow(),
                    "source": "text_filename"
                })
        else:
            # Provide help
            await update.message.reply_text(
                "🤔 I didn't recognize that as a filename.\n\n"
                "Try:\n"
                "• Sending a file directly\n"
                "• Using `/analyze filename.mkv`\n"
                "• Type `/help` for more info",
                parse_mode='Markdown'
            )

    def setup_handlers(self):
        """Setup all message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.start_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # File handlers
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        self.application.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        self.application.add_handler(MessageHandler(filters.AUDIO, self.handle_audio))
        
        # Text handler (should be last)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def start_bot(self):
        """Start the bot"""
        await self.start_mongodb()
        self.setup_handlers()
        
        logger.info("Starting Telegram bot...")
        await self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

async def main():
    """Main function"""
    bot = TelegramFileBot()
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())