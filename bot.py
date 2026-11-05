import asyncio
import logging
import sys
import json
import random
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = "8329580330:AAHzPc0dUnnXfT-AwWX7aT7zYqRqBNrK1a4"
DATA_FILE = "data.json"

# Список кіноцитат англійською мовою
MOVIE_QUOTES = [
    "Cinema is a matter of what's in the frame and what's out. - Martin Scorsese",
    "Talking about cinematography is like dancing about architecture. - Richard Linklater",
    "Every great film should seem new every time you see it. - Roger Ebert",
    "If it can be written, or thought, it can be filmed. - Stanley Kubrick",
    "Cinema is the most beautiful fraud in the world. - Jean-Luc Godard"
]

def read_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def write_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функція автоматичного розрахунку статусу бази на основі середнього рейтингу
def get_cinema_status(films):
    if not films:
        return ""
    try:
        ratings = [float(f.get("rate", 0)) for f in films if f.get("rate")]
        if not ratings:
            return ""
        avg = sum(ratings) / len(ratings)
    except ValueError:
        avg = 3.0
    
    if avg >= 4.5:
        status = "Masterpiece Sanctuary"
    elif avg >= 3.5:
        status = "Pretty Solid Vibes"
    elif avg >= 2.5:
        status = "Average Enjoyer Zone"
    else:
        status = "Literal Garbage Can"
        
    return f"\n--- Current Database Status: {status} (Average Rate: {avg:.1f}/5) ---\n"

class FilmStart(StatesGroup):
    Filmname = State()
    Filmdescription = State()
    Filmrate = State()
    Filmyear = State()
    Filmgenre = State()
    Filmactor = State()

dp = Dispatcher()

# Команда: /start (Привітання користувача та виведення цитати дня)
@dp.message(Command("start"))
async def start_handler(message: Message):
    random_quote = random.choice(MOVIE_QUOTES)
    
    welcome_text = (
        f"Hello! I am a movie bot. Use /films to see the list or /add_film to add a new movie.\n"
        f"You can also use /random to pick a movie.\n\n"
        f"Quote of the day:\n"
        f"\"{html.italic(random_quote)}\""
    )
    await message.answer(welcome_text)

# Команда: /films (Виведення текстового списку фільмів із загальним статусом)
@dp.message(Command("films"))
async def show_films(message: Message):
    film_data = read_data()
    if not film_data:
        await message.answer("No movies found yet. Add one using /add_film")
        return
    
    database_status = get_cinema_status(film_data)
    
    text_lines = ["Movie List:\n"]
    for idx, film in enumerate(film_data, 1):
        text_lines.append(
            f"{idx}. {html.bold(film['name'])} ({film['year']})\n"
            f"Rating: {film.get('rate', 'N/A')}/5\n"
            f"Genre: {film['genre']}\n"
            f"Actors: {film['actors']}\n"
            f"Description: {film['description']}\n"
            "---------------------------"
        )
    
    full_text = "\n".join(text_lines) + f"\n{database_status}"
    await message.answer(full_text)

# Команда: /random (Нова функція: вибір випадкового фільму)
@dp.message(Command("random"))
async def random_film_handler(message: Message):
    film_data = read_data()
    if not film_data:
        await message.answer("No movies found yet. Add one using /add_film")
        return
    
    film = random.choice(film_data)
    text = (
        f"Suggested Movie: {html.bold(film['name'])} ({film['year']})\n"
        f"Rating: {film.get('rate', 'N/A')}/5\n"
        f"Genre: {film['genre']}\n"
        f"Actors: {film['actors']}\n"
        f"Description: {film['description']}"
    )
    await message.answer(text)

# Команда: /add_film (Початок процесу додавання нового фільму через FSM)
@dp.message(Command("add_film"))
async def add_films_handler(message: Message, state: FSMContext):
    await message.answer("Enter movie name:")
    await state.set_state(FilmStart.Filmname)

# Крок FSM: Обробка назви та перехід до опису
@dp.message(FilmStart.Filmname)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(Filmname=message.text)
    await message.answer("Enter description:")
    await state.set_state(FilmStart.Filmdescription)

# Крок FSM: Обробка опису та перехід до оцінки
@dp.message(FilmStart.Filmdescription)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(Filmdescription=message.text)
    await message.answer("Enter movie rating (from 1 to 5):")
    await state.set_state(FilmStart.Filmrate)

# Крок FSM: Перевірка коректності рейтингу та перехід до року
@dp.message(FilmStart.Filmrate)
async def process_rate(message: Message, state: FSMContext):
    rate_value = message.text.strip()
    if not rate_value.isdigit() or not (1 <= int(rate_value) <= 5):
        await message.answer("Please, enter a valid number from 1 to 5:")
        return
        
    await state.update_data(Filmrate=rate_value)
    await message.answer(f"Rating set to: {rate_value}\n\nEnter film year:")
    await state.set_state(FilmStart.Filmyear)

# Крок FSM: Обробка року та перехід до жанру
@dp.message(FilmStart.Filmyear)
async def process_year(message: Message, state: FSMContext):
    await state.update_data(Filmyear=message.text)
    await message.answer("Enter genre:")
    await state.set_state(FilmStart.Filmgenre)

# Крок FSM: Обробка жанру та перехід до акторів
@dp.message(FilmStart.Filmgenre)
async def process_genre(message: Message, state: FSMContext):
    await state.update_data(Filmgenre=message.text.lower())
    await message.answer("Enter actors (separated by comma):")
    await state.set_state(FilmStart.Filmactor)

# Крок FSM: Збереження акторів, формування структури фільму та запис у JSON
@dp.message(FilmStart.Filmactor)
async def process_actors(message: Message, state: FSMContext):
    await state.update_data(Filmactor=message.text)
    user_data = await state.get_data()
    
    new_film = {
        "name": user_data["Filmname"],
        "year": user_data["Filmyear"],
        "genre": user_data["Filmgenre"],
        "actors": user_data["Filmactor"],
        "description": user_data["Filmdescription"],
        "rate": user_data["Filmrate"],
        "poster": "None"
    }
    
    current_films = read_data()
    current_films.append(new_film)
    write_data(current_films)
    
    await message.answer("Movie added successfully! Type /films to see the updated list.")
    await state.clear()

# Команда: /search_by_actor (Пошук фільмів за текстовим запитом імені актора)
@dp.message(Command("search_by_actor"))
async def search_by_actor_handler(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /search_by_actor Tom Cruise")
        return
        
    query = args[1].lower()
    film_data = read_data()
    found_films = []
    
    for film in film_data:
        if query in film["actors"].lower() or query in film.get("description", "").lower():
            found_films.append(f"- {html.bold(film['name'])} ({film['year']})")
            
    if found_films:
        response_text = "Found movies:\n" + "\n".join(found_films)
        await message.answer(response_text)
    else:
        await message.answer("No films found.")

async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
