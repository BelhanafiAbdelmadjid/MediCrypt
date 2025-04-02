import unittest
import json
import sys
import os

# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app import app, db

from models import ProfilMedical, MedecinTraitant, Utilisateur
from utils.cryptIT import encryptDossier,decryptDossier





class TestEncryption(unittest.TestCase):

    def setUp(self):
        # Sample email and dossier for testing
        self.email = "medecin@test.com"
        self.dossier = {"key": "value"}  # Sample JSON data

    def test_encrypt_dossier(self):
        # Encrypt the dossier
        encrypted_dossier = encryptDossier(self.email, self.dossier)
        
        # Ensure the encrypted dossier is returned and is in bytes format (assuming encryption returns bytes)
        self.assertIsNotNone(encrypted_dossier)
        self.assertIsInstance(encrypted_dossier, str)  # Adjust according to the actual encryption output

    def test_decrypt_dossier(self):
        # Encrypt the dossier first
        encrypted_dossier = encryptDossier(self.email, self.dossier)
        print(encrypted_dossier)
        
        # Decrypt the encrypted dossier
        decrypted_dossier = decryptDossier(self.email, encrypted_dossier)
        print(decrypted_dossier)
        
        # Ensure the decrypted dossier matches the original JSON data
        self.assertEqual(decrypted_dossier, self.dossier)

if __name__ == "__main__":
    unittest.main()

