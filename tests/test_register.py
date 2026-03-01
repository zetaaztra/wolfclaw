from api.routes.auth import register, RegisterRequest
import asyncio
r=RegisterRequest(email='test@test.com', password='pass')
print(asyncio.run(register(r)))
