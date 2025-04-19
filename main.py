import yaml
import logging

def main():
    with open("config/settings.yaml", "r") as file:
        settings = yaml.safe_load(file)
    
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Loaded settings: {settings}")

if __name__ == "__main__":
    main()
