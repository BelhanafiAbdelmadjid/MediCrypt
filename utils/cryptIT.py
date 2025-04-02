from .IBE.ibeprocess import generate_keys as IBE_generate_keys    
from .IBE.ibeprocess import encrypt as IBE_encrypt 
from .IBE.ibeprocess import decrypt as IBE_decrypt
import json
import base64
from app import db


def encryptDossier(email, dossier):
    # Convert the Dossier (JSON) to a string
    dossier_json = json.dumps(dossier)
    
    # Encrypt the Dossier string
    encrypted_dossier = IBE_encrypt(email, dossier_json)  # Assuming email is the identity

    if encrypted_dossier:
        return encrypted_dossier
    else:
        print("Erreur lors du chiffrement du Dossier.")
        return None


def decryptDossier(email, encrypted_dossier):
    # Decrypt the Dossier string using the provided email as the identity
    decrypted_dossier = IBE_decrypt(email, encrypted_dossier)

    if decrypted_dossier:
        # Convert the decrypted string back into a JSON object
        return json.loads(decrypted_dossier)
    else:
        print("Erreur lors du déchiffrement du Dossier.")
        return None