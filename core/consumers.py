from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.restaurant_code = self.scope['url_route']['kwargs']['restaurant_code']
        self.room_group_name = f'orders_{self.restaurant_code}'
        
        # Obtendo o usuário da scope
        self.user = self.scope['user']

        # Verifica se o usuário pertence ao grupo "Garçon"
        if self.user.is_authenticated and await self.user_in_group('Garçons'):
            await self.close()
            return  # Certifique-se de retornar aqui para evitar adicionar o consumidor ao grupo

        # Adiciona o consumidor ao grupo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Remove o consumidor do grupo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def new_order(self, event):
        message = event['message']
        order = event['order']  # Certifique-se de que o pedido está sendo passado aqui

        # Envia a mensagem para o WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'message': message,
            'order': order  # Incluindo os detalhes do pedido
        }))
        
    async def new_order_table(self, event):
        message = event['message']
        order = event['order']

        # Envie a mensagem de volta para o WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_order_table',
            'message': message,
            'order': order
        }))

    async def receive(self, text_data):
        # Você pode lidar com mensagens recebidas aqui, se necessário
        pass

    @database_sync_to_async
    def user_in_group(self, group_name):
        return self.user.groups.filter(name=group_name).exists()
