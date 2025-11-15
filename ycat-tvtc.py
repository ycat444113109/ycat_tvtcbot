#!/usr/bin/env python3
# run_bot.py

from ycat_tvtcbot import YCatTVTCBot

if __name__ == '__main__':
    bot = YCatTVTCBot()
    
    # إعدادات السيرفر
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True
    
    print("🎯 Starting YCat TVTC Bot...")
    print(f"🔑 Token: 8344408126:AAHir9gUCkH7PM5szpzNfERphyFOmLHPxsk")
    print(f"🌐 Server: {HOST}:{PORT}")
    print(f"🔧 Debug: {DEBUG}")
    
    bot.run(host=HOST, port=PORT, debug=DEBUG)