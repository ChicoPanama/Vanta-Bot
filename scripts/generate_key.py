from cryptography.fernet import Fernet

# Generate a key
key = Fernet.generate_key()
print(f"Your encryption key: {key.decode()}")
print("Add this to your .env file as ENCRYPTION_KEY")