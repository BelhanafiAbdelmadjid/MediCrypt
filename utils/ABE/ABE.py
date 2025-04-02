import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64

class ABESystem:
    def __init__(self):
        self.attributes = ["MEDECIN", "LABORANTIN", "RADIOLOGUE", "PATIENT"]
        self.master_key = os.urandom(32)
        self.user_keys = {}
        self.encrypted_messages = []
    
    def generate_user_key(self, user_id, user_attributes):
        """Génère une clé utilisateur basée sur ses attributs"""
        for attr in user_attributes:
            if attr.upper() not in self.attributes:
                raise ValueError(f"Attribut invalide: {attr}")
                
        salt = os.urandom(16)
        info = b"".join([attr.encode() for attr in user_attributes])
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
            backend=default_backend()
        )
        
        user_key = hkdf.derive(self.master_key)
        
        self.user_keys[user_id] = {
            "attributes": [attr.upper() for attr in user_attributes],
            "key": base64.b64encode(user_key).decode(),
            "salt": base64.b64encode(salt).decode()
        }
        
        return self.user_keys[user_id]
    
    def encrypt(self, message, access_policy):
        """Chiffre un message avec une politique d'accès"""
        policy_attrs = [attr.upper() for attr in access_policy.split(" OR ")]
        for attr in policy_attrs:
            if attr not in self.attributes:
                raise ValueError(f"Attribut invalide dans la politique: {attr}")
                
        encryption_key = os.urandom(32)
        iv = os.urandom(16)
        
        cipher = Cipher(
            algorithms.AES(encryption_key),
            modes.CFB(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted_msg = encryptor.update(message.encode()) + encryptor.finalize()
        
        encrypted_data = {
            "message": base64.b64encode(encrypted_msg).decode(),
            "iv": base64.b64encode(iv).decode(),
            "access_policy": access_policy,
            "policy_attrs": policy_attrs,  # Sauvegarde des attributs de politique
            "encryption_key": self._wrap_key(encryption_key, policy_attrs)
        }
        
        self.encrypted_messages.append(encrypted_data)
        return encrypted_data
    
    def _wrap_key(self, key, policy_attrs):
        wrapped_keys = {}
        
        for attr in policy_attrs:
            salt = os.urandom(16)
            info = attr.encode()
            
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                info=info,
                backend=default_backend()
            )
            
            wrapping_key = hkdf.derive(self.master_key)
            iv = bytes(16)
            cipher = Cipher(
                algorithms.AES(wrapping_key),
                modes.CFB(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            wrapped_key = encryptor.update(key) + encryptor.finalize()
            
            wrapped_keys[attr] = {
                "wrapped_key": base64.b64encode(wrapped_key).decode(),
                "salt": base64.b64encode(salt).decode(),
                "attribute": attr  # Sauvegarde de l'attribut
            }
        
        return wrapped_keys
    
    def decrypt(self, user_id, encrypted_data):
        if user_id not in self.user_keys:
            raise ValueError("Utilisateur inconnu")
            
        user_attrs = self.user_keys[user_id]["attributes"]
        policy_attrs = encrypted_data["policy_attrs"]  # Chargé depuis le JSON
        
        if not set(user_attrs).intersection(set(policy_attrs)):
            raise ValueError("Accès refusé: attributs insuffisants")
            
        matching_attr = next(attr for attr in user_attrs if attr in policy_attrs)
        
        wrapped_key_data = encrypted_data["encryption_key"][matching_attr]
        wrapped_key = base64.b64decode(wrapped_key_data["wrapped_key"])
        salt = base64.b64decode(wrapped_key_data["salt"])
        
        info = matching_attr.encode()
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
            backend=default_backend()
        )
        wrapping_key = hkdf.derive(self.master_key)
        
        iv = bytes(16)
        cipher = Cipher(
            algorithms.AES(wrapping_key),
            modes.CFB(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        encryption_key = decryptor.update(wrapped_key) + decryptor.finalize()
        
        iv = base64.b64decode(encrypted_data["iv"])
        encrypted_msg = base64.b64decode(encrypted_data["message"])
        
        cipher = Cipher(
            algorithms.AES(encryption_key),
            modes.CFB(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_msg = decryptor.update(encrypted_msg) + decryptor.finalize()
        
        return decrypted_msg.decode()
    
    def save_to_json(self, filename):
        """Sauvegarde complète du système dans un fichier JSON"""
        data = {
            "system_info": {
                "attributes": self.attributes,
                "master_key": base64.b64encode(self.master_key).decode()
            },
            "user_keys": self.user_keys,
            "encrypted_messages": self.encrypted_messages
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_json(self, filename):
        """Charge le système depuis un fichier JSON"""
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.attributes = data["system_info"]["attributes"]
        self.master_key = base64.b64decode(data["system_info"]["master_key"])
        self.user_keys = data["user_keys"]
        self.encrypted_messages = data["encrypted_messages"]

def interactive_test():
    abe = ABESystem()
    print("Système de chiffrement médical basé sur les attributs")
    
    while True:
        print("\n=== Menu ===")
        print("1. Générer une clé utilisateur")
        print("2. Chiffrer un message")
        print("3. Déchiffrer un message")
        print("4. Afficher les messages")
        print("5. Sauvegarder dans JSON")
        print("6. Charger depuis JSON")
        print("7. Quitter")
        
        choice = input("Choix: ")
        
        if choice == "1":
            user_id = input("ID utilisateur: ")
            attrs = input("Attributs (séparés par virgule): ").split(",")
            attrs = [a.strip().upper() for a in attrs]
            try:
                abe.generate_user_key(user_id, attrs)
                print(f"Utilisateur {user_id} créé avec attributs: {attrs}")
            except Exception as e:
                print(f"Erreur: {e}")
        
        elif choice == "2":
            message = input("Message à chiffrer: ")
            print("Attributs disponibles:", ", ".join(abe.attributes))
            policy = input("Politique d'accès (ex: 'MEDECIN OR LABORANTIN'): ")
            try:
                encrypted = abe.encrypt(message, policy)
                print(f"Message chiffré (ID: {len(abe.encrypted_messages)-1})")
                print("Politique:", encrypted["access_policy"])
            except Exception as e:
                print(f"Erreur: {e}")
        
        elif choice == "3":
            user_id = input("ID utilisateur: ")
            msg_id = int(input("ID du message: "))
            try:
                decrypted = abe.decrypt(user_id, abe.encrypted_messages[msg_id])
                print("Message déchiffré:", decrypted)
            except Exception as e:
                print(f"Erreur: {e}")
        
        elif choice == "4":
            print("\nMessages chiffrés:")
            for i, msg in enumerate(abe.encrypted_messages):
                print(f"[{i}] Politique: {msg['access_policy']}")
                print(f"    Message: {msg['message'][:30]}...")
        
        elif choice == "5":
            filename = input("Nom du fichier JSON: ")
            abe.save_to_json(filename)
            print("Système sauvegardé avec succès!")
        
        elif choice == "6":
            filename = input("Nom du fichier JSON: ")
            try:
                abe.load_from_json(filename)
                print("Système chargé avec succès!")
                print("Attributs disponibles:", ", ".join(abe.attributes))
            except Exception as e:
                print(f"Erreur: {e}")
        
        elif choice == "7":
            break
        
        else:
            print("Choix invalide")

if __name__ == "__main__":
    interactive_test()