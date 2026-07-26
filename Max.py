from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
import asyncio

# Bot Configuration - Tera Token
BOT_TOKEN = "8504226443:AAHNZDKZISgUjVxktp6AFziscQzzZHtdSIE"

# Admin IDs - Teri ID
ADMIN_IDS = [8102646437]

app = Client(
    "request_bot",
    bot_token=BOT_TOKEN
)

# Dictionary to store pending requests for all channels
pending_requests = {}  # {channel_id: {user_id: {user, request}}}

# Get all admin channels where bot is admin
async def get_admin_channels():
    admin_channels = []
    try:
        async for dialog in app.get_dialogs():
            if dialog.chat.type in ["channel", "supergroup"]:
                try:
                    member = await app.get_chat_member(dialog.chat.id, "me")
                    if member.status in ["administrator", "creator"]:
                        admin_channels.append(dialog.chat.id)
                        print(f"📢 Admin in: {dialog.chat.title} ({dialog.chat.id})")
                except:
                    pass
        return admin_channels
    except Exception as e:
        print(f"❌ Error getting channels: {e}")
        return []

# Load pending requests from all admin channels
async def load_all_pending_requests():
    print("🔍 Loading pending requests from all channels...")
    
    admin_channels = await get_admin_channels()
    if not admin_channels:
        print("❌ Bot is not admin in any channel!")
        return 0
    
    total_count = 0
    
    for channel_id in admin_channels:
        try:
            channel_pending = []
            async for request in app.get_chat_join_requests(channel_id):
                user = request.from_user
                channel_pending.append({
                    'user': user,
                    'request': request
                })
            
            if channel_pending:
                pending_requests[channel_id] = {}
                for data in channel_pending:
                    user = data['user']
                    pending_requests[channel_id][user.id] = data
                    total_count += 1
                    print(f"📋 Pending in channel {channel_id}: {user.first_name} (@{user.username if user.username else 'N/A'})")
                
                print(f"📋 Channel {channel_id}: {len(channel_pending)} pending requests")
            
        except Exception as e:
            print(f"❌ Error loading requests from {channel_id}: {e}")
    
    print(f"📋 Total pending requests loaded: {total_count}")
    return total_count

# Start command
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    # Check if user is admin
    is_admin = user_id in ADMIN_IDS
    
    # Get admin channels
    admin_channels = await get_admin_channels()
    
    # Count total pending
    total_pending = sum(len(reqs) for reqs in pending_requests.values())
    
    text = f"🤖 **Multi-Channel Request Bot**\n\n"
    text += f"📢 Admin in {len(admin_channels)} channels\n"
    text += f"📋 Total Pending: {total_pending}\n"
    text += f"👤 Your ID: `{user_id}`\n\n"
    
    if is_admin:
        text += f"**Admin Commands:**\n"
        text += f"/approve - Approve all pending in ALL channels\n"
        text += f"/pending - Show pending requests\n"
        text += f"/channels - Show admin channels\n"
        text += f"/refresh - Reload pending from all channels\n"
        text += f"/clear - Clear pending list\n\n"
        text += f"⚠️ Bot will NOT auto-approve new requests!"
    else:
        text += f"⏳ Your request status: Pending\n"
        text += f"📢 Admin will approve manually."
    
    await message.reply(text)

# Approve all pending requests from all channels
@app.on_message(filters.command("approve") & filters.user(ADMIN_IDS))
async def approve_all(client, message):
    if not pending_requests:
        await message.reply("📭 No pending requests in any channel!")
        return
    
    total_pending = sum(len(reqs) for reqs in pending_requests.values())
    msg = await message.reply(f"🔄 Approving {total_pending} pending requests from all channels...")
    
    total_accepted = 0
    total_failed = 0
    channel_stats = {}
    
    for channel_id, requests in list(pending_requests.items()):
        channel_accepted = 0
        channel_failed = 0
        
        for user_id, data in list(requests.items()):
            try:
                request = data['request']
                user = data['user']
                
                # Approve the request
                await request.approve()
                channel_accepted += 1
                total_accepted += 1
                
                print(f"✅ Approved: {user.first_name} from channel {channel_id}")
                
                # Notify user
                try:
                    await client.send_message(
                        user.id,
                        f"✅ **Congratulations!**\n\n"
                        f"Your request to join the channel has been approved!\n"
                        f"🎉 Welcome to the community!"
                    )
                except:
                    pass
                
                await asyncio.sleep(0.3)  # Rate limit
                
            except Exception as e:
                channel_failed += 1
                total_failed += 1
                print(f"❌ Error approving {user_id}: {e}")
        
        channel_stats[channel_id] = {
            'accepted': channel_accepted,
            'failed': channel_failed
        }
    
    # Clear all pending requests
    pending_requests.clear()
    
    # Create response
    response = f"✅ **Approval Complete!**\n\n"
    response += f"✅ Total Accepted: {total_accepted}\n"
    response += f"❌ Total Failed: {total_failed}\n\n"
    
    response += "📊 **Channel-wise Stats:**\n"
    for channel_id, stats in channel_stats.items():
        try:
            chat = await client.get_chat(channel_id)
            channel_name = chat.title
        except:
            channel_name = f"Channel {channel_id}"
        
        response += f"📢 {channel_name}: {stats['accepted']} accepted, {stats['failed']} failed\n"
    
    await msg.edit_text(response)

# Show pending requests
@app.on_message(filters.command("pending") & filters.user(ADMIN_IDS))
async def show_pending(client, message):
    if not pending_requests:
        await message.reply("📭 No pending requests in any channel!")
        return
    
    total_pending = sum(len(reqs) for reqs in pending_requests.values())
    text = f"📋 **Pending Requests** (Total: {total_pending})\n\n"
    
    count = 0
    for channel_id, requests in list(pending_requests.items()):
        try:
            chat = await client.get_chat(channel_id)
            channel_name = chat.title
        except:
            channel_name = f"Channel {channel_id}"
        
        text += f"📢 **{channel_name}** ({len(requests)} pending)\n"
        
        for user_id, data in list(requests.items())[:5]:  # Show first 5
            user = data['user']
            count += 1
            text += f"  {count}. 👤 {user.first_name}\n"
            text += f"     🆔 `{user_id}`\n"
            text += f"     @{user.username if user.username else 'No username'}\n"
        
        if len(requests) > 5:
            text += f"  ... and {len(requests) - 5} more\n"
        
        text += "\n"
        
        if count >= 20:  # Limit total display
            text += f"... and {total_pending - count} more total"
            break
    
    await message.reply(text)

# Show admin channels
@app.on_message(filters.command("channels") & filters.user(ADMIN_IDS))
async def show_channels(client, message):
    admin_channels = await get_admin_channels()
    
    if not admin_channels:
        await message.reply("❌ Bot is not admin in any channel!")
        return
    
    text = "📢 **Admin Channels:**\n\n"
    
    for channel_id in admin_channels:
        try:
            chat = await client.get_chat(channel_id)
            channel_name = chat.title
            members = await client.get_chat_members_count(channel_id)
            pending = len(pending_requests.get(channel_id, {}))
            
            text += f"📢 {channel_name}\n"
            text += f"   🆔 `{channel_id}`\n"
            text += f"   👥 Members: {members}\n"
            text += f"   📋 Pending: {pending}\n\n"
        except:
            text += f"📢 Channel {channel_id}\n\n"
    
    await message.reply(text)

# Refresh pending requests
@app.on_message(filters.command("refresh") & filters.user(ADMIN_IDS))
async def refresh_pending(client, message):
    msg = await message.reply("🔄 Refreshing pending requests from all channels...")
    
    # Clear current list
    pending_requests.clear()
    
    # Reload from all admin channels
    total = await load_all_pending_requests()
    
    await msg.edit_text(f"✅ Refreshed! Found {total} pending requests across all channels.")

# Clear pending list
@app.on_message(filters.command("clear") & filters.user(ADMIN_IDS))
async def clear_pending(client, message):
    total = sum(len(reqs) for reqs in pending_requests.values())
    pending_requests.clear()
    await message.reply(f"🗑️ Cleared {total} pending requests from memory!")

# Handle new join requests
@app.on_chat_join_request()
async def handle_join_request(client, request: ChatJoinRequest):
    user = request.from_user
    channel_id = request.chat.id
    
    # Check if bot is admin in this channel
    try:
        member = await client.get_chat_member(channel_id, "me")
        if member.status not in ["administrator", "creator"]:
            return  # Bot is not admin, ignore
    except:
        return
    
    # Initialize channel in pending_requests if not exists
    if channel_id not in pending_requests:
        pending_requests[channel_id] = {}
    
    # Store in pending requests
    pending_requests[channel_id][user.id] = {
        'user': user,
        'request': request
    }
    
    print(f"📥 New request from: {user.first_name} in channel {channel_id}")
    print(f"📋 Total pending: {sum(len(reqs) for reqs in pending_requests.values())}")
    
    # Notify user
    try:
        await client.send_message(
            user.id,
            f"✅ Your request to join has been received!\n\n"
            f"⏳ Please wait for admin approval.\n"
            f"You will be notified once approved."
        )
    except:
        pass
    
    # Notify admins about new request
    for admin_id in ADMIN_IDS:
        try:
            chat = await client.get_chat(channel_id)
            await client.send_message(
                admin_id,
                f"🔔 **New Join Request**\n\n"
                f"📢 Channel: {chat.title}\n"
                f"👤 User: {user.first_name}\n"
                f"🆔 ID: `{user.id}`\n"
                f"👤 @{user.username if user.username else 'N/A'}\n"
                f"📋 Pending: {sum(len(reqs) for reqs in pending_requests.values())}\n\n"
                f"Use /approve to approve all!"
            )
        except:
            pass

# Status command
@app.on_message(filters.command("status"))
async def status(client, message):
    admin_channels = await get_admin_channels()
    total_pending = sum(len(reqs) for reqs in pending_requests.values())
    
    text = f"📊 **Bot Status**\n\n"
    text += f"📢 Admin in {len(admin_channels)} channels\n"
    text += f"📋 Pending requests: {total_pending}\n"
    text += f"🤖 Auto-approve: ❌ Disabled\n"
    text += f"👥 Admins: {len(ADMIN_IDS)}\n\n"
    text += f"⚠️ New requests will be stored, not auto-approved.\n"
    text += f"📢 Use /approve to approve all pending requests."
    
    await message.reply(text)

# Main function
async def main():
    await app.start()
    
    print("\n" + "="*60)
    print("🤖 MULTI-CHANNEL REQUEST BOT STARTED!")
    print("="*60)
    
    # Get all admin channels
    admin_channels = await get_admin_channels()
    
    if not admin_channels:
        print("❌ Bot is not admin in any channel!")
        print("⚠️ Add bot as admin in channels with 'Approve members' permission!")
    else:
        print(f"✅ Bot is admin in {len(admin_channels)} channels")
        for channel_id in admin_channels:
            try:
                chat = await app.get_chat(channel_id)
                print(f"   📢 {chat.title} ({channel_id})")
            except:
                print(f"   📢 Channel {channel_id}")
    
    # Load existing pending requests
    total = await load_all_pending_requests()
    
    print("\n" + "="*60)
    print("✅ Bot is ready!")
    print(f"📋 Total pending requests: {total}")
    print("⚠️ Auto-approve: DISABLED")
    print("📢 Use /approve to approve all pending requests")
    print("="*60)
    print("\nAdmin Commands:")
    print("  /approve - Approve all pending in ALL channels")
    print("  /pending - Show pending requests")
    print("  /channels - Show admin channels")
    print("  /refresh - Reload pending from all channels")
    print("  /clear - Clear pending list")
    print("  /status - Check bot status")
    print("\n" + "="*60)
    
    await idle()

if __name__ == "__main__":
    app.run()
