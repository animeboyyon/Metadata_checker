#!/usr/bin/env python3
"""
Telegram Bot - Simple version that works with our environment
"""

import logging
import os
import sys
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

# Bot configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

if not TOKEN:
    logger.error("No TELEGRAM_TOKEN provided")
    print("❌ No Telegram Bot Token provided")
    sys.exit(1)

# Global MongoDB client
mongodb_client = None
mongodb = None

async def init_mongodb():
    """Initialize MongoDB"""
    global mongodb_client, mongodb
    try:
        mongodb_client = AsyncIOMotorClient(MONGO_URL)
        mongodb = mongodb_client.telegram_bot
        logger.info("MongoDB connected successfully")
        print("✅ MongoDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        print(f"❌ MongoDB connection failed: {e}")

async def start_command(update, context):
    """Handle /start and /help commands"""
    welcome_message = """
🤖 *Welcome to File Metadata Analyzer Bot\\!*

I can analyze Telegram files and extract detailed metadata including:
• File format \\(MKV, MP4, AVI, etc\\.\\)
• Quality \\(BluRay, WEB\\-DL, DVDRip, etc\\.\\) 
• Resolution \\(4K, 1080p, 720p, etc\\.\\)
• Video/Audio codecs \\(H\\.264, H\\.265, AAC, etc\\.\\)
• Source platform \\(Netflix, Amazon Prime, etc\\.\\)
• Language and subtitle information

*How to use:*
1\\. Forward any file to me
2\\. Send a file directly  
3\\. Use `/analyze filename\\.mkv` with any filename

*Commands:*
/start \\- Show this help message
/analyze <filename> \\- Analyze a specific filename
/stats \\- Show your analysis history

Just send me any file and I'll analyze it\\! 📁✨
    """
    
    await update.message.reply_text(welcome_message, parse_mode='MarkdownV2')
    
    # Log to database
    if mongodb:
        try:
            await mongodb.messages.insert_one({
                "id": str(uuid.uuid4()),
                "chat_id": update.effective_chat.id,
                "username": update.effective_user.username,
                "command": "/start",
                "timestamp": datetime.utcnow(),
                "message_type": "command"
            })
        except Exception as e:
            logger.error(f"DB log error: {e}")

async def analyze_command(update, context):
    """Handle /analyze command"""
    if not context.args:
        await update.message.reply_text(
            "Please provide a filename\\. Example:\n`/analyze Movie\\.2023\\.1080p\\.BluRay\\.x264\\.mkv`",
            parse_mode='MarkdownV2'
        )
        return
    
    filename = " ".join(context.args)
    analysis = analyzer.analyze_filename(filename)
    response = format_analysis_response(analysis)
    
    await update.message.reply_text(response, parse_mode='Markdown')
    
    # Log to database
    if mongodb:
        try:
            await mongodb.analyses.insert_one({
                "id": str(uuid.uuid4()),
                "chat_id": update.effective_chat.id,
                "username": update.effective_user.username,
                "filename": filename,
                "analysis": analysis.dict(),
                "timestamp": datetime.utcnow(),
                "source": "command"
            })
        except Exception as e:
            logger.error(f"DB log error: {e}")

async def stats_command(update, context):
    """Handle /stats command"""
    chat_id = update.effective_chat.id
    
    if not mongodb:
        await update.message.reply_text("Stats not available right now\\.", parse_mode='MarkdownV2')
        return
    
    try:
        total_analyses = await mongodb.analyses.count_documents({"chat_id": chat_id})
        
        # Get most common formats
        pipeline = [
            {"$match": {"chat_id": chat_id}},
            {"$group": {"_id": "$analysis.file_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        
        format_stats = await mongodb.analyses.aggregate(pipeline).to_list(5)
        
        response = f"📊 *Your Analysis Stats*\n\n"
        response += f"🔢 *Total Files Analyzed:* {total_analyses}\n\n"
        
        if format_stats:
            response += "📁 *Most Common Formats:*\n"
            for stat in format_stats:
                response += f"• {stat['_id']}: {stat['count']} files\n"
        else:
            response += "No analyses yet\\. Send me some files to analyze\\!"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text("Sorry, couldn't retrieve your stats right now\\.", parse_mode='MarkdownV2')

async def handle_document(update, context):
    """Handle document files"""
    document = update.message.document
    
    file_info = FileMetadata(
        file_id=document.file_id,
        file_name=document.file_name or "Unknown",
        file_size=document.file_size,
        mime_type=document.mime_type,
        file_unique_id=document.file_unique_id
    )
    
    await analyze_and_respond(update, file_info, context)

async def handle_video(update, context):
    """Handle video files"""
    video = update.message.video
    
    file_info = FileMetadata(
        file_id=video.file_id,
        file_name=video.file_name or "Unknown Video",
        file_size=video.file_size,
        mime_type=video.mime_type,
        file_unique_id=video.file_unique_id
    )
    
    await analyze_and_respond(update, file_info, context)

async def handle_audio(update, context):
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
    
    await analyze_and_respond(update, file_info, context)

async def handle_text(update, context):
    """Handle text messages that might be filenames"""
    text = update.message.text
    
    # Check if text looks like a filename
    if ('.' in text and 
        any(ext in text.lower() for ext in ['.mkv', '.mp4', '.avi', '.webm', '.mov', '.flv', '.wmv'])):
        
        analysis = analyzer.analyze_filename(text)
        response = format_analysis_response(analysis)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # Log to database
        if mongodb:
            try:
                await mongodb.analyses.insert_one({
                    "id": str(uuid.uuid4()),
                    "chat_id": update.effective_chat.id,
                    "username": update.effective_user.username,
                    "filename": text,
                    "analysis": analysis.dict(),
                    "timestamp": datetime.utcnow(),
                    "source": "text_filename"
                })
            except Exception as e:
                logger.error(f"DB log error: {e}")
    else:
        # Provide help
        await update.message.reply_text(
            "🤔 I didn't recognize that as a filename\\.\n\n"
            "Try:\n"
            "• Sending a file directly\n"
            "• Using `/analyze filename\\.mkv`\n"
            "• Type `/help` for more info",
            parse_mode='MarkdownV2'
        )

async def analyze_and_respond(update, file_info, context):
    """Analyze file and send response"""
    try:
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action='typing'
        )
        
        # Analyze the file
        analysis = analyzer.analyze_filename(file_info.file_name)
        response = format_analysis_response(analysis, file_info)
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        # Log to database
        if mongodb:
            try:
                await mongodb.analyses.insert_one({
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
                logger.error(f"DB log error: {e}")
                
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        await update.message.reply_text(
            "Sorry, there was an error analyzing this file\\. Please try again\\.",
            parse_mode='MarkdownV2'
        )

async def setup_database(context):
    """Setup database connection on startup"""
    await init_mongodb()

def main():
    """Main function"""
    print("🤖 Starting Telegram File Analyzer Bot...")
    
    try:
        # Create application
        application = Application.builder().token(TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler(["start", "help"], start_command))
        application.add_handler(CommandHandler("analyze", analyze_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        # Add file handlers
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.VIDEO, handle_video))
        application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
        
        # Add text handler (should be last)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        print("✅ Bot handlers configured")
        print(f"✅ Bot Token: {TOKEN[:20]}...")
        print("🚀 Starting polling...")
        
        # Start the bot
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logger.error(f"Bot error: {e}")
        raise

if __name__ == '__main__':
    main()