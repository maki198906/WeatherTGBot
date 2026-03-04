## WeWeather TG Bot

<img src="weather.png" style="height: 100px; width:100px"/>

A Telegram weather bot powered by [OpenWeather API](https://openweathermap.org/api) and built with [aiogram 3](https://docs.aiogram.dev/).

Try it live: **[@NeedWeatherInPlaceBot](https://t.me/NeedWeatherInPlaceBot)**

## Features

- 🌡 **Current weather** by city name or GPS location
- 📅 **5-day forecast** with daily breakdown
- 💨 Wind speed, 🔽 pressure, 💧 humidity included in every response
- 🗺 **Map link** to OpenWeatherMap for every weather result
- 🎲 **Random weather** — discover weather anywhere on Earth
- ❤️ **Favourite cities** — save up to 3 cities for one-tap access
- ⏰ **Daily subscription** — receive weather every day at your chosen local time
- 🔍 **Inline mode** — share weather in any chat by typing `@NeedWeatherInPlaceBot <city>`

## Commands

| Command | Description |
|---|---|
| `<city name>` | Current weather for any city |
| `/inplace` | Share GPS location for local weather |
| `/forecast <city>` | 5-day forecast |
| `/random` | Weather at a random location |
| `/save <city>` | Save a city to favourites (max 3) |
| `/my` | Show saved cities as tappable buttons |
| `/remove <city>` | Remove a city from favourites |
| `/subscribe <city> <HH:MM>` | Daily weather at a set local time |
| `/unsubscribe` | Cancel daily subscription |
| `/mysub` | Show current subscription |

## Setup

### 1. Clone and install

```bash
git clone https://github.com/maki198906/WeatherTGBot.git
cd WeatherTGBot
pip install -r requirements.txt
```

### 2. Create `.env`

```env
TELEGRAM_API_TOKEN=your_telegram_bot_token
OPEN_WEATHER_API_TOKEN=your_openweather_api_key
```

- **Telegram token**: message [@BotFather](https://t.me/BotFather) → `/newbot`
- **OpenWeather key**: [openweathermap.org/api](https://openweathermap.org/api) (free tier is sufficient)

### 3. Run

```bash
python server.py
```

The bot creates `favourites.db` (SQLite) automatically on first run — no database setup needed.

## Docker

```bash
docker build -t tgweather .

docker run -d --name tgbot \
  -e TELEGRAM_API_TOKEN=your_token \
  -e OPEN_WEATHER_API_TOKEN=your_token \
  tgweather
```

## Project Structure

```
WeatherTGBot/
├── server.py               # Bot entry point — all handlers
├── weather_api_service.py  # OpenWeather API calls and data models
├── weather_repr.py         # Weather data → readable text
├── favourites.py           # Favourite cities (SQLite)
├── subscriptions.py        # Daily subscriptions (SQLite)
├── scheduler.py            # APScheduler — background daily jobs
├── timezoneutils.py        # Sunrise/sunset and timezone helpers
├── random_weather.py       # Random coordinate generator
├── exceptions.py           # Custom exceptions
├── requirements.txt
├── Dockerfile
├── favourites.db           # Auto-created on first run (not committed)
└── .env                    # Not committed — create manually
```
