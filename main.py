import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime, timedelta
import asyncio

# ID do usuário autorizado
AUTHORIZED_USER_ID = 1451570927711158313

# Configurações do bot
CONFIG = {
    "source_server_id": 1448597315207299126,
    "source_channel_id": 1448604275323306116,
    "target_server_id": 1455657852562571297,
    "target_channel_id": 1456074927907143912,
    "bot_active": False,
    "start_time": None
}

# Tempo de uptime do Replit (aproximadamente 12 horas)
UPTIME_HOURS = 12

# Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=["!", "/"], intents=intents)

startup_sent = False

def is_authorized():
    """Decorator para verificar se o usuário é autorizado"""
    async def predicate(ctx):
        if ctx.author.id != AUTHORIZED_USER_ID:
            await ctx.send("❌ Você não tem permissão para usar este comando!")
            return False
        return True
    return commands.check(predicate)

def get_remaining_time():
    """Calcula o tempo restante até o bot desligar"""
    if CONFIG["start_time"] is None:
        return "N/A"
    
    elapsed = datetime.now() - CONFIG["start_time"]
    remaining = timedelta(hours=UPTIME_HOURS) - elapsed
    
    if remaining.total_seconds() <= 0:
        return "Reiniciando em breve..."
    
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    seconds = int(remaining.total_seconds() % 60)
    
    return f"{hours}h {minutes}m {seconds}s"

@bot.event
async def on_ready():
    global startup_sent
    print(f'✅ Bot conectado como {bot.user}')
    print(f'🆔 ID do Bot: {bot.user.id}')
    print(f'👤 Usuário autorizado: {AUTHORIZED_USER_ID}')
    
    # Define o tempo de início
    if CONFIG["start_time"] is None:
        CONFIG["start_time"] = datetime.now()
    
    # Enviar mensagem de startup em todos os servidores
    if not startup_sent:
        await send_startup_message()
        startup_sent = True
    
    # Iniciar contador de tempo
    if not time_counter.is_running():
        time_counter.start()
    
    # Iniciar auto-restart
    if not auto_restart_check.is_running():
        auto_restart_check.start()

async def send_startup_message():
    """Envia mensagem de inicialização em todos os servidores"""
    embed = discord.Embed(
        title="🚀 Galaxy Scripts Bot Online!",
        description="O bot de espelhamento está ativo e pronto para uso!",
        color=0x00ff00
    )
    embed.add_field(name="📊 Status", value="✅ Operacional", inline=True)
    embed.add_field(name="🔄 Sistema", value="✅ Ativo", inline=True)
    embed.add_field(name="⚡ Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="⏱️ Tempo até desligar", value=get_remaining_time(), inline=False)
    embed.add_field(name="📝 Comandos", value="`!start` - Iniciar cópia\n`!stop` - Parar cópia\n`!status` - Ver status", inline=False)
    embed.set_footer(text="Galaxy Scripts • Sistema Automático de Espelhamento")
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
    # Ignora mensagens do próprio bot
    if message.author == bot.user:
        await bot.process_commands(message)
        return
    
    # Verifica se o bot está ativo
    if not CONFIG["bot_active"]:
        await bot.process_commands(message)
        return
    
    # Verifica se a mensagem é do canal fonte correto
    if message.channel.id == CONFIG["source_channel_id"] and message.guild.id == CONFIG["source_server_id"]:
        try:
            # Busca o canal de destino
            target_guild = bot.get_guild(CONFIG["target_server_id"])
            if not target_guild:
                print(f"❌ Servidor de destino não encontrado: {CONFIG['target_server_id']}")
                await bot.process_commands(message)
                return
            
            target_channel = target_guild.get_channel(CONFIG["target_channel_id"])
            if not target_channel:
                print(f"❌ Canal de destino não encontrado: {CONFIG['target_channel_id']}")
                await bot.process_commands(message)
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
            
            # Informações do autor (para identificar webhooks, bots, etc)
            author_info = f"**{message.author.name}**"
            if message.author.bot:
                author_info += " [BOT]"
            if message.webhook_id:
                author_info += " [WEBHOOK]"
            
            # Monta o conteúdo final
            final_content = f"{author_info}\n{content}" if content else author_info
            
            # Envia a mensagem
            await target_channel.send(
                content=final_content if final_content else None,
                embeds=embeds if embeds else None,
                files=files if files else None
            )
            print(f"✅ Mensagem espelhada de {message.author} ({message.author.id})")
        
        except Exception as e:
            print(f"❌ Erro ao espelhar mensagem: {e}")
    
    await bot.process_commands(message)

@bot.command(name='start')
@is_authorized()
async def start_mirror(ctx):
    """Inicia o espelhamento de mensagens"""
    if CONFIG["bot_active"]:
        await ctx.send("⚠️ O bot já está ativo!")
        return
    
    CONFIG["bot_active"] = True
    
    embed = discord.Embed(
        title="✅ Espelhamento Iniciado!",
        description="O bot começou a copiar mensagens.",
        color=0x00ff00
    )
    embed.add_field(name="📥 Origem", value=f"Servidor: `{CONFIG['source_server_id']}`\nCanal: `{CONFIG['source_channel_id']}`", inline=False)
    embed.add_field(name="📤 Destino", value=f"Servidor: `{CONFIG['target_server_id']}`\nCanal: `{CONFIG['target_channel_id']}`", inline=False)
    embed.add_field(name="⏱️ Tempo restante", value=get_remaining_time(), inline=False)
    embed.set_footer(text="Use !stop para parar o espelhamento")
    
    await ctx.send(embed=embed)
    print(f"🟢 Espelhamento INICIADO por {ctx.author}")

@bot.command(name='stop')
@is_authorized()
async def stop_mirror(ctx):
    """Para o espelhamento de mensagens"""
    if not CONFIG["bot_active"]:
        await ctx.send("⚠️ O bot já está inativo!")
        return
    
    CONFIG["bot_active"] = False
    
    embed = discord.Embed(
        title="🛑 Espelhamento Parado!",
        description="O bot parou de copiar mensagens.",
        color=0xff0000
    )
    embed.add_field(name="ℹ️ Info", value="Use `!start` para reativar o espelhamento", inline=False)
    embed.set_footer(text="Bot em standby")
    
    await ctx.send(embed=embed)
    print(f"🔴 Espelhamento PARADO por {ctx.author}")

@bot.command(name='status')
@is_authorized()
async def check_status(ctx):
    """Verifica o status atual do bot"""
    status_emoji = "🟢" if CONFIG["bot_active"] else "🔴"
    status_text = "Ativo" if CONFIG["bot_active"] else "Inativo"
    
    embed = discord.Embed(
        title=f"{status_emoji} Status do Bot",
        description=f"Estado atual: **{status_text}**",
        color=0x00ff00 if CONFIG["bot_active"] else 0xff0000
    )
    embed.add_field(name="⚡ Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Servidores", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="⏱️ Tempo restante", value=get_remaining_time(), inline=True)
    embed.add_field(name="📥 Canal Origem", value=f"`{CONFIG['source_channel_id']}`", inline=True)
    embed.add_field(name="📤 Canal Destino", value=f"`{CONFIG['target_channel_id']}`", inline=True)
    embed.set_footer(text="Galaxy Scripts Bot")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)

@tasks.loop(minutes=1)
async def time_counter():
    """Atualiza o contador de tempo a cada minuto"""
    remaining = get_remaining_time()
    print(f"⏱️ Tempo restante: {remaining} | Bot ativo: {CONFIG['bot_active']}")

@tasks.loop(minutes=5)
async def auto_restart_check():
    """Verifica se está próximo do limite e prepara para reiniciar"""
    if CONFIG["start_time"] is None:
        return
    
    elapsed = datetime.now() - CONFIG["start_time"]
    remaining = timedelta(hours=UPTIME_HOURS) - elapsed
    
    # Se faltam menos de 10 minutos, avisa
    if remaining.total_seconds() <= 600 and remaining.total_seconds() > 0:
        print(f"⚠️ AVISO: Bot vai reiniciar em {get_remaining_time()}")
    
    # Se passou do tempo, reinicia
    if remaining.total_seconds() <= 0:
        print("🔄 Reiniciando bot...")
        CONFIG["start_time"] = datetime.now()
        await asyncio.sleep(3)  # Aguarda 3 segundos
        print("✅ Bot reiniciado!")

@time_counter.before_loop
async def before_time_counter():
    await bot.wait_until_ready()

@auto_restart_check.before_loop
async def before_auto_restart():
    await bot.wait_until_ready()

# Tratamento de erros
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # Já foi tratado no decorator
        return
    elif isinstance(error, commands.CommandNotFound):
        return  # Ignora comandos não encontrados
    else:
        print(f"❌ Erro no comando: {error}")
        await ctx.send(f"❌ Ocorreu um erro: {str(error)}")

# Iniciar o bot
if __name__ == "__main__":
    TOKEN = os.getenv('TOKEN')
    if not TOKEN:
        print("❌ TOKEN não encontrado! Configure no Replit Secrets.")
    else:
        print("🚀 Iniciando Galaxy Scripts Bot...")
        bot.run(TOKEN)
