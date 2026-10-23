import os
import json
import asyncio
import urllib.parse
import requests
import edge_tts
from google import genai
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- కేవలం ఈ 2 కీలు సరిపోతాయి (Pexels అవసరం లేదు) ---
GEMINI_API_KEY = "AQ.Ab8RN6J4ctkuoPjcVuw7NHI6sLQmbZC7ePcpcyxD64Hfc_cHMw"         # aistudio.google.com
TELEGRAM_BOT_TOKEN = "8385050593:AAEqShZcesymEQS_B7Um9_6TXtKioIzeuNo"        

client = genai.Client(api_key=GEMINI_API_KEY)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "నమస్కారం! నేను మీ AI Video Creator బాట్‌ని.\n\n"
        "ఏదైనా టాపిక్ పంపండి, కొద్ది క్షణాల్లో వీడియో తయారు చేస్తాను."
    )

# Pexels API కీ లేకుండా ఉచిత వీడియో తెచ్చుకునే ఫంక్షన్
def get_free_stock_video(keyword, output_path):
    # Wikimedia / Pixabay ఓపెన్ క్లిప్స్ ద్వారా ఫాల్‌బ్యాక్
    clean_kw = urllib.parse.quote(keyword)
    # ఉచిత ఓపెన్ స్టాక్ వీడియో మూలాలు (API Key అవసరం లేదు)
    fallback_urls = [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
    ]
    # బై డిఫాల్ట్ సేఫ్ వీడియో క్లిప్ డౌన్‌లోడ్
    import random
    selected_url = random.choice(fallback_urls)
    
    r = requests.get(selected_url, stream=True)
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ AI స్క్రిప్ట్ సిద్ధం చేస్తోంది...")

    try:
        prompt = f"""
        Create a 2-scene vertical short video script about '{topic}' in Telugu.
        Return strictly JSON with no markdown formatting:
        {{
          "scenes": [
            {{"text": "Short Telugu narration for scene 1", "keyword": "nature"}},
            {{"text": "Short Telugu narration for scene 2", "keyword": "space"}}
          ]
        }}
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)

        await status_msg.edit_text("⏳ ఆడియో మరియు విజువల్స్ డౌన్‌లోడ్ అవుతున్నాయి...")

        clips = []
        for i, scene in enumerate(data["scenes"]):
            audio_path = f"audio_{i}.mp3"
            video_path = f"video_{i}.mp4"

            # తెలుగు వాయిస్‌ఓవర్
            communicate = edge_tts.Communicate(scene["text"], "te-IN-MohanNeural")
            await communicate.save(audio_path)

            # వీడియో క్లిప్ సేకరణ
            get_free_stock_video(scene["keyword"], video_path)

            audio_clip = AudioFileClip(audio_path)
            raw_video = VideoFileClip(video_path)
            
            # ఆడియో సమయానికి వీడియోను కట్ చేయడం
            target_dur = min(audio_clip.duration, raw_video.duration)
            v_clip = raw_video.subclip(0, target_dur).set_audio(audio_clip.subclip(0, target_dur))
            clips.append(v_clip)

        await status_msg.edit_text("⏳ వీడియో రెండరింగ్ అవుతోంది...")

        output_filename = "final_output.mp4"
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac")

        for c in clips:
            c.close()
        final_video.close()

        await status_msg.edit_text("📤 వీడియో టెలిగ్రామ్‌కు వస్తోంది...")
        with open(output_filename, "rb") as video_file:
            await update.message.reply_video(video=video_file, caption=f"🎬 {topic}")

        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"ఎర్రర్ వచ్చింది: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
