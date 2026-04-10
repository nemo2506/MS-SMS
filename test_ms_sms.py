from ms_sms import MessagePlugin, APIError

plugin = MessagePlugin(
    base_url="http://192.168.1.39:8086",
    bearer_token="dab92e57a751455cbe5ef96d0c0a93d8",
    sender_id="",   # optionnel
)

# SMS simple
result = plugin.send(recipient="0634058195", text="Bonjour !", image_path="/home/marc/data/photos/saule-images/snap-1775469610980.jpg")
print(result)