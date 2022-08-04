## This is WeWeather TG Bot that shows the weather and more around you

<img src="weather.png" style="height: 100px; width:100px"/>


This bot utilizes your GPS coordinates/ or city you're requesting to show the weather conditions using [OpenWeather](https://openweathermap.org/api)

To run the bot install all necessary packages

```bash
pip install -r requirements.txt
```
Obtain your own OpenWeather/Telegram API Tokens:

`OPEN_WEATHER_API_TOKEN`

`TELEGRAM_API_TOKEN`

Then execute ```server.py```

```bash
python server.py
```

This Bot supports Docker:

In order to launch Bot run commands as follows:
```bash
docker build -t tgweather ./
docker run -d --name tgbot tgweather
```
**NOTE:** First fill in Tokens in `Dockerfile`

You can check out how it works finding **@NeedWeatherInPlaceBot** in Telegram
