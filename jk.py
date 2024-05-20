import telebot
from telebot import types
import sqlite3
import requests
import g4f
from g4f.client import Client

def get_db_connection():
    conn = sqlite3.connect('cities.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS user_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, city TEXT, temperature TEXT, gender TEXT)")
    conn.commit()
    return conn

def save_user_request(username, city, temperature, gender):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_requests (username, city, temperature, gender) VALUES (?, ?, ?, ?)", (username, city, temperature, gender))
    conn.commit()
    conn.close()

def get_user_requests(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT city, temperature, gender FROM user_requests WHERE username = ?", (username,))
    requests = cursor.fetchall()
    conn.close()
    return requests

def get_cities():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT city_name FROM cities")
    cities = [city[0] for city in cursor.fetchall()]
    conn.close()
    return cities

TOKEN = '6882167184:AAFO94HQVBWtZ9GRnB89AgHIz8Z9veNVY6A'
bot = telebot.TeleBot(TOKEN)
user_info = {}
@bot.message_handler(func=lambda message: message.text == 'Новый запрос')
def new_request(message):
    send_welcome(message)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_info[message.from_user.id] = {'username': message.from_user.username}
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button_male = types.KeyboardButton('Мужской')
    button_female = types.KeyboardButton('Женский')
    button_history = types.KeyboardButton('Показать историю запросов')
    markup.add(button_male, button_female, button_history)
    bot.send_message(message.chat.id, "Выберите ваш пол или просмотрите историю:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Показать историю запросов')
def show_history(message):
    username = user_info.get(message.from_user.id, {}).get('username')
    if username:
        requests = get_user_requests(username)
        history = '\n'.join([f"Город: {r[0]}, Температура: {r[1]}, Пол: {r[2]}" for r in requests])
        bot.reply_to(message, history if history else "Нет истории запросов.")
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text in ['Мужской', 'Женский'])
def gender_chosen(message):
    user_info[message.from_user.id]['gender'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    cities = get_cities()
    for city in cities:
        markup.add(types.KeyboardButton(city))
    bot.send_message(message.chat.id, "Выберите ваш город или введите его вручную:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text)
def city_chosen(message):
    city = message.text
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&lang=ru&appid=79d1ca96933b0328e1c7e3e7a26cb347'
    weather_data = requests.get(url).json()
    if 'main' in weather_data and 'temp' in weather_data['main']:
        temperature = str(round(weather_data['main']['temp']))
        pog = f'Ответь на русском. В городе {city} {temperature}°C, пол: {user_info[message.from_user.id]["gender"]}. Как мне одеться для такой погоды? Ответь на русском '
        save_user_request(user_info[message.from_user.id]['username'], city, temperature, user_info[message.from_user.id]['gender'])
        client = Client()
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{"role": "user", "content": pog}]
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton('Новый запрос'))
        bot.reply_to(message, response.choices[0].message.content if response.choices else "Не удалось получить ответ от AI.", reply_markup=markup)
    else:
        bot.reply_to(message, "Не удалось получить данные о погоде или город не найден.")


bot.polling()
