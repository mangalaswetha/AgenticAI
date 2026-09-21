from app.db import get_client

client = get_client()

# Test reading members
result = client.schema("library").table("member").select("*").execute()
print("Members found:", len(result.data))
print(result.data)