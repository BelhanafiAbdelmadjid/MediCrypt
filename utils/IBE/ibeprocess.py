import subprocess
import json
import base64
import os

def run_go_program(command, input_data=None):
    process = subprocess.Popen(
        ["go", "run", "./utils/IBE/ibe.go", command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=json.dumps(input_data) if input_data else None)
    
    if process.returncode != 0:
        print(f"Erreur Go: {stderr.strip()}")
        return None
    
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(f"Erreur lors de l'analyse JSON de la sortie Go: {stdout.strip()}")
        return None

def generate_keys(identity):
    result = run_go_program("generate_keys", {"identity": identity})
    # if result:
    #     print(f"Clé privée générée pour {identity}.")

def encrypt(identity, message):
    encoded_message = base64.b64encode(message.encode()).decode()
    result = run_go_program("encrypt", {"identity": identity, "message": encoded_message})
    if result:
        # print("Message chiffré:", result["ciphertext"])
        return result["ciphertext"]
    return None

def decrypt(identity, ciphertext):
    result = run_go_program("decrypt", {"identity": identity, "ciphertext": ciphertext})
    if result:
        plaintext = base64.b64decode(result["plaintext"]).decode("utf-8")
        # print("Message déchiffré:", plaintext)
        return plaintext
    return None

def main():
    while True:
        print("\nMenu:")
        print("1. Générer une clé privée")
        print("2. Chiffrer un message")
        print("3. Déchiffrer un message")
        print("4. Quitter")
        
        choix = input("Choisissez une option: ")
        
        if choix == "1":
            email = input("Entrez l'email pour générer la clé: ")
            generate_keys(email)
        
        elif choix == "2":
            email = input("Entrez l'email utilisé pour le chiffrement: ")
            message = input("Entrez le message à chiffrer: ")
            encrypt(email, message)
        
        elif choix == "3":
            email = input("Entrez l'email utilisé pour le déchiffrement: ")
            ciphertext = input("Entrez le message chiffré: ")
            decrypt(email, ciphertext)
        
        elif choix == "4":
            print("Au revoir !")
            break
        else:
            print("Option invalide, veuillez réessayer.")

if __name__ == "__main__":
    main()
