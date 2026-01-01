from aiohttp import web
import aiohttp_jinja2
import jinja2
import asyncio
from database import db
import logging

logging.basicConfig(level=logging.INFO)

async def handle_index(request):
    return aiohttp_jinja2.render_template('index.html', request, {})

async def handle_style(request):
    return web.FileResponse('./style.css')

async def handle_script(request):
    return web.FileResponse('./script.js')

async def handle_api_inventory(request):
    user_id = request.query.get('user_id')
    if not user_id:
        return web.json_response({'error': 'user_id required'}, status=400)
    
    try:
        user_id = int(user_id)
        inventory = db.get_user_inventory(user_id)
        return web.json_response({'inventory': inventory})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def start_web_app():
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./'))
    
    app.router.add_get('/', handle_index)
    app.router.add_get('/style.css', handle_style)
    app.router.add_get('/script.js', handle_script)
    app.router.add_get('/api/inventory', handle_api_inventory)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("Web app started on http://0.0.0.0:8080")
    return runner

async def main():
    web_runner = await start_web_app()
    try:
        await asyncio.Event().wait()
    finally:
        await web_runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())