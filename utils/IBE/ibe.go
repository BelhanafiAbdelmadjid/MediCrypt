package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"v.io/x/lib/ibe"
)

const keyFile = "ibe_keys.json"

type Request struct {
	Identity   string `json:"identity"`
	Message    string `json:"message,omitempty"`
	Ciphertext string `json:"ciphertext,omitempty"`
}

type Response struct {
	Result     string `json:"result,omitempty"`
	Ciphertext string `json:"ciphertext,omitempty"`
	Plaintext  string `json:"plaintext,omitempty"`
	Error      string `json:"error,omitempty"`
}

type StoredKeys struct {
	MasterData  []byte            `json:"master"`
	ParamsData  []byte            `json:"params"`
	PrivateKeys map[string][]byte `json:"private_keys"`
}

// Sauvegarde les clés dans un fichier JSON
func saveKeys(keys StoredKeys) error {
	data, err := json.Marshal(keys)
	if err != nil {
		return err
	}
	return os.WriteFile(keyFile, data, 0644)
}

// Charge les clés depuis le fichier JSON
func loadKeys() (StoredKeys, error) {
	var keys StoredKeys
	data, err := os.ReadFile(keyFile)
	if err != nil {
		return keys, err
	}
	err = json.Unmarshal(data, &keys)
	return keys, err
}

func generateParams() (ibe.Master, ibe.Params, error) {
	keys, err := loadKeys()
	if err == nil {
		params, err := ibe.UnmarshalParams(keys.ParamsData)
		if err != nil {
			return nil, nil, err
		}
		master, err := ibe.UnmarshalMasterKey(params, keys.MasterData)
		if err != nil {
			return nil, nil, err
		}
		return master, params, nil
	}

	master, err := ibe.SetupBB1()
	if err != nil {
		return nil, nil, err
	}

	params := master.Params()
	masterBytes, _ := ibe.MarshalMasterKey(master)
	paramsBytes, _ := ibe.MarshalParams(params)

	keys = StoredKeys{
		MasterData:  masterBytes,
		ParamsData:  paramsBytes,
		PrivateKeys: make(map[string][]byte),
	}
	saveKeys(keys)

	return master, params, nil
}

func generatePrivateKey(master ibe.Master, identity string) (ibe.PrivateKey, error) {
	keys, _ := loadKeys()
	if privKeyData, exists := keys.PrivateKeys[identity]; exists {
		privKey, err := ibe.UnmarshalPrivateKey(master.Params(), privKeyData)
		if err != nil {
			return nil, err
		}
		return privKey, nil
	}

	privKey, err := master.Extract(identity)
	if err != nil {
		return nil, err
	}

	privKeyBytes, _ := ibe.MarshalPrivateKey(privKey)
	keys.PrivateKeys[identity] = privKeyBytes
	saveKeys(keys)

	return privKey, nil
}

func encryptMessage(params ibe.Params, identity string, message []byte) (string, error) {
	ciphertext := make([]byte, len(message)+176) // Taille fixe de l'overhead pour IBE
	err := params.Encrypt(identity, message, ciphertext)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func decryptMessage(privKey ibe.PrivateKey, ciphertext string) (string, error) {
	ciphertextBytes, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return "", err
	}

	// Définition d'un buffer pour stocker le message déchiffré
	plaintext := make([]byte, len(ciphertextBytes)-176) // Taille du message après suppression de l'overhead IBE
	err = privKey.Decrypt(ciphertextBytes, plaintext)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}

func main() {
	decoder := json.NewDecoder(os.Stdin)
	var req Request
	err := decoder.Decode(&req)
	if err != nil {
		log.Fatalf("Erreur lors de la lecture de l'entrée JSON: %v", err)
	}

	master, params, err := generateParams()
	if err != nil {
		log.Fatalf("Erreur lors de la génération des paramètres IBE: %v", err)
	}

	switch os.Args[1] {
	case "generate_keys":
		_, err := generatePrivateKey(master, req.Identity)
		if err != nil {
			log.Fatalf("Erreur lors de l'extraction de la clé privée: %v", err)
		}
		fmt.Println(`{"result": "Clé privée générée pour ` + req.Identity + `"}`)

	case "encrypt":
		messageBytes, _ := base64.StdEncoding.DecodeString(req.Message)
		ciphertext, err := encryptMessage(params, req.Identity, messageBytes)
		if err != nil {
			log.Fatalf("Erreur lors du chiffrement: %v", err)
		}
		fmt.Println(`{"ciphertext": "` + ciphertext + `"}`)

	case "decrypt":
		privKey, err := generatePrivateKey(master, req.Identity)
		if err != nil {
			log.Fatalf("Erreur lors de la récupération de la clé privée: %v", err)
		}
		plaintext, err := decryptMessage(privKey, req.Ciphertext)
		if err != nil {
			log.Fatalf("Erreur lors du déchiffrement: %v", err)
		}

		encodedPlaintext := base64.StdEncoding.EncodeToString([]byte(plaintext))
		fmt.Println(`{"plaintext": "` + encodedPlaintext + `"}`)

	default:
		log.Fatalf("Commande non reconnue")
	}
}
