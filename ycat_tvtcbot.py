#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# YCat TVTC Bot - Telegram Bot for GitLab Integration
# File: ycat_tvtcbot.py

import os
import logging
from flask import Flask, request, jsonify
import requests
import json
from threading import Thread
import time
import sqlite3
from datetime import datetime

# تكوين اللوجر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ycat_tvtcbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('YCatTVTCBot')

class YCatTVTCBot:
    def __init__(self):
        self.telegram_token = "8344408126:AAHir9gUCkH7PM5szpzNfERphyFOmLHPxsk"
        self.bot_username = "YCatTVTCBot"
        self.webhook_url = None
        self.admin_chat_ids = []  # قائمة بآيدي المشرفين
        self.app = Flask(__name__)
        self.setup_database()
        self.setup_routes()
        
    def setup_database(self):
        """إعداد قاعدة البيانات SQLite"""
        self.conn = sqlite3.connect('ycat_tvtcbot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # إنشاء جدول المستخدمين
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # إنشاء جدول المشاريع
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                gitlab_url TEXT,
                chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ Database setup completed")
    
    def setup_routes(self):
        """إعداد مسارات الويب هوك"""
        @self.app.route('/')
        def home():
            return """
            <html>
                <head>
                    <title>YCat TVTC Bot</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .container { max-width: 800px; margin: 0 auto; }
                        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; }
                        .content { margin: 20px 0; }
                        .command { background: #f8f9fa; padding: 10px; border-left: 4px solid #3498db; margin: 10px 0; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🎯 YCat TVTC Bot</h1>
                            <p>Telegram Bot for GitLab Integration</p>
                        </div>
                        <div class="content">
                            <h2>🤖 Bot is Running Successfully</h2>
                            <p><strong>Token:</strong> 8344408126:AAHir9gUCkH7PM5szpzNfERphyFOmLHPxsk</p>
                            <p><strong>Username:</strong> @YCatTVTCBot</p>
                            
                            <h3>📡 Available Endpoints:</h3>
                            <div class="command">POST /webhook/telegram - Telegram updates</div>
                            <div class="command">POST /webhook/gitlab - GitLab events</div>
                            <div class="command">GET /status - Bot status</div>
                            
                            <h3>🔧 How to Use:</h3>
                            <ol>
                                <li>Start chat with @YCatTVTCBot on Telegram</li>
                                <li>Use /setup to configure GitLab integration</li>
                                <li>Add webhook URL to your GitLab project</li>
                            </ol>
                        </div>
                    </div>
                </body>
            </html>
            """
        
        @self.app.route('/status')
        def status():
            stats = self.get_bot_stats()
            return jsonify({
                "status": "running",
                "bot_name": "YCat TVTC Bot",
                "telegram_token": self.telegram_token[:10] + "...",
                "registered_users": stats['users_count'],
                "active_projects": stats['projects_count'],
                "uptime": stats['uptime']
            })
        
        @self.app.route('/webhook/telegram', methods=['POST'])
        def telegram_webhook():
            """استقبال التحديثات من التليجرام"""
            try:
                update = request.get_json()
                logger.info(f"📨 Telegram update received: {update.get('update_id')}")
                self.handle_telegram_update(update)
                return jsonify({"status": "success"})
            except Exception as e:
                logger.error(f"❌ Error in telegram webhook: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @self.app.route('/webhook/gitlab', methods=['POST'])
        def gitlab_webhook():
            """استقبال الأحداث من GitLab"""
            try:
                event = request.get_json()
                event_type = event.get('object_kind', 'unknown')
                logger.info(f"🔔 GitLab event received: {event_type}")
                self.handle_gitlab_event(event)
                return jsonify({"status": "success", "event": event_type})
            except Exception as e:
                logger.error(f"❌ Error in gitlab webhook: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @self.app.route('/users')
        def list_users():
            """قائمة المستخدمين المسجلين (لأغراض التطوير)"""
            users = self.get_registered_users()
            return jsonify({"users": users})
    
    def handle_telegram_update(self, update):
        """معالجة رسائل التليجرام"""
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            username = message['chat'].get('username', '')
            first_name = message['chat'].get('first_name', '')
            
            # تسجيل المستخدم
            self.register_user(chat_id, username, first_name)
            
            if text.startswith('/'):
                self.handle_command(chat_id, text, username)
            else:
                self.send_message(chat_id, "🤖 استخدم /help لرؤية الأوامر المتاحة")
    
    def handle_command(self, chat_id, command, username):
        """معالجة الأوامر من التليجرام"""
        commands = {
            '/start': self.cmd_start,
            '/help': self.cmd_help,
            '/setup': self.cmd_setup,
            '/status': self.cmd_status,
            '/gitlab': self.cmd_gitlab,
            '/projects': self.cmd_projects,
            '/broadcast': self.cmd_broadcast,
            '/stats': self.cmd_stats
        }
        
        cmd = command.split()[0].lower()
        if cmd in commands:
            commands[cmd](chat_id, username)
        else:
            self.send_message(chat_id, "❌ أمر غير معروف. استخدم /help لرؤية الأوامر المتاحة.")
    
    def cmd_start(self, chat_id, username):
        """أمر البدء"""
        welcome_msg = f"""
🚀 **مرحباً {username} في YCat TVTC Bot!**

أنا بوت متخصص لربط منصة GitLab مع Telegram. يمكنني:

📊 • متابعة الـ commits والـ push events
🎯 • إدارة الـ issues والمشاكل
🔄 • متابعة الـ merge requests
⚙️ • مراقبة الـ pipelines والبناء
🏷️ • متابعة الـ tags والإصدارات
⚠️  • إشعارات الأخطاء والمشاكل

**الأوامر المتاحة:**
/start - بدء البوت
/help - المساعدة
/setup - إعداد GitLab
/projects - إدارة المشاريع
/status - حالة البوت
/stats - إحصائيات

🔧 **للبداية استخدم:** /setup
        """
        self.send_message(chat_id, welcome_msg)
    
    def cmd_help(self, chat_id, username):
        """أمر المساعدة"""
        help_msg = """
📖 **دليل استخدام YCat TVTC Bot:**

**الأوامر الأساسية:**
/start - بدء البوت والترحيب
/help - عرض هذه المساعدة
/status - حالة البوت والمشاريع

**أوامر GitLab:**
/setup - إعداد ربط GitLab
/gitlab - معلومات عن الإعداد
/projects - عرض المشاريع المربوطة

**أوامر المشرفين:**
/stats - إحصائيات البوت
/broadcast - بث رسالة للمستخدمين

🔗 **خطوات الإعداد:**
1. استخدم /setup للحصول على رابط Webhook
2. اذهب إلى إعدادات مشروعك في GitLab
3. اختر Webhooks → Add Webhook
4. الصق الرابط الذي حصلت عليه
5. اختر الأحداث المراد متابعتها
6. احفظ واضغط Test

📧 **ستصلك إشعارات فورية عند أي حدث!**
        """
        self.send_message(chat_id, help_msg)
    
    def cmd_setup(self, chat_id, username):
        """إعداد GitLab"""
        setup_msg = f"""
🔧 **إعداد ربط GitLab مع YCat TVTC Bot**

**الخطوة 1:** اذهب إلى مشروعك في GitLab

**الخطوة 2:** اضغط على:
⚙️ **Settings** → **Webhooks**

**الخطوة 3:** أضف رابط Webhook التالي: