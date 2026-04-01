import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from flask import Flask
import threading

# Создаём веб-сервер для Render
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running!"

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (замените на свой)
TOKEN = "7731941666:AAEgb1zKlsef7WjMfC0rD_5RnGhnZkdDg2s"

# Создаем бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определяем состояния
class States(StatesGroup):
    from_decimal_number = State()
    from_decimal_base = State()
    to_decimal_number = State()
    to_decimal_base = State()
    arithmetic_first = State()
    arithmetic_first_base = State()
    arithmetic_operation = State()
    arithmetic_second = State()
    arithmetic_second_base = State()
    arithmetic_result_base = State()

# Функции перевода
def from_decimal(num, base):
    if num == 0:
        return "0"
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    n = abs(num)
    while n > 0:
        result = digits[n % base] + result
        n //= base
    return ("-" if num < 0 else "") + result

def to_decimal(num, base):
    if num == 0:
        return 0
    result = 0
    power = 0
    n = abs(num)
    while n > 0:
        result += (n % 10) * (base ** power)
        n //= 10
        power += 1
    return -result if num < 0 else result

def calculate(num1, base1, num2, base2, op, result_base):
    def to_dec(x, b):
        res = 0
        p = 0
        xa = abs(x)
        while xa > 0:
            res += (xa % 10) * (b ** p)
            xa //= 10
            p += 1
        return -res if x < 0 else res
    
    d1 = to_dec(num1, base1)
    d2 = to_dec(num2, base2)
    
    if op == '+':
        res = d1 + d2
    elif op == '-':
        res = d1 - d2
    elif op == '*':
        res = d1 * d2
    else:
        if d2 == 0:
            return "Ошибка: деление на 0"
        res = d1 // d2
    
    if res == 0:
        return "0"
    
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    ra = abs(res)
    while ra > 0:
        result = digits[ra % result_base] + result
        ra //= result_base
    return ("-" if res < 0 else "") + result

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Из десятичной")],
        [KeyboardButton(text="📥 В десятичную")],
        [KeyboardButton(text="🧮 Арифметика")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

operation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕"), KeyboardButton(text="➖")],
        [KeyboardButton(text="✖️"), KeyboardButton(text="➗")],
        [KeyboardButton(text="🔙 Назад")]
    ],
    resize_keyboard=True
)

def safe_int(s):
    try:
        if isinstance(s, str):
            s = s.strip()
        return int(s)
    except (ValueError, TypeError):
        return None

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Я бот для перевода чисел и арифметических операций.\n"
        "Выберите действие:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📌 Доступные команды:\n"
        "/start - главное меню\n\n"
        "📝 Примеры:\n"
        "• Из десятичной: 42 → 2 → 101010\n"
        "• В десятичную: 1010 (2) → 10\n"
        "• Арифметика: 101 (2) + 10 (8) → 13",
        reply_markup=main_keyboard
    )

@dp.message()
async def handle_message(message: Message, state: FSMContext):
    text = message.text.strip()
    current_state = await state.get_state()
    
    # Обработка кнопок меню
    if text == "📤 Из десятичной":
        await state.set_state(States.from_decimal_number)
        await message.answer("Введите число:", reply_markup=types.ReplyKeyboardRemove())
        return
    elif text == "📥 В десятичную":
        await state.set_state(States.to_decimal_number)
        await message.answer("Введите число:", reply_markup=types.ReplyKeyboardRemove())
        return
    elif text == "🧮 Арифметика":
        await state.set_state(States.arithmetic_first)
        await message.answer("Введите первое число:", reply_markup=types.ReplyKeyboardRemove())
        return
    elif text == "❓ Помощь":
        await cmd_help(message)
        return
    elif text == "🔙 Назад":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_keyboard)
        return
    
    try:
        if current_state == States.from_decimal_number.state:
            num = safe_int(text)
            if num is None:
                await message.answer("❌ Введите целое число!")
                return
            await state.update_data(number=num)
            await state.set_state(States.from_decimal_base)
            await message.answer("Введите систему счисления (2-36):")
            
        elif current_state == States.from_decimal_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Введите число от 2 до 36!")
                return
            data = await state.get_data()
            result = from_decimal(data['number'], base)
            await message.answer(f"✅ Результат: {result}", reply_markup=main_keyboard)
            await state.clear()
            
        elif current_state == States.to_decimal_number.state:
            num = safe_int(text)
            if num is None or num < 0:
                await message.answer("❌ Введите неотрицательное число!")
                return
            await state.update_data(number=num)
            await state.set_state(States.to_decimal_base)
            await message.answer("Введите систему счисления (2-36):")
            
        elif current_state == States.to_decimal_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Введите число от 2 до 36!")
                return
            data = await state.get_data()
            number = data['number']
            
            valid = True
            temp = number
            while temp > 0:
                if temp % 10 >= base:
                    valid = False
                    break
                temp //= 10
            
            if not valid and number != 0:
                await message.answer(f"❌ Недопустимые цифры для системы {base}", reply_markup=main_keyboard)
                await state.clear()
                return
            
            result = to_decimal(number, base)
            await message.answer(f"✅ Результат: {result}", reply_markup=main_keyboard)
            await state.clear()
            
        elif current_state == States.arithmetic_first.state:
            num = safe_int(text)
            if num is None:
                await message.answer("❌ Введите целое число!")
                return
            await state.update_data(num1=num)
            await state.set_state(States.arithmetic_first_base)
            await message.answer("Введите систему первого числа (2-36):")
            
        elif current_state == States.arithmetic_first_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Введите число от 2 до 36!")
                return
            await state.update_data(base1=base)
            await state.set_state(States.arithmetic_operation)
            await message.answer("Выберите операцию:", reply_markup=operation_keyboard)
            
        elif current_state == States.arithmetic_operation.state:
            op_map = {"➕": "+", "➖": "-", "✖️": "*", "➗": "/"}
            if text in op_map:
                await state.update_data(operation=op_map[text])
                await state.set_state(States.arithmetic_second)
                await message.answer("Введите второе число:", reply_markup=types.ReplyKeyboardRemove())
            else:
                await message.answer("Выберите операцию из меню!", reply_markup=operation_keyboard)
            
        elif current_state == States.arithmetic_second.state:
            num = safe_int(text)
            if num is None:
                await message.answer("❌ Введите целое число!")
                return
            await state.update_data(num2=num)
            await state.set_state(States.arithmetic_second_base)
            await message.answer("Введите систему второго числа (2-36):")
            
        elif current_state == States.arithmetic_second_base.state:
            base = safe_int(text)
            if base is None or base < 2 or base > 36:
                await message.answer("❌ Введите число от 2 до 36!")
                return
            await state.update_data(base2=base)
            await state.set_state(States.arithmetic_result_base)
            await message.answer("Введите систему для результата (2-36):")
            
        elif current_state == States.arithmetic_result_base.state:
            res_base = safe_int(text)
            if res_base is None or res_base < 2 or res_base > 36:
                await message.answer("❌ Введите число от 2 до 36!")
                return
            data = await state.get_data()
            result = calculate(
                data['num1'], data['base1'],
                data['num2'], data['base2'],
                data['operation'], res_base
            )
            await message.answer(f"✅ Результат: {result}", reply_markup=main_keyboard)
            await state.clear()
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=main_keyboard)
        await state.clear()

def main():
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    # Запускаем бота
    print("🚀 Бот запущен!")
    print(f"🤖 Бот: @{asyncio.run(bot.get_me()).username}")
    print("🎯 Готов к работе!")
    
    dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
