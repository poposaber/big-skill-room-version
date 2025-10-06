import client

c = client.Client()
c.connect_to_lobby_server(host="linux1.cs.nycu.edu.tw")
c.interact_to_lobby_server()
