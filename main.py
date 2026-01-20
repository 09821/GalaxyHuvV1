import discord
from discord.ext import commands, tasks
import os
import json
from flask import Flask, render_template, request, redirect, jsonify
from threading import Thread
import time

# Flask para o dashboard
app = Flask(__name__)

# Configurações padrão
CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        default_config = {
            "source_server_id": 1448597315207299126,
            "source_channel_id": 1448604275323306116,
            "target_server_id": 1451576221518266428,
            "target_channel_id": 1452048190407970859,
            "bot_enabled": True,
            "startup_message_enabled": True
        }
        save_config(default_config)
        return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

# Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

startup_sent = False

@bot.event
async def on_ready():
    global startup_sent
    print(f'✅ Bot conectado como {bot.user}')
    print(f'📡 Monitorando: {config["source_channel_id"]}')
    print(f'📤 Enviando para: {config["target_channel_id"]}')
    
    # Enviar mensagem de startup em todos os servidores
    if config["startup_message_enabled"] and not startup_sent:
        await send_startup_message()
        startup_sent = True
    
    # Iniciar monitoramento de saúde
    if not health_check.is_running():
        health_check.start()

async def send_startup_message():
    embed = discord.Embed(
        title="🚀 Galaxy Scripts Bot Online!",
        description="O bot de espelhamento está ativo e funcionando!",
        color=0x00ff00
    )
    embed.add_field(name="📊 Status", value="✅ Operacional", inline=True)
    embed.add_field(name="🔄 Monitoramento", value="✅ Ativo", inline=True)
    embed.add_field(name="⚡ Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text="Galaxy Scripts • Sistema Automático")
    embed.timestamp = discord.utils.utcnow()
    
    for guild in bot.guilds:
        try:
            # Procura o canal geral ou primeiro canal com permissão
            channel = None
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
            
            if channel:
                await channel.send("@everyone @here Bot Galaxy Scripts on!", embed=embed)
                print(f"✅ Mensagem de startup enviada em: {guild.name}")
        except Exception as e:
            print(f"❌ Erro ao enviar startup em {guild.name}: {e}")

@bot.event
async def on_message(message):
    global config
    
    # Ignora mensagens do próprio bot
    if message.author == bot.user:
        return
    
    # Verifica se o bot está habilitado
    if not config["bot_enabled"]:
        return
    
    # Verifica se a mensagem é do canal fonte correto
    if message.channel.id == config["source_channel_id"] and message.guild.id == config["source_server_id"]:
        try:
            # Busca o canal de destino
            target_guild = bot.get_guild(config["target_server_id"])
            if not target_guild:
                print(f"❌ Servidor de destino não encontrado: {config['target_server_id']}")
                return
            
            target_channel = target_guild.get_channel(config["target_channel_id"])
            if not target_channel:
                print(f"❌ Canal de destino não encontrado: {config['target_channel_id']}")
                return
            
            # Copia a mensagem
            content = message.content
            
            # Copia embeds
            embeds = message.embeds
            
            # Copia anexos
            files = []
            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)
            
            # Envia a mensagem
            if content or embeds or files:
                await target_channel.send(
                    content=content if content else None,
                    embeds=embeds if embeds else None,
                    files=files if files else None
                )
                print(f"✅ Mensagem espelhada de {message.author}")
        
        except Exception as e:
            print(f"❌ Erro ao espelhar mensagem: {e}")
    
    await bot.process_commands(message)

# Sistema de auto-restart e health check
@tasks.loop(seconds=30)
async def health_check():
    print(f"💓 Health check - Bot ativo | Ping: {round(bot.latency * 1000)}ms")

@health_check.before_loop
async def before_health_check():
    await bot.wait_until_ready()

# Dashboard Flask
@app.route('/')
def dashboard():
    return render_template('dashboard.html', config=config, bot_user=bot.user if bot.is_ready() else None)

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    global config
    data = request.json
    
    config['source_server_id'] = int(data.get('source_server_id', config['source_server_id']))
    config['source_channel_id'] = int(data.get('source_channel_id', config['source_channel_id']))
    config['target_server_id'] = int(data.get('target_server_id', config['target_server_id']))
    config['target_channel_id'] = int(data.get('target_channel_id', config['target_channel_id']))
    config['bot_enabled'] = data.get('bot_enabled', config['bot_enabled'])
    config['startup_message_enabled'] = data.get('startup_message_enabled', config['startup_message_enabled'])
    
    save_config(config)
    return jsonify({"success": True, "message": "Configuração atualizada!"})

@app.route('/api/toggle', methods=['POST'])
def toggle_bot():
    global config
    config['bot_enabled'] = not config['bot_enabled']
    save_config(config)
    status = "ligado" if config['bot_enabled'] else "desligado"
    return jsonify({"success": True, "enabled": config['bot_enabled'], "message": f"Bot {status}!"})

@app.route('/api/status', methods=['GET'])
def bot_status():
    return jsonify({
        "online": bot.is_ready(),
        "latency": round(bot.latency * 1000) if bot.is_ready() else None,
        "servers": len(bot.guilds) if bot.is_ready() else 0,
        "enabled": config['bot_enabled']
    })

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    TOKEN = os.getenv('TOKEN')
    if not TOKEN:
        print("❌ TOKEN não encontrado! Configure no Replit Secrets.")
        return
    
    bot.run(TOKEN)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Iniciar tudo
if __name__ == "__main__":
    keep_alive()
    run_bot()
