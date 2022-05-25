# crypto-exporter

Scrape crypto price data from coingecko, see config.example.yml for examples.

There is also some supports for scraping wallet data from ubiquity api from blockdaemon.

Exporter will by default expose an port on 8000 and scrape the data that's configured in config.yml

# Blockdaemon API
Get your free API key here: https://blockdaemon.com/platform/ubiquity/

# Requirements
## Local 
- Python3
- pip3

## Docker
- Docker
- Docker-compose

# Run in Docker-compose
Running docker compose will expose grafana on http://localhost:300
``` 
cp config.example.yml config.yml
docker-compose build && docker-compose up -d
```

# Run local

```shell
pip install -r requirements.txt
cp config.example.yml config.yml
python main.py

curl http://localhost:8000
```

# Run in Docker
```shell
cp config.example.yml config.yml
docker build . -t cryptoexporter:latest
docker run -d --rm --name -v ./config.yml:/usr/app/src/config.yml cryptoexporter cryptoexporter:latest 

curl http://localhost:8000
```

